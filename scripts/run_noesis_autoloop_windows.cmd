@echo off
setlocal
set "ROOT=B:\Downloads\Portable\NOESIS-VC-ONE\models\llm\NOESIS-3.5B-A0.5B-DUBBING-FILM\_research_2026-08\NOESIS-Harness-Agent-Memory"
set "PY=C:\Users\djbionicl\AppData\Local\Programs\Python\Python311\python.exe"
if not exist "%ROOT%\scripts\noesis_autoloop.py" exit /b 20
if not exist "%PY%" exit /b 21
cd /d "%ROOT%"
"%PY%" scripts\noesis_autoloop.py --interval 900 --timeout 900
exit /b %errorlevel%
