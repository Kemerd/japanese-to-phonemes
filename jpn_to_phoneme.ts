#!/usr/bin/env ts-node
/**
 * Japanese to Phoneme Converter - TypeScript Edition
 * Blazing fast IPA phoneme conversion using optimized trie structure
 */

import * as fs from 'fs';
import * as readline from 'readline';
import { performance } from 'perf_hooks';

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// CONFIGURATION
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

// Enable word segmentation to add spaces between words in output
// Uses ja_words.txt for Japanese word boundaries
const USE_WORD_SEGMENTATION = true;

/**
 * High-performance trie node for phoneme lookup
 * Uses Map for O(1) character code access
 */
class TrieNode {
  // Map character codes to child nodes for instant lookup
  children: Map<number, TrieNode> = new Map();
  
  // Phoneme value if this node represents end of a word
  phoneme: string | null = null;
}

/**
 * Individual match from Japanese text to phoneme
 */
interface Match {
  original: string;
  phoneme: string;
  startIndex: number;
}

/**
 * Detailed conversion result with match information
 */
interface ConversionResult {
  phonemes: string;
  matches: Match[];
  unmatched: string[];
}

/**
 * Ultra-fast phoneme converter using trie data structure
 * Achieves microsecond-level lookups for typical text
 */
class PhonemeConverter {
  private root: TrieNode = new TrieNode();
  private entryCount: number = 0;
  
  /**
   * Build trie from JSON dictionary file
   * Optimized for fast construction from large datasets
   */
  async loadFromJson(filePath: string): Promise<void> {
    const contents = fs.readFileSync(filePath, 'utf-8');
    const data: Record<string, string> = JSON.parse(contents);
    
    console.log(`🔥 Loading ${Object.keys(data).length} entries into trie...`);
    const startTime = performance.now();
    
    // Insert each entry into the trie
    for (const [key, value] of Object.entries(data)) {
      this.insert(key, value);
      this.entryCount++;
      
      // Progress indicator for large datasets
      if (this.entryCount % 50000 === 0) {
        process.stdout.write(`\r   Processed: ${this.entryCount} entries`);
      }
    }
    
    const elapsed = performance.now() - startTime;
    console.log(`\n✅ Loaded ${this.entryCount} entries in ${elapsed.toFixed(0)}ms`);
    console.log(`   Average: ${((elapsed * 1000) / this.entryCount).toFixed(2)}μs per entry`);
  }
  
  /**
   * Insert a Japanese text -> phoneme mapping into the trie
   * Uses character codes for maximum performance
   */
  private insert(text: string, phoneme: string): void {
    let current = this.root;
    
    // Traverse/build trie using character codes
    for (let i = 0; i < text.length; i++) {
      const charCode = text.charCodeAt(i);
      
      // Create child node if doesn't exist
      if (!current.children.has(charCode)) {
        current.children.set(charCode, new TrieNode());
      }
      current = current.children.get(charCode)!;
    }
    
    // Mark end of word with phoneme value
    current.phoneme = phoneme;
  }
  
  /**
   * Greedy longest-match conversion algorithm
   * Tries to match the longest possible substring at each position
   */
  convert(japaneseText: string): string {
    const result: string[] = [];
    let pos = 0;
    
    while (pos < japaneseText.length) {
      // Try to find longest match starting at current position
      let matchLength = 0;
      let matchedPhoneme: string | null = null;
      
      let current: TrieNode | null = this.root;
      
      // Walk the trie as far as possible
      for (let i = pos; i < japaneseText.length && current !== null; i++) {
        const charCode = japaneseText.charCodeAt(i);
        current = current.children.get(charCode) || null;
        
        if (current === null) break;
        
        // If this node has a phoneme, it's a valid match
        if (current.phoneme !== null) {
          matchLength = i - pos + 1;
          matchedPhoneme = current.phoneme;
        }
      }
      
      if (matchLength > 0) {
        // Found a match - add phoneme and advance position
        result.push(matchedPhoneme!);
        pos += matchLength;
      } else {
        // No match found - keep original character and continue
        // This handles spaces, punctuation, unknown characters
        result.push(japaneseText[pos]);
        pos++;
      }
    }
    
    return result.join('');
  }
  
  /**
   * Convert with detailed matching information for debugging
   */
  convertDetailed(japaneseText: string): ConversionResult {
    const matches: Match[] = [];
    const unmatched: string[] = [];
    const result: string[] = [];
    let pos = 0;
    
    while (pos < japaneseText.length) {
      let matchLength = 0;
      let matchedPhoneme: string | null = null;
      
      let current: TrieNode | null = this.root;
      
      // Walk the trie as far as possible
      for (let i = pos; i < japaneseText.length && current !== null; i++) {
        const charCode = japaneseText.charCodeAt(i);
        current = current.children.get(charCode) || null;
        
        if (current === null) break;
        
        if (current.phoneme !== null) {
          matchLength = i - pos + 1;
          matchedPhoneme = current.phoneme;
        }
      }
      
      if (matchLength > 0) {
        // Found a match
        matches.push({
          original: japaneseText.substring(pos, pos + matchLength),
          phoneme: matchedPhoneme!,
          startIndex: pos,
        });
        result.push(matchedPhoneme!);
        pos += matchLength;
      } else {
        // No match found
        const char = japaneseText[pos];
        unmatched.push(char);
        result.push(char);
        pos++;
      }
    }
    
    return {
      phonemes: result.join(''),
      matches,
      unmatched,
    };
  }
}

/**
 * Word segmenter using longest-match algorithm with word dictionary
 * Splits Japanese text into words for better phoneme spacing
 */
class WordSegmenter {
  private root: TrieNode = new TrieNode();
  private wordCount: number = 0;
  
  /**
   * Load word list from text file (one word per line)
   */
  loadFromFile(filePath: string): void {
    console.log('🔥 Loading word dictionary for segmentation...');
    const startTime = performance.now();
    
    const contents = fs.readFileSync(filePath, 'utf-8');
    const lines = contents.split('\n');
    
    for (let line of lines) {
      line = line.trim();
      if (line) {
        this.insertWord(line);
        this.wordCount++;
        
        if (this.wordCount % 50000 === 0) {
          process.stdout.write(`\r   Loaded: ${this.wordCount} words`);
        }
      }
    }
    
    const elapsed = performance.now() - startTime;
    console.log(`\n✅ Loaded ${this.wordCount} words in ${elapsed.toFixed(0)}ms`);
  }
  
  /**
   * Insert a word into the trie
   */
  private insertWord(word: string): void {
    let current = this.root;
    
    for (let i = 0; i < word.length; i++) {
      const charCode = word.charCodeAt(i);
      
      if (!current.children.has(charCode)) {
        current.children.set(charCode, new TrieNode());
      }
      current = current.children.get(charCode)!;
    }
    
    // Mark end of word (use empty string as marker)
    current.phoneme = "";
  }
  
  /**
   * Segment text into words using longest-match algorithm
   * 
   * SMART SEGMENTATION: Words are matched from dictionary, and any
   * unmatched sequences between words are treated as grammatical elements
   * (particles, conjugations, etc.) and given their own space.
   * 
   * Example: 私はリンゴがすきです
   * - Matches: 私, リンゴ, すき
   * - Grammar (unmatched): は, が, です
   * - Result: [私, は, リンゴ, が, すき, です]
   */
  segment(text: string): string[] {
    const words: string[] = [];
    let pos = 0;
    
    while (pos < text.length) {
      // Skip spaces in input
      const char = text[pos];
      if (char === ' ' || char === '\t' || char === '\n' || char === '\r') {
        pos++;
        continue;
      }
      
      // Try to find longest word match starting at current position
      let matchLength = 0;
      let current: TrieNode | null = this.root;
      
      for (let i = pos; i < text.length && current !== null; i++) {
        const charCode = text.charCodeAt(i);
        current = current.children.get(charCode) || null;
        
        if (current === null) break;
        
        // If this node marks end of word, it's a valid match
        if (current.phoneme !== null) {
          matchLength = i - pos + 1;
        }
      }
      
      if (matchLength > 0) {
        // Found a word match - extract it
        words.push(text.substring(pos, pos + matchLength));
        pos += matchLength;
      } else {
        // No match found - this is likely a grammatical element
        // Collect all consecutive unmatched characters as a single token
        const grammarStart = pos;
        
        // Keep collecting characters until we find another word match
        while (pos < text.length) {
          // Skip spaces
          const char = text[pos];
          if (char === ' ' || char === '\t' || char === '\n' || char === '\r') {
            break;
          }
          
          // Try to match a word starting from current position
          let lookaheadMatch = 0;
          let lookahead: TrieNode | null = this.root;
          
          for (let i = pos; i < text.length && lookahead !== null; i++) {
            const charCode = text.charCodeAt(i);
            lookahead = lookahead.children.get(charCode) || null;
            
            if (lookahead === null) break;
            
            if (lookahead.phoneme !== null) {
              lookaheadMatch = i - pos + 1;
            }
          }
          
          // If we found a word match, stop here
          if (lookaheadMatch > 0) {
            break;
          }
          
          // Otherwise, this character is part of the grammar sequence
          pos++;
        }
        
        // Extract the grammar token
        if (pos > grammarStart) {
          words.push(text.substring(grammarStart, pos));
        }
      }
    }
    
    return words;
  }
}

/**
 * Convert with word segmentation support
 */
function convertWithSegmentation(converter: PhonemeConverter, text: string, segmenter: WordSegmenter): string {
  // First pass: segment into words
  const words = segmenter.segment(text);
  
  // Second pass: convert each word to phonemes
  const phonemes = words.map(word => converter.convert(word));
  
  return phonemes.join(' ');  // Space-separated!
}

/**
 * Convert with word segmentation and detailed information
 */
function convertDetailedWithSegmentation(converter: PhonemeConverter, text: string, segmenter: WordSegmenter): ConversionResult {
  // First pass: segment into words
  const words = segmenter.segment(text);
  
  // Second pass: convert each word to phonemes
  const allMatches: Match[] = [];
  const allUnmatched: string[] = [];
  const phonemeParts: string[] = [];
  let byteOffset = 0;
  
  for (const word of words) {
    const wordResult = converter.convertDetailed(word);
    
    // Adjust match positions to account for original text position
    for (const match of wordResult.matches) {
      allMatches.push({
        original: match.original,
        phoneme: match.phoneme,
        startIndex: match.startIndex + byteOffset,
      });
    }
    
    phonemeParts.push(wordResult.phonemes);
    allUnmatched.push(...wordResult.unmatched);
    byteOffset += word.length;
  }
  
  return {
    phonemes: phonemeParts.join(' '),
    matches: allMatches,
    unmatched: allUnmatched,
  };
}

/**
 * Main entry point for standalone execution
 */
async function main() {
  console.log('╔══════════════════════════════════════════════════════════╗');
  console.log('║  Japanese → Phoneme Converter (TypeScript)              ║');
  console.log('║  Blazing fast IPA phoneme conversion                    ║');
  console.log('╚══════════════════════════════════════════════════════════╝\n');
  
  // Check if JSON file exists
  if (!fs.existsSync('ja_phonemes.json')) {
    console.error('❌ Error: ja_phonemes.json not found in current directory');
    console.error('   Please ensure the phoneme dictionary is present.');
    process.exit(1);
  }
  
  // Initialize converter and load dictionary
  const converter = new PhonemeConverter();
  await converter.loadFromJson('ja_phonemes.json');
  
  // Initialize word segmenter if enabled
  let segmenter: WordSegmenter | null = null;
  if (USE_WORD_SEGMENTATION) {
    if (fs.existsSync('ja_words.txt')) {
      segmenter = new WordSegmenter();
      try {
        segmenter.loadFromFile('ja_words.txt');
        console.log('   💡 Word segmentation: ENABLED (spaces will separate words)');
      } catch (e) {
        console.error('⚠️  Warning: Could not load word dictionary:', e);
        console.error('   Continuing without word segmentation...');
        segmenter = null;
      }
    } else {
      console.log('   💡 Word segmentation: DISABLED (ja_words.txt not found)');
    }
  }
  
  console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');
  
  const args = process.argv.slice(2);
  
  // Handle command-line arguments
  if (args.length === 0) {
    // Interactive mode
    console.log('💡 Usage: ts-node jpn_to_phoneme.ts "日本語テキスト"');
    console.log('   Or enter Japanese text interactively:\n');
    
    const rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout,
    });
    
    const prompt = () => {
      rl.question('Japanese text (or "quit" to exit): ', (input) => {
        const trimmed = input.trim();
        
        if (!trimmed) {
          prompt();
          return;
        }
        
        if (trimmed.toLowerCase() === 'quit' || trimmed.toLowerCase() === 'exit') {
          console.log('\n👋 Goodbye!');
          rl.close();
          return;
        }
        
        // Perform conversion with timing
        const startTime = performance.now();
        const result = segmenter
          ? convertDetailedWithSegmentation(converter, trimmed, segmenter)
          : converter.convertDetailed(trimmed);
        const elapsed = performance.now() - startTime;
        
        // Display results
        console.log('\n┌─────────────────────────────────────────');
        console.log(`│ Input:    ${trimmed}`);
        console.log(`│ Phonemes: ${result.phonemes}`);
        console.log(`│ Time:     ${(elapsed * 1000).toFixed(0)}μs`);
        console.log('└─────────────────────────────────────────');
        
        // Show detailed matches if requested
        if (result.matches.length > 0) {
          console.log(`\n  Matches (${result.matches.length}):`);
          for (const match of result.matches) {
            console.log(`    • "${match.original}" → "${match.phoneme}" (pos: ${match.startIndex})`);
          }
        }
        
        if (result.unmatched.length > 0) {
          console.log(`\n  ⚠️  Unmatched characters: ${result.unmatched.join(', ')}`);
        }
        
        console.log('');
        prompt();
      });
    };
    
    prompt();
  } else {
    // Batch mode - convert all arguments
    for (const text of args) {
      // Perform conversion with timing
      const startTime = performance.now();
      const result = segmenter
        ? convertDetailedWithSegmentation(converter, text, segmenter)
        : converter.convertDetailed(text);
      const elapsed = performance.now() - startTime;
      
      // Display results
      console.log('┌─────────────────────────────────────────');
      console.log(`│ Input:    ${text}`);
      console.log(`│ Phonemes: ${result.phonemes}`);
      console.log(`│ Time:     ${(elapsed * 1000).toFixed(0)}μs (${elapsed.toFixed(0)}ms)`);
      console.log('└─────────────────────────────────────────');
      
      // Show detailed matches
      if (result.matches.length > 0) {
        console.log(`\n  ✅ Matches (${result.matches.length}):`);
        for (const match of result.matches) {
          console.log(`    • "${match.original}" → "${match.phoneme}" (pos: ${match.startIndex})`);
        }
      }
      
      if (result.unmatched.length > 0) {
        console.log(`\n  ⚠️  Unmatched characters: ${result.unmatched.join(', ')}`);
      }
      
      console.log('');
    }
    
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');
    console.log('✨ Conversion complete!');
  }
}

// Run if executed directly
if (require.main === module) {
  main().catch(console.error);
}

export { PhonemeConverter, TrieNode, Match, ConversionResult };

