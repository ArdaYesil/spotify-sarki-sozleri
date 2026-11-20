@echo off
rem Spotify Şarkı Sözleri penceresini konsolsuz başlatır.
rem İlk çalıştırmada gerekli Python paketlerini kurar.
cd /d "%~dp0"
python -m pip show winrt-Windows.Media.Control >nul 2>&1 || python -m pip install --quiet -r requirements.txt
start "" pythonw "%~dp0sozler.py"
