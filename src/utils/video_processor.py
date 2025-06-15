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
import logging
import traceback

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
        self.detection_interval = 0.1  # Reduced from 0.2 to 0.1 for faster response
        self.last_detection_time = 0
        self.detection_callback = None
        self.camera = None
        self.frame_count = 0
        self.processing_frame = False
        self.last_detection_result = None
        self.detection_thread = None
        self.detection_running = False
        self.detection_lock = threading.Lock()
        self.frame_skip = 1  # Reduced from 2 to 1 for more frequent processing
        
        # Performance metrics
        self.performance_metrics = {
            'fps': [],
            'preprocess': [],
            'inference': [],
            'postprocess': [],
            'total': [],
            'confidence': []
        }
        self.metrics_counter = 0
        self.metrics_interval = 30
        
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
        self.frame_size = (480, 640)
        self.finalized_timeout = 5.0
        self.finalized_times = {}
        self.min_detection_area = 10000
        self.max_detection_area = 300000
        self.processing_size = (416, 416)  # Increased from (320, 240) for better accuracy
        
        # Cooldown timer for detections
        self.last_detection_times = {}
        self.detection_cooldown = 1.0  # Reduced from 3.0 to 1.0 for faster response

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
        """Process video frames for object detection"""
        while self.running:
            try:
                if not self.camera or not self.camera.isOpened():
                    time.sleep(0.1)
                    continue
                    
                ret, frame = self.camera.read()
                if not ret:
                    continue
                    
                # Resize frame for processing
                frame = cv2.resize(frame, self.processing_size)
                
                # Process frame
                start_time = time.time()
                results = self.model(frame)
                processing_time = time.time() - start_time
                
                # Get detection results
                detections = results.xyxy[0].cpu().numpy()
                
                if len(detections) > 0:
                    # Get the first detection
                    detection = detections[0]
                    confidence = float(detection[4])
                    
                    if confidence >= self.confidence_threshold:
                        # Get class name and calculate contamination
                        class_id = int(detection[5])
                        class_name = self.model.names[class_id]
                        contamination = self._calculate_contamination(detection, frame)
                        
                        # Classify the output
                        classification = self._classify_output(class_name, contamination)
                        
                        # Create result dictionary
                        result = {
                            'waste_type': class_name,
                            'confidence_level': confidence * 100,
                            'contamination_score': contamination * 100,
                            'classification': classification
                        }
                        
                        # Print performance metrics
                        print("\n=== Video Processor Metrics ===")
                        print(f"Processing Time: {processing_time*1000:.2f}ms")
                        print(f"FPS: {1/processing_time:.2f}")
                        print(f"Waste Type: {class_name}")
                        print(f"Confidence: {confidence*100:.2f}%")
                        print(f"Contamination: {contamination*100:.2f}%")
                        print(f"Classification: {classification}")
                        print("=============================\n")
                        
                        # Emit detection result
                        self.emit_detection_result(result)
                    else:
                        self._show_no_object_detected()
                else:
                    self._show_no_object_detected()
                    
            except Exception as e:
                logging.error(f"Error in frame processing: {e}")
                logging.error(traceback.format_exc())
                time.sleep(0.1)

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