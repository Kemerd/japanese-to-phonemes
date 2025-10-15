// Japanese to Phoneme Converter - Rust Edition
// Blazing fast IPA phoneme conversion using optimized trie structure
// Compile: rustc -O jpn_to_phoneme.rs
// Or with Cargo: cargo build --release
// Usage: ./jpn_to_phoneme "日本語テキスト"

use std::collections::HashMap;
use std::env;
use std::fs;
use std::io::{self, Write, BufRead, BufReader};
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
    fn convert_detailed(&self, japanese_text: &str) -> ConversionResult {
        let mut matches = Vec::new();
        let mut unmatched = Vec::new();
        let mut result = String::new();
        let chars: Vec<char> = japanese_text.chars().collect();
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
                    start_index: pos,
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
                    if current.phoneme.is_some() {
                        match_length = i - pos + 1;
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
                            
                            if lookahead.phoneme.is_some() {
                                lookahead_match = i - pos + 1;
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
}

/// Convert with word segmentation support
fn convert_with_segmentation(converter: &PhonemeConverter, text: &str, segmenter: &WordSegmenter) -> String {
    // First pass: segment into words
    let words = segmenter.segment(text);
    
    // Second pass: convert each word to phonemes
    let phonemes: Vec<String> = words.iter()
        .map(|word| converter.convert(word))
        .collect();
    
    phonemes.join(" ")  // Space-separated!
}

/// Convert with word segmentation and detailed information
fn convert_detailed_with_segmentation(converter: &PhonemeConverter, text: &str, segmenter: &WordSegmenter) -> ConversionResult {
    // First pass: segment into words
    let words = segmenter.segment(text);
    
    // Second pass: convert each word to phonemes
    let mut all_matches = Vec::new();
    let mut all_unmatched = Vec::new();
    let mut phoneme_parts = Vec::new();
    let mut byte_offset = 0;
    
    for word in &words {
        let mut word_result = converter.convert_detailed(word);
        
        // Adjust match positions to account for original text position
        for match_item in &mut word_result.matches {
            match_item.start_index += byte_offset;
            all_matches.push(match_item.clone());
        }
        
        phoneme_parts.push(word_result.phonemes);
        all_unmatched.extend(word_result.unmatched);
        byte_offset += word.len();
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
    let mut converter = PhonemeConverter::new();
    converter.load_from_json("ja_phonemes.json")?;
    
    // Initialize word segmenter if enabled
    let mut segmenter: Option<WordSegmenter> = None;
    if USE_WORD_SEGMENTATION {
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

