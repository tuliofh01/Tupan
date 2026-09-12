@echo off
REM ===========================================================================
REM  TUPAN, MAQUINA DE CHUVA - Build Script Windows 10/11 (MSVC 2019/2022)
REM  --------------------------------------------------------------------------
REM  Uso: scripts\build-windows.bat [clean] [package] [nogui]
REM  Saida:
REM    build-win\                     -> artefatos CMake (.pyd de tupan_native)
REM    dist\windows-x86_64\bin\        -> tupan_sim.exe, tupan_tests.exe, .pyd
REM  Requer: CMake >= 3.25, Visual Studio 2019/2022 (C++23), Python 3.10+.
REM ===========================================================================
setlocal EnableDelayedExpansion
set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "ROOT_DIR=%%~fI"
set "SOURCE_DIR=%ROOT_DIR%"
set "BUILD_DIR=%ROOT_DIR%\build-win"
set "DIST_DIR=%ROOT_DIR%\dist\windows-x86_64"
set "PACKAGE=0"
set "CLEAN=0"
set "WITH_STUDIO=ON"

:parse
if "%~1"=="" goto after_parse
if /I "%~1"=="clean"   set "CLEAN=1"
if /I "%~1"=="package" set "PACKAGE=1"
if /I "%~1"=="nostudio" set "WITH_STUDIO=OFF"
shift
goto parse
:after_parse

echo [BUILD] Verificando dependencias...
where cmake >nul 2>nul || (echo [ERROR] cmake nao encontrado no PATH. & exit /b 1)
where python >nul 2>nul || (echo [ERROR] python nao encontrado no PATH. & exit /b 1)

REM Descobre o diretorio CMake do pybind11 instalado via pip.
set "PYBIND11_ARG="
for /f "delims=" %%D in ('python -c "import pybind11,sys; sys.stdout.write(pybind11.get_cmake_dir())" 2^>nul') do set "PYBIND11_DIR=%%D"
if defined PYBIND11_DIR (
  set "PYBIND11_ARG=-Dpybind11_DIR=!PYBIND11_DIR!"
  echo [OK] pybind11: !PYBIND11_DIR!
) else (
  echo [WARN] pybind11 ausente: pip install pybind11
)

if "%CLEAN%"=="1" (
  echo [BUILD] Limpando...
  if exist "%BUILD_DIR%" rmdir /s /q "%BUILD_DIR%"
  if exist "%DIST_DIR%"  rmdir /s /q "%DIST_DIR%"
)

echo [BUILD] Configurando CMake...
cmake -S "%SOURCE_DIR%" -B "%BUILD_DIR%" -DCMAKE_BUILD_TYPE=Release -DTUPAN_WITH_STUDIO=%WITH_STUDIO% -DTUPAN_WITH_PYBIND=ON !PYBIND11_ARG!
if errorlevel 1 (echo [ERROR] Falha na configuracao do CMake. & exit /b 1)

echo [BUILD] Compilando...
cmake --build "%BUILD_DIR%" --config Release -j
if errorlevel 1 (echo [ERROR] Falha na compilacao. & exit /b 1)

echo [BUILD] Executando testes (CTest)...
ctest --test-dir "%BUILD_DIR%" -C Release --output-on-failure

echo [BUILD] Organizando "%DIST_DIR%"...
if not exist "%DIST_DIR%\bin" mkdir "%DIST_DIR%\bin"
if not exist "%DIST_DIR%\share\tupan" mkdir "%DIST_DIR%\share\tupan"
copy /Y "%BUILD_DIR%\Release\*.exe" "%DIST_DIR%\bin\" >nul 2>nul
if exist "%BUILD_DIR%\Release\tupan_native*.pyd" copy /Y "%BUILD_DIR%\Release\tupan_native*.pyd" "%DIST_DIR%\bin\" >nul
copy /Y "%SOURCE_DIR%\tupan_constants.json" "%DIST_DIR%\share\tupan\" >nul

if "%PACKAGE%"=="1" (
  echo [BUILD] Gerando pacote .zip...
  if not exist "%ROOT_DIR%\dist\packages" mkdir "%ROOT_DIR%\dist\packages"
  powershell -NoProfile -Command "Compress-Archive -Path '%DIST_DIR%\*' -DestinationPath '%ROOT_DIR%\dist\packages\tupan-0.1.0-windows-x86_64.zip' -Force"
  echo [OK] Pacote: %ROOT_DIR%\dist\packages\tupan-0.1.0-windows-x86_64.zip
)

echo [OK] Build Windows concluido!
echo   Binarios: %DIST_DIR%\bin\
endlocal
