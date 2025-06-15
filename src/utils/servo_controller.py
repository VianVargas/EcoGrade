import board
import busio
from adafruit_pca9685 import PCA9685
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
        
        # Load configuration
        self.config = self._load_config()
        
        # Initialize servos
        self.servos = {}
        self._initialize_servos()
        
        # Set initial positions
        self._set_initial_positions()
    
    def _load_config(self):
        """Load servo configuration from JSON file"""
        config_path = Path('config/raspberry_pi/gpio_config.json')
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, 'r') as f:
            return json.load(f)
    
    def _initialize_servos(self):
        """Initialize all servos from configuration"""
        for servo_name, servo_config in self.config['servos'].items():
            channel = servo_config['channel']
            min_pulse = servo_config['min_pulse']
            max_pulse = servo_config['max_pulse']
            
            self.servos[servo_name] = {
                'channel': channel,
                'min_pulse': min_pulse,
                'max_pulse': max_pulse,
                'current_angle': 0
            }
    
    def _set_initial_positions(self):
        """Set all servos to their initial positions"""
        for servo_name, servo_config in self.config['servos'].items():
            if 'initial_position' in servo_config:
                self.set_angle(servo_name, servo_config['initial_position'])
    
    def set_angle(self, servo_name, angle):
        """Set the angle of a specific servo"""
        if servo_name not in self.servos:
            raise ValueError(f"Unknown servo: {servo_name}")
        
        servo = self.servos[servo_name]
        channel = servo['channel']
        min_pulse = servo['min_pulse']
        max_pulse = servo['max_pulse']
        
        # Constrain angle to valid range
        angle = max(0, min(180, angle))
        
        # Convert angle to pulse length
        pulse = min_pulse + (max_pulse - min_pulse) * angle / 180.0
        
        # Set PWM
        self.pca.channels[channel].duty_cycle = int(pulse * 65535 / 20000)
        
        # Update current angle
        servo['current_angle'] = angle
    
    def get_angle(self, servo_name):
        """Get the current angle of a specific servo"""
        if servo_name not in self.servos:
            raise ValueError(f"Unknown servo: {servo_name}")
        
        return self.servos[servo_name]['current_angle']
    
    def cleanup(self):
        """Clean up resources"""
        # Set all servos to their initial positions
        self._set_initial_positions()
        
        # Small delay to allow servos to reach position
        time.sleep(0.5)
        
        # Release I2C bus
        self.i2c.deinit()

# Dummy class for laptop testing
# class ServoController:
#     def __init__(self):
#         """Dummy initialization for laptop testing"""
#         pass
#     
#     def set_angle(self, servo_name, angle):
#         """Dummy method for laptop testing"""
#         print(f"Servo {servo_name} would move to {angle} degrees")
#     
#     def get_angle(self, servo_name):
#         """Dummy method for laptop testing"""
#         return 0
#     
#     def cleanup(self):
#         """Dummy cleanup for laptop testing"""
#         pass 