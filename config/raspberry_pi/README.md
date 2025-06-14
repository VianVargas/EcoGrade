# Raspberry Pi Configuration

This directory contains configuration files and setup instructions for running EcoGrade on a Raspberry Pi system, optimized for Raspberry Pi 5.

## System Requirements

- Raspberry Pi 5 (4GB RAM or higher recommended)
- Raspberry Pi OS (64-bit) Bookworm or newer
- Camera Module v3 or compatible USB camera
- Servo motors for waste sorting mechanism
- GPIO pins for servo control

## Setup Instructions

1. Install Raspberry Pi OS
2. Update system packages:

   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

3. Install required system packages:

   ```bash
   sudo apt install -y python3-pip python3-venv libatlas-base-dev libopenblas-dev \
       libopencv-dev python3-opencv v4l-utils
   ```

4. Set up Python virtual environment:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

5. Configure camera:

   - Enable camera interface in `raspbi-config`
   - Enable legacy camera support if using Camera Module v2
   - Adjust camera settings in `camera_config.json`

6. Configure GPIO pins:

   - Review and adjust pin assignments in `gpio_config.json`
   - Ensure proper servo motor connections

7. Optimize system for Pi 5:

   ```bash
   # Enable GPU memory
   sudo raspi-config nonint do_memory_split 256

   # Set CPU governor to performance
   echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

   # Enable DMA for camera
   sudo modprobe bcm2835-v4l2
   ```

8. Start the application:
   ```bash
   python main.py
   ```

## Configuration Files

- `camera_config.json`: Camera settings and parameters (optimized for Pi 5)
- `gpio_config.json`: GPIO pin assignments and servo configurations
- `system_config.json`: System-wide settings and optimizations for Pi 5

## Performance Optimization

The Raspberry Pi 5 configuration includes several optimizations:

- Higher resolution camera support (1280x720 @ 60fps)
- GPU-accelerated image processing
- DMA-enabled camera interface
- Optimized memory management
- Increased processing thread count
- Enhanced buffer management

For detailed optimization settings, refer to `system_config.json`.

## Troubleshooting

See `TROUBLESHOOTING.md` for common issues and solutions specific to Raspberry Pi 5.
