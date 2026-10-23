@echo off
setlocal EnableDelayedExpansion
REM Show the window
title RimDeck Update
mode con: cols=100 lines=30
echo RimDeck update in progress... Please wait.

REM ========================================================================
REM RimDeck Updater Script (Windows 10 & 11 Compatible)
REM Safely backs up and updates RimDeck from provided temp path
REM Usage: update.bat <temp_update_path> <log_path>
REM ========================================================================

REM Get arguments
set "TEMP_UPDATE_PATH=%~1"
set "LOG_PATH=%~2"

REM Validate arguments
if "%TEMP_UPDATE_PATH%" == "" (
    echo ERROR: Temp update path is required as first argument.
    if defined LOG_PATH (
        echo [%date% %time%] ERROR: Temp update path is required as first argument. >> "%LOG_PATH%"
    )
    pause
    exit /b 1
)

REM Log start
if defined LOG_PATH (
    echo [%date% %time%] INFO: Starting RimDeck update process... >> "%LOG_PATH%"
    echo [%date% %time%] INFO: Temp update path: %TEMP_UPDATE_PATH% >> "%LOG_PATH%"
    echo [%date% %time%] INFO: Log path: %LOG_PATH% >> "%LOG_PATH%"
) else (
    echo [%date% %time%] INFO: Starting RimDeck update process...
    echo [%date% %time%] INFO: Temp update path: %TEMP_UPDATE_PATH%
)

REM Get current directory (should be application folder)
set "current_dir=%CD%"
if "%current_dir:~-1%"=="\" (
    set "current_dir_no_slash=%current_dir:~0,-1%"
) else (
    set "current_dir_no_slash=%current_dir%"
)

set "executable_path=%current_dir%\RimDeck.exe"
set "update_source_folder=%TEMP_UPDATE_PATH%"

if defined LOG_PATH (
    echo [%date% %time%] INFO: Current directory: %current_dir% >> "%LOG_PATH%"
    echo [%date% %time%] INFO: Update source folder: %update_source_folder% >> "%LOG_PATH%"
    echo [%date% %time%] INFO: Executable path: %executable_path% >> "%LOG_PATH%"
) else (
    echo [%date% %time%] INFO: Current directory: %current_dir%
    echo [%date% %time%] INFO: Update source folder: %update_source_folder%
    echo [%date% %time%] INFO: Executable path: %executable_path%
)

REM Attempt to stop RimDeck if it's already running
if defined LOG_PATH (
    echo [%date% %time%] INFO: Stopping RimDeck process... >> "%LOG_PATH%"
) else (
    echo [%date% %time%] INFO: Stopping RimDeck process...
)
taskkill /F /im RimDeck.exe >nul 2>&1
if errorlevel 1 (
    if defined LOG_PATH (
        echo [%date% %time%] INFO: No running RimDeck process found. >> "%LOG_PATH%"
    ) else (
        echo [%date% %time%] INFO: No running RimDeck process found.
    )
) else (
    if defined LOG_PATH (
        echo [%date% %time%] INFO: RimDeck process terminated. >> "%LOG_PATH%"
    ) else (
        echo [%date% %time%] INFO: RimDeck process terminated.
    )
    ping -n 3 127.0.0.1 >nul
)

REM Check if update folder exists
if not exist "%update_source_folder%" (
    if defined LOG_PATH (
        echo [%date% %time%] ERROR: Update source folder does not exist: %update_source_folder% >> "%LOG_PATH%"
    ) else (
        echo [%date% %time%] ERROR: Update source folder does not exist: %update_source_folder%
    )
    pause
    exit /b 1
)

REM Check if RimDeck.exe exists in the update folder
if not exist "%update_source_folder%\RimDeck.exe" (
    if defined LOG_PATH (
        echo [%date% %time%] ERROR: RimDeck.exe not found in update source folder. >> "%LOG_PATH%"
    ) else (
        echo [%date% %time%] ERROR: RimDeck.exe not found in update source folder.
    )
    pause
    exit /b 1
)

REM Show update information
echo.
echo ========================================================================
echo RimDeck Update Ready
echo Source: %update_source_folder%
echo Target: %current_dir%
echo.
echo The update will start automatically...
echo ========================================================================
if defined LOG_PATH (
    echo. >> "%LOG_PATH%"
    echo RimDeck Update Ready >> "%LOG_PATH%"
    echo Source: %update_source_folder% >> "%LOG_PATH%"
    echo Target: %current_dir% >> "%LOG_PATH%"
    echo. >> "%LOG_PATH%"
    echo The update will start automatically... >> "%LOG_PATH%"
    echo ======================================================================== >> "%LOG_PATH%"
)

REM Begin update by copying files from temp update folder to app folder
if defined LOG_PATH (
    echo [%date% %time%] INFO: Updating RimDeck files... >> "%LOG_PATH%"
    echo [%date% %time%] INFO: Source: %update_source_folder% >> "%LOG_PATH%"
    echo [%date% %time%] INFO: Target: %current_dir_no_slash% >> "%LOG_PATH%"
) else (
    echo [%date% %time%] INFO: Updating RimDeck files...
    echo [%date% %time%] INFO: Source: %update_source_folder%
    echo [%date% %time%] INFO: Target: %current_dir_no_slash%
)

REM Use robocopy for file copying with error handling
if defined LOG_PATH (
    echo [%date% %time%] INFO: Starting robocopy operation... >> "%LOG_PATH%"
)
robocopy "%update_source_folder%" "%current_dir_no_slash%" /E /COPY:DAT /R:3 /W:5 /NFL /NDL
set "robocopy_exit=%errorlevel%"
if defined LOG_PATH (
    echo [%date% %time%] INFO: Robocopy completed with exit code: !robocopy_exit! >> "%LOG_PATH%"
)

REM Robocopy exit codes: 0=no errors, 1=files copied, 2=extra files, 4=mismatches, 8=some failures, 16=serious error
REM For update, 0, 1, 2, 4 are generally acceptable
if !robocopy_exit! LEQ 4 goto :robocopy_success
goto :robocopy_error

:robocopy_success
if defined LOG_PATH (
    echo [%date% %time%] INFO: Files copied successfully. >> "%LOG_PATH%"
) else (
    echo [%date% %time%] INFO: Files copied successfully.
)
goto :robocopy_done

:robocopy_error
if defined LOG_PATH (
    echo [%date% %time%] ERROR: Update failed during file copy. >> "%LOG_PATH%"
) else (
    echo [%date% %time%] ERROR: Update failed during file copy.
)
pause
exit /b 1

:robocopy_done

REM Give time for filesystem to sync
ping -n 4 127.0.0.1 >nul

REM Verify the new executable exists
if exist "%executable_path%" (
    if defined LOG_PATH (
        echo [%date% %time%] INFO: RimDeck.exe verified after update. >> "%LOG_PATH%"
    ) else (
        echo [%date% %time%] INFO: RimDeck.exe verified after update.
    )
) else (
    if defined LOG_PATH (
        echo [%date% %time%] ERROR: RimDeck.exe not found after update. >> "%LOG_PATH%"
    ) else (
        echo [%date% %time%] ERROR: RimDeck.exe not found after update.
    )
    pause
    exit /b 1
)

REM Cleanup temp update files
if defined LOG_PATH (
    echo [%date% %time%] INFO: Cleaning up temporary files... >> "%LOG_PATH%"
    echo [%date% %time%] INFO: Removing: %update_source_folder% >> "%LOG_PATH%"
) else (
    echo [%date% %time%] INFO: Cleaning up temporary files...
    echo [%date% %time%] INFO: Removing: %update_source_folder%
)
rd /s /q "%update_source_folder%" 2>nul
if exist "%update_source_folder%" (
    if defined LOG_PATH (
        echo [%date% %time%] WARNING: Failed to remove temporary folder. >> "%LOG_PATH%"
    ) else (
        echo [%date% %time%] WARNING: Failed to remove temporary folder.
    )
) else (
    if defined LOG_PATH (
        echo [%date% %time%] INFO: Temporary files cleaned up. >> "%LOG_PATH%"
    ) else (
        echo [%date% %time%] INFO: Temporary files cleaned up.
    )
)

REM Launch updated RimDeck
if defined LOG_PATH (
    echo [%date% %time%] INFO: Launching RimDeck from: %executable_path% >> "%LOG_PATH%"
) else (
    echo [%date% %time%] INFO: Launching RimDeck from: %executable_path%
)

REM Give additional time for files to fully settle
ping -n 2 127.0.0.1 >nul

REM Start RimDeck with better error handling
if exist "%executable_path%" (
    echo Launching: %executable_path%
    REM Change to app directory and launch with proper context
    cd /d "%current_dir%"

    REM Use PowerShell to start the process for better reliability
    powershell -command "Start-Process '%executable_path%' -WorkingDirectory '%current_dir%'"

    REM Wait for process to fully start (give it more time)
    ping -n 6 127.0.0.1 >nul
) else (
    if defined LOG_PATH (
        echo [%date% %time%] ERROR: RimDeck.exe not found at: %executable_path% >> "%LOG_PATH%"
    ) else (
        echo [%date% %time%] ERROR: RimDeck.exe not found at: %executable_path%
    )
    echo.
    echo ERROR: RimDeck.exe not found at expected location: %executable_path%
    echo.
    echo Press any key to close this window...
    pause >nul
    exit /b 1
)

REM Confirm process launch (retry up to 5 times with longer wait)
set "launch_confirmed=0"
set "attempt=0"
:check_launch
set /a attempt+=1
if !attempt! gtr 5 goto :launch_complete

tasklist /fi "imagename eq RimDeck.exe" /fo csv | find /i "RimDeck.exe" >nul
if not errorlevel 1 (
    set "launch_confirmed=1"
    goto :launch_success
)
ping -n 3 127.0.0.1 >nul
goto :check_launch

:launch_complete

:launch_success
if !launch_confirmed! EQU 1 (
    if defined LOG_PATH (
        echo [%date% %time%] INFO: RimDeck update completed and launched successfully! >> "%LOG_PATH%"
    ) else (
        echo [%date% %time%] INFO: RimDeck update completed and launched successfully!
    )
    echo.
    echo Update completed successfully! The new RimDeck version is now running.
    echo This window will close automatically in 5 seconds...
    ping -n 6 127.0.0.1 >nul
) else (
    if defined LOG_PATH (
        echo [%date% %time%] WARNING: RimDeck may not have started. >> "%LOG_PATH%"
        echo [%date% %time%] INFO: You can start it manually from: %executable_path% >> "%LOG_PATH%"
    ) else (
        echo [%date% %time%] WARNING: RimDeck may not have started.
        echo [%date% %time%] INFO: You can start it manually from: %executable_path%
    )
    echo.
    echo Note: RimDeck may still be starting in the background.
    echo Press any key to close this window...
    pause >nul
)



exit
