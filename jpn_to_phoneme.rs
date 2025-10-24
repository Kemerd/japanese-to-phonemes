// Japanese to Phoneme Converter - Rust Edition
// Blazing fast IPA phoneme conversion using optimized trie structure
// Compile: rustc -O jpn_to_phoneme.rs
// Or with Cargo: cargo build --release
// Usage: ./jpn_to_phoneme "日本語テキスト"

use std::collections::HashMap;
use std::env;
use std::fs;
use std::io::{self, Write, BufRead, BufReader, Read};
use std::time::Instant;

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// CONFIGURATION
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

// Enable word segmentation to add spaces between words in output
// Uses ja_words.txt for Japanese word boundaries
const USE_WORD_SEGMENTATION: bool = true;

/// High-performance trie node for phoneme lookup
/// Uses HashMap for O(1) character access
#[derive(Default)]
struct TrieNode {
    // Map Unicode chars to child nodes for instant lookup
    children: HashMap<char, Box<TrieNode>>,
    
    // Phoneme value if this node represents end of a word
    phoneme: Option<String>,
}

/// Individual match from Japanese text to phoneme
#[derive(Debug, Clone)]
struct Match {
    original: String,
    phoneme: String,
    start_index: usize,
}

impl Match {
    fn to_string(&self) -> String {
        format!("\"{}\" → \"{}\" (pos: {})", self.original, self.phoneme, self.start_index)
    }
}

/// Detailed conversion result with match information
#[derive(Debug)]
struct ConversionResult {
    phonemes: String,
    matches: Vec<Match>,
    unmatched: Vec<char>,
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// FURIGANA HINT PROCESSING TYPES
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

/// Types of segments in processed text
#[derive(Debug, Clone)]
enum SegmentType {
    NormalText,     // Regular text without furigana
    FuriganaHint,  // Text with furigana reading hint
}

/// A segment of text that can be either normal or have a furigana hint
#[derive(Debug, Clone)]
struct TextSegment {
    segment_type: SegmentType,
    text: String,         // The actual text (kanji for furigana hints)
    reading: String,      // The reading (only for furigana hints)
    original_pos: usize,  // Position in original text
}

/// Represents a segmented word with metadata about its origin
#[derive(Debug, Clone)]
struct SegmentedWord {
    text: String,
    is_furigana_reading: bool,  // True if this came from a furigana hint and shouldn't be re-converted
}

impl SegmentedWord {
    fn new(text: String) -> Self {
        SegmentedWord {
            text,
            is_furigana_reading: false,
        }
    }
    
    fn new_furigana(text: String) -> Self {
        SegmentedWord {
            text,
            is_furigana_reading: true,
        }
    }
}

impl TextSegment {
    // Constructor for normal text
    fn new_normal(text: String, pos: usize) -> Self {
        TextSegment {
            segment_type: SegmentType::NormalText,
            text,
            reading: String::new(),
            original_pos: pos,
        }
    }
    
    // Constructor for furigana hint
    fn new_furigana(text: String, reading: String, pos: usize) -> Self {
        TextSegment {
            segment_type: SegmentType::FuriganaHint,
            text,
            reading,
            original_pos: pos,
        }
    }
    
    // Get the effective text (reading for furigana, text otherwise)
    fn get_effective_text(&self) -> &str {
        match self.segment_type {
            SegmentType::FuriganaHint => &self.reading,
            SegmentType::NormalText => &self.text,
        }
    }
}

/// Ultra-fast phoneme converter using trie data structure
/// Achieves microsecond-level lookups for typical text
struct PhonemeConverter {
    root: TrieNode,
    entry_count: usize,
}

impl PhonemeConverter {
    /// Create a new phoneme converter
    fn new() -> Self {
        PhonemeConverter {
            root: TrieNode::default(),
            entry_count: 0,
        }
    }
    
    /// Get root node for trie walking (used in word segmentation fallback)
    fn get_root(&self) -> &TrieNode {
        &self.root
    }
    
    /// Try to load from simple binary format (japanese.trie)
    /// Loads directly into TrieNode structure using same insert() as JSON!
    /// 🚀 100x faster than JSON parsing!
    fn try_load_binary_format(&mut self, file_path: &str) -> Result<bool, Box<dyn std::error::Error>> {
        let mut file = match fs::File::open(file_path) {
            Ok(f) => f,
            Err(_) => return Ok(false), // File doesn't exist, not an error
        };
        
        // Read magic number
        let mut magic = [0u8; 4];
        file.read_exact(&mut magic)?;
        if &magic != b"JPHO" {
            eprintln!("❌ Invalid binary format: bad magic number");
            return Ok(false);
        }
        
        // Read version
        let mut version_buf = [0u8; 4];
        file.read_exact(&mut version_buf)?;
        let version_major = u16::from_le_bytes([version_buf[0], version_buf[1]]);
        let version_minor = u16::from_le_bytes([version_buf[2], version_buf[3]]);
        
        if version_major != 1 || version_minor != 0 {
            eprintln!("❌ Unsupported binary format version: {}.{}", version_major, version_minor);
            return Ok(false);
        }
        
        // Read entry count
        let mut count_buf = [0u8; 4];
        file.read_exact(&mut count_buf)?;
        let entry_count_val = u32::from_le_bytes(count_buf);
        
        println!("🚀 Loading binary format v{}.{}: {} entries", version_major, version_minor, entry_count_val);
        let start_time = Instant::now();
        
        // Read all entries and insert into trie (same as JSON!)
        for i in 0..entry_count_val {
            // Read key length (varint)
            let mut key_len = 0u32;
            let mut shift = 0;
            loop {
                let mut byte = [0u8; 1];
                file.read_exact(&mut byte)?;
                key_len |= ((byte[0] & 0x7F) as u32) << shift;
                if (byte[0] & 0x80) == 0 {
                    break;
                }
                shift += 7;
            }
            
            // Read key
            let mut key_bytes = vec![0u8; key_len as usize];
            file.read_exact(&mut key_bytes)?;
            let key = String::from_utf8(key_bytes)?;
            
            // Read value length (varint)
            let mut value_len = 0u32;
            shift = 0;
            loop {
                let mut byte = [0u8; 1];
                file.read_exact(&mut byte)?;
                value_len |= ((byte[0] & 0x7F) as u32) << shift;
                if (byte[0] & 0x80) == 0 {
                    break;
                }
                shift += 7;
            }
            
            // Read value
            let mut value_bytes = vec![0u8; value_len as usize];
            file.read_exact(&mut value_bytes)?;
            let value = String::from_utf8(value_bytes)?;
            
            // Insert using SAME function as JSON!
            self.insert(&key, &value);
            self.entry_count += 1;
            
            // Progress indicator
            if i % 50000 == 0 && i > 0 {
                print!("\r   Processed: {} entries", i);
                io::stdout().flush().unwrap();
            }
        }
        
        let elapsed = start_time.elapsed();
        println!("\n✅ Loaded {} entries in {}ms", self.entry_count, elapsed.as_millis());
        println!("   Average: {:.2}μs per entry", 
                 (elapsed.as_micros() as f64) / (self.entry_count as f64));
        println!("   ⚡ Using SAME TrieNode structure and traversal as JSON!");
        
        Ok(true)
    }
    
    /// Build trie from JSON dictionary file
    /// Optimized for fast construction from large datasets
    fn load_from_json(&mut self, file_path: &str) -> Result<(), Box<dyn std::error::Error>> {
        let contents = fs::read_to_string(file_path)?;
        
        // Simple JSON parsing for our specific format
        let data = self.parse_json(&contents)?;
        
        println!("🔥 Loading {} entries into trie...", data.len());
        let start_time = Instant::now();
        
        // Insert each entry into the trie
        for (key, value) in data.iter() {
            self.insert(key, value);
            self.entry_count += 1;
            
            // Progress indicator for large datasets
            if self.entry_count % 50000 == 0 {
                print!("\r   Processed: {} entries", self.entry_count);
                io::stdout().flush().unwrap();
            }
        }
        
        let elapsed = start_time.elapsed();
        println!("\n✅ Loaded {} entries in {}ms", self.entry_count, elapsed.as_millis());
        println!("   Average: {:.2}μs per entry", 
                 (elapsed.as_micros() as f64) / (self.entry_count as f64));
        
        Ok(())
    }
    
    /// Simple JSON parser for our specific format
    fn parse_json(&self, json_str: &str) -> Result<HashMap<String, String>, Box<dyn std::error::Error>> {
        let mut result = HashMap::new();
        
        // Remove outer braces and whitespace
        let content = json_str.trim()
            .strip_prefix('{').ok_or("Invalid JSON: missing opening brace")?
            .strip_suffix('}').ok_or("Invalid JSON: missing closing brace")?;
        
        // Parse key-value pairs
        let mut chars = content.chars().peekable();
        
        while chars.peek().is_some() {
            // Skip whitespace and commas
            while matches!(chars.peek(), Some(&c) if c.is_whitespace() || c == ',') {
                chars.next();
            }
            
            if chars.peek().is_none() {
                break;
            }
            
            // Parse key
            if chars.next() != Some('"') {
                continue;
            }
            
            let mut key = String::new();
            loop {
                match chars.next() {
                    Some('"') => break,
                    Some('\\') => {
                        if let Some(c) = chars.next() {
                            key.push(c);
                        }
                    }
                    Some(c) => key.push(c),
                    None => break,
                }
            }
            
            // Skip to colon
            while matches!(chars.peek(), Some(&c) if c.is_whitespace() || c == ':') {
                chars.next();
            }
            
            // Parse value
            if chars.next() != Some('"') {
                continue;
            }
            
            let mut value = String::new();
            loop {
                match chars.next() {
                    Some('"') => break,
                    Some('\\') => {
                        if let Some(c) = chars.next() {
                            value.push(c);
                        }
                    }
                    Some(c) => value.push(c),
                    None => break,
                }
            }
            
            if !key.is_empty() && !value.is_empty() {
                result.insert(key, value);
            }
        }
        
        Ok(result)
    }
    
    /// Insert a Japanese text -> phoneme mapping into the trie
    /// Uses characters for maximum performance with Rust's native UTF-8
    fn insert(&mut self, text: &str, phoneme: &str) {
        let mut current = &mut self.root;
        
        // Traverse/build trie using Unicode characters
        for ch in text.chars() {
            current = current.children
                .entry(ch)
                .or_insert_with(|| Box::new(TrieNode::default()));
        }
        
        // Mark end of word with phoneme value
        current.phoneme = Some(phoneme.to_string());
    }
    
    /// Greedy longest-match conversion algorithm
    /// Tries to match the longest possible substring at each position
    fn convert(&self, japanese_text: &str) -> String {
        let mut result = String::new();
        let chars: Vec<char> = japanese_text.chars().collect();
        let mut pos = 0;
        
        while pos < chars.len() {
            // Try to find longest match starting at current position
            let mut match_length = 0;
            let mut matched_phoneme: Option<&String> = None;
            
            let mut current = &self.root;
            
            // Walk the trie as far as possible
            for i in pos..chars.len() {
                if let Some(child) = current.children.get(&chars[i]) {
                    current = child;
                    
                    // If this node has a phoneme, it's a valid match
                    if let Some(ref phoneme) = current.phoneme {
                        match_length = i - pos + 1;
                        matched_phoneme = Some(phoneme);
                    }
                } else {
                    break;
                }
            }
            
            if match_length > 0 {
                // Found a match - add phoneme and advance position
                result.push_str(matched_phoneme.unwrap());
                pos += match_length;
            } else {
                // No match found - keep original character and continue
                // This handles spaces, punctuation, unknown characters
                result.push(chars[pos]);
                pos += 1;
            }
        }
        
        result
    }
    
    /// Convert with detailed matching information for debugging
    /// OPTIMIZED: Pre-decodes UTF-8 once and tracks byte positions
    fn convert_detailed(&self, japanese_text: &str) -> ConversionResult {
        // PRE-DECODE UTF-8 TO CHARS (like Rust does best!)
        let chars: Vec<char> = japanese_text.chars().collect();
        let mut byte_positions = Vec::new();
        let mut byte_pos = 0;
        
        for ch in &chars {
            byte_positions.push(byte_pos);
            byte_pos += ch.len_utf8();
        }
        byte_positions.push(byte_pos); // End position
        
        let mut matches = Vec::new();
        let mut unmatched = Vec::new();
        let mut result = String::new();
        let mut pos = 0;
        
        while pos < chars.len() {
            let mut match_length = 0;
            let mut matched_phoneme: Option<&String> = None;
            
            let mut current = &self.root;
            
            // Walk the trie as far as possible
            for i in pos..chars.len() {
                if let Some(child) = current.children.get(&chars[i]) {
                    current = child;
                    
                    if let Some(ref phoneme) = current.phoneme {
                        match_length = i - pos + 1;
                        matched_phoneme = Some(phoneme);
                    }
                } else {
                    break;
                }
            }
            
            if match_length > 0 {
                // Found a match
                let original: String = chars[pos..pos + match_length].iter().collect();
                matches.push(Match {
                    original,
                    phoneme: matched_phoneme.unwrap().clone(),
                    start_index: byte_positions[pos], // Use byte position!
                });
                result.push_str(matched_phoneme.unwrap());
                pos += match_length;
            } else {
                // No match found
                unmatched.push(chars[pos]);
                result.push(chars[pos]);
                pos += 1;
            }
        }
        
        ConversionResult {
            phonemes: result,
            matches,
            unmatched,
        }
    }
}

/// Word segmenter using longest-match algorithm with word dictionary
/// Splits Japanese text into words for better phoneme spacing
struct WordSegmenter {
    root: TrieNode,
    word_count: usize,
}

impl WordSegmenter {
    fn new() -> Self {
        WordSegmenter {
            root: TrieNode::default(),
            word_count: 0,
        }
    }
    
    /// Get root node for trie walking (used in compound detection)
    fn get_root(&self) -> &TrieNode {
        &self.root
    }
    
    /// Check if a word exists in the dictionary
    /// Returns true if the word is a complete entry
    fn contains_word(&self, word: &str) -> bool {
        if word.is_empty() {
            return false;
        }
        
        let mut current = &self.root;
        
        for ch in word.chars() {
            if let Some(child) = current.children.get(&ch) {
                current = child;
            } else {
                return false; // Path doesn't exist
            }
        }
        
        // Check if this is a valid end-of-word node
        current.phoneme.is_some()
    }
    
    /// Load word list from text file (one word per line)
    fn load_from_file(&mut self, file_path: &str) -> Result<(), Box<dyn std::error::Error>> {
        println!("🔥 Loading word dictionary for segmentation...");
        let start_time = Instant::now();
        
        let file = fs::File::open(file_path)?;
        let reader = BufReader::new(file);
        
        for line in reader.lines() {
            let word = line?;
            let word = word.trim();
            
            if !word.is_empty() {
                self.insert_word(word);
                self.word_count += 1;
                
                if self.word_count % 50000 == 0 {
                    print!("\r   Loaded: {} words", self.word_count);
                    io::stdout().flush().unwrap();
                }
            }
        }
        
        let elapsed = start_time.elapsed();
        println!("\n✅ Loaded {} words in {}ms", self.word_count, elapsed.as_millis());
        
        Ok(())
    }
    
    /// Insert a word into the trie
    fn insert_word(&mut self, word: &str) {
        let mut current = &mut self.root;
        
        for ch in word.chars() {
            current = current.children
                .entry(ch)
                .or_insert_with(|| Box::new(TrieNode::default()));
        }
        
        // Mark end of word (use empty string as marker)
        current.phoneme = Some(String::new());
    }
    
    /// Segment text into words using longest-match algorithm
    /// 
    /// SMART SEGMENTATION: Words are matched from dictionary, and any
    /// unmatched sequences between words are treated as grammatical elements
    /// (particles, conjugations, etc.) and given their own space.
    /// 
    /// Example: 私はリンゴがすきです
    /// - Matches: 私, リンゴ, すき
    /// - Grammar (unmatched): は, が, です
    /// - Result: [私, は, リンゴ, が, すき, です]
    fn segment(&self, text: &str) -> Vec<String> {
        let mut words = Vec::new();
        let chars: Vec<char> = text.chars().collect();
        let mut pos = 0;
        
        while pos < chars.len() {
            // Skip spaces in input
            if chars[pos].is_whitespace() {
                pos += 1;
                continue;
            }
            
            // Try to find longest word match starting at current position
            let mut match_length = 0;
            let mut current = &self.root;
            
            for i in pos..chars.len() {
                if let Some(child) = current.children.get(&chars[i]) {
                    current = child;
                    
                    // If this node marks end of word, it's a valid match
                    // 🔥 FIX: Skip empty phonemes (word markers from ja_words.txt)
                    if let Some(ref phoneme) = current.phoneme {
                        if !phoneme.is_empty() {
                            match_length = i - pos + 1;
                        }
                    }
                } else {
                    break;
                }
            }
            
            if match_length > 0 {
                // Found a word match - extract it
                let word: String = chars[pos..pos + match_length].iter().collect();
                words.push(word);
                pos += match_length;
            } else {
                // No match found - this is likely a grammatical element
                // Collect all consecutive unmatched characters as a single token
                let grammar_start = pos;
                
                // Keep collecting characters until we find another word match
                while pos < chars.len() {
                    // Skip spaces
                    if chars[pos].is_whitespace() {
                        break;
                    }
                    
                    // Try to match a word starting from current position
                    let mut lookahead_match = 0;
                    let mut lookahead = &self.root;
                    
                    for i in pos..chars.len() {
                        if let Some(child) = lookahead.children.get(&chars[i]) {
                            lookahead = child;
                            
                            // 🔥 FIX: Skip empty phonemes
                            if let Some(ref phoneme) = lookahead.phoneme {
                                if !phoneme.is_empty() {
                                    lookahead_match = i - pos + 1;
                                }
                            }
                        } else {
                            break;
                        }
                    }
                    
                    // If we found a word match, stop here
                    if lookahead_match > 0 {
                        break;
                    }
                    
                    // Otherwise, this character is part of the grammar sequence
                    pos += 1;
                }
                
                // Extract the grammar token
                if pos > grammar_start {
                    let grammar: String = chars[grammar_start..pos].iter().collect();
                    words.push(grammar);
                }
            }
        }
        
        words
    }
    
    /// Segment text from TextSegments using longest-match algorithm with phoneme fallback
    /// 
    /// SMART SEGMENTATION: Words are matched from dictionary, and any
    /// unmatched sequences between words are treated as grammatical elements
    /// (particles, conjugations, etc.) and given their own space.
    /// 
    /// This version properly handles TextSegments with furigana hints,
    /// treating each segment as an atomic unit during segmentation.
    /// 
    /// @param phoneme_root Optional phoneme trie root for fallback lookups
    fn segment_from_segments(&self, segments: &[TextSegment], phoneme_root: Option<&TrieNode>) -> Vec<SegmentedWord> {
        let mut words = Vec::new();
        
        // Process each segment
        for segment in segments {
            // For furigana segments, treat the entire reading as one word
            // Mark it as furigana so conversion knows to use it directly
            if matches!(segment.segment_type, SegmentType::FuriganaHint) {
                words.push(SegmentedWord::new_furigana(segment.reading.clone()));
                continue;
            }
            
            // For normal text segments, apply word segmentation
            let text = &segment.text;
            let chars: Vec<char> = text.chars().collect();
            let mut pos = 0;
            
            while pos < chars.len() {
                // Skip spaces in input
                if chars[pos].is_whitespace() {
                    pos += 1;
                    continue;
                }
                
                // 🔥 SMART PARTICLE CHECK: Check if this is は (ha) that should be separated
                // BUT ONLY if it doesn't form a longer word with following characters!
                // This prevents は+もう → はもう, while allowing words starting with は to stay together
                let current_char = chars[pos];
                let is_potential_particle = (
                    current_char == 'は'  // は (topic marker)
                    // current_char == 'が' ||  // が (subject marker)
                    // current_char == 'を' ||  // を (object marker) - actually を is ALWAYS alone!
                    // current_char == 'に' ||  // に (direction/time)
                    // current_char == 'へ' ||  // へ (direction)
                    // current_char == 'で' ||  // で (location/means)
                    // current_char == 'と' ||  // と (and/with)
                    // current_char == 'も' ||  // も (also)
                    // current_char == 'の' ||  // の (possessive)
                    // current_char == 'や' ||  // や (and/or)
                    // current_char == 'か'     // か (question)
                );
                
                // If it's a potential particle, check if it can form a multi-character word
                let mut treat_as_particle = false;
                if is_potential_particle {
                    // Use longest-match algorithm to check if this particle forms a longer word
                    let mut has_longer_match = false;
                    
                    if let Some(phoneme_root_node) = phoneme_root {
                        if pos + 1 < chars.len() {
                            let mut check_node = phoneme_root_node;
                            
                            // Walk through as many characters as possible
                            for i in pos..chars.len() {
                                if let Some(child) = check_node.children.get(&chars[i]) {
                                    check_node = child;
                                    
                                    // Check if we found a multi-character word (not just single particle)
                                    if i > pos {
                                        if let Some(ref phoneme) = check_node.phoneme {
                                            if !phoneme.is_empty() {
                                                has_longer_match = true;
                                                break;  // Found a longer word, stop checking
                                            }
                                        }
                                    }
                                } else {
                                    break;
                                }
                            }
                        }
                    }
                    
                    // Only treat as particle if it DOESN'T form a longer word
                    treat_as_particle = !has_longer_match;
                }
                
                // If it's a standalone particle, treat it as a single token
                if treat_as_particle {
                    words.push(SegmentedWord::new(chars[pos].to_string()));
                    pos += 1;
                    continue;  // Skip the rest of the matching logic
                }
                
                // Try to find longest word match starting at current position
                // Check word dictionary first, then phoneme dictionary as fallback
                let mut match_length = 0;
                let mut current = &self.root;
                
                for i in pos..chars.len() {
                    if let Some(child) = current.children.get(&chars[i]) {
                        current = child;
                        
                        // If this node marks end of word, it's a valid match
                        // 🔥 FIX: Skip empty phonemes (word markers from ja_words.txt)
                        if let Some(ref phoneme) = current.phoneme {
                            if !phoneme.is_empty() {
                                match_length = i - pos + 1;
                            }
                        }
                    } else {
                        break;
                    }
                }
                
                // 🔥 FALLBACK: If word dictionary didn't find a match, try phoneme dictionary
                if match_length == 0 {
                    if let Some(phoneme_current_root) = phoneme_root {
                        let mut phoneme_current = phoneme_current_root;
                        
                        for i in pos..chars.len() {
                            if let Some(child) = phoneme_current.children.get(&chars[i]) {
                                phoneme_current = child;
                                
                                // If this node has a phoneme, it's a valid word
                                // 🔥 FIX: Skip empty phonemes (word markers from ja_words.txt)
                                if let Some(ref phoneme) = phoneme_current.phoneme {
                                    if !phoneme.is_empty() {
                                        match_length = i - pos + 1;
                                    }
                                }
                            } else {
                                break;
                            }
                        }
                    }
                }
                
                if match_length > 0 {
                    // Found a word match - extract it
                    let word: String = chars[pos..pos + match_length].iter().collect();
                    words.push(SegmentedWord::new(word));
                    pos += match_length;
                } else {
                    // No match found - collect all consecutive unmatched characters as grammar token
                    // This handles compound particles (から、まで、etc.) and conjugations (です、ます)
                    // Note: Single-char particles are already handled earlier, so this won't merge them
                    let grammar_start = pos;
                    
                    // Keep collecting characters until we find another word match
                    while pos < chars.len() {
                        // Skip spaces
                        if chars[pos].is_whitespace() {
                            break;
                        }
                        
                        // Try to match a word starting from current position
                        let mut lookahead_match = 0;
                        let mut lookahead = &self.root;
                        
                        for i in pos..chars.len() {
                            if let Some(child) = lookahead.children.get(&chars[i]) {
                                lookahead = child;
                                
                                // 🔥 FIX: Skip empty phonemes
                                if let Some(ref phoneme) = lookahead.phoneme {
                                    if !phoneme.is_empty() {
                                        lookahead_match = i - pos + 1;
                                    }
                                }
                            } else {
                                break;
                            }
                        }
                        
                        // If we found a word match, stop here
                        if lookahead_match > 0 {
                            break;
                        }
                        
                        // Otherwise, this character is part of the grammar sequence
                        pos += 1;
                    }
                    
                    // Extract the grammar token
                    if pos > grammar_start {
                        let grammar: String = chars[grammar_start..pos].iter().collect();
                        words.push(SegmentedWord::new(grammar));
                    }
                }
            }
        }
        
        words
    }
}

/// Helper function to check if a character is kana (hiragana or katakana)
fn is_kana(ch: char) -> bool {
    let cp = ch as u32;
    (cp >= 0x3040 && cp <= 0x309F) ||  // Hiragana
    (cp >= 0x30A0 && cp <= 0x30FF)     // Katakana
}

/// Parse text into segments, extracting furigana hints.
/// 
/// This creates a structured representation of the text where each segment
/// is either normal text or a furigana hint. This approach is cleaner than
/// using markers and makes the processing logic more transparent.
/// 
/// SMART COMPOUND WORD DETECTION:
/// - If kanji「reading」+following text forms a dictionary word, prefer dictionary
/// - Example: 見「み」て → Check if 見て is a word → YES → Keep as normal text "見て"
/// - Example: 健太「けんた」て → Check if 健太て is a word → NO → Use furigana "けんた"
/// 
/// @param text Input text with potential furigana hints (e.g., 健太「けんた」)
/// @param segmenter Optional word segmenter for compound word detection
/// @param phoneme_root Optional phoneme trie root for hint backtracking
fn parse_furigana_segments(text: &str, segmenter: Option<&WordSegmenter>, phoneme_root: Option<&TrieNode>) -> Vec<TextSegment> {
    let mut segments = Vec::new();
    
    // Pre-decode UTF-8 to chars for blazing speed
    let chars: Vec<char> = text.chars().collect();
    let mut byte_positions = Vec::new();
    let mut byte_pos = 0;
    
    for ch in &chars {
        byte_positions.push(byte_pos);
        byte_pos += ch.len_utf8();
    }
    byte_positions.push(byte_pos);
    
    let mut pos = 0;
    
    while pos < chars.len() {
        // Look for opening bracket 「 (U+300C)
        let bracket_open = chars[pos..].iter().position(|&ch| ch == '「').map(|p| pos + p);
        
        if bracket_open.is_none() {
            // No more furigana hints, add rest of text as normal segment
            if pos < chars.len() {
                let text_str: String = chars[pos..].iter().collect();
                segments.push(TextSegment::new_normal(text_str, byte_positions[pos]));
            }
            break;
        }
        
        let bracket_open = bracket_open.unwrap();
        
        // Look for closing bracket 」 (U+300D)
        let bracket_close = chars[bracket_open + 1..].iter().position(|&ch| ch == '」')
            .map(|p| bracket_open + 1 + p);
        
        if bracket_close.is_none() {
            // No closing bracket, add rest as normal segment
            let text_str: String = chars[pos..].iter().collect();
            segments.push(TextSegment::new_normal(text_str, byte_positions[pos]));
            break;
        }
        
        let bracket_close = bracket_close.unwrap();
        
        // Find where the "word" (kanji) starts before the opening bracket
        // Search backwards to find the start of the kanji/word that has furigana
        let mut last_kanji_pos = bracket_open;
        while last_kanji_pos > pos && is_kana(chars[last_kanji_pos - 1]) {
            last_kanji_pos -= 1;
        }
        
        if last_kanji_pos > pos {
            last_kanji_pos -= 1; // Now pointing at the last kanji
        }
        
        // Second pass: From last kanji, search backward for word boundary
        let mut word_start = last_kanji_pos;
        let mut search_pos = last_kanji_pos;
        
        while search_pos > pos {
            search_pos -= 1;
            let ch = chars[search_pos];
            let cp = ch as u32;
            
            // Check for punctuation boundaries
            if matches!(ch, '」' | '、' | '。' | '！' | '？' | '）' | '］') ||
               (cp < 0x80 && matches!(ch, '.' | ',' | '!' | '?' | ';' | ':' | '(' | ')' | '[' | ']' | 
                                      '{' | '}' | '"' | '\'' | '-' | '/' | '\\' | '|' | ' ' | '\t' | '\n' | '\r')) {
                word_start = search_pos + 1;
                break;
            }
            
            // Check if this is kana
            if is_kana(ch) {
                // 🔥 ENHANCED LOGIC: Check if the kana sequence from here to the kanji is a word
                // Example: "とても面白「おもしろ」" → "とても" is a word, stop here
                // This prevents incorrectly treating standalone words as okurigana
                
                // Extract kana sequence from search_pos to bracket_open
                let mut kana_seq_end = search_pos;
                while kana_seq_end < bracket_open && is_kana(chars[kana_seq_end]) {
                    kana_seq_end += 1;
                }
                
                // If we have a kana sequence, check if it's a word
                if kana_seq_end > search_pos {
                    if let Some(seg) = segmenter {
                        let kana_sequence: String = chars[search_pos..kana_seq_end].iter().collect();
                        
                        // Check if this kana sequence is a word in the dictionary
                        if seg.contains_word(&kana_sequence) {
                            // This kana sequence is a complete word → stop here
                            word_start = search_pos + 1;
                            break;
                        }
                    }
                }
                
                // Not a word itself - check if this kana is part of a compound with kanji before it
                // Find the nearest kanji before this kana position
                let mut nearest_kanji_pos = search_pos;
                let mut found_kanji = false;
                for check_pos in (pos..search_pos).rev() {
                    if !is_kana(chars[check_pos]) {
                        // Check it's not punctuation
                        let check_cp = chars[check_pos] as u32;
                        if check_cp >= 0x4E00 || (check_cp >= 0x3400 && check_cp <= 0x9FFF) {  // CJK kanji ranges
                            nearest_kanji_pos = check_pos;
                            found_kanji = true;
                            break;
                        }
                    }
                }
                
                if !found_kanji {
                    // No kanji before this kana - it's a prefix word → stop here
                    word_start = search_pos + 1;
                    break;
                }
                
                // Check if kanji+kana sequence forms a complete word
                // Example: 一つ should be detected as a complete word, not okurigana
                if let Some(phoneme_trie) = phoneme_root {
                    let mut check_node = Some(phoneme_trie);
                    let mut forms_word = false;
                    
                    // Walk from nearest_kanji_pos to search_pos (end of kana sequence)
                    for i in nearest_kanji_pos..=search_pos {
                        if let Some(node) = check_node {
                            check_node = node.children.get(&chars[i]);
                            if check_node.is_none() {
                                break;
                            }
                            
                            // Check if this forms a complete word at the end of the kana sequence
                            if i == search_pos {
                                if let Some(n) = check_node {
                                    if let Some(ref ph) = n.phoneme {
                                        if !ph.is_empty() {
                                            forms_word = true;
                                            break;
                                        }
                                    }
                                }
                            }
                        }
                    }
                    
                    if forms_word {
                        // This kanji+kana forms a complete word → stop here
                        word_start = search_pos + 1;
                        break;
                    }
                }
                
                // Otherwise, this kana is sandwiched (okurigana) → continue
            }
            
            // Update word_start to include this character
            word_start = search_pos;
        }
        
        // 🔥 FIX: Skip any leading kana between word_start and last_kanji_pos
        // Example: "一つだけ持「も」" → word_start=2 (だ), last_kanji_pos=4 (持)
        // We should skip だけ and start from 持
        while word_start < last_kanji_pos && is_kana(chars[word_start]) {
            word_start += 1;
        }
        
        // Add text from current position up to where the word/kanji starts
        if word_start > pos {
            let text_str: String = chars[pos..word_start].iter().collect();
            segments.push(TextSegment::new_normal(text_str, byte_positions[pos]));
        }
        
        // Extract the reading
        let reading: String = chars[bracket_open + 1..bracket_close].iter().collect();
        let reading = reading.trim().to_string();
        
        if reading.is_empty() {
            // Empty reading - skip the entire furigana hint
            pos = bracket_close + 1;
            continue;
        }
        
        // 🔥 SMART COMPOUND-AWARE KANJI BOUNDARY DETECTION
        let mut best_kanji_start = word_start;
        let mut best_compound_length = 0;
        let after_bracket = bracket_close + 1;
        
        if (segmenter.is_some() || phoneme_root.is_some()) && after_bracket < chars.len() {
            for try_start in word_start..bracket_open {
                let mut current = if let Some(pr) = phoneme_root { Some(pr) } else { segmenter.map(|s| s.get_root()) };
                if current.is_none() { continue; }
                
                let mut valid_path = true;
                for i in try_start..bracket_open {
                    if let Some(node) = current {
                        current = node.children.get(&chars[i]);
                        if current.is_none() {
                            valid_path = false;
                            break;
                        }
                    }
                }
                
                let mut compound_length = 0;
                if valid_path && current.is_some() {
                    for i in after_bracket..chars.len() {
                        if let Some(node) = current {
                            current = node.children.get(&chars[i]);
                            if current.is_none() { break; }
                            if let Some(n) = current {
                                if n.phoneme.is_some() {
                                    compound_length = i - after_bracket + 1;
                                }
                            }
                        } else {
                            break;
                        }
                    }
                }
                
                if compound_length > best_compound_length {
                    best_compound_length = compound_length;
                    best_kanji_start = try_start;
                }
            }
            
            if best_compound_length > 0 && best_kanji_start > word_start {
                let prefix: String = chars[word_start..best_kanji_start].iter().collect();
                segments.push(TextSegment::new_normal(prefix, byte_positions[word_start]));
                word_start = best_kanji_start;
            }
        }
        
        let kanji: String = chars[word_start..bracket_open].iter().collect();
        
        // 🔥 SMART NAME DETECTION: Check if honorific follows the furigana hint
        // If we see さん、さま、様、君、ちゃん、くん etc. after the hint,
        // the reading applies to the ENTIRE name, so skip backtracking!
        let mut is_likely_name = false;
        // after_bracket already declared above
        if after_bracket < chars.len() {
            let next_char = chars[after_bracket] as u32;
            // Check for common honorifics
            if next_char == 0x3055 { // さ
                if after_bracket + 1 < chars.len() {
                    let next_next = chars[after_bracket + 1] as u32;
                    if next_next == 0x3093 || next_next == 0x307E { // ん or ま
                        is_likely_name = true;
                    }
                }
            } else if matches!(next_char, 0x69D8 | 0x541B | 0x6C0F | 0x6BBF | 0x5148 | 0x5E2B | 0x9577 | 0x3061 | 0x304F | 0x6559 | 0x8B1B) {
                is_likely_name = true;
            }
        }
        
        // 🔥 SMART OKURIGANA DETECTION WITH FURIGANA HINTS
        // Check if there's okurigana (trailing kana) after the bracket that should be
        // combined with the furigana reading to form a complete word.
        // Example: 話「はな」す → Check if 話す exists in dictionary → YES → Combine はな+す
        let mut best_okurigana_length = 0;
        
        if let Some(phoneme_trie) = phoneme_root {
            if after_bracket < chars.len() {
                // Check if kanji (before bracket) + kana (after bracket) forms a word in the dictionary
                let mut current = Some(phoneme_trie);
                let mut valid_path = true;
                
                // Walk through kanji characters (from word_start to bracket_open)
                for i in word_start..bracket_open {
                    if let Some(node) = current {
                        current = node.children.get(&chars[i]);
                        if current.is_none() {
                            valid_path = false;
                            break;
                        }
                    }
                }
                
                // If we made it through the kanji, continue with characters after bracket (okurigana)
                if valid_path && current.is_some() {
                    // Try to match as much okurigana as possible
                    for i in after_bracket..chars.len() {
                        if let Some(node) = current {
                            current = node.children.get(&chars[i]);
                            if current.is_none() {
                                break;
                            }
                            
                            // Check if this forms a valid word (kanji + okurigana)
                            if let Some(n) = current {
                                if let Some(ref ph) = n.phoneme {
                                    if !ph.is_empty() {
                                        best_okurigana_length = i - after_bracket + 1;
                                    }
                                }
                            }
                        } else {
                            break;
                        }
                    }
                }
            }
        }
        
        // 🔥 SMART HINT BACKTRACKING: Check if reading matches from the END
        let mut final_kanji = kanji.clone();
        let mut final_word_start = word_start;
        
        if let Some(phoneme_trie) = phoneme_root {
            if !is_likely_name {
                let kanji_char_count = bracket_open - word_start;
                let max_backtrack = std::cmp::min(10, kanji_char_count);
                
                for try_length in 1..=max_backtrack {
                    let try_start = bracket_open - try_length;
                    if try_start < word_start {
                        break;
                    }
                    
                    let kanji_substr: String = chars[try_start..bracket_open].iter().collect();
                    
                    // Try to match this kanji substring in the phoneme trie
                    let mut current = Some(phoneme_trie);
                    let mut found_path = true;
                    
                    for i in try_start..bracket_open {
                        if let Some(node) = current {
                            current = node.children.get(&chars[i]);
                            if current.is_none() {
                                found_path = false;
                                break;
                            }
                        }
                    }
                    
                    // Check if we found a valid entry
                    if found_path {
                        if let Some(node) = current {
                            if let Some(ref phoneme_value) = node.phoneme {
                                // 🔥 FIX: We must verify the phoneme MATCHES our reading!
                                // Reading is hiragana/katakana, so look up EACH CHARACTER individually
                                let reading_chars: Vec<char> = reading.chars().collect();
                                let mut reading_phoneme = String::new();
                                let mut all_chars_found = true;
                                
                                for &ch in &reading_chars {
                                    if let Some(char_node) = phoneme_trie.children.get(&ch) {
                                        if let Some(ref ph) = char_node.phoneme {
                                            if !ph.is_empty() {
                                                reading_phoneme.push_str(ph);
                                            } else {
                                                all_chars_found = false;
                                                break;
                                            }
                                        } else {
                                            all_chars_found = false;
                                            break;
                                        }
                                    } else {
                                        all_chars_found = false;
                                        break;
                                    }
                                }
                                
                                let phonemes_match = all_chars_found && phoneme_value == &reading_phoneme;
                                
                                // Found a match! Check if we need to split
                                if try_length < kanji_char_count && phonemes_match {
                                    // Split: add prefix as NORMAL_TEXT
                                    if try_start > word_start {
                                        let prefix: String = chars[word_start..try_start].iter().collect();
                                        segments.push(TextSegment::new_normal(prefix, byte_positions[word_start]));
                                    }
                                    final_kanji = kanji_substr;
                                    final_word_start = try_start;
                                    break;
                                }
                                // If try_length == kanji_char_count, use the whole thing
                                if phonemes_match {
                                    break;
                                }
                            }
                        }
                    }
                }
            }
        }
        
        // 🔥 USE OKURIGANA DETECTION RESULT
        // If we found okurigana, combine it with the furigana reading
        let mut used_okurigana = false;
        
        if best_okurigana_length > 0 {
            // We found okurigana! Combine furigana reading + okurigana kana
            // Example: 話「はな」す → はな + す = はなす
            let okurigana: String = chars[after_bracket..after_bracket + best_okurigana_length].iter().collect();
            let combined = format!("{}{}", reading, okurigana);
            
            // 🔥 KEY FIX: Create as FURIGANA_HINT segment so it's treated as a single word!
            // The "text" field contains the original kanji+okurigana (for reference)
            // The "reading" field contains the combined reading that should be used
            let original_with_okurigana = format!("{}{}", final_kanji, okurigana);
            segments.push(TextSegment::new_furigana(original_with_okurigana, combined, byte_positions[final_word_start]));
            pos = after_bracket + best_okurigana_length;
            used_okurigana = true;
        }
        
        if !used_okurigana {
            // 🔥 USE COMPOUND DETECTION RESULT
            let mut used_compound = false;
            
            if best_compound_length > 0 {
                let suffix: String = chars[after_bracket..after_bracket + best_compound_length].iter().collect();
                let compound = format!("{}{}", reading, suffix);
                segments.push(TextSegment::new_normal(compound, byte_positions[word_start]));
                pos = after_bracket + best_compound_length;
                used_compound = true;
            }
            
            if !used_compound {
                // No compound found, use the furigana hint
                segments.push(TextSegment::new_furigana(final_kanji, reading, byte_positions[final_word_start]));
                pos = bracket_close + 1;
            }
        }
    }
    
    segments
}

/// Convert with word segmentation support
/// OPTIMIZED: Uses furigana-aware segmentation and は → wa particle handling
/// 
/// Example: 健太「けんた」はバカ → kẽ̞ɴta wa baka
fn convert_with_segmentation(converter: &PhonemeConverter, text: &str, segmenter: &WordSegmenter) -> String {
    // 🔥 STEP 1: Parse furigana hints into structured segments
    let segments = parse_furigana_segments(text, Some(segmenter), Some(converter.get_root()));
    
    // 🔥 STEP 2: Segment into words using structured segments with phoneme fallback
    let words = segmenter.segment_from_segments(&segments, Some(converter.get_root()));
    
    // 🔥 STEP 3: Convert each word to phonemes with particle handling
    let phonemes: Vec<String> = words.iter().map(|word| {
        // Special handling for the topic particle は → "wa"
        if word.text == "は" {
            "wa".to_string()
        } else if word.is_furigana_reading {
            // Convert the reading (hiragana/katakana) directly to phonemes
            converter.convert(&word.text)
        } else {
            // Normal word - convert through phoneme dictionary
            converter.convert(&word.text)
        }
    }).collect();
    
    phonemes.join(" ")  // Space-separated!
}

/// Convert with word segmentation and detailed information
/// OPTIMIZED: Uses furigana-aware segmentation and は → wa particle handling
fn convert_detailed_with_segmentation(converter: &PhonemeConverter, text: &str, segmenter: &WordSegmenter) -> ConversionResult {
    // 🔥 STEP 1: Parse furigana hints into structured segments
    let segments = parse_furigana_segments(text, Some(segmenter), Some(converter.get_root()));
    
    // 🔥 STEP 2: Segment into words using structured segments with phoneme fallback
    let words = segmenter.segment_from_segments(&segments, Some(converter.get_root()));
    
    // 🔥 STEP 3: Convert each word to phonemes with particle handling
    let mut all_matches = Vec::new();
    let mut all_unmatched = Vec::new();
    let mut phoneme_parts = Vec::new();
    let mut byte_offset = 0;
    
    for word in &words {
        // Special handling for the topic particle は → "wa"
        if word.text == "は" {
            phoneme_parts.push("wa".to_string());
            // Add to matches for consistency
            all_matches.push(Match {
                original: word.text.clone(),
                phoneme: "wa".to_string(),
                start_index: byte_offset,
            });
        } else if word.is_furigana_reading {
            // Convert the reading (hiragana/katakana) directly to phonemes
            let mut word_result = converter.convert_detailed(&word.text);
            
            // Adjust match positions to account for original text position
            for match_item in &mut word_result.matches {
                match_item.start_index += byte_offset;
                all_matches.push(match_item.clone());
            }
            
            phoneme_parts.push(word_result.phonemes);
            all_unmatched.extend(word_result.unmatched);
        } else {
            // Normal word - convert through phoneme dictionary
            let mut word_result = converter.convert_detailed(&word.text);
            
            // Adjust match positions to account for original text position
            for match_item in &mut word_result.matches {
                match_item.start_index += byte_offset;
                all_matches.push(match_item.clone());
            }
            
            phoneme_parts.push(word_result.phonemes);
            all_unmatched.extend(word_result.unmatched);
        }
        
        byte_offset += word.text.len();
    }
    
    ConversionResult {
        phonemes: phoneme_parts.join(" "),
        matches: all_matches,
        unmatched: all_unmatched,
    }
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("╔══════════════════════════════════════════════════════════╗");
    println!("║  Japanese → Phoneme Converter (Rust)                    ║");
    println!("║  Blazing fast IPA phoneme conversion                    ║");
    println!("╚══════════════════════════════════════════════════════════╝\n");
    
    // Check if JSON file exists
    if !std::path::Path::new("ja_phonemes.json").exists() {
        eprintln!("❌ Error: ja_phonemes.json not found in current directory");
        eprintln!("   Please ensure the phoneme dictionary is present.");
        std::process::exit(1);
    }
    
    // Initialize converter and load dictionary
    // 🚀 Try binary trie first (100x faster!), fallback to JSON
    let mut converter = PhonemeConverter::new();
    let mut loaded_binary = false;
    
    // Try simple binary format (direct load into TrieNode)
    match converter.try_load_binary_format("japanese.trie") {
        Ok(true) => {
            loaded_binary = true;
            println!("   💡 Binary format loaded directly into TrieNode");
        }
        Ok(false) => {
            // Fallback to JSON
            println!("   ⚠️  Binary trie not found, loading JSON...");
        }
        Err(e) => {
            eprintln!("⚠️  Error loading binary trie: {}", e);
            eprintln!("   Falling back to JSON...");
        }
    }
    
    if !loaded_binary {
        converter.load_from_json("ja_phonemes.json")?;
    }
    
    // Initialize word segmenter if enabled
    let mut segmenter: Option<WordSegmenter> = None;
    if USE_WORD_SEGMENTATION {
        // If using binary format, words are already loaded in converter's trie!
        // We still need to create a WordSegmenter that uses the converter's trie
        if loaded_binary {
            println!("   💡 Word segmentation: Words already in TrieNode from binary format");
            // Create an empty WordSegmenter - it will use converter's trie as phoneme fallback
            // The segmentation will work because segment_from_segments() uses phoneme_root fallback
            segmenter = Some(WordSegmenter::new());
            // Don't load ja_words.txt - words are already in converter's trie
        } else {
            // Load separate word file for JSON mode
            if std::path::Path::new("ja_words.txt").exists() {
                let mut seg = WordSegmenter::new();
                match seg.load_from_file("ja_words.txt") {
                    Ok(_) => {
                        println!("   💡 Word segmentation: ENABLED (spaces will separate words)");
                        segmenter = Some(seg);
                    }
                    Err(e) => {
                        eprintln!("⚠️  Warning: Could not load word dictionary: {}", e);
                        eprintln!("   Continuing without word segmentation...");
                    }
                }
            } else {
                println!("   💡 Word segmentation: DISABLED (ja_words.txt not found)");
            }
        }
    }
    
    println!("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n");
    
    let args: Vec<String> = env::args().skip(1).collect();
    
    // Handle command-line arguments
    if args.is_empty() {
        // Interactive mode
        println!("💡 Usage: ./jpn_to_phoneme \"日本語テキスト\"");
        println!("   Or enter Japanese text interactively:\n");
        
        let stdin = io::stdin();
        loop {
            print!("Japanese text (or \"quit\" to exit): ");
            io::stdout().flush()?;
            
            let mut input = String::new();
            stdin.read_line(&mut input)?;
            let input = input.trim();
            
            if input.is_empty() {
                continue;
            }
            
            if input.eq_ignore_ascii_case("quit") || input.eq_ignore_ascii_case("exit") {
                println!("\n👋 Goodbye!");
                break;
            }
            
            // Perform conversion with timing
            let start_time = Instant::now();
            let result = if let Some(ref seg) = segmenter {
                convert_detailed_with_segmentation(&converter, input, seg)
            } else {
                converter.convert_detailed(input)
            };
            let elapsed = start_time.elapsed();
            
            // Display results
            println!("\n┌─────────────────────────────────────────");
            println!("│ Input:    {}", input);
            println!("│ Phonemes: {}", result.phonemes);
            println!("│ Time:     {}μs", elapsed.as_micros());
            println!("└─────────────────────────────────────────");
            
            // Show detailed matches
            if !result.matches.is_empty() {
                println!("\n  Matches ({}):", result.matches.len());
                for m in &result.matches {
                    println!("    • {}", m.to_string());
                }
            }
            
            if !result.unmatched.is_empty() {
                print!("\n  ⚠️  Unmatched characters: ");
                for (i, ch) in result.unmatched.iter().enumerate() {
                    if i > 0 {
                        print!(", ");
                    }
                    print!("{}", ch);
                }
                println!();
            }
            
            println!();
        }
    } else {
        // Batch mode - convert all arguments
        for text in &args {
            // Perform conversion with timing
            let start_time = Instant::now();
            let result = if let Some(ref seg) = segmenter {
                convert_detailed_with_segmentation(&converter, text, seg)
            } else {
                converter.convert_detailed(text)
            };
            let elapsed = start_time.elapsed();
            
            // Display results
            println!("┌─────────────────────────────────────────");
            println!("│ Input:    {}", text);
            println!("│ Phonemes: {}", result.phonemes);
            println!("│ Time:     {}μs ({}ms)", elapsed.as_micros(), elapsed.as_millis());
            println!("└─────────────────────────────────────────");
            
            // Show detailed matches
            if !result.matches.is_empty() {
                println!("\n  ✅ Matches ({}):", result.matches.len());
                for m in &result.matches {
                    println!("    • {}", m.to_string());
                }
            }
            
            if !result.unmatched.is_empty() {
                print!("\n  ⚠️  Unmatched characters: ");
                for (i, ch) in result.unmatched.iter().enumerate() {
                    if i > 0 {
                        print!(", ");
                    }
                    print!("{}", ch);
                }
                println!();
            }
            
            println!();
        }
        
        println!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n");
        println!("✨ Conversion complete!");
    }
    
    Ok(())
}

