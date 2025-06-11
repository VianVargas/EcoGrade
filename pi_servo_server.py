#!/usr/bin/env python3
import time
import board
import busio
import socket
import threading
import logging
from typing import Optional
from adafruit_pca9685 import PCA9685
from adafruit_motor import servo

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('servo_debug.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ServoController:
    def __init__(self):
        """Initialize servo controller on Raspberry Pi."""
        # Set up I2C and PCA9685
        logger.info("Initializing I2C and PCA9685...")
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
        
        # Movement timing parameters
        self.movement_delay = 0.15  # Reduced from 0.3
        self.return_delay = 0.5     # Reduced from 1.0
        self.flap_delay = 0.8       # Reduced from 1.75
    
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

class ServoServer:
    def __init__(self, host='0.0.0.0', port=5001):
        """Initialize servo server."""
        self.host = host
        self.port = port
        self.servo = ServoController()
        self.running = False
        self.server_socket: Optional[socket.socket] = None
        self.last_command_time = 0
        self.command_cooldown = 0.1  # Minimum time between commands
    
    def handle_client(self, client_socket: socket.socket) -> None:
        """Handle client connection and commands."""
        try:
            while self.running:
                # Receive data
                data = client_socket.recv(1024)
                if not data:
                    break
                
                try:
                    # Parse command
                    command = data.decode().strip()
                    logger.info(f"Received command: {command}")
                    
                    # Check command cooldown
                    current_time = time.time()
                    if current_time - self.last_command_time < self.command_cooldown:
                        continue
                    self.last_command_time = current_time
                    
                    # Process command with optimized timing
                    if command in ["ldpe", "pp"]:  # LDPE and PP at max value go to low
                        logger.info("[DEBUG] Executing LOW command sequence for LDPE/PP")
                        self.servo.move_to_angles(180, 50)
                        time.sleep(self.servo.flap_delay)
                        self.servo.move_to_angles(180, 103)
                        time.sleep(self.servo.return_delay)
                        self.servo.move_to_angles(120, 103)
                    elif command == "uht":  # UHT boxes go to mix
                        logger.info("[DEBUG] Executing MIX command sequence for UHT")
                        self.servo.move_to_angles(60, 150)
                        time.sleep(self.servo.flap_delay)
                        self.servo.move_to_angles(60, 103)
                        time.sleep(self.servo.return_delay)
                        self.servo.move_to_angles(120, 103)
                    elif command == "contam":  # Contaminated items go to reject
                        logger.info("[DEBUG] Executing REJECT command sequence for contaminated items")
                        self.servo.move_to_angles(180, 150)
                        time.sleep(self.servo.flap_delay)
                        self.servo.move_to_angles(180, 103)
                        time.sleep(self.servo.return_delay)
                        self.servo.move_to_angles(120, 103)
                    else:
                        logger.error(f"Invalid command: {command}")
                    
                except ValueError:
                    logger.error(f"Invalid data received: {data}")
                    continue
                
        except Exception as e:
            logger.error(f"Error handling client: {e}")
        finally:
            client_socket.close()
    
    def start(self) -> None:
        """Start the server."""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(1)
            
            self.running = True
            logger.info(f"Server started on {self.host}:{self.port}")
            
            while self.running:
                try:
                    client_socket, address = self.server_socket.accept()
                    logger.info(f"Client connected from {address}")
                    
                    # Handle client in a separate thread
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket,)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                    
                except Exception as e:
                    logger.error(f"Error accepting connection: {e}")
                    continue
                
        except Exception as e:
            logger.error(f"Server error: {e}")
        finally:
            self.cleanup()
    
    def cleanup(self) -> None:
        """Clean up server resources."""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        self.servo.cleanup()
        logger.info("Server stopped")

if __name__ == '__main__':
    try:
        server = ServoServer()
        server.start()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}") 