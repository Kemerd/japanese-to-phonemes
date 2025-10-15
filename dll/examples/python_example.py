#!/usr/bin/env python3
"""
Python ctypes Example for Japanese to Phoneme Converter
This demonstrates how to use the native library from Python

Usage:
    python python_example.py
"""

import ctypes
import os
import platform
from pathlib import Path
from typing import Optional, Tuple

# ============================================================================
# Platform-specific library loading
# ============================================================================

def get_library_path() -> str:
    """Get the appropriate library path for the current platform"""
    system = platform.system()
    base_path = Path(__file__).parent.parent / "output"
    
    if system == "Windows":
        return str(base_path / "windows" / "jpn_to_phoneme_ffi.dll")
    elif system == "Linux":
        return str(base_path / "linux" / "jpn_to_phoneme_ffi.so")
    elif system == "Darwin":
        return str(base_path / "macos" / "jpn_to_phoneme_ffi.dylib")
    else:
        raise RuntimeError(f"Unsupported platform: {system}")

# ============================================================================
# Japanese Phoneme Converter Class
# ============================================================================

class JapanesePhonemeConverter:
    """Wrapper class for the native Japanese phoneme converter library"""
    
    def __init__(self, library_path: str):
        """
        Initialize the converter by loading the native library
        
        Args:
            library_path: Path to the native library file
        """
        # Load the native library
        self.lib = ctypes.CDLL(library_path)
        
        # Define function signatures
        # jpn_phoneme_init(const char* json_file_path) -> int32
        self.lib.jpn_phoneme_init.argtypes = [ctypes.c_char_p]
        self.lib.jpn_phoneme_init.restype = ctypes.c_int32
        
        # jpn_phoneme_convert(const char* text, char* buffer, int32 size, int64* time) -> int32
        self.lib.jpn_phoneme_convert.argtypes = [
            ctypes.c_char_p,
            ctypes.c_char_p,
            ctypes.c_int32,
            ctypes.POINTER(ctypes.c_int64)
        ]
        self.lib.jpn_phoneme_convert.restype = ctypes.c_int32
        
        # jpn_phoneme_get_error() -> const char*
        self.lib.jpn_phoneme_get_error.argtypes = []
        self.lib.jpn_phoneme_get_error.restype = ctypes.c_char_p
        
        # jpn_phoneme_get_entry_count() -> int32
        self.lib.jpn_phoneme_get_entry_count.argtypes = []
        self.lib.jpn_phoneme_get_entry_count.restype = ctypes.c_int32
        
        # jpn_phoneme_cleanup() -> void
        self.lib.jpn_phoneme_cleanup.argtypes = []
        self.lib.jpn_phoneme_cleanup.restype = None
        
        # jpn_phoneme_version() -> const char*
        self.lib.jpn_phoneme_version.argtypes = []
        self.lib.jpn_phoneme_version.restype = ctypes.c_char_p
    
    def init(self, json_file_path: str) -> bool:
        """
        Initialize the converter with a JSON dictionary file
        
        Args:
            json_file_path: Path to the ja_phonemes.json file
            
        Returns:
            True on success, False on failure
        """
        result = self.lib.jpn_phoneme_init(json_file_path.encode('utf-8'))
        if result == 0:
            error = self.get_error()
            print(f"❌ Initialization failed: {error}")
            return False
        return True
    
    def convert(self, japanese_text: str) -> Optional[Tuple[str, int]]:
        """
        Convert Japanese text to phonemes
        
        Args:
            japanese_text: Input Japanese text
            
        Returns:
            Tuple of (phonemes, processing_time_us) or None on error
        """
        # Allocate buffer for output
        buffer_size = 4096
        buffer = ctypes.create_string_buffer(buffer_size)
        time_ptr = ctypes.c_int64()
        
        # Call the native function
        length = self.lib.jpn_phoneme_convert(
            japanese_text.encode('utf-8'),
            buffer,
            buffer_size,
            ctypes.byref(time_ptr)
        )
        
        if length < 0:
            error = self.get_error()
            print(f"❌ Conversion failed: {error}")
            return None
        
        # Decode result
        phonemes = buffer.value.decode('utf-8')
        time_us = time_ptr.value
        
        return phonemes, time_us
    
    def get_error(self) -> str:
        """Get the last error message"""
        error_ptr = self.lib.jpn_phoneme_get_error()
        return error_ptr.decode('utf-8') if error_ptr else ""
    
    def get_entry_count(self) -> int:
        """Get the number of entries in the dictionary"""
        return self.lib.jpn_phoneme_get_entry_count()
    
    def get_version(self) -> str:
        """Get library version"""
        version_ptr = self.lib.jpn_phoneme_version()
        return version_ptr.decode('utf-8') if version_ptr else ""
    
    def dispose(self):
        """Clean up resources (call when done)"""
        self.lib.jpn_phoneme_cleanup()
    
    def __enter__(self):
        """Context manager support"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager cleanup"""
        self.dispose()

# ============================================================================
# Example Usage
# ============================================================================

def main():
    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  Japanese → Phoneme Converter (Python ctypes Example)   ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()
    
    try:
        # Get library path for current platform
        library_path = get_library_path()
        
        # Check if library exists
        if not os.path.exists(library_path):
            print(f"❌ Library not found: {library_path}")
            print("   Please build the library first using build.bat or build.sh")
            return
        
        # Create converter instance using context manager
        with JapanesePhonemeConverter(library_path) as converter:
            print(f"📚 Library version: {converter.get_version()}")
            print()
            
            # Initialize with dictionary
            print("🔥 Loading phoneme dictionary...")
            json_path = str(Path(__file__).parent.parent.parent / "ja_phonemes.json")
            if not converter.init(json_path):
                return
            
            entry_count = converter.get_entry_count()
            print(f"✅ Loaded {entry_count} entries")
            print()
            print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            print()
            
            # Test conversion examples
            examples = [
                "こんにちは",
                "日本語",
                "東京",
                "ありがとうございます",
                "今日はいい天気ですね",
            ]
            
            for text in examples:
                result = converter.convert(text)
                if result:
                    phonemes, time_us = result
                    time_ms = time_us / 1000.0
                    print(f"Input:    {text}")
                    print(f"Phonemes: {phonemes}")
                    print(f"Time:     {time_us}μs ({time_ms:.2f}ms)")
                    print()
            
            print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            print("✨ Conversion complete!")
            print()
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

