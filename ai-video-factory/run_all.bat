@echo off
setlocal

REM Resolve project root from this script location
set "ROOT=%~dp0"
cd /d "%ROOT%"

set "HOST=0.0.0.0"
set "SCRIPT_PORT=8001"
set "VOICE_PORT=8002"
set "RENDER_PORT=8003"
set "ORCH_PORT=8000"

REM SCRIPT SERVICE
start "script_service" cmd /k "cd /d \"%ROOT%script_service\" && py -m uvicorn main:app --host %HOST% --port %SCRIPT_PORT%"

REM VOICE SERVICE
start "voice_service" cmd /k "cd /d \"%ROOT%voice_service\" && py -m uvicorn main:app --host %HOST% --port %VOICE_PORT%"

REM RENDER SERVICE
start "render_service" cmd /k "cd /d \"%ROOT%render_service\" && py -m uvicorn main:app --host %HOST% --port %RENDER_PORT%"

REM ORCHESTRATOR
start "orchestrator" cmd /k "cd /d \"%ROOT%orchestrator\" && py -m uvicorn main:app --host %HOST% --port %ORCH_PORT%"

endlocal
