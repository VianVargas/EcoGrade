import time
import board
import busio
import json
import threading
import logging
from typing import Dict, Optional
import os
from adafruit_pca9685 import PCA9685
from adafruit_motor import servo

class ServoController:
    def __init__(self, config_path: str = 'config/raspberry_pi/gpio_config.json'):
        self.config = self._load_config(config_path)
        self.servos: Dict[str, Dict] = {}
        self.running = False
        self.control_thread = None
        self.lock = threading.Lock()
        
        # Set up I2C and PCA9685
        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.pca = PCA9685(self.i2c)
        self.pca.frequency = 50
        
        self._initialize_servos()
        
    def _load_config(self, config_path: str) -> dict:
        """Load GPIO configuration from JSON file"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Error loading GPIO config: {e}")
            raise

    def _initialize_servos(self):
        """Initialize servos using PCA9685"""
        # Create servo objects for main arm and flap
        self.servos['main_arm'] = {
            'servo': servo.Servo(self.pca.channels[0]),
            'current_position': 120,
            'target_position': 120,
            'config': {
                'min_angle': 0,
                'max_angle': 180,
                'default_position': 120,
                'sort_position': 60,
                'safety': {
                    'cooldown_time': 0.1
                }
            },
            'last_move_time': 0
        }
        
        self.servos['flap'] = {
            'servo': servo.Servo(self.pca.channels[4]),
            'current_position': 103,
            'target_position': 103,
            'config': {
                'min_angle': 0,
                'max_angle': 180,
                'default_position': 103,
                'sort_position': 50,
                'safety': {
                    'cooldown_time': 0.1
                }
            },
            'last_move_time': 0
        }
        
        # Move to default positions
        self.move_to_position('main_arm', 120)
        self.move_to_position('flap', 103)
        time.sleep(2)  # Wait for servos to reach position

    def move_to_position(self, servo_name: str, position: float, speed: Optional[float] = None):
        """Move servo to specified position"""
        if servo_name not in self.servos:
            raise ValueError(f"Unknown servo: {servo_name}")

        with self.lock:
            servo = self.servos[servo_name]
            config = servo['config']
            
            # Apply position limits
            position = max(config['min_angle'], min(config['max_angle'], position))
            
            # Check safety limits
            current_time = time.time()
            if current_time - servo['last_move_time'] < config['safety']['cooldown_time']:
                logging.warning(f"Servo {servo_name} in cooldown period")
                return
            
            # Update servo state
            servo['target_position'] = position
            servo['last_move_time'] = current_time
            
            # Apply movement
            servo['servo'].angle = position
            servo['current_position'] = position

    def move_to_sort_position(self, servo_name: str):
        """Move servo to its sorting position"""
        if servo_name not in self.servos:
            raise ValueError(f"Unknown servo: {servo_name}")
        
        sort_position = self.servos[servo_name]['config']['sort_position']
        self.move_to_position(servo_name, sort_position)

    def process_command(self, command: str):
        """Process sorting commands"""
        if command == "high":
            logging.info("HIGH: Main arm → Left, Flap → Left")
            self.move_to_position('main_arm', 60)
            time.sleep(1.75)
            self.move_to_position('flap', 50)
            time.sleep(1)
            self.move_to_position('flap', 103)
            time.sleep(1)
            self.move_to_position('main_arm', 120)
            time.sleep(1.75)

        elif command == "mix":
            logging.info("MIX: Main arm → Left, Flap → Right")
            self.move_to_position('main_arm', 60)
            time.sleep(1.75)
            self.move_to_position('flap', 150)
            time.sleep(1)
            self.move_to_position('flap', 103)
            time.sleep(1)
            self.move_to_position('main_arm', 120)
            time.sleep(1.75)

        elif command == "low":
            logging.info("LOW: Main arm → Right, Flap → Left")
            self.move_to_position('main_arm', 180)
            time.sleep(1.75)
            self.move_to_position('flap', 50)
            time.sleep(1)
            self.move_to_position('flap', 103)
            time.sleep(1)
            self.move_to_position('main_arm', 120)
            time.sleep(1.75)

        elif command == "reject":
            logging.info("REJECT: Main arm → Right, Flap → Right")
            self.move_to_position('main_arm', 180)
            time.sleep(1.75)
            self.move_to_position('flap', 150)
            time.sleep(1)
            self.move_to_position('flap', 103)
            time.sleep(1)
            self.move_to_position('main_arm', 120)
            time.sleep(1.75)

        else:
            logging.warning(f"Invalid command: {command}")

    def emergency_stop(self):
        """Emergency stop all servos"""
        with self.lock:
            for servo_name, servo in self.servos.items():
                servo['servo'].angle = None  # Release servo
                logging.warning(f"Emergency stop activated for {servo_name}")

    def cleanup(self):
        """Clean up resources"""
        self.running = False
        if self.control_thread:
            self.control_thread.join()
        
        # Release all servos
        for servo in self.servos.values():
            servo['servo'].angle = None
        
        # Deinitialize PCA9685
        self.pca.deinit()

    def get_position(self, servo_name: str) -> float:
        """Get current position of servo"""
        if servo_name not in self.servos:
            raise ValueError(f"Unknown servo: {servo_name}")
        return self.servos[servo_name]['current_position']

    def is_moving(self, servo_name: str) -> bool:
        """Check if servo is currently moving"""
        if servo_name not in self.servos:
            raise ValueError(f"Unknown servo: {servo_name}")
        
        servo = self.servos[servo_name]
        return abs(servo['current_position'] - servo['target_position']) > 0.1

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup() 