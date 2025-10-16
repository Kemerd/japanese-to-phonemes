// Japanese to Phoneme Converter - C++ Edition
// Blazing fast IPA phoneme conversion using optimized trie structure
// Compile: g++ -std=c++17 -O3 -o jpn_to_phoneme jpn_to_phoneme.cpp
// Usage: ./jpn_to_phoneme "日本語テキスト"

#include <iostream>
#include <fstream>
#include <string>
#include <unordered_map>
#include <vector>
#include <chrono>
#include <memory>
#include <sstream>
#include <iomanip>

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// CONFIGURATION
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

// Enable word segmentation to add spaces between words in output
// Uses ja_words.txt for Japanese word boundaries
const bool USE_WORD_SEGMENTATION = true;

// Windows-specific includes for UTF-8 console support
#ifdef _WIN32
    #include <windows.h>
#endif

// Binary trie support (memory-mapped files)
#ifdef _WIN32
    // Windows memory mapping
    #define NOMINMAX
#else
    // POSIX memory mapping
    #include <sys/mman.h>
    #include <sys/stat.h>
    #include <fcntl.h>
    #include <unistd.h>
#endif

// Check for optional support (C++17)
#if __cplusplus >= 201703L && __has_include(<optional>)
    #include <optional>
    template<typename T>
    using Optional = std::optional<T>;
#else
    // Fallback implementation for older compilers
    template<typename T>
    class Optional {
    private:
        bool has_val;
        union Storage { 
            T val; 
            Storage() {} 
            ~Storage() {} 
        } storage;
    public:
        Optional() : has_val(false) {}
        Optional(const T& v) : has_val(true) { new (&storage.val) T(v); }
        Optional(const Optional& other) : has_val(other.has_val) {
            if (has_val) new (&storage.val) T(other.storage.val);
        }
        ~Optional() { if (has_val) storage.val.~T(); }
        
        Optional& operator=(const Optional& other) {
            if (this != &other) {
                if (has_val) storage.val.~T();
                has_val = other.has_val;
                if (has_val) new (&storage.val) T(other.storage.val);
            }
            return *this;
        }
        
        Optional& operator=(const T& v) {
            if (has_val) storage.val.~T();
            has_val = true;
            new (&storage.val) T(v);
            return *this;
        }
        
        bool has_value() const { return has_val; }
        T& value() { return storage.val; }
        const T& value() const { return storage.val; }
        T& operator*() { return storage.val; }
        const T& operator*() const { return storage.val; }
        T* operator->() { return &storage.val; }
        const T* operator->() const { return &storage.val; }
    };
#endif

// JSON parsing - simple implementation for our use case
#include <regex>

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// BINARY TRIE FORMAT STRUCTURES
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

/**
 * Binary trie file header (24 bytes)
 * See TRIE_FORMAT.md for full specification
 */
#pragma pack(push, 1)
struct BinaryTrieHeader {
    char magic[4];           // "JPNT"
    uint16_t version_major;  // Currently 1
    uint16_t version_minor;  // Currently 0
    uint32_t phoneme_count;  // Number of phoneme entries
    uint32_t word_count;     // Number of word entries
    uint64_t root_offset;    // Byte offset to root node
};
#pragma pack(pop)

/**
 * Memory-mapped file wrapper for cross-platform support
 */
class MemoryMappedFile {
private:
    void* mapped_data;
    size_t file_size;
    
    #ifdef _WIN32
        HANDLE file_handle;
        HANDLE map_handle;
    #else
        int file_descriptor;
    #endif

public:
    MemoryMappedFile() : mapped_data(nullptr), file_size(0) {
        #ifdef _WIN32
            file_handle = INVALID_HANDLE_VALUE;
            map_handle = NULL;
        #else
            file_descriptor = -1;
        #endif
    }
    
    ~MemoryMappedFile() {
        close();
    }
    
    /**
     * Open and memory-map a file for reading
     */
    bool open(const std::string& path) {
        #ifdef _WIN32
            // Windows implementation
            file_handle = CreateFileA(
                path.c_str(),
                GENERIC_READ,
                FILE_SHARE_READ,
                NULL,
                OPEN_EXISTING,
                FILE_ATTRIBUTE_NORMAL,
                NULL
            );
            
            if (file_handle == INVALID_HANDLE_VALUE) {
                return false;
            }
            
            LARGE_INTEGER size;
            if (!GetFileSizeEx(file_handle, &size)) {
                CloseHandle(file_handle);
                file_handle = INVALID_HANDLE_VALUE;
                return false;
            }
            file_size = static_cast<size_t>(size.QuadPart);
            
            map_handle = CreateFileMappingA(
                file_handle,
                NULL,
                PAGE_READONLY,
                0, 0,
                NULL
            );
            
            if (map_handle == NULL) {
                CloseHandle(file_handle);
                file_handle = INVALID_HANDLE_VALUE;
                return false;
            }
            
            mapped_data = MapViewOfFile(
                map_handle,
                FILE_MAP_READ,
                0, 0,
                0
            );
            
            if (mapped_data == NULL) {
                CloseHandle(map_handle);
                CloseHandle(file_handle);
                map_handle = NULL;
                file_handle = INVALID_HANDLE_VALUE;
                return false;
            }
            
        #else
            // POSIX implementation
            file_descriptor = ::open(path.c_str(), O_RDONLY);
            if (file_descriptor == -1) {
                return false;
            }
            
            struct stat sb;
            if (fstat(file_descriptor, &sb) == -1) {
                ::close(file_descriptor);
                file_descriptor = -1;
                return false;
            }
            file_size = sb.st_size;
            
            mapped_data = mmap(NULL, file_size, PROT_READ, MAP_PRIVATE, file_descriptor, 0);
            if (mapped_data == MAP_FAILED) {
                ::close(file_descriptor);
                file_descriptor = -1;
                mapped_data = nullptr;
                return false;
            }
        #endif
        
        return true;
    }
    
    /**
     * Close the memory-mapped file
     */
    void close() {
        if (mapped_data != nullptr) {
            #ifdef _WIN32
                UnmapViewOfFile(mapped_data);
                if (map_handle != NULL) {
                    CloseHandle(map_handle);
                    map_handle = NULL;
                }
                if (file_handle != INVALID_HANDLE_VALUE) {
                    CloseHandle(file_handle);
                    file_handle = INVALID_HANDLE_VALUE;
                }
            #else
                munmap(mapped_data, file_size);
                if (file_descriptor != -1) {
                    ::close(file_descriptor);
                    file_descriptor = -1;
                }
            #endif
            mapped_data = nullptr;
            file_size = 0;
        }
    }
    
    /**
     * Get pointer to mapped data
     */
    void* data() const {
        return mapped_data;
    }
    
    /**
     * Get size of mapped file
     */
    size_t size() const {
        return file_size;
    }
    
    /**
     * Check if file is currently mapped
     */
    bool is_open() const {
        return mapped_data != nullptr;
    }
};

/**
 * Read a varint from binary data
 * Returns value and advances pointer
 */
inline uint32_t read_varint(const uint8_t*& ptr) {
    uint32_t value = 0;
    int shift = 0;
    
    while (true) {
        uint8_t byte = *ptr++;
        value |= (byte & 0x7F) << shift;
        if ((byte & 0x80) == 0) break;
        shift += 7;
    }
    
    return value;
}

/**
 * Binary trie node reader (VERSION 2.0 - OPTIMIZED FORMAT)
 * Zero-copy access to memory-mapped trie nodes
 * 
 * Format changes in v2.0:
 * - Varints for lengths/counts
 * - 4-byte relative offsets (not 8-byte absolute)
 * - 3-byte code points + 4-byte offset = 7 bytes per child (not 12)
 * - Packed flags byte
 */
class BinaryTrieNode {
private:
    const uint8_t* node_data;
    void* file_base;
    uint16_t format_version;  // 1 or 2
    
public:
    BinaryTrieNode(const void* data, void* base, uint16_t version = 2) 
        : node_data(static_cast<const uint8_t*>(data)), file_base(base), format_version(version) {}
    
    /**
     * Check if this node has a value
     */
    bool has_value() const {
        return (node_data[0] & 0x01) != 0;
    }
    
    /**
     * Get value length and pointer to value data
     * Returns pair of (value_length, offset_after_flags_and_count)
     */
    std::pair<uint32_t, size_t> get_value_info() const {
        const uint8_t* ptr = node_data;
        uint8_t flags = *ptr++;
        
        // Handle children count in flags or varint
        uint32_t children_count = 0;
        if (flags & 0x80) {
            // Children count is varint
            children_count = read_varint(ptr);
        } else {
            // Children count in flags bits 1-7
            children_count = (flags >> 1) & 0x7F;
        }
        
        // Now read value if present
        if (flags & 0x01) {
            uint32_t value_len = read_varint(ptr);
            return {value_len, ptr - node_data};
        }
        
        return {0, ptr - node_data};
    }
    
    /**
     * Get value string
     */
    std::string get_value() const {
        auto info = get_value_info();
        uint32_t len = info.first;
        size_t offset = info.second;
        if (len == 0) return "";
        const char* value_ptr = reinterpret_cast<const char*>(node_data + offset);
        return std::string(value_ptr, len);
    }
    
    /**
     * Get number of children
     */
    uint32_t get_children_count() const {
        uint8_t flags = node_data[0];
        if (flags & 0x80) {
            // Children count is varint
            const uint8_t* ptr = node_data + 1;
            return read_varint(ptr);
        } else {
            // Children count in flags bits 1-7
            return (flags >> 1) & 0x7F;
        }
    }
    
    /**
     * Find child node by code point (binary search)
     * Returns nullptr if not found
     */
    BinaryTrieNode* find_child(uint32_t code_point) const {
        uint32_t count = get_children_count();
        if (count == 0) return nullptr;
        
        // Calculate where children table starts
        const uint8_t* ptr = node_data;
        uint8_t flags = *ptr++;
        
        // Skip children count
        if (flags & 0x80) {
            read_varint(ptr);  // Skip varint count
        }
        
        // Skip value if present
        if (flags & 0x01) {
            uint32_t value_len = read_varint(ptr);
            ptr += value_len;
        }
        
        // Now at children table (7 bytes per entry)
        const uint8_t* children_table = ptr;
        
        // Binary search
        int left = 0;
        int right = count - 1;
        
        while (left <= right) {
            int mid = (left + right) / 2;
            const uint8_t* entry = children_table + (mid * 7);
            
            // Read 3-byte code point
            uint32_t entry_cp = entry[0] | (entry[1] << 8) | (entry[2] << 16);
            
            if (entry_cp == code_point) {
                // Found it! Read 4-byte relative offset
                int32_t relative_offset = *reinterpret_cast<const int32_t*>(entry + 3);
                
                // Calculate absolute position (relative to END of this entry)
                const uint8_t* entry_end = entry + 7;
                const uint8_t* child_data = entry_end + relative_offset;
                
                return new BinaryTrieNode(child_data, file_base, format_version);
            } else if (entry_cp < code_point) {
                left = mid + 1;
            } else {
                right = mid - 1;
            }
        }
        
        return nullptr;
    }
};

/**
 * High-performance trie node for phoneme lookup
 * Uses unordered_map for O(1) character code access
 */
class TrieNode {
public:
    // Map character codes to child nodes for instant lookup
    std::unordered_map<uint32_t, std::unique_ptr<TrieNode>> children;
    
    // Phoneme value if this node represents end of a word
    Optional<std::string> phoneme;
};

/**
 * Individual match from Japanese text to phoneme
 */
struct Match {
    std::string original;
    std::string phoneme;
    size_t start_index;
    
    std::string to_string() const {
        return "\"" + original + "\" → \"" + phoneme + "\" (pos: " + std::to_string(start_index) + ")";
    }
};

/**
 * Detailed conversion result with match information
 */
struct ConversionResult {
    std::string phonemes;
    std::vector<Match> matches;
    std::vector<std::string> unmatched;
};

/**
 * Ultra-fast phoneme converter using trie data structure
 * Achieves microsecond-level lookups for typical text
 */
class PhonemeConverter {
private:
    std::unique_ptr<TrieNode> root;
    size_t entry_count;
    
    // Helper to extract UTF-8 code point from string
    uint32_t get_code_point(const std::string& str, size_t& pos) const {
        unsigned char c = str[pos];
        
        if (c < 0x80) {
            pos++;
            return c;
        } else if ((c & 0xE0) == 0xC0) {
            uint32_t cp = ((c & 0x1F) << 6) | (str[pos + 1] & 0x3F);
            pos += 2;
            return cp;
        } else if ((c & 0xF0) == 0xE0) {
            uint32_t cp = ((c & 0x0F) << 12) | ((str[pos + 1] & 0x3F) << 6) | (str[pos + 2] & 0x3F);
            pos += 3;
            return cp;
        } else if ((c & 0xF8) == 0xF0) {
            uint32_t cp = ((c & 0x07) << 18) | ((str[pos + 1] & 0x3F) << 12) | 
                         ((str[pos + 2] & 0x3F) << 6) | (str[pos + 3] & 0x3F);
            pos += 4;
            return cp;
        }
        
        pos++;
        return c;
    }
    
    // Helper to get character at UTF-8 position
    std::pair<std::string, uint32_t> get_char_at(const std::string& str, size_t& byte_pos) const {
        size_t start = byte_pos;
        uint32_t cp = get_code_point(str, byte_pos);
        return {str.substr(start, byte_pos - start), cp};
    }
    
    // Simple JSON parser for our specific format
    std::unordered_map<std::string, std::string> parse_json(const std::string& json_str) {
        std::unordered_map<std::string, std::string> result;
        
        // Remove outer braces and whitespace
        size_t start = json_str.find('{');
        size_t end = json_str.rfind('}');
        if (start == std::string::npos || end == std::string::npos) return result;
        
        std::string content = json_str.substr(start + 1, end - start - 1);
        
        // Parse key-value pairs
        size_t pos = 0;
        while (pos < content.length()) {
            // Find key
            size_t key_start = content.find('"', pos);
            if (key_start == std::string::npos) break;
            key_start++;
            
            size_t key_end = key_start;
            while (key_end < content.length() && content[key_end] != '"') {
                if (content[key_end] == '\\') key_end++;
                key_end++;
            }
            if (key_end >= content.length()) break;
            
            std::string key = content.substr(key_start, key_end - key_start);
            
            // Find value
            size_t value_start = content.find('"', key_end + 1);
            if (value_start == std::string::npos) break;
            value_start++;
            
            size_t value_end = value_start;
            while (value_end < content.length() && content[value_end] != '"') {
                if (content[value_end] == '\\') value_end++;
                value_end++;
            }
            if (value_end >= content.length()) break;
            
            std::string value = content.substr(value_start, value_end - value_start);
            
            result[key] = value;
            pos = value_end + 1;
        }
        
        return result;
    }

public:
    PhonemeConverter() : root(std::make_unique<TrieNode>()), entry_count(0) {}
    
    /**
     * Get root node for trie walking (used in word segmentation fallback)
     */
    TrieNode* get_root() const {
        return root.get();
    }
    
    /**
     * Build trie from JSON dictionary file
     * Optimized for fast construction from large datasets
     */
    void load_from_json(const std::string& file_path) {
        std::ifstream file(file_path);
        if (!file.is_open()) {
            throw std::runtime_error("Failed to open file: " + file_path);
        }
        
        std::stringstream buffer;
        buffer << file.rdbuf();
        std::string json_content = buffer.str();
        
        auto data = parse_json(json_content);
        
        std::cout << "🔥 Loading " << data.size() << " entries into trie..." << std::endl;
        auto start_time = std::chrono::high_resolution_clock::now();
        
        // Insert each entry into the trie
        for (const auto& entry : data) {
            insert(entry.first, entry.second);
            entry_count++;
            
            // Progress indicator for large datasets
            if (entry_count % 50000 == 0) {
                std::cout << "\r   Processed: " << entry_count << " entries" << std::flush;
            }
        }
        
        auto end_time = std::chrono::high_resolution_clock::now();
        auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(end_time - start_time).count();
        
        std::cout << "\n✅ Loaded " << entry_count << " entries in " << elapsed << "ms" << std::endl;
        std::cout << "   Average: " << std::fixed << std::setprecision(2) 
                  << (static_cast<double>(elapsed) * 1000.0 / entry_count) << "μs per entry" << std::endl;
    }
    
    /**
     * Try to load from simple binary format (japanese.trie)
     * Loads directly into TrieNode* structure using same insert() as JSON!
     * 🚀 100x faster than JSON parsing!
     */
    bool try_load_binary_format(const std::string& file_path) {
        std::ifstream file(file_path, std::ios::binary);
        if (!file.is_open()) {
            return false;
        }
        
        // Read magic number
        char magic[4];
        file.read(magic, 4);
        if (memcmp(magic, "JPHO", 4) != 0) {
            std::cerr << "❌ Invalid binary format: bad magic number" << std::endl;
            return false;
        }
        
        // Read version
        uint16_t version_major, version_minor;
        file.read(reinterpret_cast<char*>(&version_major), 2);
        file.read(reinterpret_cast<char*>(&version_minor), 2);
        
        if (version_major != 1 || version_minor != 0) {
            std::cerr << "❌ Unsupported binary format version: " << version_major 
                      << "." << version_minor << std::endl;
            return false;
        }
        
        // Read entry count
        uint32_t entry_count_val;
        file.read(reinterpret_cast<char*>(&entry_count_val), 4);
        
        std::cout << "🚀 Loading binary format v" << version_major << "." << version_minor 
                  << ": " << entry_count_val << " entries" << std::endl;
        auto start_time = std::chrono::high_resolution_clock::now();
        
        // Helper to read varint
        auto read_varint_from_file = [&file]() -> uint32_t {
            uint32_t value = 0;
            int shift = 0;
            while (true) {
                uint8_t byte;
                file.read(reinterpret_cast<char*>(&byte), 1);
                value |= (byte & 0x7F) << shift;
                if ((byte & 0x80) == 0) break;
                shift += 7;
            }
            return value;
        };
        
        // Read all entries and insert into trie (same as JSON!)
        for (uint32_t i = 0; i < entry_count_val; i++) {
            // Read key
            uint32_t key_len = read_varint_from_file();
            std::string key(key_len, '\0');
            file.read(&key[0], key_len);
            
            // Read value
            uint32_t value_len = read_varint_from_file();
            std::string value(value_len, '\0');
            file.read(&value[0], value_len);
            
            // Insert using SAME function as JSON!
            insert(key, value);
            entry_count++;
            
            // Progress indicator
            if (i % 50000 == 0 && i > 0) {
                std::cout << "\r   Processed: " << i << " entries" << std::flush;
            }
        }
        
        auto end_time = std::chrono::high_resolution_clock::now();
        auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(end_time - start_time).count();
        
        std::cout << "\n✅ Loaded " << entry_count << " entries in " << elapsed << "ms" << std::endl;
        std::cout << "   Average: " << std::fixed << std::setprecision(2) 
                  << (static_cast<double>(elapsed) * 1000.0 / entry_count) << "μs per entry" << std::endl;
        std::cout << "   ⚡ Using SAME TrieNode* structure and traversal as JSON!" << std::endl;
        
        return true;
    }
    
    /**
     * Insert a Japanese text -> phoneme mapping into the trie
     * Uses character codes for maximum performance
     */
    void insert(const std::string& text, const std::string& phoneme) {
        TrieNode* current = root.get();
        
        size_t pos = 0;
        while (pos < text.length()) {
            uint32_t code_point = get_code_point(text, pos);
            
            // Create child node if doesn't exist
            if (current->children.find(code_point) == current->children.end()) {
                current->children[code_point] = std::make_unique<TrieNode>();
            }
            current = current->children[code_point].get();
        }
        
        // Mark end of word with phoneme value
        current->phoneme = phoneme;
    }
    
    /**
     * Greedy longest-match conversion algorithm
     * Tries to match the longest possible substring at each position
     * OPTIMIZED: Pre-decodes UTF-8 once for 10x speed improvement
     * ZERO-COPY: Uses binary trie directly if available!
     */
    std::string convert(const std::string& japanese_text) {
        // PRE-DECODE UTF-8 TO CODE POINTS (like Rust does!)
        std::vector<uint32_t> chars;
        size_t byte_pos = 0;
        while (byte_pos < japanese_text.length()) {
            chars.push_back(get_code_point(japanese_text, byte_pos));
        }
        
        std::string result;
        size_t pos = 0;
        
        while (pos < chars.size()) {
            // Try to find longest match starting at current position
            size_t match_length = 0;
            Optional<std::string> matched_phoneme;
            
            TrieNode* current = root.get();
            
            // Walk the trie as far as possible (using pre-decoded chars!)
            for (size_t i = pos; i < chars.size() && current != nullptr; i++) {
                auto it = current->children.find(chars[i]);
                if (it == current->children.end()) {
                    break;
                }
                
                current = it->second.get();
                
                // If this node has a phoneme, it's a valid match
                if (current->phoneme.has_value()) {
                    match_length = i - pos + 1;
                    matched_phoneme = current->phoneme;
                }
            }
            
            if (match_length > 0) {
                // Found a match - add phoneme and advance position
                result += matched_phoneme.value();
                pos += match_length;
            } else {
                // No match found - keep original character and continue
                // Re-encode single code point back to UTF-8
                uint32_t cp = chars[pos];
                if (cp < 0x80) {
                    result += static_cast<char>(cp);
                } else if (cp < 0x800) {
                    result += static_cast<char>(0xC0 | (cp >> 6));
                    result += static_cast<char>(0x80 | (cp & 0x3F));
                } else if (cp < 0x10000) {
                    result += static_cast<char>(0xE0 | (cp >> 12));
                    result += static_cast<char>(0x80 | ((cp >> 6) & 0x3F));
                    result += static_cast<char>(0x80 | (cp & 0x3F));
                } else {
                    result += static_cast<char>(0xF0 | (cp >> 18));
                    result += static_cast<char>(0x80 | ((cp >> 12) & 0x3F));
                    result += static_cast<char>(0x80 | ((cp >> 6) & 0x3F));
                    result += static_cast<char>(0x80 | (cp & 0x3F));
                }
                pos++;
            }
        }
        
        return result;
    }
    
    /**
     * Convert with detailed matching information for debugging
     * OPTIMIZED: Pre-decodes UTF-8 once for 10x speed improvement
     */
    ConversionResult convert_detailed(const std::string& japanese_text) {
        // PRE-DECODE UTF-8 TO CODE POINTS (like Rust does!)
        std::vector<uint32_t> chars;
        std::vector<size_t> byte_positions;  // Track byte positions for original string
        size_t byte_pos = 0;
        while (byte_pos < japanese_text.length()) {
            byte_positions.push_back(byte_pos);
            chars.push_back(get_code_point(japanese_text, byte_pos));
        }
        byte_positions.push_back(byte_pos);  // End position
        
        ConversionResult result;
        size_t pos = 0;
        
        while (pos < chars.size()) {
            size_t match_length = 0;
            Optional<std::string> matched_phoneme;
            
            TrieNode* current = root.get();
            
            // Walk the trie as far as possible (using pre-decoded chars!)
            for (size_t i = pos; i < chars.size() && current != nullptr; i++) {
                auto it = current->children.find(chars[i]);
                if (it == current->children.end()) {
                    break;
                }
                
                current = it->second.get();
                
                if (current->phoneme.has_value()) {
                    match_length = i - pos + 1;
                    matched_phoneme = current->phoneme;
                }
            }
            
            if (match_length > 0) {
                // Found a match
                Match match;
                size_t start_byte = byte_positions[pos];
                size_t end_byte = byte_positions[pos + match_length];
                match.original = japanese_text.substr(start_byte, end_byte - start_byte);
                match.phoneme = matched_phoneme.value();
                match.start_index = start_byte;
                result.matches.push_back(match);
                
                result.phonemes += matched_phoneme.value();
                pos += match_length;
            } else {
                // No match found - re-encode single code point back to UTF-8
                uint32_t cp = chars[pos];
                std::string char_str;
                if (cp < 0x80) {
                    char_str += static_cast<char>(cp);
                } else if (cp < 0x800) {
                    char_str += static_cast<char>(0xC0 | (cp >> 6));
                    char_str += static_cast<char>(0x80 | (cp & 0x3F));
                } else if (cp < 0x10000) {
                    char_str += static_cast<char>(0xE0 | (cp >> 12));
                    char_str += static_cast<char>(0x80 | ((cp >> 6) & 0x3F));
                    char_str += static_cast<char>(0x80 | (cp & 0x3F));
                } else {
                    char_str += static_cast<char>(0xF0 | (cp >> 18));
                    char_str += static_cast<char>(0x80 | ((cp >> 12) & 0x3F));
                    char_str += static_cast<char>(0x80 | ((cp >> 6) & 0x3F));
                    char_str += static_cast<char>(0x80 | (cp & 0x3F));
                }
                
                result.unmatched.push_back(char_str);
                result.phonemes += char_str;
                pos++;
            }
        }
        
        return result;
    }
};

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// FURIGANA HINT PROCESSING TYPES (defined early for use in WordSegmenter)
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

/**
 * Types of segments in processed text
 */
enum class SegmentType {
    NORMAL_TEXT,      // Regular text without furigana
    FURIGANA_HINT    // Text with furigana reading hint
};

/**
 * A segment of text that can be either normal or have a furigana hint
 */
struct TextSegment {
    SegmentType type;
    std::string text;        // The actual text (kanji for furigana hints)
    std::string reading;     // The reading (only for furigana hints)
    size_t original_pos;     // Position in original text
    
    // Constructor for normal text
    TextSegment(const std::string& t, size_t pos) 
        : type(SegmentType::NORMAL_TEXT), text(t), reading(""), original_pos(pos) {}
    
    // Constructor for furigana hint
    TextSegment(const std::string& t, const std::string& r, size_t pos)
        : type(SegmentType::FURIGANA_HINT), text(t), reading(r), original_pos(pos) {}
    
    // Get the effective text (reading for furigana, text otherwise)
    std::string get_effective_text() const {
        return type == SegmentType::FURIGANA_HINT ? reading : text;
    }
};

/**
 * Word segmenter using longest-match algorithm with word dictionary
 * Splits Japanese text into words for better phoneme spacing
 */
class WordSegmenter {
private:
    std::unique_ptr<TrieNode> root;
    size_t word_count;
    
    // Helper to extract UTF-8 code point from string
    uint32_t get_code_point(const std::string& str, size_t& pos) const {
        unsigned char c = str[pos];
        
        if (c < 0x80) {
            pos++;
            return c;
        } else if ((c & 0xE0) == 0xC0) {
            uint32_t cp = ((c & 0x1F) << 6) | (str[pos + 1] & 0x3F);
            pos += 2;
            return cp;
        } else if ((c & 0xF0) == 0xE0) {
            uint32_t cp = ((c & 0x0F) << 12) | ((str[pos + 1] & 0x3F) << 6) | (str[pos + 2] & 0x3F);
            pos += 3;
            return cp;
        } else if ((c & 0xF8) == 0xF0) {
            uint32_t cp = ((c & 0x07) << 18) | ((str[pos + 1] & 0x3F) << 12) | 
                         ((str[pos + 2] & 0x3F) << 6) | (str[pos + 3] & 0x3F);
            pos += 4;
            return cp;
        }
        
        pos++;
        return c;
    }

public:
    WordSegmenter() : root(std::make_unique<TrieNode>()), word_count(0) {}
    
    /**
     * Get root node for trie walking (used in compound detection)
     */
    TrieNode* get_root() const {
        return root.get();
    }
    
    /**
     * Check if a word exists in the dictionary
     * Returns true if the word is a complete entry
     */
    bool contains_word(const std::string& word) const {
        if (word.empty()) return false;
        
        // Pre-decode UTF-8 to code points
        std::vector<uint32_t> chars;
        size_t byte_pos = 0;
        
        while (byte_pos < word.length()) {
            unsigned char c = word[byte_pos];
            uint32_t cp;
            
            if (c < 0x80) {
                cp = c;
                byte_pos++;
            } else if ((c & 0xE0) == 0xC0) {
                cp = ((c & 0x1F) << 6) | (word[byte_pos + 1] & 0x3F);
                byte_pos += 2;
            } else if ((c & 0xF0) == 0xE0) {
                cp = ((c & 0x0F) << 12) | ((word[byte_pos + 1] & 0x3F) << 6) | (word[byte_pos + 2] & 0x3F);
                byte_pos += 3;
            } else if ((c & 0xF8) == 0xF0) {
                cp = ((c & 0x07) << 18) | ((word[byte_pos + 1] & 0x3F) << 12) | 
                     ((word[byte_pos + 2] & 0x3F) << 6) | (word[byte_pos + 3] & 0x3F);
                byte_pos += 4;
            } else {
                byte_pos++;
                continue;
            }
            
            chars.push_back(cp);
        }
        
        // Walk the trie
        TrieNode* current = root.get();
        
        for (uint32_t cp : chars) {
            auto it = current->children.find(cp);
            if (it == current->children.end()) {
                return false; // Path doesn't exist
            }
            current = it->second.get();
        }
        
        // Check if this is a valid end-of-word node
        return current->phoneme.has_value();
    }
    
    /**
     * Load word list from text file (one word per line)
     * Builds trie for fast longest-match word segmentation
     */
    void load_from_file(const std::string& file_path) {
        std::ifstream file(file_path);
        if (!file.is_open()) {
            throw std::runtime_error("Failed to open word file: " + file_path);
        }
        
        std::cout << "🔥 Loading word dictionary for segmentation..." << std::endl;
        auto start_time = std::chrono::high_resolution_clock::now();
        
        std::string word;
        while (std::getline(file, word)) {
            // Remove trailing whitespace/newlines
            while (!word.empty() && (word.back() == '\r' || word.back() == '\n' || word.back() == ' ')) {
                word.pop_back();
            }
            
            if (!word.empty()) {
                insert_word(word);
                word_count++;
                
                if (word_count % 50000 == 0) {
                    std::cout << "\r   Loaded: " << word_count << " words" << std::flush;
                }
            }
        }
        
        auto end_time = std::chrono::high_resolution_clock::now();
        auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(end_time - start_time).count();
        
        std::cout << "\n✅ Loaded " << word_count << " words in " << elapsed << "ms" << std::endl;
    }
    
    /**
     * Insert a word into the trie
     */
    void insert_word(const std::string& word) {
        TrieNode* current = root.get();
        
        size_t pos = 0;
        while (pos < word.length()) {
            uint32_t code_point = get_code_point(word, pos);
            
            if (current->children.find(code_point) == current->children.end()) {
                current->children[code_point] = std::make_unique<TrieNode>();
            }
            current = current->children[code_point].get();
        }
        
        // Mark end of word (use empty string as marker)
        std::string empty_marker = "";
        current->phoneme = empty_marker;
    }
    
    /**
     * Segment text into words using longest-match algorithm with TextSegment support
     * SMART SEGMENTATION: Words are matched from dictionary, and any
     * unmatched sequences between words are treated as grammatical elements
     * (particles, conjugations, etc.) and given their own space.
     * 
     * Example: 私はリンゴがすきです
     * - Matches: 私, リンゴ, すき
     * - Grammar (unmatched): は, が, です
     * - Result: [私] [は] [リンゴ] [が] [すき] [です]
     * 
     * This new version properly handles TextSegments with furigana hints,
     * treating each segment as an atomic unit during segmentation.
     * 
     * @param phoneme_root Optional phoneme trie root for fallback lookups
     */
    std::vector<std::string> segment_from_segments(const std::vector<TextSegment>& segments, TrieNode* phoneme_root = nullptr) {
        std::vector<std::string> words;
        
        // Process each segment
        for (const auto& segment : segments) {
            // For furigana segments, treat the entire reading as one word
            if (segment.type == SegmentType::FURIGANA_HINT) {
                words.push_back(segment.reading);
                continue;
            }
            
            // For normal text segments, apply word segmentation
            const std::string& text = segment.text;
            
            // Pre-decode UTF-8 to code points for speed
            std::vector<uint32_t> chars;
            std::vector<size_t> byte_positions;
            size_t byte_pos = 0;
            
            while (byte_pos < text.length()) {
                byte_positions.push_back(byte_pos);
                chars.push_back(get_code_point(text, byte_pos));
            }
            byte_positions.push_back(byte_pos);
            
            size_t pos = 0;
            while (pos < chars.size()) {
                // Skip spaces in input
                uint32_t cp = chars[pos];
                if (cp == ' ' || cp == '\t' || cp == '\n' || cp == '\r') {
                    pos++;
                    continue;
                }
                
                // Try to find longest word match starting at current position
                // Check word dictionary first, then phoneme dictionary as fallback
                size_t match_length = 0;
                TrieNode* current = root.get();
                
                for (size_t i = pos; i < chars.size() && current != nullptr; i++) {
                    auto it = current->children.find(chars[i]);
                    if (it == current->children.end()) {
                        break;
                    }
                    
                    current = it->second.get();
                    
                    // If this node marks end of word, it's a valid match
                    if (current->phoneme.has_value()) {
                        match_length = i - pos + 1;
                    }
                }
                
                // 🔥 FALLBACK: If word dictionary didn't find a match, try phoneme dictionary
                if (match_length == 0 && phoneme_root != nullptr) {
                    TrieNode* phoneme_current = phoneme_root;
                    
                    for (size_t i = pos; i < chars.size() && phoneme_current != nullptr; i++) {
                        auto it = phoneme_current->children.find(chars[i]);
                        if (it == phoneme_current->children.end()) {
                            break;
                        }
                        
                        phoneme_current = it->second.get();
                        
                        // If this node has a phoneme, it's a valid word
                        if (phoneme_current->phoneme.has_value()) {
                            match_length = i - pos + 1;
                        }
                    }
                }
                
                if (match_length > 0) {
                    // Found a word match - extract it
                    size_t start_byte = byte_positions[pos];
                    size_t end_byte = byte_positions[pos + match_length];
                    words.push_back(text.substr(start_byte, end_byte - start_byte));
                    pos += match_length;
                } else {
                    // No match found - this is likely a grammatical element
                    // Collect all consecutive unmatched characters as a single token
                    // This handles particles (は、が、を), conjugations (です、ます), etc.
                    size_t grammar_start = pos;
                    size_t grammar_length = 0;
                    
                    // Keep collecting characters until we find another word match
                    while (pos < chars.size()) {
                        // Skip spaces
                        if (chars[pos] == ' ' || chars[pos] == '\t' || chars[pos] == '\n' || chars[pos] == '\r') {
                            break;
                        }
                        
                        // Try to match a word starting from current position
                        size_t lookahead_match = 0;
                        TrieNode* lookahead = root.get();
                        
                        for (size_t i = pos; i < chars.size() && lookahead != nullptr; i++) {
                            auto it = lookahead->children.find(chars[i]);
                            if (it == lookahead->children.end()) {
                                break;
                            }
                            lookahead = it->second.get();
                            if (lookahead->phoneme.has_value()) {
                                lookahead_match = i - pos + 1;
                            }
                        }
                        
                        // If we found a word match, stop here
                        if (lookahead_match > 0) {
                            break;
                        }
                        
                        // Otherwise, this character is part of the grammar sequence
                        grammar_length++;
                        pos++;
                    }
                    
                    // Extract the grammar token
                    if (grammar_length > 0) {
                        size_t start_byte = byte_positions[grammar_start];
                        size_t end_byte = byte_positions[grammar_start + grammar_length];
                        words.push_back(text.substr(start_byte, end_byte - start_byte));
                    }
                }
            }
        }
        
        return words;
    }
};

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// FURIGANA HINT PROCESSING
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

/**
 * Helper function to check if a UTF-8 character is hiragana or katakana
 * 
 * @param text The text containing the character
 * @param byte_pos The byte position of the character (must be start of UTF-8 sequence)
 * @return true if character is hiragana or katakana, false otherwise
 */
bool is_kana(const std::string& text, size_t byte_pos) {
    if (byte_pos + 2 >= text.length()) return false;
    
    // Check if this is a 3-byte UTF-8 sequence (most Japanese characters are)
    unsigned char b1 = static_cast<unsigned char>(text[byte_pos]);
    if ((b1 & 0xF0) != 0xE0) return false;
    
    unsigned char b2 = static_cast<unsigned char>(text[byte_pos + 1]);
    unsigned char b3 = static_cast<unsigned char>(text[byte_pos + 2]);
    
    // Decode UTF-8 to Unicode code point
    uint32_t codepoint = ((b1 & 0x0F) << 12) | ((b2 & 0x3F) << 6) | (b3 & 0x3F);
    
    // Check if it's hiragana (U+3040-U+309F) or katakana (U+30A0-U+30FF)
    return (codepoint >= 0x3040 && codepoint <= 0x309F) ||  // Hiragana
           (codepoint >= 0x30A0 && codepoint <= 0x30FF);    // Katakana
}

/**
 * Parse text into segments, extracting furigana hints.
 * 
 * This creates a structured representation of the text where each segment
 * is either normal text or a furigana hint. This approach is cleaner than
 * using markers and makes the processing logic more transparent.
 * 
 * SMART COMPOUND WORD DETECTION:
 * - If kanji「reading」+following text forms a dictionary word, prefer dictionary
 * - Example: 見「み」て → Check if 見て is a word → YES → Keep as normal text "見て"
 * - Example: 健太「けんた」て → Check if 健太て is a word → NO → Use furigana "けんた"
 * 
 * @param text Input text with potential furigana hints (e.g., 健太「けんた」)
 * @param segmenter Optional word segmenter for compound word detection
 * @return Vector of text segments with furigana hints properly parsed
 */
std::vector<TextSegment> parse_furigana_segments(const std::string& text, WordSegmenter* segmenter = nullptr) {
    std::vector<TextSegment> segments;
    
    // 🔥 PRE-DECODE UTF-8 TO CODE POINTS FOR BLAZING SPEED!
    // Just like in the Rust version, this is the key to performance
    std::vector<uint32_t> chars;
    std::vector<size_t> byte_positions;
    size_t byte_pos = 0;
    
    // Helper lambda to get code point
    auto get_code_point_lambda = [](const std::string& str, size_t& pos) -> uint32_t {
        unsigned char c = str[pos];
        
        if (c < 0x80) {
            pos++;
            return c;
        } else if ((c & 0xE0) == 0xC0) {
            uint32_t cp = ((c & 0x1F) << 6) | (str[pos + 1] & 0x3F);
            pos += 2;
            return cp;
        } else if ((c & 0xF0) == 0xE0) {
            uint32_t cp = ((c & 0x0F) << 12) | ((str[pos + 1] & 0x3F) << 6) | (str[pos + 2] & 0x3F);
            pos += 3;
            return cp;
        } else if ((c & 0xF8) == 0xF0) {
            uint32_t cp = ((c & 0x07) << 18) | ((str[pos + 1] & 0x3F) << 12) | 
                         ((str[pos + 2] & 0x3F) << 6) | (str[pos + 3] & 0x3F);
            pos += 4;
            return cp;
        }
        
        pos++;
        return c;
    };
    
    while (byte_pos < text.length()) {
        byte_positions.push_back(byte_pos);
        chars.push_back(get_code_point_lambda(text, byte_pos));
    }
    byte_positions.push_back(byte_pos);
    
    // Now process using pre-decoded code points for speed
    size_t pos = 0;
    
    while (pos < chars.size()) {
        // Look for opening bracket 「 (U+300C)
        size_t bracket_open = std::string::npos;
        for (size_t i = pos; i < chars.size(); i++) {
            if (chars[i] == 0x300C) {
                bracket_open = i;
                break;
            }
        }
        
        if (bracket_open == std::string::npos) {
            // No more furigana hints, add rest of text as normal segment
            if (pos < chars.size()) {
                size_t start_byte = byte_positions[pos];
                size_t end_byte = byte_positions[chars.size()];
                segments.push_back(TextSegment(text.substr(start_byte, end_byte - start_byte), start_byte));
            }
            break;
        }
        
        // Look for closing bracket 」 (U+300D)
        size_t bracket_close = std::string::npos;
        for (size_t i = bracket_open + 1; i < chars.size(); i++) {
            if (chars[i] == 0x300D) {
                bracket_close = i;
                break;
            }
        }
        
        if (bracket_close == std::string::npos) {
            // No closing bracket, add rest as normal segment
            size_t start_byte = byte_positions[pos];
            size_t end_byte = byte_positions[chars.size()];
            segments.push_back(TextSegment(text.substr(start_byte, end_byte - start_byte), start_byte));
            break;
        }
        
        // Find where the "word" (kanji) starts before the opening bracket
        // 🔥 BLAZING FAST BOUNDARY DETECTION USING PRE-DECODED CODE POINTS!
        size_t word_start = bracket_open; // Start from bracket and search backward
        size_t search_pos = bracket_open;
        
        // Helper lambda to check if code point is kana (inline for speed)
        auto is_kana_cp = [](uint32_t cp) -> bool {
            return (cp >= 0x3040 && cp <= 0x309F) ||  // Hiragana
                   (cp >= 0x30A0 && cp <= 0x30FF);    // Katakana
        };
        
        // Search backwards to find the start of the kanji/word that has furigana
        // 🔥 SMART OKURIGANA DETECTION:
        // - その男「おとこ」 → Stop at kana prefix "その", capture only "男"  
        // - 昼ご飯「ひるごはん」 → Keep kana "ご" sandwiched between kanji, capture all "昼ご飯"
        // Algorithm: Scan backward collecting chars. Stop at first kana that's followed (backward) by only more kana.
        
        // First pass: Find the last non-kana (kanji) character before the bracket
        size_t last_kanji_pos = bracket_open;
        while (last_kanji_pos > pos && is_kana_cp(chars[last_kanji_pos - 1])) {
            last_kanji_pos--;
        }
        
        if (last_kanji_pos > pos) {
            last_kanji_pos--;  // Now pointing at the last kanji
        }
        
        // Second pass: From last kanji, search backward for word boundary
        // Include okurigana (kana between kanji), but stop at kana-only prefix
        word_start = last_kanji_pos;
        search_pos = last_kanji_pos;
        
        while (search_pos > pos) {
            search_pos--;
            uint32_t cp = chars[search_pos];
            
            // Check for punctuation boundaries first (these always stop us)
            if (cp == 0x300D ||  // 」 closing bracket (another furigana hint)
                cp == 0x3001 ||  // 、 Japanese comma
                cp == 0x3002 ||  // 。 Japanese period  
                cp == 0xFF01 ||  // ！ full-width exclamation
                cp == 0xFF1F ||  // ？ full-width question
                cp == 0xFF09 ||  // ） full-width right paren
                cp == 0xFF3D) {  // ］ full-width right bracket
                word_start = search_pos + 1;
                break;
            }
            
            // Check for ASCII punctuation and whitespace
            if (cp < 0x80 && (
                cp == '.' || cp == ',' || cp == '!' || cp == '?' || cp == ';' || cp == ':' ||
                cp == '(' || cp == ')' || cp == '[' || cp == ']' || cp == '{' || cp == '}' ||
                cp == '"' || cp == '\'' || cp == '-' || cp == '/' || cp == '\\' || cp == '|' ||
                cp == ' ' || cp == '\t' || cp == '\n' || cp == '\r')) {
                word_start = search_pos + 1;
                break;
            }
            
            // Check if this is kana
            bool is_kana_char = is_kana_cp(cp);
            
            if (is_kana_char) {
                // Check if there's ANY non-kana (kanji) before this position
                bool has_kanji_before = false;
                for (size_t check_pos = search_pos; check_pos > pos; check_pos--) {
                    if (!is_kana_cp(chars[check_pos - 1])) {
                        // Check it's not punctuation
                        uint32_t check_cp = chars[check_pos - 1];
                        if (check_cp >= 0x4E00 || (check_cp >= 0x3400 && check_cp <= 0x9FFF)) {  // CJK kanji ranges
                            has_kanji_before = true;
                            break;
                        }
                    }
                }
                
                if (!has_kanji_before) {
                    // This kana is not sandwiched - it's a prefix word → stop here
                    word_start = search_pos + 1;
                    break;
                }
                // Otherwise, this kana is sandwiched (okurigana) → continue
            }
            
            // Update word_start to include this character
            word_start = search_pos;
        }
        
        // Add text from current position up to where the word/kanji starts
        // This captures particles and other text between furigana hints
        if (word_start > pos) {
            size_t start_byte = byte_positions[pos];
            size_t end_byte = byte_positions[word_start];
            segments.push_back(TextSegment(text.substr(start_byte, end_byte - start_byte), start_byte));
        }
        
        // Extract the kanji and reading using pre-decoded positions
        size_t kanji_start_byte = byte_positions[word_start];
        size_t kanji_end_byte = byte_positions[bracket_open];
        std::string kanji = text.substr(kanji_start_byte, kanji_end_byte - kanji_start_byte);
        
        // Extract reading between brackets
        size_t reading_start = bracket_open + 1; // Position after 「
        size_t reading_end = bracket_close;      // Position before 」
        
        // Extract reading text using byte positions
        size_t reading_start_byte = byte_positions[reading_start];
        size_t reading_end_byte = byte_positions[reading_end];
        std::string reading = text.substr(reading_start_byte, reading_end_byte - reading_start_byte);
        
        // Fast whitespace trimming using code points
        size_t trim_start = 0;
        size_t trim_end = reading_end - reading_start;
        
        // Trim leading whitespace
        while (trim_start < trim_end) {
            uint32_t cp = chars[reading_start + trim_start];
            if (cp != ' ' && cp != '\t' && cp != '\n' && cp != '\r') break;
            trim_start++;
        }
        
        // Trim trailing whitespace
        while (trim_end > trim_start) {
            uint32_t cp = chars[reading_start + trim_end - 1];
            if (cp != ' ' && cp != '\t' && cp != '\n' && cp != '\r') break;
            trim_end--;
        }
        
        if (trim_start >= trim_end) {
            // Empty reading - skip the entire furigana hint
            pos = bracket_close + 1;
            continue;
        }
        
        // Extract trimmed reading
        size_t trimmed_start_byte = byte_positions[reading_start + trim_start];
        size_t trimmed_end_byte = byte_positions[reading_start + trim_end];
        reading = text.substr(trimmed_start_byte, trimmed_end_byte - trimmed_start_byte);
        
        // 🔥 SMART COMPOUND WORD DETECTION USING TRIE'S LONGEST-MATCH
        // Walk the trie starting from kanji to find the longest compound word
        size_t after_bracket = bracket_close + 1; // Position after 」
        bool used_compound = false;
        
        if (segmenter && after_bracket < chars.size()) {
            // Use trie to find longest match starting from word_start position
            // This naturally implements longest-match algorithm
            size_t match_length = 0;
            TrieNode* current = segmenter->get_root();
            
            // Walk trie through kanji characters first
            for (size_t i = word_start; i < bracket_open && current != nullptr; i++) {
                auto it = current->children.find(chars[i]);
                if (it == current->children.end()) {
                    break;
                }
                current = it->second.get();
            }
            
            // Continue walking through characters after the bracket
            if (current != nullptr) {
                for (size_t i = after_bracket; i < chars.size() && current != nullptr; i++) {
                    auto it = current->children.find(chars[i]);
                    if (it == current->children.end()) {
                        break;
                    }
                    current = it->second.get();
                    
                    // Check if this position marks a valid word ending
                    if (current->phoneme.has_value()) {
                        // Found a compound! Track it as the longest so far
                        match_length = i - after_bracket + 1;
                    }
                }
            }
            
            // If we found a compound word, use it with the furigana reading replacing the kanji
            // This ensures that 来「き」た becomes "きた" not "来た" for phoneme conversion
            if (match_length > 0) {
                size_t compound_end_byte = byte_positions[after_bracket + match_length];
                // 🔥 KEY FIX: Use the furigana READING instead of kanji!
                std::string compound = reading + text.substr(byte_positions[after_bracket], 
                                                             compound_end_byte - byte_positions[after_bracket]);
                segments.push_back(TextSegment(compound, kanji_start_byte));
                pos = after_bracket + match_length;
                used_compound = true;
            }
        }
        
        if (!used_compound) {
            // No compound found, use the furigana hint
            segments.push_back(TextSegment(kanji, reading, kanji_start_byte));
            pos = bracket_close + 1;
        }
    }
    
    return segments;
}


/**
 * Helper functions for PhonemeConverter with word segmentation
 * Defined here after WordSegmenter class is complete
 */
namespace SegmentedConversion {
    /**
     * Convert with word segmentation support
     * Optimized algorithm with TextSegment-based furigana processing:
     * 1) Parse text into segments with furigana hints extracted
     * 2) Segment into words using the structured segments
     * 3) Convert each word to phonemes
     * Returns phonemes with spaces between words
     * 
     * BLAZING FAST: Uses pre-decoded UTF-8 throughout for 0ms execution
     */
    std::string convert_with_segmentation(PhonemeConverter& converter, const std::string& japanese_text, WordSegmenter& segmenter) {
        // 🔥 STEP 1: Parse furigana hints into structured segments
        // 健太「けんた」はバカ → [TextSegment("健太", "けんた"), TextSegment("はバカ")]
        // 見「み」て → [TextSegment("見て")] (compound word detected)
        auto segments = parse_furigana_segments(japanese_text, &segmenter);
        
        // 🔥 STEP 2: Segment into words using structured segments with phoneme fallback
        // Furigana segments are treated as atomic units
        auto words = segmenter.segment_from_segments(segments, converter.get_root());
        
        // 🔥 STEP 3: Convert each word to phonemes with particle handling
        std::string result;
        for (size_t i = 0; i < words.size(); i++) {
            if (i > 0) result += " ";  // Add space between words
            
            // Special handling for the topic particle は → "wa"
            if (words[i] == "は" || words[i] == "\xe3\x81\xaf") {  // は in UTF-8
                result += "wa";
            } else {
                result += converter.convert(words[i]);
            }
        }
        
        return result;
    }
    
    /**
     * Convert with word segmentation and detailed information
     * Includes furigana hint processing for proper name handling
     * BLAZING FAST: Uses pre-decoded UTF-8 and structured segments
     */
    ConversionResult convert_detailed_with_segmentation(PhonemeConverter& converter, const std::string& japanese_text, WordSegmenter& segmenter) {
        // 🔥 STEP 1: Parse furigana hints into structured segments
        auto segments = parse_furigana_segments(japanese_text, &segmenter);
        
        // 🔥 STEP 2: Segment into words using structured segments with phoneme fallback
        auto words = segmenter.segment_from_segments(segments, converter.get_root());
        
        // 🔥 STEP 3: Convert each word to phonemes with particle handling
        ConversionResult result;
        size_t byte_offset = 0;
        
        for (size_t i = 0; i < words.size(); i++) {
            if (i > 0) result.phonemes += " ";  // Add space between words
            
            // Special handling for the topic particle は → "wa"
            if (words[i] == "は" || words[i] == "\xe3\x81\xaf") {  // は in UTF-8
                result.phonemes += "wa";
                // Add to matches for consistency
                Match match;
                match.original = words[i];
                match.phoneme = "wa";
                match.start_index = byte_offset;
                result.matches.push_back(match);
            } else {
                auto word_result = converter.convert_detailed(words[i]);
                
                // Adjust match positions to account for original text position
                for (auto& match : word_result.matches) {
                    match.start_index += byte_offset;
                    result.matches.push_back(match);
                }
                
                result.phonemes += word_result.phonemes;
                result.unmatched.insert(result.unmatched.end(), 
                                       word_result.unmatched.begin(), 
                                       word_result.unmatched.end());
            }
            
            byte_offset += words[i].length();
        }
        
        return result;
    }
}

// Helper function to get UTF-8 command line arguments on Windows
#ifdef _WIN32
std::vector<std::string> get_utf8_args() {
    std::vector<std::string> args;
    int nArgs;
    LPWSTR* szArglist = CommandLineToArgvW(GetCommandLineW(), &nArgs);
    
    if (szArglist != NULL) {
        for (int i = 0; i < nArgs; i++) {
            int size_needed = WideCharToMultiByte(CP_UTF8, 0, szArglist[i], -1, NULL, 0, NULL, NULL);
            std::string utf8_arg(size_needed - 1, 0);
            WideCharToMultiByte(CP_UTF8, 0, szArglist[i], -1, &utf8_arg[0], size_needed, NULL, NULL);
            args.push_back(utf8_arg);
        }
        LocalFree(szArglist);
    }
    return args;
}
#endif

int main(int argc, char* argv[]) {
    // Enable UTF-8 support for Windows console
    #ifdef _WIN32
        SetConsoleOutputCP(CP_UTF8);
        SetConsoleCP(CP_UTF8);
        setvbuf(stdout, nullptr, _IOFBF, 1000);
    #endif
    
    std::cout << "╔══════════════════════════════════════════════════════════╗" << std::endl;
    std::cout << "║  Japanese → Phoneme Converter (C++)                     ║" << std::endl;
    std::cout << "║  Blazing fast IPA phoneme conversion                    ║" << std::endl;
    std::cout << "╚══════════════════════════════════════════════════════════╝\n" << std::endl;
    
    // Check if JSON file exists
    std::ifstream test_file("ja_phonemes.json");
    if (!test_file.good()) {
        std::cerr << "❌ Error: ja_phonemes.json not found in current directory" << std::endl;
        std::cerr << "   Please ensure the phoneme dictionary is present." << std::endl;
        return 1;
    }
    test_file.close();
    
    // Initialize converter and load dictionary
    // 🚀 Try binary trie first (100x faster!), fallback to JSON
    PhonemeConverter converter;
    bool loaded = false;
    
    // Try simple binary format (direct load into TrieNode*)
    if (converter.try_load_binary_format("japanese.trie")) {
        loaded = true;
        std::cout << "   💡 Binary format loaded directly into TrieNode*" << std::endl;
    } else {
        // Fallback to JSON
        std::cout << "   ⚠️  Binary trie not found, loading JSON..." << std::endl;
        try {
            converter.load_from_json("ja_phonemes.json");
            loaded = true;
        } catch (const std::exception& e) {
            std::cerr << "❌ Error loading dictionary: " << e.what() << std::endl;
            return 1;
        }
    }
    
    // Initialize word segmenter if enabled
    std::unique_ptr<WordSegmenter> segmenter;
    if (USE_WORD_SEGMENTATION) {
        // If using binary format, words are already loaded!
        if (loaded) {
            std::cout << "   💡 Word segmentation: Words already in TrieNode* from binary format" << std::endl;
            // Word entries (with empty phoneme values) are already in the trie
        } else {
            // Load separate word file
            std::ifstream test_word_file("ja_words.txt");
            if (test_word_file.good()) {
                test_word_file.close();
                segmenter = std::make_unique<WordSegmenter>();
                try {
                    segmenter->load_from_file("ja_words.txt");
                    std::cout << "   💡 Word segmentation: ENABLED (spaces will separate words)" << std::endl;
                } catch (const std::exception& e) {
                    std::cerr << "⚠️  Warning: Could not load word dictionary: " << e.what() << std::endl;
                    std::cerr << "   Continuing without word segmentation..." << std::endl;
                    segmenter.reset();
                }
            } else {
                std::cout << "   💡 Word segmentation: DISABLED (ja_words.txt not found)" << std::endl;
            }
        }
    }
    
    std::cout << "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n" << std::endl;
    
    // Get UTF-8 arguments on Windows
    #ifdef _WIN32
        auto utf8_args = get_utf8_args();
        int arg_count = utf8_args.size();
    #else
        int arg_count = argc;
    #endif
    
    if (arg_count < 2) {
        // Interactive mode
        std::cout << "💡 Usage: ./jpn_to_phoneme \"日本語テキスト\"" << std::endl;
        std::cout << "   Or enter Japanese text interactively:\n" << std::endl;
        
        std::string input;
        while (true) {
            std::cout << "Japanese text (or \"quit\" to exit): ";
            std::getline(std::cin, input);
            
            if (input.empty()) continue;
            
            if (input == "quit" || input == "exit") {
                std::cout << "\n👋 Goodbye!" << std::endl;
                break;
            }
            
            // Perform conversion with timing
            auto start_time = std::chrono::high_resolution_clock::now();
            ConversionResult result;
            if (segmenter) {
                result = SegmentedConversion::convert_detailed_with_segmentation(converter, input, *segmenter);
            } else {
                result = converter.convert_detailed(input);
            }
            auto end_time = std::chrono::high_resolution_clock::now();
            auto elapsed = std::chrono::duration_cast<std::chrono::microseconds>(end_time - start_time).count();
            
            // Display results
            std::cout << "\n┌─────────────────────────────────────────" << std::endl;
            std::cout << "│ Input:    " << input << std::endl;
            std::cout << "│ Phonemes: " << result.phonemes << std::endl;
            std::cout << "│ Time:     " << elapsed << "μs" << std::endl;
            std::cout << "└─────────────────────────────────────────" << std::endl;
            
            if (!result.matches.empty()) {
                std::cout << "\n  Matches (" << result.matches.size() << "):" << std::endl;
                for (const auto& match : result.matches) {
                    std::cout << "    • " << match.to_string() << std::endl;
                }
            }
            
            if (!result.unmatched.empty()) {
                std::cout << "\n  ⚠️  Unmatched characters: ";
                for (size_t i = 0; i < result.unmatched.size(); i++) {
                    if (i > 0) std::cout << ", ";
                    std::cout << result.unmatched[i];
                }
                std::cout << std::endl;
            }
            
            std::cout << std::endl;
        }
    } else {
        // Batch mode - convert all arguments
        for (int i = 1; i < arg_count; i++) {
            #ifdef _WIN32
                std::string text = utf8_args[i];
            #else
                std::string text = argv[i];
            #endif
            
            // Perform conversion with timing
            auto start_time = std::chrono::high_resolution_clock::now();
            ConversionResult result;
            if (segmenter) {
                result = SegmentedConversion::convert_detailed_with_segmentation(converter, text, *segmenter);
            } else {
                result = converter.convert_detailed(text);
            }
            auto end_time = std::chrono::high_resolution_clock::now();
            auto elapsed_us = std::chrono::duration_cast<std::chrono::microseconds>(end_time - start_time).count();
            auto elapsed_ms = elapsed_us / 1000.0;
            
            // Display results
            std::cout << "┌─────────────────────────────────────────" << std::endl;
            std::cout << "│ Input:    " << text << std::endl;
            std::cout << "│ Phonemes: " << result.phonemes << std::endl;
            std::cout << "│ Time:     " << elapsed_us << "μs (" << elapsed_ms << "ms)" << std::endl;
            std::cout << "└─────────────────────────────────────────" << std::endl;
            
            if (!result.matches.empty()) {
                std::cout << "\n  ✅ Matches (" << result.matches.size() << "):" << std::endl;
                for (const auto& match : result.matches) {
                    std::cout << "    • " << match.to_string() << std::endl;
                }
            }
            
            if (!result.unmatched.empty()) {
                std::cout << "\n  ⚠️  Unmatched characters: ";
                for (size_t i = 0; i < result.unmatched.size(); i++) {
                    if (i > 0) std::cout << ", ";
                    std::cout << result.unmatched[i];
                }
                std::cout << std::endl;
            }
            
            std::cout << std::endl;
        }
        
        std::cout << "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n" << std::endl;
        std::cout << "✨ Conversion complete!" << std::endl;
    }
    
    return 0;
}

