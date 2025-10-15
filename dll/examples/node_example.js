// Node.js FFI Example for Japanese to Phoneme Converter
// This demonstrates how to use the native library from Node.js
//
// Installation:
//   npm install ffi-napi ref-napi
//
// Usage:
//   node node_example.js

const ffi = require('ffi-napi');
const ref = require('ref-napi');
const path = require('path');
const os = require('os');

// ============================================================================
// FFI Type Definitions
// ============================================================================

const int32 = ref.types.int32;
const int64 = ref.types.int64;
const string = ref.types.CString;
const voidType = ref.types.void;
const uint8Ptr = ref.refType(ref.types.uint8);
const int64Ptr = ref.refType(int64);

// ============================================================================
// Load Native Library
// ============================================================================

function getLibraryPath() {
    const platform = os.platform();
    switch (platform) {
        case 'win32':
            return path.join(__dirname, '../output/windows/jpn_to_phoneme_ffi.dll');
        case 'linux':
            return path.join(__dirname, '../output/linux/jpn_to_phoneme_ffi.so');
        case 'darwin':
            return path.join(__dirname, '../output/macos/jpn_to_phoneme_ffi.dylib');
        default:
            throw new Error(`Unsupported platform: ${platform}`);
    }
}

const libraryPath = getLibraryPath();

// Load the native library with FFI bindings
const lib = ffi.Library(libraryPath, {
    'jpn_phoneme_init': [int32, [string]],
    'jpn_phoneme_convert': [int32, [string, uint8Ptr, int32, int64Ptr]],
    'jpn_phoneme_get_error': [string, []],
    'jpn_phoneme_get_entry_count': [int32, []],
    'jpn_phoneme_cleanup': [voidType, []],
    'jpn_phoneme_version': [string, []],
});

// ============================================================================
// Japanese Phoneme Converter Class
// ============================================================================

class JapanesePhonemeConverter {
    /**
     * Initialize the converter with a JSON dictionary file
     * @param {string} jsonFilePath - Path to ja_phonemes.json
     * @returns {boolean} - Success status
     */
    init(jsonFilePath) {
        const result = lib.jpn_phoneme_init(jsonFilePath);
        if (result === 0) {
            console.error(`❌ Initialization failed: ${this.getError()}`);
            return false;
        }
        return true;
    }

    /**
     * Convert Japanese text to phonemes
     * @param {string} japaneseText - Input Japanese text
     * @returns {Object|null} - {phonemes: string, time: number} or null on error
     */
    convert(japaneseText) {
        const bufferSize = 4096;
        const buffer = Buffer.alloc(bufferSize);
        const timePtr = ref.alloc(int64);

        const length = lib.jpn_phoneme_convert(japaneseText, buffer, bufferSize, timePtr);

        if (length < 0) {
            console.error(`❌ Conversion failed: ${this.getError()}`);
            return null;
        }

        const phonemes = buffer.toString('utf8', 0, length);
        const time = timePtr.deref();

        return { phonemes, time };
    }

    /**
     * Get the last error message
     * @returns {string} - Error message
     */
    getError() {
        return lib.jpn_phoneme_get_error();
    }

    /**
     * Get the number of entries in the dictionary
     * @returns {number} - Entry count
     */
    getEntryCount() {
        return lib.jpn_phoneme_get_entry_count();
    }

    /**
     * Get library version
     * @returns {string} - Version string
     */
    getVersion() {
        return lib.jpn_phoneme_version();
    }

    /**
     * Clean up resources (call when done)
     */
    dispose() {
        lib.jpn_phoneme_cleanup();
    }
}

// ============================================================================
// Example Usage
// ============================================================================

async function main() {
    console.log('');
    console.log('╔══════════════════════════════════════════════════════════╗');
    console.log('║  Japanese → Phoneme Converter (Node.js FFI Example)     ║');
    console.log('╚══════════════════════════════════════════════════════════╝');
    console.log('');

    try {
        // Create converter instance
        const converter = new JapanesePhonemeConverter();
        console.log(`📚 Library version: ${converter.getVersion()}`);
        console.log('');

        // Initialize with dictionary
        console.log('🔥 Loading phoneme dictionary...');
        if (!converter.init(path.join(__dirname, '../../ja_phonemes.json'))) {
            return;
        }

        const entryCount = converter.getEntryCount();
        console.log(`✅ Loaded ${entryCount} entries`);
        console.log('');
        console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
        console.log('');

        // Test conversion examples
        const examples = [
            'こんにちは',
            '日本語',
            '東京',
            'ありがとうございます',
            '今日はいい天気ですね',
        ];

        for (const text of examples) {
            const result = converter.convert(text);
            if (result) {
                const { phonemes, time } = result;
                console.log(`Input:    ${text}`);
                console.log(`Phonemes: ${phonemes}`);
                console.log(`Time:     ${time}μs (${(time / 1000.0).toFixed(2)}ms)`);
                console.log('');
            }
        }

        console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
        console.log('✨ Conversion complete!');
        console.log('');

        // Clean up
        converter.dispose();
    } catch (error) {
        console.error(`❌ Error: ${error.message}`);
        console.error(error.stack);
    }
}

// Run the example
main().catch(console.error);

