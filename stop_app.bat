@echo off
echo Stopping CritterVid...

REM Packaged app: stop CritterVid.exe and everything it started (/T), such as
REM the pipeline and FFmpeg
taskkill /F /T /IM CritterVid.exe >nul 2>&1

REM Development mode (run_app.bat): find "streamlit run app.py" by its command
REM line, whatever port it chose, instead of killing whatever listens on 8501
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.ProcessId -ne $PID -and $_.CommandLine -match 'streamlit(\.exe)?\W+run\W+(.*\W)?app\.py' } | ForEach-Object { taskkill /F /T /PID $_.ProcessId | Out-Null }"

echo Done!
timeout /t 2
