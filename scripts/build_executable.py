import os
import sys
import shutil
from pathlib import Path

def build_executable():
    # Get the project root directory
    project_root = Path(__file__).parent.parent
    
    # Create a spec file for PyInstaller
    spec_content = f"""
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['{project_root}/main.py'],
    pathex=['{project_root}'],
    binaries=[],
    datas=[
        ('{project_root}/src/ui/assets', 'src/ui/assets'),
        ('{project_root}/EcoGrade_v11n_SGD.pt', '.'),
        ('{project_root}/best.pt', '.'),
    ],
    hiddenimports=[
        'PyQt5',
        'numpy',
        'pandas',
        'cv2',
        'pyqtgraph',
        'openpyxl',
        'matplotlib',
        'ultralytics',
        'torch',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='EcoGrade',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='{project_root}/src/ui/assets/LOGO.ico'
)
"""
    
    # Write the spec file
    spec_path = project_root / 'EcoGrade.spec'
    with open(spec_path, 'w') as f:
        f.write(spec_content)
    
    # Install PyInstaller if not already installed
    os.system(f"{sys.executable} -m pip install pyinstaller")
    
    # Build the executable
    os.system(f"pyinstaller --clean {spec_path}")
    
    # Clean up
    spec_path.unlink()
    
    print("Build completed! The executable can be found in the 'dist' directory.")

if __name__ == "__main__":
    build_executable() 