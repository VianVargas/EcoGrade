import cv2
import torch
import time
import numpy as np
from ultralytics import YOLO
import threading
from queue import Queue
import pandas as pd
import os
from datetime import datetime
import sqlite3
from pathlib import Path
import math
import random
import string

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

def detect_transparency(frame, bbox):
    try:
        # Extract object and background regions
        x, y, w, h = bbox
        object_region = frame[y:y+h, x:x+w]
        background_region = frame[max(0, y-10):y, x:x+w]

        # Convert to HSV
        object_hsv = cv2.cvtColor(object_region, cv2.COLOR_BGR2HSV)
        background_hsv = cv2.cvtColor(background_region, cv2.COLOR_BGR2HSV)

        # Calculate mean HSV values
        object_mean = cv2.mean(object_hsv)[:3]
        background_mean = cv2.mean(background_hsv)[:3]

        # Calculate differences
        color_intensity = object_mean[1]  # Saturation
        saturation_diff = abs(object_mean[1] - background_mean[1])
        value_diff = abs(object_mean[2] - background_mean[2])

        # Determine if background is dark
        is_dark_bg = background_mean[2] < 50

        # Debug output
        print("\n=== Opacity Detection Debug ===")
        print(f"Color Intensity: {color_intensity:.2f}")
        print(f"Saturation Difference: {saturation_diff:.2f}")
        print(f"Value Difference: {value_diff:.2f}")
        print(f"Object HSV Mean: H={object_mean[0]:.2f}, S={object_mean[1]:.2f}, V={object_mean[2]:.2f}")
        print(f"Background HSV Mean: H={background_mean[0]:.2f}, S={background_mean[1]:.2f}, V={background_mean[2]:.2f}")
        print(f"Dark Background: {is_dark_bg}")

        # Classify based on thresholds
        if is_dark_bg:
            if color_intensity > 45 and value_diff > 120:  # Increased thresholds
                classification = 'Opaque'
                reason = 'dark bg, high color, large diff'
            elif color_intensity > 35 and value_diff > 60:  # Increased thresholds
                classification = 'Semi-Opaque'
                reason = 'dark bg, high color, medium diff'
            else:
                classification = 'Clear'
                reason = 'dark bg, low color, small diff'
        else:
            if color_intensity > 45 and value_diff > 60:  # Increased thresholds
                classification = 'Opaque'
                reason = 'light bg, high color, large diff'
            elif color_intensity > 35 and value_diff > 40:  # Increased thresholds
                classification = 'Semi-Opaque'
                reason = 'light bg, high color, medium diff'
            else:
                classification = 'Clear'
                reason = 'light bg, low color, small diff'

        print(f"Classified as {classification} ({reason})")
        return classification

    except Exception as e:
        print(f"Error in detect_transparency: {str(e)}")
        return 'Unknown'

def classify_output(waste_type, residue_score, transparency):
    # Initialize scores
    waste_type_score = 0
    cleanliness_score = 0
    transparency_score = 0

    # Score waste type with weighted values
    if waste_type == 'PET Bottle':
        waste_type_score = 10  # Highest base score
    elif waste_type == 'HDPE Plastic':
        waste_type_score = 9   # High base score
    elif waste_type == 'LDPE':
        waste_type_score = 5   # Medium-high base score
    elif waste_type == 'PP':
        waste_type_score = 6   # Medium base score
    elif waste_type == 'Tin-Steel Can':
        waste_type_score = 10   # High base score for metal
    elif waste_type == 'Mixed Trash':
        waste_type_score = 3   # Low base score for mixed waste

    # Score cleanliness based on residue score with weighted penalties
    if residue_score < 2:
        cleanliness_score = 10  # Excellent
    elif residue_score < 4:
        cleanliness_score = 8   # Good
    elif residue_score < 6:
        cleanliness_score = 6   # Fair
    elif residue_score < 8:
        cleanliness_score = 4   # Poor
    else:
        cleanliness_score = 2   # Very poor

    # Score transparency with weighted values
    if transparency == 'Clear':
        transparency_score = 10  # Best for recycling
    elif transparency == 'Semi-Opaque':
        transparency_score = 5   # Medium value
    else:
        transparency_score = 2   # Lowest value

    # Calculate weighted sum with adjusted weights
    final_score = (waste_type_score * 0.4) + (cleanliness_score * 0.35) + (transparency_score * 0.25)

    # Apply bonuses and penalties
    if waste_type == 'PET Bottle' and transparency == 'Clear':
        final_score += 1.0  # Bonus for clear PET
    elif waste_type == 'HDPE Plastic' and transparency in ['Clear', 'Semi-Opaque']:
        final_score += 0.5  # Bonus for clear/semi-opaque HDPE
    elif waste_type == 'Tin-Steel Can' and residue_score > 25:
        final_score -= 1.0  # Penalty for heavily contaminated metal

    # Print classification breakdown
    print("\nClassification Breakdown:")
    print(f"  - Waste Type: '{waste_type}' → Score: {waste_type_score} × 0.4 = {waste_type_score * 0.4:.2f}")
    print(f"  - Residue Score: {residue_score} → Cleanliness Score: {cleanliness_score} × 0.35 = {cleanliness_score * 0.35:.2f}")
    print(f"  - Transparency: '{transparency}' → Score: {transparency_score} × 0.25 = {transparency_score * 0.25:.2f}")
    print(f"  → Final Score: {final_score:.2f}")

    # Determine classification based on final score and waste type
    if waste_type == 'PET Bottle':
        if transparency == 'Clear':
            classification = 'High Value'
        else:
            classification = 'Low Value'
    elif waste_type == 'HDPE Plastic':
        if transparency in ['Clear', 'Semi-Opaque']:
            classification = 'High Value' if final_score >= 7.0 else 'Low Value'
        else:
            classification = 'Low Value'
    elif waste_type == 'Tin-Steel Can':
        classification = 'High Value' if residue_score < 25 else 'Low Value'
    else:
        classification = 'High Value' if final_score >= 7.0 else 'Low Value'

    return classification

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
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(VideoProcessor, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, model_path='best.pt'):
        self.model = YOLO(model_path)
        self.is_running = False
        self.current_frame = None
        self.frame_lock = threading.Lock()
        self.detection_interval = 0.1  # Reduced from 0.1 to 0.05 seconds for faster updates
        self.last_detection_time = 0
        self.detection_callback = None
        self.camera = None
        self.frame_count = 0
        self.processing_frame = False
        self.last_detection_result = None
        self.detection_thread = None
        self.detection_running = False
        self.detection_lock = threading.Lock()
        self.frame_skip = 2  # Process every 2nd frame instead of every 3rd
        
        # Tracking variables
        self.tracker = cv2.TrackerCSRT_create()
        self.tracking = False
        self.tracked_bbox = None
        self.tracking_lost_count = 0
        self.max_tracking_lost = 20  # Maximum frames to keep tracking after detection is lost
        self.last_valid_bbox = None
        self.smoothing_factor = 0.7
        self.min_confidence = 0.3
        self.min_iou = 0.3
        self.bbox_history = []
        self.max_history = 5
        self.cap = None
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
        self.object_trackers = {}
        self.next_object_id = 1
        self.finalized_ids = set()
        self._frame_skip_counter = 0
        self.crop_factor = 0.9
        self.frame_size = (640, 480)  # Reduced frame size for faster processing
    
    def initialize(self):
        if not VideoProcessor._initialized:
            print("Trying to connect to camera index 0...")
            VideoProcessor._camera = cv2.VideoCapture(0)
            if not VideoProcessor._camera.isOpened():
                raise Exception("Could not connect to camera at index 0. Please check your camera connection.")
            try:
                # Set optimized resolution for Raspberry Pi
                VideoProcessor._camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                VideoProcessor._camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                VideoProcessor._camera.set(cv2.CAP_PROP_FPS, 30)
                VideoProcessor._camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                VideoProcessor._camera.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)
                VideoProcessor._camera.set(cv2.CAP_PROP_EXPOSURE, -6)
                VideoProcessor._camera.set(cv2.CAP_PROP_GAIN, 100)
                actual_width = VideoProcessor._camera.get(cv2.CAP_PROP_FRAME_WIDTH)
                actual_height = VideoProcessor._camera.get(cv2.CAP_PROP_FRAME_HEIGHT)
                print(f"Camera resolution set to: {actual_width}x{actual_height}")
            except Exception as e:
                print(f"Warning: Could not set all camera properties: {str(e)}")
            try:
                self.model = YOLO("best.pt")
                self.model.to('cpu')  # Force CPU usage
                print("Model loaded successfully")
            except Exception as e:
                raise Exception(f"Failed to load YOLO model: {str(e)}")
            try:
                ret, frame = VideoProcessor._camera.read()
                if ret:
                    # Resize frame for faster processing
                    frame = cv2.resize(frame, self.frame_size)
                    frame = cv2.GaussianBlur(frame, (5, 5), 0)
                    frame = cv2.convertScaleAbs(frame, alpha=1.2, beta=10)
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
        self.latest_result = None  # Clear the latest result
        # Do NOT release the camera or set _initialized to False here
        # Only stop threads and clear results
    
    def release_camera(self):
        # Call this only on app exit
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
                if self.last_classification == 'High Value':
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
        best_match = None
        min_distance = float('inf')
        
        for obj_id, data in self.object_trackers.items():
            prev_centroid = data['centroid']
            distance = math.hypot(centroid[0] - prev_centroid[0], centroid[1] - prev_centroid[1])
            if distance < threshold and distance < min_distance:
                min_distance = distance
                best_match = obj_id
                
        return best_match

    def _generate_unique_id(self):
        # Generate a unique 4-character alphanumeric ID
        while True:
            new_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
            if new_id not in self.object_trackers and new_id not in self.finalized_ids:
                return new_id

    def _process_frames(self):
        while self.running:
            if not self.frame_queue.empty() and not self.processing:
                self._frame_skip_counter += 1
                if self._frame_skip_counter % 3 != 0:  # Process every 3rd frame
                    self.frame_queue.get()
                    continue
                self.processing = True
                frame = self.frame_queue.get()
                try:
                    # Resize frame for faster processing
                    frame = cv2.resize(frame, self.frame_size)
                    
                    # Simplified preprocessing
                    frame = cv2.GaussianBlur(frame, (3, 3), 0)  # Reduced kernel size
                    frame = cv2.convertScaleAbs(frame, alpha=1.2, beta=10)
                    
                    # Process frame
                    height, width = frame.shape[:2]
                    crop_factor = 1
                    crop_width = int(width * crop_factor)
                    crop_height = int(height * crop_factor)
                    start_x = (width - crop_width) // 2
                    start_y = (height - crop_height) // 2
                    frame_cropped = frame[start_y:start_y + crop_height, start_x:start_x + crop_width]

                    # Initialize output frames
                    model_output = frame_cropped.copy()
                    gray_contrast = cv2.cvtColor(frame_cropped, cv2.COLOR_BGR2GRAY)
                    gray_contrast = cv2.equalizeHist(gray_contrast)
                    mask_display = cv2.cvtColor(gray_contrast, cv2.COLOR_GRAY2BGR)
                    transparency_vis = frame_cropped.copy()
                    residue_detection = frame_cropped.copy()
                    
                    # Run YOLO detection with optimized parameters
                    results = self.model(frame_cropped, 
                                      conf=0.45,  # Slightly lower confidence threshold
                                      iou=0.45,   # IOU threshold for NMS
                                      verbose=False,
                                      agnostic_nms=True,
                                      max_det=1)  # Limit to 1 detection
                    
                    current_boxes = []
                    object_detected = False
                    object_mask = np.zeros((frame_cropped.shape[0], frame_cropped.shape[1]), dtype=np.uint8)
                    current_waste_type = '-'
                    transparency_level = '-'
                    classification = '-'
                    current_obj_id = None
                    
                    detected_ids = set()
                    now = time.time()

                    # Process detection results with improved logic
                    for result in results:
                        boxes = result.boxes
                        for box in boxes:
                            cls_id = int(box.cls.cpu().numpy()[0])
                            conf = float(box.conf.cpu().numpy()[0])
                            
                            # Skip low confidence detections
                            if conf < 0.45:  # Increased minimum confidence
                                continue
                                
                            x1, y1, x2, y2 = map(int, box.xyxy.cpu().numpy()[0])
                            
                            # Skip very small detections
                            if (x2 - x1) * (y2 - y1) < 800:  # Increased minimum area threshold
                                continue
                                
                            centroid = self._get_centroid(x1, y1, x2, y2)
                            obj_id = self._match_object(centroid)
                            
                            if obj_id is None:
                                obj_id = self._generate_unique_id()
                                self.object_trackers[obj_id] = {
                                    'centroid': centroid,
                                    'timer': now,
                                    'state': 'analyzing',
                                    'result': None,
                                    'confidence': conf,
                                    'waste_type': None,
                                    'transparency': None,
                                    'detection_count': 0,
                                    'last_update': now,
                                    'stable_count': 0
                                }
                            else:
                                # Update tracking data
                                tracker = self.object_trackers[obj_id]
                                prev_centroid = tracker['centroid']
                                distance = math.hypot(centroid[0] - prev_centroid[0], centroid[1] - prev_centroid[1])
                                
                                # Check if object is stable
                                if distance < 10:  # Small movement threshold
                                    tracker['stable_count'] += 1
                                else:
                                    tracker['stable_count'] = 0
                                
                                # Update confidence if new detection is more confident
                                if conf > tracker.get('confidence', 0):
                                    tracker['confidence'] = conf
                                    tracker['centroid'] = centroid
                                    tracker['last_update'] = now
                            
                            detected_ids.add(obj_id)
                            current_obj_id = obj_id
                            
                            if obj_id in self.finalized_ids:
                                continue
                                
                            # Waste type mapping with improved confidence
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
                            
                            # Only use high confidence detections for waste type
                            if conf > 0.4:
                                current_waste_type = waste_types.get(cls_id, 'Unknown')
                                if current_obj_id:
                                    self.object_trackers[current_obj_id]['waste_type'] = current_waste_type
                            else:
                                current_waste_type = 'Unknown'
                                
                            object_detected = True
                            
                            # Draw bounding box
                            box_color = (0, 255, 0)
                            cv2.rectangle(model_output, (x1, y1), (x2, y2), box_color, 4)
                            current_boxes.append((x1, y1, x2, y2, cls_id, conf))
                            
                            # Create mask with improved accuracy
                            if hasattr(box, 'masks') and box.masks is not None:
                                mask = box.masks.cpu().numpy()[0]
                                object_mask = (mask * 255).astype(np.uint8)
                            else:
                                object_mask[y1:y2, x1:x2] = 255
                            
                            # Process residue detection with improved accuracy
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
                    if object_detected and current_waste_type in ['PET Bottle', 'HDPE Plastic', 'LDPE', 'PP']:
                        transparency_level = detect_transparency(frame, (x1, y1, x2, y2))
                        if transparency_level in ['Clear', 'Semi-Opaque', 'Opaque']:
                            if current_obj_id:
                                self.object_trackers[current_obj_id]['transparency'] = transparency_level
                            if transparency_level == 'Clear':
                                mask_color = (0, 255, 0)
                            elif transparency_level == 'Semi-Opaque':
                                mask_color = (255, 165, 0)
                            else:
                                mask_color = (255, 0, 0)
                            mask_overlay = np.zeros_like(transparency_vis)
                            mask_overlay[object_mask > 0] = mask_color
                            transparency_vis = cv2.addWeighted(transparency_vis, 1, mask_overlay, 0.35, 0)
                            glow = np.zeros_like(transparency_vis)
                            for x1, y1, x2, y2, cls_id, conf in current_boxes:
                                cv2.rectangle(glow, (x1, y1), (x2, y2), mask_color, 18)
                            alpha = 0.18 + 0.12 * np.sin(self.animation_time * 4)
                            glow = cv2.GaussianBlur(glow, (25, 25), 0)
                            transparency_vis = cv2.addWeighted(transparency_vis, 1, glow, alpha, 0)
                            for x1, y1, x2, y2, cls_id, conf in current_boxes:
                                cv2.rectangle(transparency_vis, (x1, y1), (x2, y2), mask_color, 2)
                    else:
                        transparency_vis = model_output.copy()
                        transparency_level = 'N/A' if current_waste_type == 'Tin-Steel Can' else '-'
                        if current_waste_type == 'Tin-Steel Can':
                            transparency_vis = self.add_scan_effect(transparency_vis, is_tin=True, boxes=current_boxes)
                    
                    # Update classification with improved logic
                    if object_detected:
                        criteria_met = (current_waste_type != '-' and 
                                     (transparency_level != '-' or current_waste_type == 'Tin-Steel Can'))
                        current_time = time.time()
                        
                        if criteria_met:
                            if self.detection_start_time is None:
                                self.detection_start_time = current_time
                                classification = 'Analyzing...'
                            elif current_time - self.detection_start_time >= 0.5:
                                # Only classify if object is stable
                                if current_obj_id and self.object_trackers[current_obj_id]['stable_count'] >= 3:
                                    classification = classify_output(current_waste_type, self.current_contamination_score, transparency_level)
                                    self.last_classification = classification
                                else:
                                    classification = 'Analyzing...'
                        else:
                            missing_criteria = []
                            if current_waste_type == '-':
                                missing_criteria.append('Type')
                            if transparency_level == '-' and current_waste_type in ['PET Bottle', 'HDPE Plastic', 'LDPE', 'PP']:
                                missing_criteria.append('Transparency')
                            classification = f"Waiting for: {', '.join(missing_criteria)}"
                            self.detection_start_time = None
                    else:
                        self.detection_start_time = None
                        classification = 'No object detected'
                    
                    # Add animation to model output
                    model_output = self.add_detection_animation(model_output, object_detected, current_boxes)
                    
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
                            'confidence_level': conf if object_detected else 0,
                            'contamination_score': self.current_contamination_score,
                            'transparency': transparency_level,
                            'classification': classification
                        }
                    }
                    self.latest_result = result
                    
                    # 2s analysis window with improved tracking
                    if current_obj_id is not None:
                        tracker = self.object_trackers[current_obj_id]
                        if tracker['state'] == 'analyzing':
                            if now - tracker['timer'] >= 1:
                                classification = classify_output(current_waste_type, self.current_contamination_score, transparency_level)
                                tracker['result'] = {
                                    'id': current_obj_id,
                                    'waste_type': current_waste_type,
                                    'opacity': transparency_level,
                                    'contamination_score': self.current_contamination_score,
                                    'classification': classification,
                                    'confidence_level': conf if object_detected else 0
                                }
                                tracker['state'] = 'finalized'
                                self.finalized_ids.add(current_obj_id)
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
        """Emit detection result and store in database if valid"""
        # Only store valid detections
        if result_data.get('classification') not in [
            'Analyzing...', 'No object detected',
            'Waiting for: Type', 'Waiting for: Transparency',
            'Waiting for: Type, Transparency', 'Unknown', '-'
        ]:
            # Assign a timestamp and generate unique ID
            result_data['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            if 'id' not in result_data:
                result_data['id'] = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
            
            # Store in SQLite DB
            self._store_measurement(result_data)

    def _store_measurement(self, result_data):
        """Store measurement in SQLite database"""
        db_path = Path('data/measurements.db')
        db_path.parent.mkdir(exist_ok=True)
        conn = sqlite3.connect(str(db_path))
        c = conn.cursor()
        
        # Create table if not exists
        c.execute('''CREATE TABLE IF NOT EXISTS detections (
            id TEXT PRIMARY KEY,
            timestamp TEXT,
            waste_type TEXT,
            confidence_level TEXT,
            contamination REAL,
            classification TEXT
        )''')
        
        # Check if this detection already exists (by both ID and timestamp)
        c.execute('SELECT id FROM detections WHERE id = ? OR timestamp = ?', 
                 (str(result_data['id']), result_data['timestamp']))
        if not c.fetchone():
            # Only insert if it's a new detection
            try:
                # Get confidence level from the detection result
                confidence = result_data.get('confidence_level', '0%')
                if isinstance(confidence, float):
                    confidence = f"{confidence:.1f}%"
                
                c.execute('''INSERT INTO detections (id, timestamp, waste_type, confidence_level, contamination, classification)
                             VALUES (?, ?, ?, ?, ?, ?)''',
                          (str(result_data['id']), result_data['timestamp'], result_data['waste_type'],
                           confidence, float(result_data['contamination_score']), result_data['classification']))
                conn.commit()
            except sqlite3.IntegrityError:
                # If there's still a conflict, skip this insertion
                pass
        
        conn.close()

    def _update_tracking(self, frame):
        if not self.tracking or self.tracked_bbox is None:
            return None
        
        success, bbox = self.tracker.update(frame)
        
        if success:
            # Convert bbox to integers
            x, y, w, h = [int(v) for v in bbox]
            
            # Add to history
            self.bbox_history.append((x, y, w, h))
            if len(self.bbox_history) > self.max_history:
                self.bbox_history.pop(0)
            
            # Calculate smoothed bbox
            if len(self.bbox_history) > 0:
                avg_x = int(np.mean([b[0] for b in self.bbox_history]))
                avg_y = int(np.mean([b[1] for b in self.bbox_history]))
                avg_w = int(np.mean([b[2] for b in self.bbox_history]))
                avg_h = int(np.mean([b[3] for b in self.bbox_history]))
                
                # Apply smoothing
                if self.last_valid_bbox is not None:
                    last_x, last_y, last_w, last_h = self.last_valid_bbox
                    x = int(self.smoothing_factor * last_x + (1 - self.smoothing_factor) * avg_x)
                    y = int(self.smoothing_factor * last_y + (1 - self.smoothing_factor) * avg_y)
                    w = int(self.smoothing_factor * last_w + (1 - self.smoothing_factor) * avg_w)
                    h = int(self.smoothing_factor * last_h + (1 - self.smoothing_factor) * avg_h)
                else:
                    x, y, w, h = avg_x, avg_y, avg_w, avg_h
                
                # Ensure minimum size
                w = max(w, 50)
                h = max(h, 50)
                
                # Update last valid bbox
                self.last_valid_bbox = (x, y, w, h)
                self.tracking_lost_count = 0
                
                return (x, y, w, h)
        
        self.tracking_lost_count += 1
        if self.tracking_lost_count > self.max_tracking_lost:
            self.tracking = False
            self.tracked_bbox = None
            self.last_valid_bbox = None
            self.bbox_history.clear()
        
        return None

    def _start_tracking(self, frame, bbox):
        self.tracker = cv2.TrackerCSRT_create()  # Create new tracker instance
        success = self.tracker.init(frame, bbox)
        if success:
            self.tracking = True
            self.tracked_bbox = bbox
            self.last_valid_bbox = bbox
            self.bbox_history = [bbox]
            self.tracking_lost_count = 0
            return True
        return False

    def apply_crop_factor(self, frame):
        if self.crop_factor <= 0.9:
            return frame  # No crop
        h, w = frame.shape[:2]
        new_w, new_h = int(w / self.crop_factor), int(h / self.crop_factor)
        x1 = (w - new_w) // 2
        y1 = (h - new_h) // 2
        cropped = frame[y1:y1+new_h, x1:x1+new_w]
        # Resize back to original size for display
        return cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LINEAR)

    def get_waste_type(self, class_name):
        """Get the waste type from the class name"""
        waste_types = {
            'PET': 'PET',
            'HDPE': 'HDPE',
            'LDPE': 'LDPE',
            'PP': 'PP',
            'PS': 'PS',
            'PVC': 'PVC',
            'Tin-Steel Can': 'Tin-Steel Can',
            'Mixed Trash': 'Mixed Trash'
        }
        return waste_types.get(class_name, 'Unknown')

    def get_transparency(self, class_name):
        """Get the transparency level from the class name"""
        transparency_levels = {
            'PET': 'Transparent',
            'HDPE': 'Opaque',
            'LDPE': 'Opaque',
            'PP': 'Opaque',
            'PS': 'Transparent',
            'PVC': 'Transparent',
            'Tin-Steel Can': 'Opaque',
            'Mixed Trash': 'Unknown'
        }
        return transparency_levels.get(class_name, 'Unknown')

    def calculate_contamination_score(self, confidence, waste_type, transparency):
        """Calculate contamination score based on confidence, waste type, and transparency"""
        # Base score from waste type
        if waste_type == 'PET':
            waste_type_score = 9   # High base score
        elif waste_type == 'LDPE':
            waste_type_score = 5   # Medium-high base score
        elif waste_type == 'PP':
            waste_type_score = 6   # Medium base score
        elif waste_type == 'Tin-Steel Can':
            waste_type_score = 10   # High base score for metal
        elif waste_type == 'Mixed Trash':
            waste_type_score = 3   # Low base score for mixed waste
        else:
            waste_type_score = 4   # Default base score

        # Calculate final score
        final_score = (waste_type_score * confidence) * 10
        return min(max(final_score, 0), 100)  # Ensure score is between 0 and 100

    def classify_waste(self, waste_type, transparency, contamination_score):
        """Classify waste based on type, transparency, and contamination score"""
        if waste_type == 'Unknown' or transparency == 'Unknown':
            return 'Unknown'
            
        if contamination_score >= 70:
            return 'Recyclable'
        elif contamination_score >= 40:
            return 'Conditionally Recyclable'
        else:
            return 'Non-Recyclable'

    def process_frame(self, frame):
        """Process a single frame for detection"""
        if frame is None:
            return None
            
        try:
            # If we're tracking, update the tracker
            if self.tracking and self.tracked_bbox is not None:
                success, bbox = self.tracker.update(frame)
                if success:
                    self.tracked_bbox = bbox
                    self.tracking_lost_count = 0
                    # Draw the tracked bounding box
                    x, y, w, h = [int(v) for v in bbox]
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    return self.last_detection_result
                else:
                    self.tracking_lost_count += 1
                    if self.tracking_lost_count > self.max_tracking_lost:
                        self.tracking = False
                        self.tracked_bbox = None
                        self.tracking_lost_count = 0
            
            # Run detection with optimized settings
            results = self.model(frame, verbose=False, conf=0.5, iou=0.45, max_det=1)
            
            # Process results
            if results and len(results) > 0:
                result = results[0]
                if result.boxes and len(result.boxes) > 0:
                    # Get the first detection
                    box = result.boxes[0]
                    confidence = float(box.conf[0])
                    class_id = int(box.cls[0])
                    class_name = result.names[class_id]
                    
                    # Get bounding box coordinates
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    bbox = (x1, y1, x2 - x1, y2 - y1)
                    
                    # Initialize tracker with new detection
                    self.tracker = cv2.TrackerCSRT_create()
                    self.tracker.init(frame, bbox)
                    self.tracking = True
                    self.tracked_bbox = bbox
                    self.tracking_lost_count = 0
                    self.last_valid_bbox = bbox
                    
                    # Get waste type
                    waste_type = self.get_waste_type(class_name)
                    
                    # Calculate contamination score
                    contamination_score = self.calculate_contamination_score(confidence, waste_type, None)
                    
                    # Determine classification
                    classification = self.classify_waste(waste_type, None, contamination_score)
                    
                    # Store the detection result
                    detection_result = {
                        'waste_type': waste_type,
                        'contamination_score': contamination_score,
                        'classification': classification,
                        'confidence': confidence
                    }
                    
                    # Update last detection result
                    with self.detection_lock:
                        self.last_detection_result = detection_result
                    
                    # Draw the detection bounding box
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    
                    return detection_result
            
            # If no detection, return "No object detected"
            return {
                'waste_type': 'No object detected',
                'contamination_score': 0.0,
                'classification': 'No object detected',
                'confidence': 0.0
            }
            
        except Exception as e:
            logger.error(f"Error processing frame: {e}")
            return None

    def run_detection_loop(self):
        """Run the detection loop in a separate thread"""
        while self.detection_running:
            current_time = time.time()
            
            # Check if it's time for a new detection
            if current_time - self.last_detection_time >= self.detection_interval:
                with self.frame_lock:
                    if self.current_frame is not None and not self.processing_frame:
                        self.processing_frame = True
                        frame = self.current_frame.copy()
                        self.processing_frame = False
                        
                        # Skip frames to reduce lag
                        self.frame_count += 1
                        if self.frame_count % (self.frame_skip + 1) != 0:
                            continue
                        
                        # Process frame
                        result = self.process_frame(frame)
                        
                        # Update last detection time
                        self.last_detection_time = current_time
                        
                        # Send result through callback immediately
                        if result and self.detection_callback:
                            self.detection_callback(result)
            
            # Reduced sleep time for more frequent updates
            time.sleep(0.005)  # Reduced from 0.01 to 0.005 seconds

    def set_crop_factor(self, factor):
        if factor < 0.9:  # Prevent zooming out too much
            factor = 0.9
        self.crop_factor = factor 