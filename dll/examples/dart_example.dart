// Dart FFI Example for Japanese to Phoneme Converter
// This demonstrates how to use the native library from Dart
//
// Usage:
//   dart run dart_example.dart

import 'dart:ffi' as ffi;
import 'dart:io';
import 'dart:convert';
import 'package:ffi/ffi.dart';

// ============================================================================
// FFI Type Definitions
// ============================================================================

// Function signatures matching the C API
typedef InitNative = ffi.Int32 Function(ffi.Pointer<Utf8> jsonFilePath);
typedef InitDart = int Function(ffi.Pointer<Utf8> jsonFilePath);

typedef ConvertNative = ffi.Int32 Function(
  ffi.Pointer<Utf8> japaneseText,
  ffi.Pointer<ffi.Uint8> outputBuffer,
  ffi.Int32 bufferSize,
  ffi.Pointer<ffi.Int64> processingTimeUs,
);
typedef ConvertDart = int Function(
  ffi.Pointer<Utf8> japaneseText,
  ffi.Pointer<ffi.Uint8> outputBuffer,
  int bufferSize,
  ffi.Pointer<ffi.Int64> processingTimeUs,
);

typedef GetErrorNative = ffi.Pointer<Utf8> Function();
typedef GetErrorDart = ffi.Pointer<Utf8> Function();

typedef GetEntryCountNative = ffi.Int32 Function();
typedef GetEntryCountDart = int Function();

typedef CleanupNative = ffi.Void Function();
typedef CleanupDart = void Function();

typedef VersionNative = ffi.Pointer<Utf8> Function();
typedef VersionDart = ffi.Pointer<Utf8> Function();

// ============================================================================
// Japanese Phoneme Converter Class
// ============================================================================

class JapanesePhonemeConverter {
  late ffi.DynamicLibrary _lib;
  late InitDart _init;
  late ConvertDart _convert;
  late GetErrorDart _getError;
  late GetEntryCountDart _getEntryCount;
  late CleanupDart _cleanup;
  late VersionDart _version;

  /// Load the native library
  /// On Windows: jpn_to_phoneme_ffi.dll
  /// On Linux: jpn_to_phoneme_ffi.so
  /// On macOS: jpn_to_phoneme_ffi.dylib
  JapanesePhonemeConverter(String libraryPath) {
    _lib = ffi.DynamicLibrary.open(libraryPath);

    // Bind native functions to Dart functions
    _init = _lib
        .lookup<ffi.NativeFunction<InitNative>>('jpn_phoneme_init')
        .asFunction();
    _convert = _lib
        .lookup<ffi.NativeFunction<ConvertNative>>('jpn_phoneme_convert')
        .asFunction();
    _getError = _lib
        .lookup<ffi.NativeFunction<GetErrorNative>>('jpn_phoneme_get_error')
        .asFunction();
    _getEntryCount = _lib
        .lookup<ffi.NativeFunction<GetEntryCountNative>>('jpn_phoneme_get_entry_count')
        .asFunction();
    _cleanup = _lib
        .lookup<ffi.NativeFunction<CleanupNative>>('jpn_phoneme_cleanup')
        .asFunction();
    _version = _lib
        .lookup<ffi.NativeFunction<VersionNative>>('jpn_phoneme_version')
        .asFunction();
  }

  /// Initialize the converter with a JSON dictionary file
  bool init(String jsonFilePath) {
    final pathPtr = jsonFilePath.toNativeUtf8();
    try {
      final result = _init(pathPtr);
      if (result == 0) {
        print('❌ Initialization failed: ${getError()}');
        return false;
      }
      return true;
    } finally {
      malloc.free(pathPtr);
    }
  }

  /// Convert Japanese text to phonemes
  /// Returns a tuple of (phonemes, processingTimeMicroseconds)
  (String, int)? convert(String japaneseText) {
    final textPtr = japaneseText.toNativeUtf8();
    final buffer = malloc<ffi.Uint8>(4096);
    final timePtr = malloc<ffi.Int64>();

    try {
      final length = _convert(textPtr, buffer, 4096, timePtr);
      
      if (length < 0) {
        print('❌ Conversion failed: ${getError()}');
        return null;
      }

      final result = utf8.decode(buffer.asTypedList(length));
      final time = timePtr.value;

      return (result, time);
    } finally {
      malloc.free(textPtr);
      malloc.free(buffer);
      malloc.free(timePtr);
    }
  }

  /// Get the last error message
  String getError() {
    final errorPtr = _getError();
    return errorPtr.toDartString();
  }

  /// Get the number of entries in the dictionary
  int getEntryCount() {
    return _getEntryCount();
  }

  /// Get library version
  String getVersion() {
    final versionPtr = _version();
    return versionPtr.toDartString();
  }

  /// Clean up resources (call when done)
  void dispose() {
    _cleanup();
  }
}

// ============================================================================
// Example Usage
// ============================================================================

void main() {
  print('');
  print('╔══════════════════════════════════════════════════════════╗');
  print('║  Japanese → Phoneme Converter (Dart FFI Example)        ║');
  print('╚══════════════════════════════════════════════════════════╝');
  print('');

  // Determine library path based on platform
  String libraryPath;
  if (Platform.isWindows) {
    libraryPath = '../output/windows/jpn_to_phoneme_ffi.dll';
  } else if (Platform.isLinux) {
    libraryPath = '../output/linux/jpn_to_phoneme_ffi.so';
  } else if (Platform.isMacOS) {
    libraryPath = '../output/macos/jpn_to_phoneme_ffi.dylib';
  } else {
    print('❌ Unsupported platform');
    return;
  }

  // Check if library exists
  if (!File(libraryPath).existsSync()) {
    print('❌ Library not found: $libraryPath');
    print('   Please build the library first using build.bat or build.sh');
    return;
  }

  try {
    // Create converter instance
    final converter = JapanesePhonemeConverter(libraryPath);
    print('📚 Library version: ${converter.getVersion()}');
    print('');

    // Initialize with dictionary
    print('🔥 Loading phoneme dictionary...');
    if (!converter.init('../../ja_phonemes.json')) {
      return;
    }

    final entryCount = converter.getEntryCount();
    print('✅ Loaded $entryCount entries');
    print('');
    print('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    print('');

    // Test conversion examples
    final examples = [
      'こんにちは',
      '日本語',
      '東京',
      'ありがとうございます',
      '今日はいい天気ですね',
    ];

    for (final text in examples) {
      final result = converter.convert(text);
      if (result != null) {
        final (phonemes, time) = result;
        print('Input:    $text');
        print('Phonemes: $phonemes');
        print('Time:     ${time}μs (${(time / 1000.0).toStringAsFixed(2)}ms)');
        print('');
      }
    }

    print('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    print('✨ Conversion complete!');
    print('');

    // Clean up
    converter.dispose();
  } catch (e) {
    print('❌ Error: $e');
  }
}

