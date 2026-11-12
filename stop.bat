@echo off
rem Vidura: stop everything (same as option 2 in start.bat). Kills only Vidura's processes.
call "%~dp0start.bat" stop
ping -n 4 127.0.0.1 >nul
