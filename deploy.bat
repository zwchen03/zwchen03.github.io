@echo off
rem Double-click to deploy the website (see deploy.ps1)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0deploy.ps1" %*
