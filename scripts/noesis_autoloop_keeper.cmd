@echo off
rem NOESIS autoloop keeper: restarts the worker whenever it exits
rem (lock contention with another rider, crash, or operator stop sentinel).
setlocal
set ROOT=%~dp0..
:loop
python "%ROOT%\scripts\noesis_autoloop.py" --root "%ROOT%" --interval 600 --timeout 600
timeout /t 15 /nobreak >nul
goto loop
