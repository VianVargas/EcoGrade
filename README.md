# EcoGrade - Object Detection Dashboard

A modern PyQt5-based dashboard for object detection and analysis.

## Features

- Modern and responsive UI with a dark theme
- Multiple camera feed support
- Real-time object detection (YOLOv11s)
- Statistical analysis and visualization
- Interactive charts and graphs
- Hardware servo support (optional)

## Installation

1. Clone the repository:

```bash
git clone https://github.com/VianVargas/EcoGrade.git
cd ecograde
```

2. Create a virtual environment (recommended):

```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Ensure all required assets are present:

- **Fonts:**
  - `src/ui/assets/fonts/Fredoka-Medium.ttf`
  - `src/ui/assets/fonts/Fredoka-SemiBold.ttf`
- **SVGs and Images:**
  - `src/ui/assets/LOGO.png`
  - `src/ui/assets/home.svg`
  - `src/ui/assets/bar-chart.svg`
  - `src/ui/assets/corner-up-left.svg`
  - `src/ui/assets/power.svg`
  - `src/ui/assets/info.svg`

If any of these files are missing, download or create them as needed. The Fredoka font can be downloaded from [Google Fonts](https://fonts.google.com/specimen/Fredoka).

## Usage

Run the application:

```bash
python main.py
```

## Project Structure

```
EcoGrade/
├── main.py
├── requirements.txt
├── README.md
├── src/
│   ├── main.py
│   ├── __init__.py
│   ├── hardware/
│   ├── utils/
│   └── ui/
│       ├── main_window.py
│       ├── analytics.py
│       ├── start_page.py
│       ├── assets/
│       │   ├── fonts/
│       │   │   ├── Fredoka-Medium.ttf
│       │   │   └── Fredoka-SemiBold.ttf
│       │   ├── LOGO.png
│       │   ├── home.svg
│       │   ├── bar-chart.svg
│       │   ├── corner-up-left.svg
│       │   ├── power.svg
│       │   └── info.svg
│       ├── widgets/
│       └── views/
├── data/
│   └── measurements.db
└── scripts/
    └── update_detection_ids.py
```

## Python Dependencies

All required Python packages are listed in `requirements.txt`. This includes:
- PyQt5 (UI framework)
- opencv-python (camera and image processing)
- numpy, pandas (data processing)
- matplotlib, pyqtgraph (visualization)
- ultralytics, torch (YOLOv11s model)
- openpyxl (Excel export)
- adafruit-pca9685, adafruit-circuitpython-motor, adafruit-blinka, board, busio (servo hardware support)

Install with:
```bash
pip install -r requirements.txt
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
