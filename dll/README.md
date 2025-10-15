# Japanese to Phoneme Converter - FFI/DLL Edition

Cross-platform shared library for **blazing fast** Japanese text to IPA phoneme conversion. Compatible with any language that supports FFI (Foreign Function Interface).

## 🚀 Features

- **Ultra-Fast Performance**: Microsecond-level conversion using optimized trie structure
- **Cross-Platform**: Works on Windows (DLL), Linux (SO), and macOS (DYLIB)
- **Universal FFI**: Compatible with Dart, Node.js, Python, C#, Go, and more
- **Zero Dependencies**: Self-contained native library with no runtime dependencies
- **Thread-Safe**: Safe for multi-threaded applications
- **Simple API**: Just 6 functions to learn

## 📦 Building the Library

### Prerequisites

- **CMake** 3.15 or later
- **C++ Compiler** with C++17 support:
  - Windows: MSVC (Visual Studio 2017+) or MinGW
  - Linux: GCC 7+ or Clang 5+
  - macOS: Xcode Command Line Tools (Clang)

### Windows

```batch
cd dll
build.bat
```

Output: `output/windows/jpn_to_phoneme_ffi.dll`

### Linux / macOS

```bash
cd dll
chmod +x build.sh
./build.sh
```

Output:
- Linux: `output/linux/jpn_to_phoneme_ffi.so`
- macOS: `output/macos/jpn_to_phoneme_ffi.dylib`

## 📖 API Reference

### C Function Signatures

```c
// Initialize the converter with a JSON dictionary file
int jpn_phoneme_init(const char* json_file_path);

// Convert Japanese text to phonemes
int jpn_phoneme_convert(
    const char* japanese_text,
    char* output_buffer,
    int buffer_size,
    int64_t* processing_time_us
);

// Get the last error message
const char* jpn_phoneme_get_error();

// Get the number of dictionary entries
int jpn_phoneme_get_entry_count();

// Clean up resources
void jpn_phoneme_cleanup();

// Get library version
const char* jpn_phoneme_version();
```

### Return Values

- **`jpn_phoneme_init`**: Returns `1` on success, `0` on failure
- **`jpn_phoneme_convert`**: Returns length of output string on success, `-1` on failure
- **`jpn_phoneme_get_entry_count`**: Returns number of entries, or `-1` if not initialized

## 💻 Usage Examples

### Dart FFI

```dart
import 'dart:ffi' as ffi;
import 'package:ffi/ffi.dart';

// Load library
final lib = ffi.DynamicLibrary.open('jpn_to_phoneme_ffi.dll');

// Bind functions
final init = lib.lookupFunction<
    ffi.Int32 Function(ffi.Pointer<Utf8>),
    int Function(ffi.Pointer<Utf8>)
>('jpn_phoneme_init');

final convert = lib.lookupFunction<
    ffi.Int32 Function(ffi.Pointer<Utf8>, ffi.Pointer<ffi.Uint8>, ffi.Int32, ffi.Pointer<ffi.Int64>),
    int Function(ffi.Pointer<Utf8>, ffi.Pointer<ffi.Uint8>, int, ffi.Pointer<ffi.Int64>)
>('jpn_phoneme_convert');

// Initialize
init('ja_phonemes.json'.toNativeUtf8());

// Convert
final buffer = malloc<ffi.Uint8>(4096);
final timePtr = malloc<ffi.Int64>();
final len = convert('こんにちは'.toNativeUtf8(), buffer, 4096, timePtr);
final phonemes = utf8.decode(buffer.asTypedList(len));
print('Phonemes: $phonemes (${timePtr.value}μs)');
```

See [examples/dart_example.dart](examples/dart_example.dart) for complete implementation.

### Node.js (ffi-napi)

```javascript
const ffi = require('ffi-napi');
const ref = require('ref-napi');

// Load library
const lib = ffi.Library('jpn_to_phoneme_ffi.dll', {
    'jpn_phoneme_init': ['int32', ['string']],
    'jpn_phoneme_convert': ['int32', ['string', 'pointer', 'int32', 'pointer']],
});

// Initialize
lib.jpn_phoneme_init('ja_phonemes.json');

// Convert
const buffer = Buffer.alloc(4096);
const timePtr = ref.alloc('int64');
const len = lib.jpn_phoneme_convert('こんにちは', buffer, 4096, timePtr);
const phonemes = buffer.toString('utf8', 0, len);
console.log(`Phonemes: ${phonemes} (${timePtr.deref()}μs)`);
```

See [examples/node_example.js](examples/node_example.js) for complete implementation.

### Python (ctypes)

```python
import ctypes

# Load library
lib = ctypes.CDLL('jpn_to_phoneme_ffi.dll')

# Define function signatures
lib.jpn_phoneme_init.argtypes = [ctypes.c_char_p]
lib.jpn_phoneme_init.restype = ctypes.c_int32

lib.jpn_phoneme_convert.argtypes = [
    ctypes.c_char_p, ctypes.c_char_p, 
    ctypes.c_int32, ctypes.POINTER(ctypes.c_int64)
]
lib.jpn_phoneme_convert.restype = ctypes.c_int32

# Initialize
lib.jpn_phoneme_init(b'ja_phonemes.json')

# Convert
buffer = ctypes.create_string_buffer(4096)
time_us = ctypes.c_int64()
length = lib.jpn_phoneme_convert(
    'こんにちは'.encode('utf-8'), 
    buffer, 4096, ctypes.byref(time_us)
)
phonemes = buffer.value.decode('utf-8')
print(f'Phonemes: {phonemes} ({time_us.value}μs)')
```

See [examples/python_example.py](examples/python_example.py) for complete implementation.

## 🎯 Language-Specific Examples

Complete, runnable examples are provided in the `examples/` directory:

- **Dart**: `examples/dart_example.dart`
- **Node.js**: `examples/node_example.js`
- **Python**: `examples/python_example.py`

Each example demonstrates:
- Loading the native library
- Initializing with dictionary
- Converting text to phonemes
- Measuring performance
- Error handling
- Resource cleanup

## ⚡ Performance

The library uses a highly optimized trie structure with pre-decoded UTF-8 for maximum speed:

| Text Length | Conversion Time |
|-------------|----------------|
| 10 chars    | ~5-10 μs       |
| 100 chars   | ~50-100 μs     |
| 1000 chars  | ~500-1000 μs   |

*Benchmarks on Intel i7-8700K, Windows 10*

## 🔧 Advanced Usage

### Custom Buffer Size

The default examples use a 4KB buffer. For longer text, allocate more:

```c
// For text up to 1MB output
char* buffer = malloc(1024 * 1024);
int64_t time;
int length = jpn_phoneme_convert(text, buffer, 1024 * 1024, &time);
```

### Error Handling

Always check return values and use `jpn_phoneme_get_error()` for debugging:

```c
if (jpn_phoneme_init("ja_phonemes.json") == 0) {
    const char* error = jpn_phoneme_get_error();
    printf("Initialization failed: %s\n", error);
}
```

### Multi-Threading

The library is thread-safe for conversions after initialization:

```c
// Initialize once
jpn_phoneme_init("ja_phonemes.json");

// Safe to call from multiple threads
#pragma omp parallel for
for (int i = 0; i < 1000; i++) {
    char buffer[4096];
    int64_t time;
    jpn_phoneme_convert(texts[i], buffer, 4096, &time);
}

// Cleanup once when done
jpn_phoneme_cleanup();
```

## 📝 Build Configuration

### Custom Optimization Flags

Edit `CMakeLists.txt` to customize compiler flags:

```cmake
# For maximum performance on specific CPU
add_compile_options(-march=skylake)

# For size optimization
add_compile_options(-Os)

# For debug builds with symbols
set(CMAKE_BUILD_TYPE Debug)
```

### Static Linking

To build a static library instead:

```cmake
add_library(jpn_to_phoneme_ffi STATIC jpn_to_phoneme_ffi.cpp)
```

## 🐛 Troubleshooting

### Library Not Found

**Windows**: Ensure DLL is in same directory as executable or in PATH  
**Linux**: Set `LD_LIBRARY_PATH`: `export LD_LIBRARY_PATH=./output/linux:$LD_LIBRARY_PATH`  
**macOS**: Set `DYLD_LIBRARY_PATH`: `export DYLD_LIBRARY_PATH=./output/macos:$DYLD_LIBRARY_PATH`

### UTF-8 Encoding Issues

Ensure all text is UTF-8 encoded:
- **Dart**: Use `.toNativeUtf8()` from `package:ffi`
- **Node.js**: Use `Buffer.from(text, 'utf8')`
- **Python**: Use `.encode('utf-8')`

### Compilation Errors

- **C++17 Required**: Update compiler or CMake flags
- **Missing CMake**: Install from https://cmake.org/download/
- **Linker Errors**: Ensure all symbols are exported with `DLL_EXPORT`

## 📄 License

Same license as the main project.

## 🤝 Contributing

Found a bug or want to add support for another language? PRs welcome!

1. Add example in `examples/your_language_example.ext`
2. Update this README with usage instructions
3. Test on all platforms (Windows, Linux, macOS)
4. Submit pull request

## 🔗 Related Projects

- [Main Repository](../) - Full Japanese to Phoneme converter with CLI
- [Rust Edition](../jpn_to_phoneme.rs) - Standalone Rust implementation
- [Python Edition](../jpn_to_phoneme.py) - Standalone Python implementation

