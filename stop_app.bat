@echo off
echo Stopping CritterVid...

REM Packaged app: stop CritterVid.exe and everything it started (/T), such as
REM the pipeline and FFmpeg
taskkill /F /T /IM CritterVid.exe >nul 2>&1

REM Development mode (run_app.bat): find "streamlit run app.py" by its command
REM line, whatever port it chose, instead of killing whatever listens on 8501.
REM app.py must be the script being run (optionally with a folder), not just
REM mentioned later on the command line. \x22 is a double quote, written as a
REM regex escape so it doesn't end the quoted -Command string.
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.ProcessId -ne $PID -and $_.CommandLine -match 'streamlit(\.exe)?\W+run\s+(\x22([^\x22]*[\\/])?app\.py\x22|([^\x22\s]*[\\/])?app\.py(\s|$))' } | ForEach-Object { taskkill /F /T /PID $_.ProcessId 2>&1 | Out-Null }"

echo Done!
timeout /t 2
