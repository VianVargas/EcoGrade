import time
import board
import busio
from adafruit_pca9685 import PCA9685
from adafruit_motor import servo

class ServoController:
    def __init__(self):
        # Set up I2C and PCA9685
        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.pca = PCA9685(self.i2c)
        self.pca.frequency = 50

        # Create servo objects on specific channels
        self.servo1 = servo.Servo(self.pca.channels[0])  # Main arm
        self.servo2 = servo.Servo(self.pca.channels[4])  # Flap

        # Initialize both servos to center positions
        print("Initializing Servos to Center Positions...")
        self.servo1.angle = 120
        self.servo2.angle = 103
        time.sleep(2)

    def process_detection(self, detection_result):
        """
        Process detection result and move servos accordingly
        Args:
            detection_result (str): The detection result ('high', 'mix', 'low', or 'reject')
        """
        if detection_result == "high":
            print("HIGH: Servo1 → Left, Servo2 → Left")

            # Servo1: Move to left (60°)
            print("Servo1: Moving to 60°")
            self.servo1.angle = 60
            time.sleep(1.75)

            # Servo2: Center → Left (50°)
            print("Servo2: Moving to 50°")
            self.servo2.angle = 50
            time.sleep(1)
            print("Servo2: Returning to center (103°)")
            self.servo2.angle = 103
            time.sleep(1)

            # Servo1: Return to center (120°)
            print("Servo1: Returning to center (120°)")
            self.servo1.angle = 120
            time.sleep(1.75)

        elif detection_result == "mix":
            print("MIX: Servo1 → Left, Servo2 → Right")

            print("Servo1: Moving to 60°")
            self.servo1.angle = 60
            time.sleep(1.75)

            print("Servo2: Moving to 150°")
            self.servo2.angle = 150
            time.sleep(1)
            print("Servo2: Returning to center (103°)")
            self.servo2.angle = 103
            time.sleep(1)

            print("Servo1: Returning to center (120°)")
            self.servo1.angle = 120
            time.sleep(1.75)

        elif detection_result == "low":
            print("LOW: Servo1 → Right, Servo2 → Left")

            print("Servo1: Moving to 180°")
            self.servo1.angle = 180
            time.sleep(1.75)

            print("Servo2: Moving to 50°")
            self.servo2.angle = 50
            time.sleep(1)
            print("Servo2: Returning to center (103°)")
            self.servo2.angle = 103
            time.sleep(1)

            print("Servo1: Returning to center (120°)")
            self.servo1.angle = 120
            time.sleep(1.75)

        elif detection_result == "reject":
            print("REJECT: Servo1 → Right, Servo2 → Right")

            print("Servo1: Moving to 180°")
            self.servo1.angle = 180
            time.sleep(1.75)

            print("Servo2: Moving to 150°")
            self.servo2.angle = 150
            time.sleep(1)
            print("Servo2: Returning to center (103°)")
            self.servo2.angle = 103
            time.sleep(1)

            print("Servo1: Returning to center (120°)")
            self.servo1.angle = 120
            time.sleep(1.75)

        else:
            print(f"Invalid detection result: {detection_result}")

    def cleanup(self):
        """Clean up resources"""
        print("Cleaning up servo controller...")
        self.pca.deinit() 