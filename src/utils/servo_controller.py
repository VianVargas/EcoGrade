import RPi.GPIO as GPIO
import time
import json
import threading
import logging
from typing import Dict, Optional
import os

class ServoController:
    def __init__(self, config_path: str = 'config/raspberry_pi/gpio_config.json'):
        self.config = self._load_config(config_path)
        self.servos: Dict[str, Dict] = {}
        self.running = False
        self.control_thread = None
        self.lock = threading.Lock()
        self._setup_gpio()
        self._initialize_servos()
        
    def _load_config(self, config_path: str) -> dict:
        """Load GPIO configuration from JSON file"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Error loading GPIO config: {e}")
            raise

    def _setup_gpio(self):
        """Initialize GPIO settings"""
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Setup PWM for servos
        for servo_name, servo_config in self.config['servo_motors'].items():
            GPIO.setup(servo_config['pin'], GPIO.OUT)
            pwm = GPIO.PWM(servo_config['pin'], servo_config['pwm_frequency'])
            pwm.start(0)
            self.servos[servo_name] = {
                'pwm': pwm,
                'current_position': servo_config['default_position'],
                'target_position': servo_config['default_position'],
                'config': servo_config,
                'last_move_time': 0,
                'operation_count': 0
            }

    def _initialize_servos(self):
        """Move all servos to default position"""
        for servo_name in self.servos:
            self.move_to_position(servo_name, self.servos[servo_name]['config']['default_position'])

    def _angle_to_duty_cycle(self, angle: float) -> float:
        """Convert angle to PWM duty cycle"""
        return 2.5 + (angle / 180.0 * 10.0)

    def move_to_position(self, servo_name: str, position: float, speed: Optional[float] = None):
        """Move servo to specified position with speed control"""
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
            servo['operation_count'] += 1
            
            # Apply movement
            duty_cycle = self._angle_to_duty_cycle(position)
            servo['pwm'].ChangeDutyCycle(duty_cycle)
            servo['current_position'] = position

    def move_to_sort_position(self, servo_name: str):
        """Move servo to its sorting position"""
        if servo_name not in self.servos:
            raise ValueError(f"Unknown servo: {servo_name}")
        
        sort_position = self.servos[servo_name]['config']['sort_position']
        self.move_to_position(servo_name, sort_position)

    def emergency_stop(self):
        """Emergency stop all servos"""
        with self.lock:
            for servo_name, servo in self.servos.items():
                servo['pwm'].ChangeDutyCycle(0)
                logging.warning(f"Emergency stop activated for {servo_name}")

    def cleanup(self):
        """Clean up GPIO resources"""
        self.running = False
        if self.control_thread:
            self.control_thread.join()
        
        for servo in self.servos.values():
            servo['pwm'].stop()
        
        GPIO.cleanup()

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