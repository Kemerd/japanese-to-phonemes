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
            
            // Walk the trie as far as possible (now using pre-decoded chars!)
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
            
            // Walk the trie as far as possible (now using pre-decoded chars!)
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
     * Segment text into words using longest-match algorithm
     * SMART SEGMENTATION: Words are matched from dictionary, and any
     * unmatched sequences between words are treated as grammatical elements
     * (particles, conjugations, etc.) and given their own space.
     * 
     * Example: 私はリンゴがすきです
     * - Matches: 私, リンゴ, すき
     * - Grammar (unmatched): は, が, です
     * - Result: [私] [は] [リンゴ] [が] [すき] [です]
     */
    std::vector<std::string> segment(const std::string& text) {
        std::vector<std::string> words;
        
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
            
            // 🔥 CHECK FOR FURIGANA MARKERS (‹ U+2039)
            // If we see a marker, grab everything until closing marker › as ONE unit
            // This prevents breaking up marked names like ‹けんた›
            if (cp == 0x2039) {
                size_t marker_start = pos;
                pos++; // Skip opening ‹
                
                // Find closing marker ›
                while (pos < chars.size() && chars[pos] != 0x203A) {
                    pos++;
                }
                
                if (pos < chars.size() && chars[pos] == 0x203A) {
                    pos++; // Include closing ›
                }
                
                // Extract the entire marked section as a single unit
                size_t start_byte = byte_positions[marker_start];
                size_t end_byte = byte_positions[pos];
                words.push_back(text.substr(start_byte, end_byte - start_byte));
                continue; // Move to next token
            }
            
            // Try to find longest word match starting at current position
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
        
        return words;
    }
};

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// FURIGANA HINT PROCESSING
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

/**
 * Lightweight structure to hold parsed furigana hint information
 * Used for efficient compound word detection and smart hint processing
 */
struct FuriganaHint {
    size_t kanji_start;      // Start position of kanji/text in original string
    size_t kanji_end;        // End position of kanji (just before 「)
    size_t bracket_open;     // Position of opening bracket 「
    size_t bracket_close;    // Position of closing bracket 」
    std::string kanji;       // The kanji/text before bracket (e.g., "健太" or "見")
    std::string reading;     // The reading inside brackets (e.g., "けんた" or "み")
    
    // Constructor for easy initialization
    FuriganaHint(size_t k_start, size_t k_end, size_t b_open, size_t b_close,
                 const std::string& k, const std::string& r)
        : kanji_start(k_start), kanji_end(k_end), 
          bracket_open(b_open), bracket_close(b_close),
          kanji(k), reading(r) {}
};


/**
 * Process furigana hints by replacing text「reading」with special markers.
 * 
 * This preserves furigana readings as single units during word segmentation.
 * Uses marker characters (U+2039/U+203A ‹›) that are unlikely in normal text.
 * 
 * HOW IT WORKS:
 * 1. Find patterns like: 健太「けんた」はバカ
 * 2. Replace with markers: ‹けんた›はバカ
 * 3. Markers prevent word segmentation from breaking up the name
 * 4. Smart segmenter recognizes ‹けんた› as a "word" and treats は as a particle
 * 5. Result: ‹けんた› は バカ (proper separation!)
 * 6. Remove markers after processing: けんた は バカ ✅
 * 
 * SMART COMPOUND WORD DETECTION:
 * - If kanji「reading」+following text forms a dictionary word, prefer dictionary
 * - Example: 見「み」て → Check if 見て is a word → YES → Use 見て from dict (drop hint)
 * - Example: 健太「けんた」て → Check if 健太て is a word → NO → Use ‹けんた›て (use hint)
 * - This prevents forcing wrong readings when compounds exist in dictionary
 * 
 * WHY MARKERS ARE BRILLIANT:
 * - No hardcoded particle lists needed (は、が、を、の、と, etc.)
 * - Leverages existing smart segmentation algorithm
 * - Grammar recognition is intrinsic, not explicit
 * - Minimal code changes, maximum impact
 * 
 * @param text Input text with potential furigana hints (e.g., 健太「けんた」)
 * @param segmenter Optional word segmenter for compound word detection
 * @return Text with furigana applied and marked for segmentation (e.g., ‹けんた›)
 */
std::string process_furigana_hints(const std::string& text, WordSegmenter* segmenter = nullptr) {
    // Manual parsing approach with smart compound word detection
    // Find patterns: kanji「reading」→ check for compounds first
    // Example: 見「み」て → Check if 見て is a word → YES → keep 見て
    // Example: 健太「けんた」て → Check if 健太て is a word → NO → use ‹けんた›て
    
    std::string output;
    size_t pos = 0;
    
    while (pos < text.length()) {
        // Look for opening bracket 「 (U+300C: E3 80 8C in UTF-8)
        size_t bracket_open = text.find("\u300C", pos);
        
        if (bracket_open == std::string::npos) {
            // No more furigana hints, add rest of text
            output += text.substr(pos);
            break;
        }
        
        // Look for closing bracket 」 (U+300D: E3 80 8D in UTF-8)
        size_t bracket_close = text.find("\u300D", bracket_open);
        
        if (bracket_close == std::string::npos) {
            // No closing bracket, add rest as-is
            output += text.substr(pos);
            break;
        }
        
        // Find where the "word" (kanji) starts before the opening bracket
        // Look backwards from bracket_open to find word boundary
        // Word boundaries: start of string, space, or previous closing bracket」
        size_t word_start = pos;
        size_t search_pos = bracket_open;
        
        // Search backwards for word boundary
        while (search_pos > pos) {
            // Check for space or previous furigana bracket
            if (search_pos >= 3) {
                std::string check = text.substr(search_pos - 3, 3);
                if (check == "\u300D" || check == " " || check == "\t" || check == "\n") {
                    word_start = search_pos;
                    break;
                }
            }
            
            // Move back one byte (we'll iterate through UTF-8 boundaries naturally)
            if (search_pos > 0) {
                search_pos--;
            } else {
                break;
            }
        }
        
        // Add text from current position up to where the word/kanji starts
        if (word_start > pos) {
            output += text.substr(pos, word_start - pos);
        }
        
        // Extract the kanji and reading
        std::string kanji = text.substr(word_start, bracket_open - word_start);
        size_t reading_start = bracket_open + 3; // +3 bytes for UTF-8 encoded 「
        size_t reading_length = bracket_close - reading_start;
        std::string reading = text.substr(reading_start, reading_length);
        
        // Trim whitespace from reading
        size_t trim_start = reading.find_first_not_of(" \t\n\r");
        size_t trim_end = reading.find_last_not_of(" \t\n\r");
        
        if (trim_start == std::string::npos || reading.empty()) {
            // Empty reading - skip the entire furigana hint
            pos = bracket_close + 3;
            continue;
        }
        
        reading = reading.substr(trim_start, trim_end - trim_start + 1);
        
        // 🔥 SMART COMPOUND WORD DETECTION
        // Check if kanji + following text forms a dictionary word
        // This prioritizes dictionary compounds over forced furigana readings
        
        size_t after_bracket = bracket_close + 3; // Position after 」
        bool used_compound = false;
        
        if (segmenter && after_bracket < text.length()) {
            // Try progressively longer combinations: kanji+1char, kanji+2char, etc.
            // We want to find the longest match that includes text after the bracket
            size_t max_lookahead = std::min(text.length() - after_bracket, size_t(30)); // Check up to 30 bytes ahead
            
            for (size_t lookahead = 3; lookahead <= max_lookahead; lookahead += 3) {
                // Extract kanji + following text
                std::string compound = kanji + text.substr(after_bracket, lookahead);
                
                // Check if this compound is a single dictionary word
                if (segmenter->contains_word(compound)) {
                    // Found a compound word! Use it instead of the furigana hint
                    output += compound;
                    pos = after_bracket + lookahead;
                    used_compound = true;
                    break;
                }
            }
        }
        
        if (!used_compound) {
            // No compound found, use the furigana hint with markers
            // Wrap reading in markers: ‹reading›
            // U+2039 = ‹ (single left-pointing angle quotation mark)
            // U+203A = › (single right-pointing angle quotation mark)
            output += "\u2039" + reading + "\u203A";
            pos = bracket_close + 3;
        }
    }
    
    return output;
}

/**
 * Remove furigana markers from text after processing.
 * 
 * Removes the ‹› markers used to preserve furigana readings as single units.
 * This is called after word segmentation and phoneme conversion to clean up output.
 * 
 * Example: ‹keɴta› wa baka → keɴta wa baka
 * 
 * @param text Text with markers (e.g., ‹けんた›)
 * @return Text without markers (e.g., けんた)
 */
std::string remove_furigana_markers(const std::string& text) {
    std::string result = text;
    
    // Remove ‹ (U+2039) markers
    // UTF-8 encoding of U+2039 is: E2 80 B9 (3 bytes)
    size_t pos = 0;
    while ((pos = result.find("\u2039", pos)) != std::string::npos) {
        result.erase(pos, 3);  // UTF-8 encoding of U+2039 is 3 bytes
    }
    
    // Remove › (U+203A) markers
    // UTF-8 encoding of U+203A is: E2 80 BA (3 bytes)
    pos = 0;
    while ((pos = result.find("\u203A", pos)) != std::string::npos) {
        result.erase(pos, 3);  // UTF-8 encoding of U+203A is 3 bytes
    }
    
    return result;
}

/**
 * Helper functions for PhonemeConverter with word segmentation
 * Defined here after WordSegmenter class is complete
 */
namespace SegmentedConversion {
    /**
     * Convert with word segmentation support
     * Three-pass algorithm with furigana hint processing:
     * 1) Process furigana hints (健太「けんた」→ ‹けんた›)
     * 2) Segment into words (‹けんた›はバカ → ‹けんた›、は、バカ)
     * 3) Convert each word to phonemes (‹けんた› → ‹keɴta›)
     * 4) Remove markers from final output (‹keɴta› → keɴta)
     * Returns phonemes with spaces between words
     */
    std::string convert_with_segmentation(PhonemeConverter& converter, const std::string& japanese_text, WordSegmenter& segmenter) {
        // 🔥 STEP 1: Process furigana hints with smart compound detection
        // 健太「けんた」はバカ → ‹けんた›はバカ (marked as single unit)
        // 見「み」て → 見て (compound word detected, use dictionary)
        std::string processed_text = process_furigana_hints(japanese_text, &segmenter);
        
        // 🔥 STEP 2: Segment into words with markers preserved
        // ‹けんた›はバカ → [‹けんた›] [は] [バカ]
        // Smart segmenter treats ‹けんた› as a word and は as a particle!
        auto words = segmenter.segment(processed_text);
        
        // 🔥 STEP 3: Convert each word to phonemes (markers stay intact)
        std::string result;
        for (size_t i = 0; i < words.size(); i++) {
            if (i > 0) result += " ";  // Add space between words
            result += converter.convert(words[i]);
        }
        
        // 🔥 STEP 4: Remove markers from final output
        // ‹keɴta› wa baka → keɴta wa baka ✅
        result = remove_furigana_markers(result);
        
        return result;
    }
    
    /**
     * Convert with word segmentation and detailed information
     * Includes furigana hint processing for proper name handling
     */
    ConversionResult convert_detailed_with_segmentation(PhonemeConverter& converter, const std::string& japanese_text, WordSegmenter& segmenter) {
        // 🔥 STEP 1: Process furigana hints with smart compound detection
        // 健太「けんた」はバカ → ‹けんた›はバカ
        // 見「み」て → 見て (compound word detected, use dictionary)
        std::string processed_text = process_furigana_hints(japanese_text, &segmenter);
        
        // 🔥 STEP 2: Segment into words with markers preserved
        auto words = segmenter.segment(processed_text);
        
        // 🔥 STEP 3: Convert each word to phonemes
        ConversionResult result;
        size_t byte_offset = 0;
        
        for (size_t i = 0; i < words.size(); i++) {
            if (i > 0) result.phonemes += " ";  // Add space between words
            
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
            
            byte_offset += words[i].length();
        }
        
        // 🔥 STEP 4: Remove markers from final output
        result.phonemes = remove_furigana_markers(result.phonemes);
        
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
    PhonemeConverter converter;
    try {
        converter.load_from_json("ja_phonemes.json");
    } catch (const std::exception& e) {
        std::cerr << "❌ Error loading dictionary: " << e.what() << std::endl;
        return 1;
    }
    
    // Initialize word segmenter if enabled
    std::unique_ptr<WordSegmenter> segmenter;
    if (USE_WORD_SEGMENTATION) {
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

