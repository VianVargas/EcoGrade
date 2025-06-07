# EcoGrade - Environmental Analysis Dashboard

A modern PyQt5-based dashboard for environmental data analysis and visualization.

## Features

- Modern and responsive UI with gradient backgrounds and dynamic animations
- Interactive data visualization and analytics
- Real-time data processing and analysis
- Statistical analysis and reporting
- Multiple view support (Front Page, Main View, Analytics, About)
- Cross-platform compatibility

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
  - `src/ui/assets/LOGO.ico`
  - `src/ui/assets/video.svg`
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

The application features a modern interface with:

- A front page with gradient animations and dynamic UI elements
- A main view for primary functionality with real-time camera feeds
- An analytics view for data visualization with interactive charts
- An about page with team information and project details
- A sidebar for easy navigation between views

## Project Structure

```
EcoGrade/
├── main.py                 # Application entry point
├── requirements.txt        # Python dependencies
├── README.md              # Project documentation
├── src/
│   ├── __init__.py
│   ├── ui/
│   │   ├── main_window.py # Main window implementation
│   │   ├── analytics.py   # Analytics widget
│   │   ├── assets/        # UI assets (fonts, icons)
│   │   ├── widgets/       # Custom widgets
│   │   └── views/         # Different view implementations
│   │       ├── front_page.py
│   │       ├── main_view.py
│   │       └── about_view.py
│   └── utils/             # Utility functions
└── data/                  # Data storage
```

## Python Dependencies

All required Python packages are listed in `requirements.txt`. This includes:

- PyQt5 (UI framework)
- numpy, pandas (data processing)
- matplotlib, pyqtgraph (visualization)
- openpyxl (Excel export)

Install with:

```bash
pip install -r requirements.txt
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Dependencies

- PyQt5: GUI framework
- OpenCV: Computer vision processing
- NumPy: Numerical computations
- Pandas: Data manipulation and analysis
- PyQtGraph: Real-time plotting
- Openpyxl: Excel file export support
- Matplotlib: Additional plotting capabilities
- Ultralytics: YOLO model integration
- PyTorch: Deep learning framework

## Data Export

The analytics view includes an export feature that allows you to:

- Export filtered detection data to Excel
- Choose custom save location
- Rename exported files
- Maintain timestamp formatting
- Filter data before export

## Acknowledgments

- YOLO model for object detection
- PyQt5 for the GUI framework
- All contributors and supporters of the project
