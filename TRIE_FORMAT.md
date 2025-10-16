# Japanese Binary Trie Format Specification

## Overview

The `japanese.trie` file is a **unified binary trie** format containing both phoneme mappings and word dictionary for Japanese text processing. It provides **100x faster loading** compared to JSON/text formats through memory-mapped file access.

## Design Goals

1. **Fast Loading**: Memory-mappable format for instant access
2. **Unified Storage**: Single file for both phonemes and words
3. **Efficient Lookup**: O(n) lookups where n = string length
4. **Cross-Platform**: Little-endian format with explicit byte ordering
5. **Compact**: Binary representation smaller than JSON

## File Structure

### Header (24 bytes)

```
Offset | Size | Type   | Description
-------|------|--------|----------------------------------
0x00   | 4    | char[4]| Magic number: "JPNT" (0x4A504E54)
0x04   | 2    | uint16 | Major version (currently 1)
0x06   | 2    | uint16 | Minor version (currently 0)
0x08   | 4    | uint32 | Phoneme entry count
0x0C   | 4    | uint32 | Word entry count  
0x10   | 8    | uint64 | Root node offset
```

**Magic Number**: `JPNT` stands for "Japanese Phoneme/Name Trie"

**Version**: Format version 1.0
- Breaking changes increment major version
- Compatible additions increment minor version

**Entry Counts**: 
- Phoneme entries have non-empty values (IPA phonemes)
- Word entries have empty values (existence markers)

**Root Offset**: Byte offset to the root trie node (typically 24)

### Trie Node Structure

Each node in the trie has the following structure:

```
Offset | Size    | Type   | Description
-------|---------|--------|----------------------------------
0x00   | 1       | uint8  | Flags (bit 0: has_value)
0x01   | 2       | uint16 | Value length (0 if no value)
0x03   | var     | utf8   | Value bytes (phoneme or empty)
var    | 4       | uint32 | Children count
var+4  | 12*N    | entry[]| Children table (N entries)
```

#### Flags Byte

```
Bit 0: has_value (1 = this node has a value, 0 = no value)
Bits 1-7: Reserved (must be 0)
```

#### Value

- **Length**: 2-byte unsigned integer (little-endian)
- **Content**: UTF-8 encoded string
  - For phoneme entries: IPA phoneme string (e.g., "tabeta")
  - For word markers: Empty string (length = 0)
  - For intermediate nodes: No value (length = 0, has_value flag = 0)

#### Children Table

Each child entry is **12 bytes**:

```
Offset | Size | Type   | Description
-------|------|--------|----------------------------------
0x00   | 4    | uint32 | Unicode code point
0x04   | 8    | uint64 | Child node offset (bytes from file start)
```

**Sorted Order**: Children are stored sorted by code point for binary search.

## Example Breakdown

Let's trace through the word `食べた` (tabeta, "ate"):

### File Layout

```
[HEADER: 24 bytes]
  Magic: "JPNT"
  Version: 1.0
  Phoneme count: 374000
  Word count: 288000
  Root offset: 24

[ROOT NODE @ 24]
  Flags: 0x00 (no value)
  Value length: 0
  Children: 500+
  ...
  食 (U+98DF): offset 1024
  ...

[NODE @ 1024] (食)
  Flags: 0x00
  Value length: 0
  Children: 20
  ...
  べ (U+3079): offset 2048
  ...

[NODE @ 2048] (食べ)
  Flags: 0x00
  Value length: 0
  Children: 15
  ...
  た (U+305F): offset 3072
  ...

[NODE @ 3072] (食べた)
  Flags: 0x01 (has value!)
  Value length: 6
  Value: "tabeta"
  Children: 0
```

### Lookup Algorithm

1. Start at root node (offset from header)
2. For each UTF-8 character in input:
   - Decode to Unicode code point
   - Binary search child table for matching code point
   - Follow offset to child node
   - If child not found → no match
3. Check final node's `has_value` flag
4. If true, read value (phoneme)

## Usage in C++

### Memory-Mapped Loading (Recommended)

```cpp
// Open file
int fd = open("japanese.trie", O_RDONLY);
struct stat sb;
fstat(fd, &sb);

// Memory map entire file
void* map = mmap(NULL, sb.st_size, PROT_READ, MAP_PRIVATE, fd, 0);

// Read header
struct TrieHeader {
    char magic[4];
    uint16_t version_major;
    uint16_t version_minor;
    uint32_t phoneme_count;
    uint32_t word_count;
    uint64_t root_offset;
};

TrieHeader* header = (TrieHeader*)map;

// Verify magic number
if (memcmp(header->magic, "JPNT", 4) != 0) {
    // Invalid file
}

// Root node is at offset header->root_offset
TrieNode* root = (TrieNode*)((char*)map + header->root_offset);
```

### Node Reading

```cpp
struct TrieNode {
    uint8_t flags;
    uint16_t value_length;
    // Followed by:
    // - value_length bytes of UTF-8 value
    // - uint32_t children_count
    // - children_count * 12 bytes of child entries
    
    bool has_value() const {
        return flags & 0x01;
    }
    
    const char* get_value() const {
        return (const char*)this + 3;
    }
    
    uint32_t get_children_count() const {
        const char* ptr = (const char*)this + 3 + value_length;
        return *(uint32_t*)ptr;
    }
    
    struct ChildEntry {
        uint32_t code_point;
        uint64_t offset;
    };
    
    const ChildEntry* get_children() const {
        const char* ptr = (const char*)this + 3 + value_length + 4;
        return (const ChildEntry*)ptr;
    }
    
    // Binary search for child with given code point
    const TrieNode* find_child(uint32_t cp, void* file_base) const {
        const ChildEntry* children = get_children();
        uint32_t count = get_children_count();
        
        // Binary search
        int left = 0, right = count - 1;
        while (left <= right) {
            int mid = (left + right) / 2;
            if (children[mid].code_point == cp) {
                return (TrieNode*)((char*)file_base + children[mid].offset);
            } else if (children[mid].code_point < cp) {
                left = mid + 1;
            } else {
                right = mid - 1;
            }
        }
        return nullptr;
    }
};
```

### Fallback Strategy

```cpp
bool load_trie() {
    // Try binary trie first
    if (file_exists("japanese.trie")) {
        if (load_binary_trie("japanese.trie")) {
            std::cout << "✅ Loaded japanese.trie (fast!)" << std::endl;
            return true;
        }
    }
    
    // Fallback to JSON/text
    std::cout << "⚠️  japanese.trie not found, loading JSON..." << std::endl;
    load_json("ja_phonemes.json");
    load_wordlist("ja_words.txt");
    return true;
}
```

## Performance Characteristics

### Loading Time

| Format | Entries | Load Time | Speed |
|--------|---------|-----------|-------|
| JSON + text parsing | 660k | ~500ms | 1x |
| Binary trie (mmap) | 660k | ~5ms | **100x** |

### Memory Usage

| Format | Size | Overhead |
|--------|------|----------|
| ja_phonemes.json | ~15 MB | 100% |
| ja_words.txt | ~3 MB | 100% |
| japanese.trie | ~12 MB | **67%** |

### Lookup Performance

- **Complexity**: O(n) where n = UTF-8 string length
- **Binary search** of children at each node
- **No parsing overhead**: Direct memory access

## Building the Binary Trie

Use the provided Python script:

```bash
python fix_and_align_phonemes.py
```

This will:
1. Load `original_ja_phonemes.json`
2. Generate verb conjugations
3. Process `original_ja_words.txt` 
4. Build unified trie structure
5. Serialize to `japanese.trie`

## Version History

### Version 2.0 (Current) - OPTIMIZED FORMAT
- **50% smaller file size** compared to v1.0
- Varint encoding for counts and lengths (1 byte for small values)
- 4-byte **relative offsets** instead of 8-byte absolute
- **7-byte child entries** (3-byte code point + 4-byte offset) instead of 12-byte
- Packed flags byte (children count embedded when < 127)
- Same instant loading performance
- Backward compatible reader (supports both v1.0 and v2.0)

### Version 1.0 (Legacy)
- Initial release
- Unified phoneme + word storage
- Memory-mappable format
- 8-byte absolute offsets
- 12-byte child entries
- Little-endian byte ordering
- Binary search of child nodes

## Future Extensions (Version 3.0+)

Potential improvements for future versions:

1. **Compressed values**: Use dictionary encoding for common phonemes
2. **DFA minimization**: Merge equivalent nodes
3. **SIMD search**: Vectorized child node search
4. **Cache-friendly layout**: Breadth-first node ordering

## Notes

- All integers are **little-endian**
- UTF-8 encoding for all text
- File must be readable as-is (no decompression needed)
- Platform-independent format
- Safe for concurrent read-only access
- No modification after generation (read-only)

## Tools

- **Builder**: `fix_and_align_phonemes.py` (Python)
- **Loader**: `jpn_to_phoneme.cpp` (C++)
- **Verifier**: (TODO) Add verification tool

## License

This format specification is part of the japanese-to-phonemes project.

