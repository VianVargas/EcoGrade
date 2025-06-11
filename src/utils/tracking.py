import cv2
import math
import random
import string
import time

def get_centroid(x1, y1, x2, y2):
    """Calculate the centroid of a bounding box"""
    return ((x1 + x2) // 2, (y1 + y2) // 2)

def match_object(centroid, object_trackers, threshold=50):
    """Find existing object ID by centroid proximity"""
    best_match = None
    min_distance = float('inf')
    
    for obj_id, data in object_trackers.items():
        prev_centroid = data['centroid']
        distance = math.hypot(centroid[0] - prev_centroid[0], centroid[1] - prev_centroid[1])
        if distance < threshold and distance < min_distance:
            min_distance = distance
            best_match = obj_id
            
    return best_match

def generate_unique_id(object_trackers, finalized_ids):
    """Generate a unique 4-character alphanumeric ID"""
    while True:
        new_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        if new_id not in object_trackers and new_id not in finalized_ids:
            return new_id

def update_tracking(frame, tracker, tracked_bbox, tracking_lost_count, max_tracking_lost):
    """Update object tracking"""
    if tracked_bbox is None:
        return None
        
    success, bbox = tracker.update(frame)
    if success:
        tracking_lost_count = 0
        return bbox
    else:
        tracking_lost_count += 1
        if tracking_lost_count > max_tracking_lost:
            return None
        return tracked_bbox

def start_tracking(frame, bbox):
    """Initialize object tracking"""
    tracker = cv2.TrackerCSRT_create()
    success = tracker.init(frame, bbox)
    if success:
        return tracker, True
    return None, False 