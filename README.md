# EcoGrade - Advanced Waste Detection and Analysis System

A sophisticated PyQt5-based application for real-time waste detection, classification, and environmental analysis using computer vision and machine learning.

## 🌟 Features

### Core Functionality

- Real-time waste detection and classification using YOLO
- Multi-camera support with split view capability
- Contamination level assessment
- Waste type classification (PET, HDPE, PP, LDPE, etc.)
- Quality grading (High Value, Low Value, Rejects)

### User Interface

- Modern, responsive UI with gradient backgrounds
- Dynamic animations and transitions
- Dark theme optimized for long viewing sessions
- Intuitive navigation with sidebar controls
- Multiple view support:
  - Front Page: Welcome screen with animations
  - Main View: Real-time detection interface
  - Analytics: Data visualization and reporting
  - About: Project information

### Analytics and Reporting

- Real-time performance metrics (FPS, processing times)
- Interactive data visualization
- Customizable time-based filtering
- Export capabilities to Excel
- Statistical analysis and trends

## 🚀 Installation

### Prerequisites

- Python 3.8 or higher
- Git
- pip (Python package manager)

### Setup Steps

1. Clone the repository:

```bash
git clone https://github.com/VianVargas/EcoGrade.git
cd ecograde
```

2. Create and activate virtual environment:

```bash
# Create virtual environment
python -m venv venv

# Activate on Windows
venv\Scripts\activate

# Activate on macOS/Linux
source venv/bin/activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Verify required assets:

```
src/ui/assets/
├── fonts/
│   ├── Fredoka-Medium.ttf
│   └── Fredoka-SemiBold.ttf
├── LOGO.ico
├── video.svg
├── bar-chart.svg
├── corner-up-left.svg
├── power.svg
└── info.svg
```

## 💻 Usage

### Starting the Application

```bash
python main.py
```

### Main Features

1. **Front Page**

   - Welcome screen with dynamic animations
   - Start button to enter main application

2. **Main View**

   - Real-time camera feed
   - Detection results display
   - Camera controls
   - Split view toggle
   - Performance metrics

3. **Analytics View**
   - Interactive charts and graphs
   - Time-based filtering
   - Data export functionality
   - Statistical analysis

## 📁 Project Structure

```
EcoGrade/
├── models/                 # ML model files
│   └── *.pt               # YOLO model weights
├── exports/               # Export directory
│   └── *.xlsx            # Exported data files
├── servers/              # Server implementations
│   ├── pi_servo_server.py
│   └── servo_server1.py
├── logs/                 # Application logs
├── src/                  # Source code
│   ├── ui/              # UI components
│   │   ├── views/       # View implementations
│   │   ├── widgets/     # Custom widgets
│   │   └── assets/      # UI assets
│   ├── utils/           # Utility functions
│   ├── hardware/        # Hardware control
│   └── main.py          # Application entry
├── data/                # Data storage
├── scripts/             # Utility scripts
├── requirements.txt     # Dependencies
└── README.md           # Documentation
```

## 🔧 Dependencies

### Core Dependencies

- PyQt5: GUI framework
- OpenCV: Computer vision
- PyTorch: Deep learning
- Ultralytics: YOLO implementation
- NumPy & Pandas: Data processing
- Matplotlib & PyQtGraph: Visualization

### Hardware Support

- Adafruit CircuitPython libraries for servo control
- Raspberry Pi GPIO support

### Development Tools

- PyInstaller: Application packaging
- Openpyxl: Excel export
- PyYAML: Configuration

## 📊 Performance Metrics

The application provides real-time performance monitoring:

- FPS (Frames Per Second)
- Preprocessing time
- Inference time
- Post-processing time
- Average processing metrics

## 🔐 Security

- Secure camera handling
- Safe file operations
- Protected data exports
- Error handling and logging

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- YOLO team for object detection model
- PyQt5 community
- All contributors and supporters
