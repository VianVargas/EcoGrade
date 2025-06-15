import board
import busio
from adafruit_pca9685 import PCA9685
from adafruit_motor import servo
import time
import logging

logger = logging.getLogger(__name__)

class ServoController:
    def __init__(self):
        """Initialize the servo controller with Adafruit PCA9685"""
        try:
            # Initialize I2C and PCA9685
            self.i2c = busio.I2C(board.SCL, board.SDA)
            self.pca = PCA9685(self.i2c)
            self.pca.frequency = 50  # Standard servo frequency
            
            # Create servo objects on specific channels
            self.servo1 = servo.Servo(self.pca.channels[0])  # Main arm
            self.servo2 = servo.Servo(self.pca.channels[4])  # Flap
            
            # Initialize to center positions
            logger.info("Initializing Servos to Center Positions...")
            self.servo1.angle = 120
            self.servo2.angle = 103
            time.sleep(2)
            
        except Exception as e:
            logger.error(f"Error initializing servo controller: {e}")
            raise
    
    def process_command(self, command):
        """Process servo commands based on classification"""
        try:
            if command == "high":
                logger.info("HIGH: Servo1 → Left, Servo2 → Left")
                self.servo1.angle = 60
                time.sleep(1.75)
                self.servo2.angle = 50
                time.sleep(1)
                self.servo2.angle = 103
                time.sleep(1)
                self.servo1.angle = 120
                time.sleep(1.75)

            elif command == "mix":
                logger.info("MIX: Servo1 → Left, Servo2 → Right")
                self.servo1.angle = 60
                time.sleep(1.75)
                self.servo2.angle = 150
                time.sleep(1)
                self.servo2.angle = 103
                time.sleep(1)
                self.servo1.angle = 120
                time.sleep(1.75)

            elif command == "low":
                logger.info("LOW: Servo1 → Right, Servo2 → Left")
                self.servo1.angle = 180
                time.sleep(1.75)
                self.servo2.angle = 50
                time.sleep(1)
                self.servo2.angle = 103
                time.sleep(1)
                self.servo1.angle = 120
                time.sleep(1.75)

            elif command == "reject":
                logger.info("REJECT: Servo1 → Right, Servo2 → Right")
                self.servo1.angle = 180
                time.sleep(1.75)
                self.servo2.angle = 150
                time.sleep(1)
                self.servo2.angle = 103
                time.sleep(1)
                self.servo1.angle = 120
                time.sleep(1.75)

            else:
                logger.warning(f"Invalid command: {command}")
                
        except Exception as e:
            logger.error(f"Error processing servo command: {e}")
            raise
    
    def cleanup(self):
        """Clean up resources"""
        try:
            # Set servos to center positions
            self.servo1.angle = 120
            self.servo2.angle = 103
            time.sleep(2)
            
            # Release I2C bus
            self.pca.deinit()
            self.i2c.deinit()
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            raise

# Dummy class for laptop testing
# class ServoController:
#     def __init__(self):
#         """Dummy initialization for laptop testing"""
#         pass
#     
#     def process_command(self, command):
#         """Dummy method for laptop testing"""
#         logger.info(f"Servo would process command: {command}")
#     
#     def cleanup(self):
#         """Dummy cleanup for laptop testing"""
#         pass 