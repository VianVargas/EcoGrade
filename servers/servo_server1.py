#!/usr/bin/env python3
import time
import board
import busio
import socket
import threading
import logging
from typing import Optional
from adafruit_pca9685 import PCA9685
from adafruit_motor import servo  # Fixed import

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ServoController:
    def __init__(self):
        """Initialize servo controller on Raspberry Pi."""
        # Movement timing parameters - Define these FIRST
        self.movement_delay = 0.15  # Reduced from 0.3
        self.return_delay = 0.5     # Reduced from 1.0
        self.flap_delay = 0.8       # Reduced from 1.75
        
        # Set up I2C and PCA9685
        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.pca = PCA9685(self.i2c)
        self.pca.frequency = 50
        
        # Create servo objects
        self.servo1 = servo.Servo(self.pca.channels[0])  # Main arm
        self.servo2 = servo.Servo(self.pca.channels[4])  # Flap
        
        # Initialize to center positions
        self.current_angle1 = 120
        self.current_angle2 = 103
        self.move_to_angles(self.current_angle1, self.current_angle2)
        logger.info("Servos initialized at center positions")
    
    def move_to_angles(self, angle1: int, angle2: int) -> None:
        """Move servos to specified angles (0-180 degrees)."""
        try:
            # Validate angles
            angle1 = max(0, min(180, angle1))
            angle2 = max(0, min(180, angle2))
            
            # Move servos
            self.servo1.angle = angle1
            self.servo2.angle = angle2
            time.sleep(self.movement_delay)  # Reduced delay
            
            self.current_angle1 = angle1
            self.current_angle2 = angle2
            logger.info(f"Servos moved to {angle1}° and {angle2}°")
            
        except Exception as e:
            logger.error(f"Error moving servos: {e}")
    
    def cleanup(self) -> None:
        """Clean up resources."""
        try:
            self.pca.deinit()
            logger.info("PCA9685 resources cleaned up")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}") 