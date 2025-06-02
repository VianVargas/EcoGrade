#!/usr/bin/env python3
import os
import sys

# Add the project root directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import and run the main application
from src.main import main

if __name__ == "__main__":
    main() 