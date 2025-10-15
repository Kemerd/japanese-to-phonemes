@echo off
REM Japanese to Phoneme Converter - FFI/DLL Build Script for Windows
REM Builds a high-performance DLL for use with Dart FFI, Node.js, etc.

echo.
echo ╔════════════════════════════════════════════════════════╗
echo ║  Japanese to Phoneme Converter - Windows DLL Build    ║
echo ╚════════════════════════════════════════════════════════╝
echo.

REM Check if CMake is installed
cmake --version >nul 2>&1
if errorlevel 1 (
    echo ❌ CMake not found! Please install CMake first.
    echo    Download: https://cmake.org/download/
    exit /b 1
)

REM Create build directory
if not exist build (
    echo 📁 Creating build directory...
    mkdir build
)

REM Configure CMake project
echo.
echo 🔧 Configuring CMake project...
cmake -B build -S . -DCMAKE_BUILD_TYPE=Release
if errorlevel 1 (
    echo ❌ CMake configuration failed!
    exit /b 1
)

REM Build the DLL
echo.
echo 🔨 Building DLL...
cmake --build build --config Release
if errorlevel 1 (
    echo ❌ Build failed!
    exit /b 1
)

REM Copy DLL to output directory
echo.
echo 📦 Copying output files...
if exist build\Release\jpn_to_phoneme_ffi.dll (
    copy build\Release\jpn_to_phoneme_ffi.dll output\windows\ >nul 2>&1
    echo    ✓ DLL: output\windows\jpn_to_phoneme_ffi.dll
) else if exist build\jpn_to_phoneme_ffi.dll (
    copy build\jpn_to_phoneme_ffi.dll output\windows\ >nul 2>&1
    echo    ✓ DLL: output\windows\jpn_to_phoneme_ffi.dll
)

echo.
echo ✨ Build complete!
echo.
echo 🚀 Usage:
echo    1. Copy output\windows\jpn_to_phoneme_ffi.dll to your project
echo    2. Load it via FFI (Dart, Node.js, Python, etc.)
echo    3. See examples\ directory for language-specific usage
echo.

