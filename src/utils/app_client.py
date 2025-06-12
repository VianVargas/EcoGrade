import socket
import logging
from pathlib import Path
import time

# Configure logging
log_dir = Path('logs')
log_dir.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / 'app_client.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AppClient:
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(AppClient, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, pi_host='192.168.1.102', pi_port=5001):
        if self._initialized:
            return
            
        self.pi_host = pi_host
        self.pi_port = pi_port
        self.socket = None
        
        # Mapping of classifications to servo commands
        self.classification_to_command = {
            'High Value': 'high',
            'Mixed': 'mix',
            'Low Value': 'low',
            'Reject': 'reject'
        }
        
        # Command timing parameters
        self.last_command_time = 0
        self.command_cooldown = 0.05  # 50ms cooldown between commands
        self.reconnect_delay = 0.1    # 100ms delay before reconnection attempts
        
        self._initialized = True
        logger.info("AppClient initialized")
    
    def connect_to_pi(self):
        """Connect to Raspberry Pi server."""
        try:
            if self.socket:
                self.socket.close()
            
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(2)  # Reduced from 5 seconds
            self.socket.connect((self.pi_host, self.pi_port))
            logger.info(f"Connected to server at {self.pi_host}:{self.pi_port}")
            return True
            
        except socket.timeout:
            logger.error("Connection timed out")
            return False
        except ConnectionRefusedError:
            logger.error("Connection refused. Is the server running?")
            return False
        except Exception as e:
            logger.error(f"Failed to connect to server: {e}")
            return False
    
    def send_command(self, command):
        """Send command to Raspberry Pi."""
        try:
            current_time = time.time()
            if current_time - self.last_command_time < self.command_cooldown:
                return False
                
            if not self.socket:
                if not self.connect_to_pi():
                    time.sleep(self.reconnect_delay)
                    return False
            
            self.socket.send(command.encode())
            self.last_command_time = current_time
            logger.info(f"Sent command: {command}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending command: {e}")
            self.socket = None  # Reset socket for reconnection
            return False
    
    def process_detection(self, detection_result):
        """Process detection result and send appropriate command."""
        if not detection_result:
            return
        
        try:
            # Get classification from detection result
            classification = detection_result.get('classification', '')
            
            # Map classification to command
            command = self.classification_to_command.get(classification)
            if command:
                logger.info(f"Processing {classification} -> Sending {command} command")
                if not self.send_command(command):
                    # If send failed, try to reconnect and send again
                    if self.connect_to_pi():
                        time.sleep(self.reconnect_delay)
                        self.send_command(command)
        except Exception as e:
            logger.error(f"Error processing detection: {e}")
    
    def cleanup(self):
        """Clean up resources."""
        try:
            if self.socket:
                self.socket.close()
                logger.info("Closed connection to Raspberry Pi")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

# Create a global instance
app_client = AppClient() 