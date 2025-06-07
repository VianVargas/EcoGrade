class ServoController:
        def __init__(self):
            print("[MockServoController] Hardware not available. Servo actions will be printed only.")
        def process_detection(self, detection_result):
            print(f"[MockServoController] Would process detection: {detection_result}")
        def cleanup(self):
            print("[MockServoController] Cleanup called.") 