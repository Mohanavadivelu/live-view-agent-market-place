# Puts the planted bugs back: the test bench's sources as committed, and nothing the fixer added.
# Then rebuild and push (or install) the app again.
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
git -C $repo checkout HEAD -- testbench/app/src
git -C $repo clean -fdq -- testbench/app/src
Write-Host "Test bench sources reset. Rebuild: cd testbench; .\gradlew.bat --offline :app:assembleDebug"
