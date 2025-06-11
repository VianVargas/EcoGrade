import cv2
import numpy as np

def add_detection_animation(frame, detected, boxes, last_classification, animation_time):
    """Add animation effects to detected objects"""
    # Create a copy of the frame
    animated_frame = frame.copy()
    
    if detected and boxes:
        for x1, y1, x2, y2, cls_id, conf in boxes:
            # Calculate border thickness based on sine wave
            border_thickness = int(5 + 3 * np.sin(animation_time * 6))
            
            # Create border color based on classification
            if last_classification == 'High Value':
                border_color = (0, 255, 0)  # Green
            elif last_classification == 'Low Value':
                border_color = (0, 165, 255)  # Orange
            else:
                border_color = (0, 0, 255)  # Red
            
            # Draw animated border
            cv2.rectangle(animated_frame, (x1, y1), (x2, y2), border_color, border_thickness)
            
            # Add pulsing corner markers
            corner_size = min(20, (x2 - x1) // 3)  # Adjust corner size based on box size
            corner_thickness = 2
            alpha = 0.5 + 0.5 * np.sin(animation_time * 4)  # Pulsing alpha
            
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
    
    return animated_frame

def add_scan_effect(frame, is_tin=False, boxes=None, animation_time=0):
    """Add scanning effect to the frame"""
    # Create a copy of the frame
    scan_frame = frame.copy()
    height, width = frame.shape[:2]
    
    if boxes and not is_tin:
        for x1, y1, x2, y2, cls_id, conf in boxes:
            # Calculate box dimensions
            box_height = y2 - y1
            box_width = x2 - x1
            
            # Create scanning line within the box
            scan_y = y1 + int(box_height * (0.5 + 0.5 * np.sin(animation_time * 3)))
            
            # Create gradient mask for the box area
            mask = np.zeros((box_height, box_width), dtype=np.float32)
            for y in range(box_height):
                # Calculate distance from scan line
                dist = abs(y - (scan_y - y1))
                # Create smooth gradient
                mask[y, :] = np.exp(-dist/30) * (0.5 + 0.5 * np.sin(animation_time * 4))
            
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
            dot_radius = int(3 + 2 * np.sin(animation_time * 4))
            cv2.circle(scan_frame, (x1, scan_y), dot_radius, (0, 165, 255), -1)
            cv2.circle(scan_frame, (x2-1, scan_y), dot_radius, (0, 165, 255), -1)
    
    return scan_frame 