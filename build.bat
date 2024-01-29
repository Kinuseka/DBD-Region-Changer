@echo off
python -m venv .venv

call .venv\Scripts\activate
where pip

pip install -r requirements.txt
python -m PyInstaller --noconfirm --onefile --windowed --icon "./res/image2.ico" --uac-admin --add-data "./res/*;res/" "./mainGUI.py" -n "DBDRegion.exe" --version-file "./res/version_file.txt"
pause