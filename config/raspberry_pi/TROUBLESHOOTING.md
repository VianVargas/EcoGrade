# Troubleshooting Guide

## Common Issues and Solutions

### Camera Issues

1. **Camera Not Detected**

   - Check if camera is enabled in `raspbi-config`
   - Verify camera ribbon cable connection
   - Try different USB port for USB cameras
   - Check camera permissions: `sudo usermod -a -G video $USER`

2. **Poor Image Quality**

   - Adjust exposure settings in `camera_config.json`
   - Check lighting conditions
   - Clean camera lens
   - Verify camera focus

3. **High Latency**
   - Reduce processing resolution
   - Increase frame skip value
   - Check CPU temperature and throttling
   - Optimize model inference settings

### Servo Motor Issues

1. **Motors Not Moving**

   - Check power supply voltage
   - Verify GPIO pin connections
   - Check PWM frequency settings
   - Ensure proper ground connection

2. **Erratic Movement**
   - Check for loose connections
   - Verify PWM signal stability
   - Adjust servo timing in `gpio_config.json`
   - Check for power supply noise

### System Performance

1. **High CPU Usage**

   - Check running processes: `top`
   - Optimize model inference settings
   - Reduce worker threads
   - Check for memory leaks

2. **Memory Issues**

   - Monitor memory usage: `free -h`
   - Adjust swap settings
   - Reduce buffer sizes
   - Check for memory leaks

3. **Overheating**
   - Check temperature: `vcgencmd measure_temp`
   - Ensure proper cooling
   - Reduce CPU frequency if needed
   - Check for dust buildup

### Network Issues

1. **Connection Problems**

   - Check network configuration
   - Verify firewall settings
   - Test network connectivity
   - Check server logs

2. **High Latency**
   - Optimize network settings
   - Check for network congestion
   - Verify server response times
   - Adjust timeout settings

## Performance Optimization

### Camera Optimization

```bash
# Enable camera interface
sudo raspi-config

# Set optimal camera parameters
v4l2-ctl --set-ctrl=exposure_auto=1
v4l2-ctl --set-ctrl=exposure_absolute=100
v4l2-ctl --set-ctrl=gain=100
```

### System Optimization

```bash
# Set CPU governor to performance
echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# Increase swap size
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# Set CONF_SWAPSIZE=2048
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

### Memory Management

```bash
# Clear system cache
sudo sync; echo 3 | sudo tee /proc/sys/vm/drop_caches

# Monitor memory usage
watch -n 1 free -h
```

## Logging and Debugging

1. Check application logs:

```bash
tail -f /var/log/ecograde/app.log
```

2. Monitor system resources:

```bash
htop
```

3. Check GPU memory:

```bash
vcgencmd get_mem gpu
```

## Emergency Procedures

1. **System Freeze**

   - Press and hold power button for 5 seconds
   - Check system logs after reboot
   - Verify hardware connections

2. **Emergency Stop**
   - Press emergency stop button
   - Check error logs
   - Verify all systems are safe
   - Restart with caution

## Maintenance

1. Regular checks:

   - Clean camera lens
   - Check servo motor connections
   - Monitor system temperature
   - Update system packages

2. Backup procedures:
   - Regular system backups
   - Configuration file backups
   - Database backups
   - Log file rotation
