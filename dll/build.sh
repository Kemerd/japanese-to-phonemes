#!/bin/bash
# Japanese to Phoneme Converter - FFI/DLL Build Script for Linux/macOS
# Builds a high-performance shared library for use with Dart FFI, Node.js, etc.

set -e

echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║  Japanese to Phoneme Converter - Shared Library Build ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

# Detect platform
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    PLATFORM="linux"
    EXT="so"
    OUTPUT_DIR="output/linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    PLATFORM="macos"
    EXT="dylib"
    OUTPUT_DIR="output/macos"
else
    echo "❌ Unsupported platform: $OSTYPE"
    exit 1
fi

echo "🖥️  Platform detected: $PLATFORM"
echo ""

# Check if CMake is installed
if ! command -v cmake &> /dev/null; then
    echo "❌ CMake not found! Please install CMake first."
    if [[ "$PLATFORM" == "linux" ]]; then
        echo "   Ubuntu/Debian: sudo apt-get install cmake"
        echo "   Fedora/RHEL:   sudo dnf install cmake"
    elif [[ "$PLATFORM" == "macos" ]]; then
        echo "   Homebrew:      brew install cmake"
    fi
    exit 1
fi

# Check if compiler is installed
if ! command -v g++ &> /dev/null && ! command -v clang++ &> /dev/null; then
    echo "❌ C++ compiler not found! Please install g++ or clang++."
    if [[ "$PLATFORM" == "linux" ]]; then
        echo "   Ubuntu/Debian: sudo apt-get install build-essential"
        echo "   Fedora/RHEL:   sudo dnf groupinstall 'Development Tools'"
    elif [[ "$PLATFORM" == "macos" ]]; then
        echo "   Install Xcode Command Line Tools: xcode-select --install"
    fi
    exit 1
fi

# Create build directory
if [ ! -d "build" ]; then
    echo "📁 Creating build directory..."
    mkdir -p build
fi

# Configure CMake project
echo ""
echo "🔧 Configuring CMake project..."
cmake -B build -S . -DCMAKE_BUILD_TYPE=Release

# Build the shared library
echo ""
echo "🔨 Building shared library..."
cmake --build build --config Release

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Copy shared library to output directory
echo ""
echo "📦 Copying output files..."
if [ -f "build/jpn_to_phoneme_ffi.$EXT" ]; then
    cp "build/jpn_to_phoneme_ffi.$EXT" "$OUTPUT_DIR/"
    echo "   ✓ Library: $OUTPUT_DIR/jpn_to_phoneme_ffi.$EXT"
fi

echo ""
echo "✨ Build complete!"
echo ""
echo "🚀 Usage:"
echo "   1. Copy $OUTPUT_DIR/jpn_to_phoneme_ffi.$EXT to your project"
echo "   2. Load it via FFI (Dart, Node.js, Python, etc.)"
echo "   3. See examples/ directory for language-specific usage"
echo ""

