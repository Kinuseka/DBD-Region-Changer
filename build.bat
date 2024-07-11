@echo off
python -m venv .venv
set FileName=DBDRegion.exe

call .venv\Scripts\activate
where pip
where python

pip install -r requirements.txt --upgrade
python -OO -m PyInstaller --noconfirm build.spec
certutil -hashfile ./dist/%FileName% SHA256 > temp.txt
for /f "skip=1 tokens=*" %%i in (temp.txt) do (
    echo %%i > ./dist/%FileName%_sha256checksum.txt
    goto :break
)
:break
del temp.txt
echo Hash has been calculated and stored in ./dist/%FileName%_sha256checksum.txt

pause