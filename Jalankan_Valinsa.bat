@echo off
title VALINSA CLOUD RUNNER
cd /d "%~dp0"
echo Menyiapkan lingkungan Cloud...
:: Menambahkan library koneksi Google Sheets
pip install streamlit pandas st-gsheets-connection
cls
echo VALINSA CLOUD sedang dijalankan...
:: Pastikan "valinsa_app.py" adalah nama file kodingan v4.0 kamu
streamlit run valinsa_app.py
pause