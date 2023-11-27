@echo off

if not exist ".venv" (
    echo .venv directory not found, creating a new virtual environment.
    python -m venv .venv
) else (
    echo .venv directory found, using the existing virtual environment.
)
call .venv\Scripts\activate.bat
where pip
pip install -r requirements.txt


python -m PyInstaller --noconfirm --onefile --windowed --icon "./res/image2.ico" --uac-admin --add-data "./res;res/" --add-data "./res/image2.jpg;res/" --add-data "./res/image1.png;res/"  "./mainGUI.py" -n "DBDRegion.exe"
pause