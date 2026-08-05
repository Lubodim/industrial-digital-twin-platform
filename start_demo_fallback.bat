@echo off
title Industrial Digital Twin Platform - Fallback

cd /d D:\LUBO\UKTC\Industrial_Digital_Twin_Platform

call .venv\Scripts\activate.bat

start "" ollama serve

timeout /t 5 /nobreak > nul

start "" http://127.0.0.1:8000

python manage.py runserver 127.0.0.1:8000

pause
