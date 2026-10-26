@echo off
cd /d %~dp0
if exist venv\Scripts\activate.bat call venv\Scripts\activate.bat
rem Optional: lock Admin Edit Mode with a password (remove "rem" and set your own)
rem set PS_SOP_ADMIN_PASSWORD=choose-a-password
streamlit run app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true
pause
