import cv2
import numpy as np
import time
import math
import threading
from queue import Queue
import os
from datetime import datetime
from pathlib import Path
import onnxruntime as ort
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
    
    def __init__(self, model_path='models/best_optimized.onnx'):
        # Initialize ONNX Runtime session with optimizations
        self.session_options = ort.SessionOptions()
        self.session_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        self.session_options.intra_op_num_threads = 4  # Optimize for Raspberry Pi 5's 4 cores
        
        # Try to use GPU if available, otherwise fall back to CPU
        try:
            self.session = ort.InferenceSession(model_path, self.session_options, 
                                              providers=['CPUExecutionProvider'])  # Simplified providers
        except Exception as e:
            print(f"Error loading ONNX model: {str(e)}")
            raise
        
        # Get model metadata
        self.input_name = self.session.get_inputs()[0].name
        self.output_names = [output.name for output in self.session.get_outputs()]
        self.input_shape = self.session.get_inputs()[0].shape
        
        # Initialize other attributes
        self.is_running = False
        self.current_frame = None
        self.frame_lock = threading.Lock()
        self.detection_interval = 0.1
        self.last_detection_time = 0
        self.detection_callback = None
        self.camera = None
        self.frame_count = 0
        self.processing_frame = False
        self.last_detection_result = None
        self.detection_thread = None
        self.detection_running = False
        self.detection_lock = threading.Lock()
        self.frame_skip = 1
        
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
        self.processing_size = (640, 640)
        
        # Cooldown timer for detections
        self.last_detection_times = {}
        self.detection_cooldown = 1.0

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

    def preprocess_frame(self, frame):
        """Preprocess frame for ONNX model input"""
        try:
            # Resize frame to model input size
            frame_resized = cv2.resize(frame, self.processing_size)
            
            # Convert to RGB and normalize
            frame_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
            frame_normalized = frame_rgb.astype(np.float32) / 255.0
            
            # Add batch dimension and transpose to NCHW format
            frame_nchw = np.transpose(frame_normalized, (2, 0, 1))
            frame_batch = np.expand_dims(frame_nchw, axis=0)
            
            return frame_batch
        except Exception as e:
            print(f"Error in preprocessing: {str(e)}")
            return None

    def postprocess_output(self, outputs, original_frame):
        """Process ONNX model outputs to get detections"""
        try:
            # YOLO ONNX output format: (1, 12, 8400) where:
            # - 1 is batch size
            # - 12 is number of classes
            # - 8400 is number of predictions per class
            predictions = outputs[0]  # Shape: (1, 12, 8400)
            
            # Debug output shape
            print(f"Predictions shape: {predictions.shape}")
            
            # Get the class with highest confidence for each prediction
            class_scores = predictions[0]  # Shape: (12, 8400)
            max_scores = np.max(class_scores, axis=0)  # Shape: (8400,)
            class_ids = np.argmax(class_scores, axis=0)  # Shape: (8400,)
            
            # Debug confidence scores
            print(f"Max confidence: {np.max(max_scores):.4f}")
            print(f"Mean confidence: {np.mean(max_scores):.4f}")
            
            # Filter predictions based on confidence
            mask = max_scores > self.min_confidence
            filtered_scores = max_scores[mask]
            filtered_class_ids = class_ids[mask]
            
            # Debug filtered predictions
            print(f"Number of detections after confidence filter: {len(filtered_scores)}")
            
            # Get corresponding indices
            indices = np.where(mask)[0]
            
            # Convert indices to box coordinates
            # Each index corresponds to a grid cell
            grid_size = 80  # 640/8 = 80 (assuming 8x8 grid)
            cell_size = 8   # 640/80 = 8
            
            detections = []
            for idx, score, cls_id in zip(indices, filtered_scores, filtered_class_ids):
                # Convert index to grid coordinates
                grid_x = idx % grid_size
                grid_y = idx // grid_size
                
                # Convert grid coordinates to pixel coordinates
                x1 = grid_x * cell_size
                y1 = grid_y * cell_size
                x2 = x1 + cell_size
                y2 = y1 + cell_size
                
                # Scale to original image size
                scale_x = original_frame.shape[1] / self.processing_size[0]
                scale_y = original_frame.shape[0] / self.processing_size[1]
                
                x1, x2 = int(x1 * scale_x), int(x2 * scale_x)
                y1, y2 = int(y1 * scale_y), int(y2 * scale_y)
                
                # Calculate detection area
                area = (x2 - x1) * (y2 - y1)
                
                # Skip if detection area is too small or too large
                if area < self.min_detection_area or area > self.max_detection_area:
                    continue
                
                detections.append({
                    'box': [x1, y1, x2, y2],
                    'score': float(score),
                    'class_id': int(cls_id)
                })
            
            # Debug final detections
            print(f"Number of final detections: {len(detections)}")
            if len(detections) > 0:
                print(f"First detection: {detections[0]}")
            
            return detections
        except Exception as e:
            print(f"Error in postprocessing: {str(e)}")
            return []

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
                    frame_cropped = self.apply_crop_factor(frame)
                    
                    # Skip frames to reduce processing load
                    self._frame_skip_counter += 1
                    if self._frame_skip_counter < self.frame_skip:
                        continue
                    self._frame_skip_counter = 0
                    
                    # Preprocess frame for ONNX
                    input_tensor = self.preprocess_frame(frame_cropped)
                    if input_tensor is None:
                        print("Error: Failed to preprocess frame")
                        continue
                        
                    timings = {
                        'preprocess': (time.time() - preprocess_start) * 1000
                    }
                    
                    # Inference timing
                    inference_start = time.time()
                    outputs = self.session.run(self.output_names, {self.input_name: input_tensor})
                    timings['inference'] = (time.time() - inference_start) * 1000
                    
                    # Post-processing timing
                    postprocess_start = time.time()
                    
                    # Process detections
                    detections = self.postprocess_output(outputs, frame_cropped)
                    
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
                    
                    # Process each detection
                    for detection in detections:
                        box = detection['box']
                        conf = detection['score']
                        cls_id = detection['class_id']
                        
                        x1, y1, x2, y2 = box
                        detection_area = (x2 - x1) * (y2 - y1)
                        
                        if detection_area < self.min_detection_area or detection_area > self.max_detection_area:
                            continue
                        
                        # Draw detection box
                        cv2.rectangle(model_output, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        
                        # Add label
                        label = f"Class {cls_id}: {conf:.2f}"
                        cv2.putText(model_output, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                        
                        object_detected = True
                        current_boxes.append(box)
                    
                    # Rest of the processing code...
                    
                    # Update metrics and prepare result
                    timings['postprocess'] = (time.time() - postprocess_start) * 1000
                    timings['total'] = (time.time() - total_start_time) * 1000
                    
                    # Calculate FPS and update metrics
                    fps = 1000 / timings['total'] if timings['total'] > 0 else 0
                    self.update_metrics(timings, fps, conf if object_detected else 0)
                    
                    # Prepare result
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

    def update_metrics(self, timings, fps, confidence):
        """Update performance metrics"""
        self.performance_metrics['fps'].append(fps)
        self.performance_metrics['preprocess'].append(timings['preprocess'])
        self.performance_metrics['inference'].append(timings['inference'])
        self.performance_metrics['postprocess'].append(timings['postprocess'])
        self.performance_metrics['total'].append(timings['total'])
        self.performance_metrics['confidence'].append(confidence)
        
        # Keep only the last 100 measurements
        max_metrics = 100
        for key in self.performance_metrics:
            if len(self.performance_metrics[key]) > max_metrics:
                self.performance_metrics[key] = self.performance_metrics[key][-max_metrics:]
        
        # Print metrics every metrics_interval frames
        self.metrics_counter += 1
        if self.metrics_counter >= self.metrics_interval:
            self.print_metrics()
            self.metrics_counter = 0

    def print_metrics(self):
        """Print performance metrics"""
        avg_fps = sum(self.performance_metrics['fps']) / len(self.performance_metrics['fps'])
        avg_preprocess = sum(self.performance_metrics['preprocess']) / len(self.performance_metrics['preprocess'])
        avg_inference = sum(self.performance_metrics['inference']) / len(self.performance_metrics['inference'])
        avg_postprocess = sum(self.performance_metrics['postprocess']) / len(self.performance_metrics['postprocess'])
        avg_total = sum(self.performance_metrics['total']) / len(self.performance_metrics['total'])
        avg_confidence = sum(self.performance_metrics['confidence']) / len(self.performance_metrics['confidence'])
        
        print("\nDetection Performance Metrics (Averaged over last 100 frames):")
        print(f"Average FPS: {avg_fps:.2f}")
        print(f"Average Preprocessing: {avg_preprocess:.2f} ms")
        print(f"Average Inference: {avg_inference:.2f} ms")
        print(f"Average Post-processing: {avg_postprocess:.2f} ms")
        print(f"Average Total processing time: {avg_total:.2f} ms")
        print(f"Average Confidence: {avg_confidence:.2%}")
        print("-" * 40)

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