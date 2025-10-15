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
            let result = converter.convert_detailed(input);
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
            let result = converter.convert_detailed(text);
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

