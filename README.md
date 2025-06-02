# EcoGrade - Object Detection Dashboard

A modern PyQt5-based dashboard for object detection and analysis.

## Features

- Modern and responsive UI with a dark theme
- Multiple camera feed support
- Real-time object detection
- Statistical analysis and visualization
- Interactive charts and graphs

## Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/ecograde.git
cd ecograde
```

2. Create a virtual environment (recommended):

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Run the application:

```bash
python src/main.py
```

## Project Structure

```
ecograde/
├── src/
│   ├── ui/
│   │   ├── widgets/
│   │   │   ├── base_widgets.py
│   │   │   ├── chart_widgets.py
│   │   │   ├── grid_widget.py
│   │   │   └── sidebar_button.py
│   │   ├── views/
│   │   │   ├── front_page.py
│   │   │   ├── main_view.py
│   │   │   └── stats_view.py
│   │   └── main_window.py
│   └── main.py
├── requirements.txt
└── README.md
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Font Dependency

This project uses the "Fredoka" font for the main title. Please download the font and place the file as:

    assets/fonts/Fredoka-Medium.ttf

You can download the font from Google Fonts: https://fonts.google.com/specimen/Fredoka
