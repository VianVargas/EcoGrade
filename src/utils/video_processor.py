import cv2
import torch
import time
import numpy as np
from ultralytics import YOLO
import threading
from queue import Queue
import pandas as pd
import uuid
import os
from datetime import datetime
import sqlite3
from pathlib import Path
import math

def detect_residue_colors(frame):
    if frame is None or frame.size == 0:
        return None, None

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    lower_residue = np.array([5, 50, 50])
    upper_residue = np.array([25, 255, 200])
    lower_margin = np.array([5, int(50 * 0.85), int(50 * 0.85)])
    upper_margin = np.array([25, 255, 200])

    residue_mask = cv2.inRange(hsv, lower_residue, upper_residue)
    margin_mask = cv2.inRange(hsv, lower_margin, upper_margin)
    combined_mask = cv2.addWeighted(residue_mask, 1.0, margin_mask, 0.3, 0)

    kernel = np.ones((7, 7), np.uint8)
    combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_OPEN, kernel)
    combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel)
    combined_mask = cv2.GaussianBlur(combined_mask, (11, 11), 0)

    contours, _ = cv2.findContours(combined_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    overlay = frame.copy()
    overlay[combined_mask > 0] = (42, 42, 165)
    alpha = 0.4
    residue_detection = cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)

    for contour in contours:
        if cv2.contourArea(contour) > 100:
            x, y, w, h = cv2.boundingRect(contour)
            cv2.rectangle(residue_detection, (x, y), (x + w, y + h), (42, 42, 165), 1)

    return residue_detection, combined_mask

def calculate_residue_score(residue_mask, frame_area):
    residue_pixels = cv2.countNonZero(residue_mask)
    residue_percentage = (residue_pixels / frame_area) * 100
    return residue_percentage

def detect_transparency(frame, mask, background=None, debug=True):
    if mask is None or np.count_nonzero(mask) < 50:
        if debug: print("[Transparency/Opacity] Skipped: Invalid or too small mask")
        return frame, '-'

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    masked_gray = cv2.bitwise_and(gray, gray, mask=mask)
    masked_hsv = cv2.bitwise_and(hsv, hsv, mask=mask)

    gray_pixels = masked_gray[mask > 0]
    sat_pixels = masked_hsv[..., 1][mask > 0]
    val_pixels = masked_hsv[..., 2][mask > 0]

    mean_brightness = np.mean(gray_pixels)
    val_mean = np.mean(val_pixels)
    val_std = np.std(val_pixels)
    sat_mean = np.mean(sat_pixels)

    # Whiteness penalty (white opaque plastics)
    is_bright = mean_brightness > 180
    is_low_saturation = sat_mean < 40
    is_val_inconsistent = val_std > 30

    whiteness_penalty = 0
    if is_bright and is_low_saturation and is_val_inconsistent:
        whiteness_penalty = 25

    # Normalized metrics
    norm_brightness = mean_brightness / 255
    norm_val_std = 1 - (val_std / 128)
    norm_sat = 1 - (sat_mean / 255)

    opacity_score = (
        norm_brightness * 0.15 +
        norm_sat * 0.4 +
        norm_val_std * 0.45
    ) * 100

    opacity_score -= whiteness_penalty
    opacity_score = max(opacity_score, 0)

    transparency_score = 0
    black_bg_correction = 0

    if background is not None:
        # Check if background is mostly black in mask region
        bg_gray = cv2.cvtColor(background, cv2.COLOR_BGR2GRAY)
        bg_pixels = bg_gray[mask > 0]
        mean_bg_brightness = np.mean(bg_pixels)

        if mean_bg_brightness < 30:
            # Black background detected
            black_bg_correction = 20  # adjust as needed

        hsv_bg = cv2.cvtColor(background, cv2.COLOR_BGR2HSV)
        bg_hue = hsv_bg[..., 0][mask > 0].astype(np.float32)
        bg_val = hsv_bg[..., 2][mask > 0].astype(np.float32)
        frame_hue = masked_hsv[..., 0][mask > 0].astype(np.float32)
        frame_val = val_pixels.astype(np.float32)

        hue_diff = np.minimum(np.abs(frame_hue - bg_hue), 180 - np.abs(frame_hue - bg_hue))
        hue_similarity = 100 - np.mean(hue_diff) / 90 * 100
        val_diff = np.abs(frame_val - bg_val)
        val_similarity = 100 - np.mean(val_diff) / 255 * 100

        transparency_score = 0.4 * hue_similarity + 0.6 * val_similarity

    # Blend scores with black bg correction
    final_score = 0.5 * opacity_score + 0.5 * transparency_score + black_bg_correction
    final_score = min(final_score, 100)  # cap max at 100

    if debug:
        print(f"[Opacity] Bright: {mean_brightness:.1f}, Sat: {sat_mean:.1f}, Val Std: {val_std:.1f}")
        print(f"[Whiteness Penalty]: {whiteness_penalty}")
        if background is not None:
            print(f"[BG Brightness]: {mean_bg_brightness:.1f}, Black BG Corr: {black_bg_correction}")
            print(f"[Transparency Score]: {transparency_score:.1f}")
        else:
            print("[Transparency] Skipped")
        print(f"[Final Score]: {final_score:.1f}")

    # Adjusted thresholds for black background scenario
    clear_threshold = 60
    semi_opaque_threshold = 40

    if final_score > clear_threshold:
        level = 'Clear'
        color = (0, 255, 0)
    elif final_score > semi_opaque_threshold:
        level = 'Semi-Opaque'
        color = (0, 165, 255)
    else:
        level = 'Opaque'
        color = (0, 0, 255)

    overlay = frame.copy()
    colored_mask = np.zeros_like(frame)
    colored_mask[mask > 0] = color
    overlay = cv2.addWeighted(overlay, 1, colored_mask, 0.3, 0)

    scan_y = int((frame.shape[0] * (0.5 + 0.5 * np.sin(time.time() * 3))))
    scan_line = np.zeros_like(mask)
    cv2.line(scan_line, (0, scan_y), (frame.shape[1], scan_y), 255, 2)
    scan_line = cv2.bitwise_and(scan_line, mask)
    overlay[scan_line > 0] = color

    return overlay, level

def classify_output(waste_type, residue_score, transparency_level):
    if waste_type == 'Tin-Steel Can':
        if residue_score < 20:
            return 'High Value Recyclable'
        else:
            return 'Low Value'

    # Step 1: Scoring dictionaries
    plastic_scores = {
        'Tin Can': 10,
        'PET Bottle': 10,
        'HDPE Plastic, Squeeze-Tube': 8,
        'HDPE Plastic': 9,
        'PP': 5,
        'LDPE': 3,
        'UHT Box': 4  # Mixed multilayer composite (cartons)
    }

    opacity_scores = {
        'Clear': 10,
        'Semi-Opaque': 7,
        'Opaque': 3
    }

    # Step 2: Residue Bonus-Malus
    if residue_score <= 1:
        residue_clean_score = 10
    elif residue_score <= 5:
        residue_clean_score = 7
    elif residue_score <= 10:
        residue_clean_score = 3
    else:
        residue_clean_score = 0

    # Step 3: Retrieve individual scores
    pt_score = plastic_scores.get(waste_type, 1)
    op_score = opacity_scores.get(transparency_level, 1)

    # Step 4: Weights
    w_pt = 0.40
    w_res = 0.35
    w_op = 0.25

    # Step 5: Final weighted score
    final_score = (pt_score * w_pt) + (residue_clean_score * w_res) + (op_score * w_op)

    # Print breakdown
    print(f"\nClassification Breakdown:")
    print(f"  - Waste Type: '{waste_type}' → Score: {pt_score} × {w_pt} = {pt_score * w_pt:.2f}")
    print(f"  - Residue Score: {residue_score} → Cleanliness Score: {residue_clean_score} × {w_res} = {residue_clean_score * w_res:.2f}")
    print(f"  - Transparency: '{transparency_level}' → Score: {op_score} × {w_op} = {op_score * w_op:.2f}")
    print(f"  → Final Score: {final_score:.2f}")

    # Step 6: Classification thresholds
    if final_score >= 8.0:
        return 'High Value Recyclable'
    elif final_score >= 4.0:
        return 'Low Value'
    else:
        return 'Rejects'

def save_detection_to_excel(detection_data, excel_path='detections.xlsx'):
    """
    Save a detection result to an Excel file. If the file doesn't exist, create it with headers.
    detection_data: dict with keys: id, timestamp, waste_type, result, and other criteria.
    """
    columns = [
        'id', 'timestamp', 'waste_type', 'result', 'transparency', 'contamination_score', 'classification'
    ]
    # Add any extra keys from detection_data
    for k in detection_data.keys():
        if k not in columns:
            columns.append(k)
    row = {col: detection_data.get(col, '') for col in columns}
    if os.path.exists(excel_path):
        df = pd.read_excel(excel_path)
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    else:
        df = pd.DataFrame([row], columns=columns)
    df.to_excel(excel_path, index=False)

class VideoProcessor:
    _instance = None
    _camera = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(VideoProcessor, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.cap = None
            self.model = None
            self.frame_queue = Queue(maxsize=2)
            self.running = False
            self.processing = False
            self.last_boxes = []
            self.detection_start_time = None
            self.criteria_met = False
            self.last_classification = '-'
            self.current_contamination_score = 0
            self.background = None
            self.background_captured = False
            self.animation_time = 0
            self.zoom_factor = 1.0
            self.initialized = True
            self.latest_result = None
            # --- New for object tracking ---
            self.object_trackers = {}  # id: {centroid, timer, state, result}
            self.next_object_id = 1
            self.finalized_ids = set()
    
    def initialize(self):
        if not VideoProcessor._initialized:
            # Only try the default camera (index 0) for fastest startup
            print("Trying to connect to camera index 0...")
            VideoProcessor._camera = cv2.VideoCapture(0)
            if not VideoProcessor._camera.isOpened():
                raise Exception("Could not connect to camera at index 0. Please check your camera connection.")
            # Set camera properties immediately
            try:
                VideoProcessor._camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                VideoProcessor._camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                VideoProcessor._camera.set(cv2.CAP_PROP_FPS, 30)
                VideoProcessor._camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                actual_width = VideoProcessor._camera.get(cv2.CAP_PROP_FRAME_WIDTH)
                actual_height = VideoProcessor._camera.get(cv2.CAP_PROP_FRAME_HEIGHT)
                print(f"Camera resolution set to: {actual_width}x{actual_height}")
            except Exception as e:
                print(f"Warning: Could not set all camera properties: {str(e)}")
            
            # Initialize model
            try:
                self.model = YOLO("best.pt")
                self.model.to('cuda' if torch.cuda.is_available() else 'cpu')
                print("Model loaded successfully")
            except Exception as e:
                raise Exception(f"Failed to load YOLO model: {str(e)}")
            
            # Capture initial background
            try:
                ret, frame = VideoProcessor._camera.read()
                if ret:
                    self.background = frame.copy()
                    self.background_captured = True
                    print("Initial background captured")
                else:
                    print("Warning: Could not capture initial background")
            except Exception as e:
                print(f"Warning: Error capturing initial background: {str(e)}")
            
            VideoProcessor._initialized = True
        
        self.cap = VideoProcessor._camera
    
    def start(self):
        if not self.running:
            self.running = True
            self.capture_thread = threading.Thread(target=self._capture_frames, daemon=True)
            self.process_thread = threading.Thread(target=self._process_frames, daemon=True)
            self.capture_thread.start()
            self.process_thread.start()
    
    def stop(self):
        self.running = False
        if VideoProcessor._camera is not None:
            VideoProcessor._camera.release()
            VideoProcessor._camera = None
            VideoProcessor._initialized = False
    
    def _capture_frames(self):
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                if not self.frame_queue.full():
                    self.frame_queue.put(frame)
            time.sleep(0.01)  # Prevent CPU overload
            
    def add_detection_animation(self, frame, detected, boxes=None):
        # Create a copy of the frame
        animated_frame = frame.copy()
        
        if detected and boxes:
            for x1, y1, x2, y2, cls_id, conf in boxes:
                # Calculate border thickness based on sine wave
                border_thickness = int(5 + 3 * np.sin(self.animation_time * 6))
                
                # Create border color based on classification
                if self.last_classification == 'High Value Recyclable':
                    border_color = (0, 255, 0)  # Green
                elif self.last_classification == 'Low Value':
                    border_color = (0, 165, 255)  # Orange
                else:
                    border_color = (0, 0, 255)  # Red
                
                # Draw animated border
                cv2.rectangle(animated_frame, (x1, y1), (x2, y2), border_color, border_thickness)
                
                # Add pulsing corner markers
                corner_size = min(20, (x2 - x1) // 3)  # Adjust corner size based on box size
                corner_thickness = 2
                alpha = 0.5 + 0.5 * np.sin(self.animation_time * 4)  # Pulsing alpha
                
                # Top-left corner
                cv2.line(animated_frame, (x1, y1 + corner_size), (x1, y1), border_color, corner_thickness)
                cv2.line(animated_frame, (x1, y1), (x1 + corner_size, y1), border_color, corner_thickness)
                
                # Top-right corner
                cv2.line(animated_frame, (x2 - corner_size, y1), (x2, y1), border_color, corner_thickness)
                cv2.line(animated_frame, (x2, y1), (x2, y1 + corner_size), border_color, corner_thickness)
                
                # Bottom-left corner
                cv2.line(animated_frame, (x1, y2 - corner_size), (x1, y2), border_color, corner_thickness)
                cv2.line(animated_frame, (x1, y2), (x1 + corner_size, y2), border_color, corner_thickness)
                
                # Bottom-right corner
                cv2.line(animated_frame, (x2 - corner_size, y2), (x2, y2), border_color, corner_thickness)
                cv2.line(animated_frame, (x2, y2), (x2, y2 - corner_size), border_color, corner_thickness)
                
                # Add a subtle glow effect
                glow = np.zeros_like(frame)
                cv2.rectangle(glow, (x1, y1), (x2, y2), border_color, border_thickness + 4)
                glow = cv2.GaussianBlur(glow, (15, 15), 0)
                animated_frame = cv2.addWeighted(animated_frame, 1, glow, alpha * 0.3, 0)
        
        # Update animation time
        self.animation_time += 0.1
        
        return animated_frame

    def add_scan_effect(self, frame, is_tin=False, boxes=None):
        # Create a copy of the frame
        scan_frame = frame.copy()
        height, width = frame.shape[:2]
        
        if boxes and not is_tin:
            for x1, y1, x2, y2, cls_id, conf in boxes:
                # Calculate box dimensions
                box_height = y2 - y1
                box_width = x2 - x1
                
                # Create scanning line within the box
                scan_y = y1 + int(box_height * (0.5 + 0.5 * np.sin(self.animation_time * 3)))
                
                # Create gradient mask for the box area
                mask = np.zeros((box_height, box_width), dtype=np.float32)
                for y in range(box_height):
                    # Calculate distance from scan line
                    dist = abs(y - (scan_y - y1))
                    # Create smooth gradient
                    mask[y, :] = np.exp(-dist/30) * (0.5 + 0.5 * np.sin(self.animation_time * 4))
                
                # Create colored overlay for the box area
                overlay = np.zeros((box_height, box_width, 3), dtype=np.uint8)
                overlay[mask > 0] = (0, 165, 255)  # Orange color for opacity scan
                
                # Blend with original frame in the box area
                scan_frame[y1:y2, x1:x2] = cv2.addWeighted(
                    scan_frame[y1:y2, x1:x2], 1,
                    overlay, 0.3, 0
                )
                
                # Add scanning line within the box
                cv2.line(scan_frame, (x1, scan_y), (x2, scan_y), (0, 165, 255), 2)
                
                # Add pulsing dots at the ends of the scan line
                dot_radius = int(3 + 2 * np.sin(self.animation_time * 4))
                cv2.circle(scan_frame, (x1, scan_y), dot_radius, (0, 165, 255), -1)
                cv2.circle(scan_frame, (x2-1, scan_y), dot_radius, (0, 165, 255), -1)
        
        return scan_frame

    def set_zoom(self, zoom_factor):
        """Set the zoom factor for the camera"""
        self.zoom_factor = max(0.5, min(2.0, zoom_factor))  # Limit zoom between 0.5x and 2.0x
        if self.cap is not None:
            try:
                # Try to set zoom through camera properties if supported
                self.cap.set(cv2.CAP_PROP_ZOOM, self.zoom_factor)
            except:
                pass  # If camera doesn't support direct zoom, we'll handle it in frame processing

    def _get_centroid(self, x1, y1, x2, y2):
        return ((x1 + x2) // 2, (y1 + y2) // 2)

    def _match_object(self, centroid, threshold=50):
        # Find existing object ID by centroid proximity
        for obj_id, data in self.object_trackers.items():
            prev_centroid = data['centroid']
            if math.hypot(centroid[0] - prev_centroid[0], centroid[1] - prev_centroid[1]) < threshold:
                return obj_id
        return None

    def _process_frames(self):
        while self.running:
            if not self.frame_queue.empty() and not self.processing:
                self.processing = True
                frame = self.frame_queue.get()
                try:
                    # Process frame
                    height, width = frame.shape[:2]
                    crop_factor = 1
                    crop_width = int(width * crop_factor)
                    crop_height = int(height * crop_factor)
                    start_x = (width - crop_width) // 2
                    start_y = (height - crop_height) // 2
                    frame_cropped = frame[start_y:start_y + crop_height, start_x:start_x + crop_width]

                    # Initialize all output frames with the cropped frame
                    model_output = frame_cropped.copy()
                    gray_contrast = cv2.cvtColor(frame_cropped, cv2.COLOR_BGR2GRAY)
                    gray_contrast = cv2.equalizeHist(gray_contrast)  # Enhance contrast
                    mask_display = cv2.cvtColor(gray_contrast, cv2.COLOR_GRAY2BGR)
                    transparency_vis = frame_cropped.copy()
                    residue_detection = frame_cropped.copy()
                    
                    # Run YOLO detection
                    results = self.model(frame_cropped, conf=0.7, verbose=False)
                    
                    current_boxes = []
                    object_detected = False
                    object_mask = np.zeros((frame_cropped.shape[0], frame_cropped.shape[1]), dtype=np.uint8)
                    current_waste_type = '-'
                    transparency_level = '-'
                    classification = '-'
                    current_obj_id = None
                    
                    detected_ids = set()
                    now = time.time()

                    # Process detection results
                    for result in results:
                        boxes = result.boxes
                        for box in boxes:
                            cls_id = int(box.cls.cpu().numpy()[0])
                            conf = float(box.conf.cpu().numpy()[0])
                            x1, y1, x2, y2 = map(int, box.xyxy.cpu().numpy()[0])
                            centroid = self._get_centroid(x1, y1, x2, y2)
                            obj_id = self._match_object(centroid)
                            if obj_id is None:
                                obj_id = self.next_object_id
                                self.next_object_id += 1
                                self.object_trackers[obj_id] = {
                                    'centroid': centroid,
                                    'timer': now,
                                    'state': 'analyzing',
                                    'result': None
                                }
                            else:
                                self.object_trackers[obj_id]['centroid'] = centroid
                            detected_ids.add(obj_id)
                            current_obj_id = obj_id  # Store the current object ID
                            # If already finalized, skip
                            if obj_id in self.finalized_ids:
                                continue
                            # Waste type mapping
                            waste_types = {
                                0: 'HDPE Plastic',
                                1: 'PP',
                                2: 'PET Bottle',
                                3: 'PP',
                                4: 'LDPE',
                                5: 'HDPE Plastic',
                                6: 'Tin-Steel Can',
                                7: 'Mixed Trash'
                            }
                            current_waste_type = waste_types.get(cls_id, 'Unknown')
                            object_detected = True
                            
                            # Draw bounding box on model output
                            box_color = (0, 255, 0)
                            cv2.rectangle(model_output, (x1, y1), (x2, y2), box_color, 4)
                            current_boxes.append((x1, y1, x2, y2, cls_id, conf))
                            
                            # Create mask
                            if hasattr(box, 'masks') and box.masks is not None:
                                mask = box.masks.cpu().numpy()[0]
                                object_mask = (mask * 255).astype(np.uint8)
                            else:
                                object_mask[y1:y2, x1:x2] = 255
                            
                            # Process residue detection
                            cropped_frame = frame_cropped[y1:y2, x1:x2]
                            if cropped_frame.size > 0:
                                residue_detection_cropped, residue_mask = detect_residue_colors(cropped_frame)
                                if residue_detection_cropped is not None:
                                    residue_detection[y1:y2, x1:x2] = residue_detection_cropped
                                    bbox_area = (x2 - x1) * (y2 - y1)
                                    contamination_score = calculate_residue_score(residue_mask, bbox_area)
                                    self.current_contamination_score = contamination_score
                                    mask_display = cv2.cvtColor(residue_mask, cv2.COLOR_GRAY2BGR)
                    
                    # Process transparency
                    if object_detected and current_waste_type != 'Tin-Steel Can':
                        transparency_vis, transparency_level = detect_transparency(frame_cropped, object_mask, self.background)
                        transparency_vis = self.add_scan_effect(transparency_vis, is_tin=False, boxes=current_boxes)
                    else:
                        transparency_vis = model_output.copy()
                        transparency_level = 'N/A' if current_waste_type == 'Tin-Steel Can' else '-'
                        if current_waste_type == 'Tin-Steel Can':
                            transparency_vis = self.add_scan_effect(transparency_vis, is_tin=True, boxes=current_boxes)
                    
                    # Update classification
                    if object_detected:
                        criteria_met = (current_waste_type != '-' and 
                                     (transparency_level != '-' or current_waste_type == 'Tin-Steel Can'))
                        current_time = time.time()
                        
                        if criteria_met:
                            if self.detection_start_time is None:
                                self.detection_start_time = current_time
                                classification = 'Analyzing...'
                            elif current_time - self.detection_start_time >= 0.5:
                                classification = classify_output(current_waste_type, self.current_contamination_score, transparency_level)
                                self.last_classification = classification
                        else:
                            missing_criteria = []
                            if current_waste_type == '-':
                                missing_criteria.append('Type')
                            if transparency_level == '-' and current_waste_type != 'Tin-Steel Can':
                                missing_criteria.append('Transparency')
                            classification = f"Waiting for: {', '.join(missing_criteria)}"
                            self.detection_start_time = None
                    else:
                        self.detection_start_time = None
                        classification = 'No object detected'
                    
                    # Add animation to model output
                    model_output = self.add_detection_animation(model_output, object_detected, current_boxes)
                    
                    # Ensure all frames are valid and properly sized
                    for frame_name, frame in [('model', model_output), ('opacity', transparency_vis),
                                            ('residue', residue_detection), ('mask', mask_display)]:
                        if frame is None or frame.size == 0:
                            frame = frame_cropped.copy()
                    
                    # Prepare result with all frames
                    result = {
                        'frames': {
                            'model': model_output,
                            'opacity': transparency_vis,
                            'residue': residue_detection,
                            'mask': mask_display
                        },
                        'data': {
                            'id': current_obj_id,
                            'waste_type': current_waste_type,
                            'confidence': conf if object_detected else 0,
                            'contamination': self.current_contamination_score,
                            'transparency': transparency_level,
                            'classification': classification
                        }
                    }
                    self.latest_result = result
                    
                    # 2s analysis window
                    if current_obj_id is not None:
                        tracker = self.object_trackers[current_obj_id]
                        if tracker['state'] == 'analyzing':
                            if now - tracker['timer'] >= 2.0:
                                # Finalize result
                                classification = classify_output(current_waste_type, self.current_contamination_score, transparency_level)
                                tracker['result'] = {
                                    'id': current_obj_id,
                                    'waste_type': current_waste_type,
                                    'opacity': transparency_level,
                                    'contamination': self.current_contamination_score,
                                    'classification': classification
                                }
                                tracker['state'] = 'finalized'
                                self.finalized_ids.add(current_obj_id)
                                # Store in DB and emit
                                self.emit_detection_result(tracker['result'])
                            else:
                                classification = 'Analyzing...'
                        elif tracker['state'] == 'finalized':
                            classification = tracker['result']['classification']
                    
                except Exception as e:
                    print(f"Error in frame processing: {str(e)}")
                finally:
                    self.processing = False
                    
            time.sleep(0.01)  # Prevent CPU overload

    def emit_detection_result(self, result_data):
        # Assign a timestamp (ID is already assigned)
        result_data['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # Store in DB (implement as needed)
        # save_detection_to_excel(result_data)  # Optionally keep Excel
        # Store in SQLite DB for charts/tables
        self._store_measurement(result_data)
        # ... emit to UI if needed ...

    def _store_measurement(self, result_data):
        # Store in SQLite DB for table/graphs
        db_path = Path('data/measurements.db')
        db_path.parent.mkdir(exist_ok=True)
        conn = sqlite3.connect(str(db_path))
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS detections (
            id TEXT PRIMARY KEY,
            timestamp TEXT,
            waste_type TEXT,
            opacity TEXT,
            contamination REAL,
            classification TEXT
        )''')
        c.execute('''INSERT OR REPLACE INTO detections (id, timestamp, waste_type, opacity, contamination, classification)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (str(result_data['id']), result_data['timestamp'], result_data['waste_type'],
                   result_data['opacity'], float(result_data['contamination']), result_data['classification']))
        conn.commit()
        conn.close()

    def process_frame(self, frame):
        # Detect a new placed object
        if self.last_opacity_scan_time is None or time.time() - self.last_opacity_scan_time >= 2:
            # Perform opacity scan
            opacity_result = self.scan_opacity(frame)
            # Store the result in the database
            self._store_measurement(opacity_result)
            self.last_opacity_scan_time = time.time()
            # Stop detecting this object and count as new ID
            self.current_detection_id += 1
            # Emit the detection result for real-time updates
            self.emit_detection_result(opacity_result)
            return frame, self.current_detection_id
        return frame, None 