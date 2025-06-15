import board
import busio
from adafruit_pca9685 import PCA9685
from adafruit_motor import servo
import time
import json
import os
from pathlib import Path

class ServoController:
    def __init__(self):
        """Initialize the servo controller with GPIO pins and PWM settings"""
        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.pca = PCA9685(self.i2c)
        self.pca.frequency = 50  # Set PWM frequency to 50Hz
        
        # Create servo objects on specific channels
        self.servo1 = servo.Servo(self.pca.channels[0])  # Main arm
        self.servo2 = servo.Servo(self.pca.channels[4])  # Flap
        
        # Initialize to center positions
        print("Initializing Servos to Center Positions...")
        self.servo1.angle = 120
        self.servo2.angle = 103
        time.sleep(2)
    
    def process_command(self, command):
        """Process servo commands based on classification"""
        if command == "high":
            print("HIGH: Servo1 → Left, Servo2 → Left")
            self.servo1.angle = 60
            time.sleep(1.75)
            self.servo2.angle = 50
            time.sleep(1)
            self.servo2.angle = 103
            time.sleep(1)
            self.servo1.angle = 120
            time.sleep(1.75)

        elif command == "mix":
            print("MIX: Servo1 → Left, Servo2 → Right")
            self.servo1.angle = 60
            time.sleep(1.75)
            self.servo2.angle = 150
            time.sleep(1)
            self.servo2.angle = 103
            time.sleep(1)
            self.servo1.angle = 120
            time.sleep(1.75)

        elif command == "low":
            print("LOW: Servo1 → Right, Servo2 → Left")
            self.servo1.angle = 180
            time.sleep(1.75)
            self.servo2.angle = 50
            time.sleep(1)
            self.servo2.angle = 103
            time.sleep(1)
            self.servo1.angle = 120
            time.sleep(1.75)

        elif command == "reject":
            print("REJECT: Servo1 → Right, Servo2 → Right")
            self.servo1.angle = 180
            time.sleep(1.75)
            self.servo2.angle = 150
            time.sleep(1)
            self.servo2.angle = 103
            time.sleep(1)
            self.servo1.angle = 120
            time.sleep(1.75)

        else:
            print("Invalid command:", command)
    
    def cleanup(self):
        """Clean up resources"""
        # Set servos to center positions
        self.servo1.angle = 120
        self.servo2.angle = 103
        time.sleep(2)
        
        # Release I2C bus
        self.pca.deinit()
        self.i2c.deinit()

# Dummy class for laptop testing
# class ServoController:
#     def __init__(self):
#         """Dummy initialization for laptop testing"""
#         pass
#     
#     def process_command(self, command):
#         """Dummy method for laptop testing"""
#         print(f"Servo would process command: {command}")
#     
#     def cleanup(self):
#         """Dummy cleanup for laptop testing"""
#         pass 