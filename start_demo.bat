@echo off
title Industrial Digital Twin Platform

cd /d D:\LUBO\UKTC\Industrial_Digital_Twin_Platform

call .venv\Scripts\activate.bat

start "" ollama serve

timeout /t 5 /nobreak > nul

start "" http://127.0.0.1:8000

waitress-serve ^
  --listen=127.0.0.1:8000 ^
  --threads=8 ^
  config.wsgi:application

pause
