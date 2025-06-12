# pi_servo_server.py
import time
import board
import busio
import socket
from adafruit_pca9685 import PCA9685
from adafruit_motor import servo

# Set up I2C and PCA9685
i2c = busio.I2C(board.SCL, board.SDA)
pca = PCA9685(i2c)
pca.frequency = 50

# Create servo objects on specific channels
servo1 = servo.Servo(pca.channels[0])  # Main arm
servo2 = servo.Servo(pca.channels[4])  # Flap

def process(command):
    if command == "high":
        print("HIGH: Servo1 ? Left, Servo2 ? Left")
        servo1.angle = 60
        time.sleep(1.75)
        servo2.angle = 50
        time.sleep(1)
        servo2.angle = 103
        time.sleep(1)
        servo1.angle = 120
        time.sleep(1.75)

    elif command == "mix":
        print("MIX: Servo1 ? Left, Servo2 ? Right")
        servo1.angle = 60
        time.sleep(1.75)
        servo2.angle = 150
        time.sleep(1)
        servo2.angle = 103
        time.sleep(1)
        servo1.angle = 120
        time.sleep(1.75)

    elif command == "low":
        print("LOW: Servo1 ? Right, Servo2 ? Left")
        servo1.angle = 180
        time.sleep(1.75)
        servo2.angle = 50
        time.sleep(1)
        servo2.angle = 103
        time.sleep(1)
        servo1.angle = 120
        time.sleep(1.75)

    elif command == "reject":
        print("REJECT: Servo1 ? Right, Servo2 ? Right")
        servo1.angle = 180
        time.sleep(1.75)
        servo2.angle = 150
        time.sleep(1)
        servo2.angle = 103
        time.sleep(1)
        servo1.angle = 120
        time.sleep(1.75)

    else:
        print("Invalid command:", command)

# Initialize to center
print("Initializing Servos to Center Positions...")
servo1.angle = 120
servo2.angle = 103
time.sleep(2)

# Start TCP server
HOST = '0.0.0.0'  # Listen on all interfaces
PORT = 5001

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((HOST, PORT))
server_socket.listen(1)
print(f"Listening for servo commands on port {PORT}...")

try:
    while True:
        client_socket, addr = server_socket.accept()
        print(f"Connection from {addr}")
        data = client_socket.recv(1024).decode('utf-8').strip()
        if data:
            print(f"Received command: {data}")
            process(data)
        client_socket.close()

except KeyboardInterrupt:
    print("Shutting down server...")

finally:
    pca.deinit()
    server_socket.close()

