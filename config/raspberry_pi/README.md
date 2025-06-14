# Raspberry Pi Configuration

This directory contains configuration files and setup instructions for running EcoGrade on a Raspberry Pi system.

## System Requirements

- Raspberry Pi 4 (4GB RAM or higher recommended)
- Raspberry Pi OS (64-bit) Bullseye or newer
- Camera Module v2 or compatible USB camera
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
   sudo apt install -y python3-pip python3-venv libatlas-base-dev libopenblas-dev
   ```

4. Set up Python virtual environment:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

5. Configure camera:

   - Enable camera interface in `raspbi-config`
   - Adjust camera settings in `camera_config.json`

6. Configure GPIO pins:

   - Review and adjust pin assignments in `gpio_config.json`
   - Ensure proper servo motor connections

7. Start the application:
   ```bash
   python main.py
   ```

## Configuration Files

- `camera_config.json`: Camera settings and parameters
- `gpio_config.json`: GPIO pin assignments and servo configurations
- `system_config.json`: System-wide settings and optimizations

## Troubleshooting

See `TROUBLESHOOTING.md` for common issues and solutions.

## Performance Optimization

The Raspberry Pi configuration includes several optimizations:

- Reduced processing resolution
- Optimized model inference
- Memory management settings
- Camera frame rate adjustments

For detailed optimization settings, refer to `system_config.json`.
