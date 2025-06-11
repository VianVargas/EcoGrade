import numpy as np
import cv2
import logging

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

def calculate_residue_score(residue_mask, bbox_area):
    """Calculate residue score based on residue mask and bounding box area"""
    try:
        # Calculate residue percentage
        residue_pixels = np.sum(residue_mask > 0)
        residue_percentage = (residue_pixels / bbox_area) * 100
        
        # Double the contamination value
        doubled_percentage = residue_percentage * 2
        
        # Cap at 100%
        return min(doubled_percentage, 100.0)
    except Exception as e:
        logging.error(f"Error calculating residue score: {str(e)}")
        return 0.0 