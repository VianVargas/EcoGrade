import cv2
import torch
import time
import numpy as np
import math
from ultralytics import YOLO
import threading
from queue import Queue
import os
from datetime import datetime
from pathlib import Path
from src.utils.classification import classify_output
from src.utils.residue import detect_residue_colors, calculate_residue_score
from src.utils.database import store_measurement, generate_unique_id
from src.utils.animation import add_detection_animation, add_scan_effect
from src.utils.tracking import get_centroid, match_object, update_tracking, start_tracking

class VideoProcessor:
    _instance = None
    _camera = None
    _initialized = False
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(VideoProcessor, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, model_path='best.pt'):
        self.model = YOLO(model_path, verbose=False)
        self.is_running = False
        self.current_frame = None
        self.frame_lock = threading.Lock()
        self.detection_interval = 0.2  # Increased from 0.1 to reduce processing load
        self.last_detection_time = 0
        self.detection_callback = None
        self.camera = None
        self.frame_count = 0
        self.processing_frame = False
        self.last_detection_result = None
        self.detection_thread = None
        self.detection_running = False
        self.detection_lock = threading.Lock()
        self.frame_skip = 2  # Increased from 2 to reduce processing load
        
        # Performance metrics
        self.performance_metrics = {
            'fps': [],
            'preprocess': [],
            'inference': [],
            'postprocess': [],
            'total': [],
            'confidence': []  # Add confidence tracking
        }
        self.metrics_counter = 0
        self.metrics_interval = 30  # Print metrics every 30 frames
        
        # Tracking variables
        self.tracker = cv2.TrackerCSRT_create()
        self.tracking = False
        self.tracked_bbox = None
        self.tracking_lost_count = 0
        self.max_tracking_lost = 30
        self.last_valid_bbox = None
        self.smoothing_factor = 0.7
        self.min_confidence = 0.5
        self.min_iou = 0.4
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
        self.frame_size = (480, 640)  # Reduced from (640, 480) for better performance
        self.finalized_timeout = 5.0
        self.finalized_times = {}
        self.min_detection_area = 10000
        self.max_detection_area = 300000
        self.processing_size = (320, 240)  # Smaller size for processing
        
        # Cooldown timer for detections
        self.last_detection_times = {}  # Dictionary to store last detection time per waste type
        self.detection_cooldown = 3.0  # Cooldown period in seconds

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
                self.model = YOLO("best.pt", verbose=False)
                self.model.to('cpu')  # Force CPU usage
                print("Model loaded successfully")
            except Exception as e:
                raise Exception(f"Failed to load YOLO model: {str(e)}")
            try:
                ret, frame = VideoProcessor._camera.read()
                if ret:
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
        self.latest_result = None

    def release_camera(self):
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
            time.sleep(0.01)

    def set_zoom(self, zoom_factor):
        """Set the zoom factor for the camera"""
        self.zoom_factor = max(0.5, min(2.0, zoom_factor))
        if self.cap is not None:
            try:
                self.cap.set(cv2.CAP_PROP_ZOOM, self.zoom_factor)
            except:
                pass

    def _process_frames(self):
        while self.running:
            if not self.processing and not self.frame_queue.empty():
                try:
                    self.processing = True
                    frame = self.frame_queue.get()
                    
                    # Start timing
                    total_start_time = time.time()
                    
                    # Preprocessing timing
                    preprocess_start = time.time()
                    # Apply crop factor
                    frame_cropped = self.apply_crop_factor(frame)
                    
                    # Skip frames to reduce processing load
                    self._frame_skip_counter += 1
                    if self._frame_skip_counter < self.frame_skip:
                        continue
                    self._frame_skip_counter = 0
                    
                    # Resize frame for processing
                    frame_small = cv2.resize(frame_cropped, self.processing_size)
                    timings = {
                        'preprocess': (time.time() - preprocess_start) * 1000
                    }
                    
                    # Inference timing
                    inference_start = time.time()
                    # Process frame with YOLO model
                    results = self.model.predict(frame_small, conf=self.min_confidence, verbose=False)
                    timings['inference'] = (time.time() - inference_start) * 1000
                    
                    # Post-processing timing
                    postprocess_start = time.time()
                    
                    # Initialize output frames
                    model_output = frame_cropped.copy()
                    residue_detection = frame_cropped.copy()
                    mask_display = np.zeros_like(frame_cropped)
                    
                    current_boxes = []
                    object_detected = False
                    object_mask = np.zeros((frame_cropped.shape[0], frame_cropped.shape[1]), dtype=np.uint8)
                    current_waste_type = '-'
                    classification = '-'
                    current_obj_id = None
                    
                    detected_ids = set()
                    now = time.time()

                    # Reset finalized objects that have timed out
                    for obj_id in list(self.finalized_ids):
                        if obj_id in self.finalized_times:
                            if now - self.finalized_times[obj_id] > self.finalized_timeout:
                                self.finalized_ids.remove(obj_id)
                                if obj_id in self.object_trackers:
                                    del self.object_trackers[obj_id]
                                if obj_id in self.finalized_times:
                                    del self.finalized_times[obj_id]
                    
                    # Process detections
                    if results and len(results) > 0:
                        result = results[0]
                        if result.boxes and len(result.boxes) > 0:
                            for box in result.boxes:
                                conf = float(box.conf[0])
                                cls_id = int(box.cls[0])
                                
                                # Scale coordinates back to original size
                                x1, y1, x2, y2 = map(int, box.xyxy[0])
                                scale_x = frame_cropped.shape[1] / self.processing_size[0]
                                scale_y = frame_cropped.shape[0] / self.processing_size[1]
                                x1, x2 = int(x1 * scale_x), int(x2 * scale_x)
                                y1, y2 = int(y1 * scale_y), int(y2 * scale_y)
                                
                                # Calculate detection area
                                detection_area = (x2 - x1) * (y2 - y1)
                                
                                # Skip if detection area is too small or too large
                                if detection_area < self.min_detection_area or detection_area > self.max_detection_area:
                                    continue
                                
                                # Calculate centroid for tracking
                                centroid = (int((x1 + x2) / 2), int((y1 + y2) / 2))
                                
                                # Find matching object ID
                                obj_id = None
                                for existing_id, tracker in self.object_trackers.items():
                                    if existing_id in self.finalized_ids:
                                        continue
                                    prev_centroid = tracker['centroid']
                                    distance = math.hypot(centroid[0] - prev_centroid[0], centroid[1] - prev_centroid[1])
                                    if distance < 50:
                                        obj_id = existing_id
                                        break
                                
                                if obj_id is None:
                                    obj_id = generate_unique_id(self.object_trackers, self.finalized_ids)
                                    self.object_trackers[obj_id] = {
                                        'centroid': centroid,
                                        'timer': now,
                                        'state': 'analyzing',
                                        'result': None,
                                        'confidence': conf,
                                        'waste_type': None,
                                        'detection_count': 0,
                                        'last_update': now,
                                        'stable_count': 0
                                    }
                                else:
                                    tracker = self.object_trackers[obj_id]
                                    prev_centroid = tracker['centroid']
                                    distance = math.hypot(centroid[0] - prev_centroid[0], centroid[1] - prev_centroid[1])
                                    
                                    if distance < 50:
                                        tracker['stable_count'] += 1
                                    else:
                                        tracker['stable_count'] = max(0, tracker['stable_count'] - 1)
                                    
                                    if conf > tracker.get('confidence', 0):
                                        tracker['confidence'] = conf
                                        tracker['centroid'] = centroid
                                        tracker['last_update'] = now
                                
                                detected_ids.add(obj_id)
                                current_obj_id = obj_id
                                
                                if obj_id in self.finalized_ids:
                                    continue
                                
                                waste_types = {
                                    0: 'HDPE Plastic',
                                    1: 'PP',
                                    2: 'PET Bottle',
                                    3: 'PP',
                                    4: 'LDPE',
                                    5: 'HDPE Plastic',
                                    6: 'Tin Can',
                                    7: 'UHT Box'
                                }
                                
                                if conf > 0.8: # Confidence level threshold
                                    current_waste_type = waste_types.get(cls_id, 'Unknown')
                                    if current_obj_id:
                                        self.object_trackers[current_obj_id]['waste_type'] = current_waste_type
                                else:
                                    current_waste_type = 'Unknown'
                                
                                object_detected = True
                                
                                box_color = (0, 255, 0)
                                cv2.rectangle(model_output, (x1, y1), (x2, y2), box_color, 4)
                                
                                if hasattr(box, 'masks') and box.masks is not None:
                                    mask = box.masks.cpu().numpy()[0]
                                    # Scale mask to original size
                                    mask = cv2.resize(mask, (frame_cropped.shape[1], frame_cropped.shape[0]))
                                    object_mask = (mask * 255).astype(np.uint8)
                                else:
                                    object_mask[y1:y2, x1:x2] = 255
                                
                                cropped_frame = frame_cropped[y1:y2, x1:x2]
                                if cropped_frame.size > 0:
                                    residue_detection_cropped, residue_mask = detect_residue_colors(cropped_frame)
                                    if residue_detection_cropped is not None:
                                        residue_detection[y1:y2, x1:x2] = residue_detection_cropped
                                        bbox_area = (x2 - x1) * (y2 - y1)
                                        contamination_score = calculate_residue_score(residue_mask, bbox_area)
                                        self.current_contamination_score = contamination_score
                                        mask_display = cv2.cvtColor(residue_mask, cv2.COLOR_GRAY2BGR)
                    
                    # Add animation to model output
                    model_output = add_detection_animation(model_output, object_detected, current_boxes, 
                                                        self.last_classification, self.animation_time)
                    
                    # Update classification
                    if object_detected:
                        criteria_met = (current_waste_type != '-')
                        current_time = time.time()
                        
                        if criteria_met:
                            if self.detection_start_time is None:
                                self.detection_start_time = current_time
                                classification = 'Analyzing...'
                            elif current_time - self.detection_start_time >= 0.5:
                                if current_obj_id and self.object_trackers[current_obj_id]['stable_count'] >= 5:
                                    classification = classify_output(current_waste_type, self.current_contamination_score)
                                    result_data = {
                                        'id': current_obj_id,
                                        'waste_type': current_waste_type,
                                        'contamination_score': self.current_contamination_score,
                                        'classification': classification,
                                        'confidence_level': conf if object_detected else 0
                                    }
                                    self.object_trackers[current_obj_id]['result'] = result_data
                                    self.object_trackers[current_obj_id]['state'] = 'finalized'
                                    self.finalized_ids.add(current_obj_id)
                                    self.finalized_times[current_obj_id] = current_time
                                    
                                    # Emit result only if it's a valid classification
                                    if classification not in ['Analyzing...', 'No object detected', 'Waiting for: Type', 'Unknown', '-']:
                                        self.emit_detection_result(result_data)
                                else:
                                    classification = 'Analyzing...'
                        else:
                            missing_criteria = []
                            if current_waste_type == '-':
                                missing_criteria.append('Type')
                            classification = f"Waiting for: {', '.join(missing_criteria)}"
                            self.detection_start_time = None
                    else:
                        self.detection_start_time = None
                        classification = 'No object detected'
                    
                    # Calculate final timings
                    timings['postprocess'] = (time.time() - postprocess_start) * 1000
                    timings['total'] = (time.time() - total_start_time) * 1000
                    
                    # Calculate FPS
                    fps = 1000 / timings['total'] if timings['total'] > 0 else 0
                    
                    # Store metrics
                    self.performance_metrics['fps'].append(fps)
                    self.performance_metrics['preprocess'].append(timings['preprocess'])
                    self.performance_metrics['inference'].append(timings['inference'])
                    self.performance_metrics['postprocess'].append(timings['postprocess'])
                    self.performance_metrics['total'].append(timings['total'])
                    
                    # Store confidence if object is detected
                    if object_detected and 'conf' in locals():
                        self.performance_metrics['confidence'].append(conf)
                    else:
                        self.performance_metrics['confidence'].append(0.0)
                    
                    # Keep only the last 100 measurements
                    max_metrics = 100
                    for key in self.performance_metrics:
                        if len(self.performance_metrics[key]) > max_metrics:
                            self.performance_metrics[key] = self.performance_metrics[key][-max_metrics:]
                    
                    # Print metrics every metrics_interval frames
                    self.metrics_counter += 1
                    if self.metrics_counter >= self.metrics_interval:
                        # Calculate averages
                        avg_fps = sum(self.performance_metrics['fps']) / len(self.performance_metrics['fps'])
                        avg_preprocess = sum(self.performance_metrics['preprocess']) / len(self.performance_metrics['preprocess'])
                        avg_inference = sum(self.performance_metrics['inference']) / len(self.performance_metrics['inference'])
                        avg_postprocess = sum(self.performance_metrics['postprocess']) / len(self.performance_metrics['postprocess'])
                        avg_total = sum(self.performance_metrics['total']) / len(self.performance_metrics['total'])
                        avg_confidence = sum(self.performance_metrics['confidence']) / len(self.performance_metrics['confidence'])
                        
                        # Print to terminal with flush=True to ensure immediate output
                        import sys
                        sys.stdout.write("\nDetection Performance Metrics (Averaged over last 100 frames):\n")
                        sys.stdout.write(f"Average FPS: {avg_fps:.2f}\n")
                        sys.stdout.write(f"Average Preprocessing: {avg_preprocess:.2f} ms\n")
                        sys.stdout.write(f"Average Inference: {avg_inference:.2f} ms\n")
                        sys.stdout.write(f"Average Post-processing: {avg_postprocess:.2f} ms\n")
                        sys.stdout.write(f"Average Total processing time: {avg_total:.2f} ms\n")
                        sys.stdout.write(f"Average Confidence: {avg_confidence:.2%}\n")
                        sys.stdout.write("-" * 40 + "\n")
                        sys.stdout.flush()
                        
                        self.metrics_counter = 0
                    
                    # Prepare result with all frames
                    result = {
                        'frames': {
                            'model': model_output,
                            'residue': residue_detection,
                            'mask': mask_display
                        },
                        'data': {
                            'id': current_obj_id,
                            'waste_type': current_waste_type,
                            'confidence_level': conf if object_detected else 0,
                            'contamination_score': self.current_contamination_score,
                            'classification': classification,
                            'processing_time_ms': timings['total']
                        }
                    }
                    self.latest_result = result
                    
                    # Update animation time
                    self.animation_time += 0.1
                    
                except Exception as e:
                    print(f"Error in frame processing: {str(e)}")
                finally:
                    self.processing = False
                    
            time.sleep(0.01)

    def emit_detection_result(self, result_data):
        """Emit detection result and store in database if valid"""
        if result_data.get('classification') not in [
            'Analyzing...', 'No object detected',
            'Waiting for: Type', 'Unknown', '-'
        ]:
            # Check cooldown for this waste type
            waste_type = result_data.get('waste_type')
            current_time = time.time()
            
            if waste_type in self.last_detection_times:
                time_since_last = current_time - self.last_detection_times[waste_type]
                if time_since_last < self.detection_cooldown:
                    return  # Skip this detection due to cooldown
            
            # Update last detection time for this waste type
            self.last_detection_times[waste_type] = current_time
            
            result_data['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            if 'id' not in result_data:
                result_data['id'] = generate_unique_id(self.object_trackers, self.finalized_ids)
            
            store_measurement(result_data)

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
            'Tin Can': 'Tin Can',
            'UHT Box': 'UHT Box'
        }
        return waste_types.get(class_name, 'Unknown')

    def process_frame(self, frame):
        """Process a single frame for detection"""
        if frame is None:
            return None
            
        try:
            # Initialize timing variables
            timings = {
                'preprocess': 0,
                'inference': 0,
                'postprocess': 0,
                'total': 0
            }
            
            # Start total timing
            total_start_time = time.time()
            
            # Preprocessing timing
            preprocess_start = time.time()
            if self.tracking and self.tracked_bbox is not None:
                success, bbox = self.tracker.update(frame)
                if success:
                    self.tracked_bbox = bbox
                    self.tracking_lost_count = 0
                    x, y, w, h = [int(v) for v in bbox]
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    return self.last_detection_result
                else:
                    self.tracking_lost_count += 1
                    if self.tracking_lost_count > self.max_tracking_lost:
                        self.tracking = False
                        self.tracked_bbox = None
                        self.tracking_lost_count = 0
            
            # Prepare frame for inference
            frame_cropped = frame.copy()
            timings['preprocess'] = (time.time() - preprocess_start) * 1000
            
            # Inference timing
            inference_start = time.time()
            results = self.model.predict(frame_cropped, verbose=False, conf=0.5, iou=0.45, max_det=1)
            timings['inference'] = (time.time() - inference_start) * 1000
            
            # Post-processing timing
            postprocess_start = time.time()
            
            if results and len(results) > 0:
                result = results[0]
                if result.boxes and len(result.boxes) > 0:
                    box = result.boxes[0]
                    confidence = float(box.conf[0])
                    class_id = int(box.cls[0])
                    class_name = result.names[class_id]
                    
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    bbox = (x1, y1, x2 - x1, y2 - y1)
                    
                    self.tracker = cv2.TrackerCSRT_create()
                    self.tracker.init(frame, bbox)
                    self.tracking = True
                    self.tracked_bbox = bbox
                    self.tracking_lost_count = 0
                    self.last_valid_bbox = bbox
                    
                    waste_type = self.get_waste_type(class_name)
                    contamination_score = self.calculate_contamination_score(confidence, waste_type, None)
                    classification = self.classify_waste(waste_type, None, contamination_score)
                    
                    detection_result = {
                        'waste_type': waste_type,
                        'contamination_score': contamination_score,
                        'classification': classification,
                        'confidence': confidence,
                        'processing_time_ms': timings['total']
                    }
                    
                    with self.detection_lock:
                        self.last_detection_result = detection_result
                    
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    
                    timings['postprocess'] = (time.time() - postprocess_start) * 1000
                    timings['total'] = (time.time() - total_start_time) * 1000
                    
                    # Calculate and print FPS and timing breakdown
                    fps = 1000 / timings['total'] if timings['total'] > 0 else 0
                    print("\nDetection Performance Metrics:")
                    print(f"FPS: {fps:.2f}")
                    print(f"Preprocessing: {timings['preprocess']:.2f} ms")
                    print(f"Inference: {timings['inference']:.2f} ms")
                    print(f"Post-processing: {timings['postprocess']:.2f} ms")
                    print(f"Total processing time: {timings['total']:.2f} ms")
                    print("-" * 40)
                    
                    return detection_result
            
            # If no detection
            timings['postprocess'] = (time.time() - postprocess_start) * 1000
            timings['total'] = (time.time() - total_start_time) * 1000
            
            # Calculate and print FPS and timing breakdown even for no detection
            fps = 1000 / timings['total'] if timings['total'] > 0 else 0
            print("\nDetection Performance Metrics (No Detection):")
            print(f"FPS: {fps:.2f}")
            print(f"Preprocessing: {timings['preprocess']:.2f} ms")
            print(f"Inference: {timings['inference']:.2f} ms")
            print(f"Post-processing: {timings['postprocess']:.2f} ms")
            print(f"Total processing time: {timings['total']:.2f} ms")
            print("-" * 40)
            
            return {
                'waste_type': 'No object detected',
                'contamination_score': 0.0,
                'classification': 'No object detected',
                'confidence': 0.0,
                'processing_time_ms': timings['total']
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
                            
                            # Print processing time from result
                            if 'processing_time_ms' in result:
                                print(f"Frame processing time: {result['processing_time_ms']:.2f} ms")
            
            # Reduced sleep time for more frequent updates
            time.sleep(0.005)  # Reduced from 0.01 to 0.005 seconds

    def set_crop_factor(self, factor):
        if factor < 0.9:  # Prevent zooming out too much
            factor = 0.9
        self.crop_factor = factor 