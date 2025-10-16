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

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// FURIGANA HINT PROCESSING TYPES
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

/**
 * Types of segments in processed text
 */
enum SegmentType {
  NORMAL_TEXT,      // Regular text without furigana
  FURIGANA_HINT     // Text with furigana reading hint
}

/**
 * A segment of text that can be either normal or have a furigana hint
 */
interface TextSegment {
  type: SegmentType;
  text: string;        // The actual text (kanji for furigana hints)
  reading: string;     // The reading (only for furigana hints)
  originalPos: number; // Position in original text
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
   * Get root node for trie walking (used in word segmentation fallback)
   */
  getRoot(): TrieNode {
    return this.root;
  }
  
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
   * Get root node for trie walking (used in compound detection)
   */
  getRoot(): TrieNode {
    return this.root;
  }
  
  /**
   * Check if a word exists in the dictionary
   * Returns true if the word is a complete entry
   */
  containsWord(word: string): boolean {
    if (!word) return false;
    
    // Walk the trie
    let current: TrieNode | null = this.root;
    
    for (let i = 0; i < word.length; i++) {
      const charCode = word.charCodeAt(i);
      current = current.children.get(charCode) || null;
      if (current === null) {
        return false; // Path doesn't exist
      }
    }
    
    // Check if this is a valid end-of-word node
    return current.phoneme !== null;
  }
  
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
   * This version properly handles TextSegments with furigana hints,
   * treating each segment as an atomic unit during segmentation.
   * 
   * @param phonemeRoot Optional phoneme trie root for fallback lookups
   */
  segmentFromSegments(segments: TextSegment[], phonemeRoot?: TrieNode): string[] {
    const words: string[] = [];
    
    // Process each segment
    for (const segment of segments) {
      // For furigana segments, treat the entire reading as one word
      if (segment.type === SegmentType.FURIGANA_HINT) {
        words.push(segment.reading);
        continue;
      }
      
      // For normal text segments, apply word segmentation
      const text = segment.text;
      
      let pos = 0;
      while (pos < text.length) {
        // Skip spaces in input
        const char = text[pos];
        if (char === ' ' || char === '\t' || char === '\n' || char === '\r') {
          pos++;
          continue;
        }
        
        // Try to find longest word match starting at current position
        // Check word dictionary first, then phoneme dictionary as fallback
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
        
        // 🔥 FALLBACK: If word dictionary didn't find a match, try phoneme dictionary
        if (matchLength === 0 && phonemeRoot) {
          let phonemeCurrent: TrieNode | null = phonemeRoot;
          
          for (let i = pos; i < text.length && phonemeCurrent !== null; i++) {
            const charCode = text.charCodeAt(i);
            phonemeCurrent = phonemeCurrent.children.get(charCode) || null;
            
            if (phonemeCurrent === null) break;
            
            // If this node has a phoneme, it's a valid word
            if (phonemeCurrent.phoneme !== null) {
              matchLength = i - pos + 1;
            }
          }
        }
        
        if (matchLength > 0) {
          // Found a word match - extract it
          words.push(text.substring(pos, pos + matchLength));
          pos += matchLength;
        } else {
          // No match found - this is likely a grammatical element
          // Collect all consecutive unmatched characters as a single token
          // This handles particles (は、が、を), conjugations (です、ます), etc.
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
    }
    
    return words;
  }
  
  /**
   * Legacy segment method for backward compatibility
   * Converts text to a single normal segment and calls segmentFromSegments
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

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// FURIGANA HINT PROCESSING
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

/**
 * Helper function to check if a character is hiragana or katakana
 */
function isKana(codePoint: number): boolean {
  return (codePoint >= 0x3040 && codePoint <= 0x309F) ||  // Hiragana
         (codePoint >= 0x30A0 && codePoint <= 0x30FF);    // Katakana
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
 * @return Array of text segments with furigana hints properly parsed
 */
function parseFuriganaSegments(text: string, segmenter?: WordSegmenter): TextSegment[] {
  const segments: TextSegment[] = [];
  
  // 🔥 PRE-DECODE UTF-16 TO CODE POINTS FOR BLAZING SPEED!
  const chars: number[] = [];
  const charPositions: number[] = [];  // UTF-16 index for each char
  
  for (let i = 0; i < text.length; ) {
    charPositions.push(i);
    const code = text.charCodeAt(i);
    
    // Handle surrogate pairs for characters beyond BMP
    if (code >= 0xD800 && code <= 0xDBFF && i + 1 < text.length) {
      const low = text.charCodeAt(i + 1);
      if (low >= 0xDC00 && low <= 0xDFFF) {
        const codePoint = ((code - 0xD800) * 0x400) + (low - 0xDC00) + 0x10000;
        chars.push(codePoint);
        i += 2;
        continue;
      }
    }
    
    chars.push(code);
    i++;
  }
  charPositions.push(text.length);
  
  // Now process using pre-decoded code points for speed
  let pos = 0;
  
  while (pos < chars.length) {
    // Look for opening bracket 「 (U+300C)
    let bracketOpen = -1;
    for (let i = pos; i < chars.length; i++) {
      if (chars[i] === 0x300C) {
        bracketOpen = i;
        break;
      }
    }
    
    if (bracketOpen === -1) {
      // No more furigana hints, add rest of text as normal segment
      if (pos < chars.length) {
        const startIdx = charPositions[pos];
        const endIdx = charPositions[chars.length];
        segments.push({
          type: SegmentType.NORMAL_TEXT,
          text: text.substring(startIdx, endIdx),
          reading: '',
          originalPos: startIdx
        });
      }
      break;
    }
    
    // Look for closing bracket 」 (U+300D)
    let bracketClose = -1;
    for (let i = bracketOpen + 1; i < chars.length; i++) {
      if (chars[i] === 0x300D) {
        bracketClose = i;
        break;
      }
    }
    
    if (bracketClose === -1) {
      // No closing bracket, add rest as normal segment
      const startIdx = charPositions[pos];
      const endIdx = charPositions[chars.length];
      segments.push({
        type: SegmentType.NORMAL_TEXT,
        text: text.substring(startIdx, endIdx),
        reading: '',
        originalPos: startIdx
      });
      break;
    }
    
    // Find where the "word" (kanji) starts before the opening bracket
    // 🔥 BLAZING FAST BOUNDARY DETECTION USING PRE-DECODED CODE POINTS!
    
    // First pass: Find the last non-kana (kanji) character before the bracket
    let lastKanjiPos = bracketOpen;
    while (lastKanjiPos > pos && isKana(chars[lastKanjiPos - 1])) {
      lastKanjiPos--;
    }
    
    if (lastKanjiPos > pos) {
      lastKanjiPos--;  // Now pointing at the last kanji
    }
    
    // Second pass: From last kanji, search backward for word boundary
    // Include okurigana (kana between kanji), but stop at kana-only prefix
    let wordStart = lastKanjiPos;
    let searchPos = lastKanjiPos;
    
    while (searchPos > pos) {
      searchPos--;
      const cp = chars[searchPos];
      
      // Check for punctuation boundaries first (these always stop us)
      if (cp === 0x300D ||  // 」 closing bracket (another furigana hint)
          cp === 0x3001 ||  // 、 Japanese comma
          cp === 0x3002 ||  // 。 Japanese period  
          cp === 0xFF01 ||  // ！ full-width exclamation
          cp === 0xFF1F ||  // ？ full-width question
          cp === 0xFF09 ||  // ） full-width right paren
          cp === 0xFF3D) {  // ］ full-width right bracket
        wordStart = searchPos + 1;
        break;
      }
      
      // Check for ASCII punctuation and whitespace
      if (cp < 0x80 && (
          cp === 0x2E || cp === 0x2C || cp === 0x21 || cp === 0x3F || cp === 0x3B || cp === 0x3A ||
          cp === 0x28 || cp === 0x29 || cp === 0x5B || cp === 0x5D || cp === 0x7B || cp === 0x7D ||
          cp === 0x22 || cp === 0x27 || cp === 0x2D || cp === 0x2F || cp === 0x5C || cp === 0x7C ||
          cp === 0x20 || cp === 0x09 || cp === 0x0A || cp === 0x0D)) {
        wordStart = searchPos + 1;
        break;
      }
      
      // Check if this is kana
      const isKanaChar = isKana(cp);
      
      if (isKanaChar) {
        // Check if there's ANY non-kana (kanji) before this position
        let hasKanjiBefore = false;
        for (let checkPos = searchPos; checkPos > pos; checkPos--) {
          if (!isKana(chars[checkPos - 1])) {
            // Check it's not punctuation
            const checkCp = chars[checkPos - 1];
            if (checkCp >= 0x4E00 || (checkCp >= 0x3400 && checkCp <= 0x9FFF)) {  // CJK kanji ranges
              hasKanjiBefore = true;
              break;
            }
          }
        }
        
        if (!hasKanjiBefore) {
          // This kana is not sandwiched - it's a prefix word → stop here
          wordStart = searchPos + 1;
          break;
        }
        // Otherwise, this kana is sandwiched (okurigana) → continue
      }
      
      // Update word_start to include this character
      wordStart = searchPos;
    }
    
    // Add text from current position up to where the word/kanji starts
    // This captures particles and other text between furigana hints
    if (wordStart > pos) {
      const startIdx = charPositions[pos];
      const endIdx = charPositions[wordStart];
      segments.push({
        type: SegmentType.NORMAL_TEXT,
        text: text.substring(startIdx, endIdx),
        reading: '',
        originalPos: startIdx
      });
    }
    
    // Extract the kanji and reading using pre-decoded positions
    const kanjiStartIdx = charPositions[wordStart];
    const kanjiEndIdx = charPositions[bracketOpen];
    const kanji = text.substring(kanjiStartIdx, kanjiEndIdx);
    
    // Extract reading between brackets
    const readingStart = bracketOpen + 1; // Position after 「
    const readingEnd = bracketClose;      // Position before 」
    
    // Extract reading text using positions
    let readingStartIdx = charPositions[readingStart];
    let readingEndIdx = charPositions[readingEnd];
    let reading = text.substring(readingStartIdx, readingEndIdx).trim();
    
    if (!reading) {
      // Empty reading - skip the entire furigana hint
      pos = bracketClose + 1;
      continue;
    }
    
    // 🔥 SMART COMPOUND WORD DETECTION USING TRIE'S LONGEST-MATCH
    // Walk the trie starting from kanji to find the longest compound word
    const afterBracket = bracketClose + 1; // Position after 」
    let usedCompound = false;
    
    if (segmenter && afterBracket < chars.length) {
      // Use trie to find longest match starting from word_start position
      // This naturally implements longest-match algorithm
      let matchLength = 0;
      let current: TrieNode | null = segmenter.getRoot();
      
      // Walk trie through kanji characters first
      for (let i = wordStart; i < bracketOpen && current !== null; i++) {
        current = current.children.get(chars[i]) || null;
        if (current === null) break;
      }
      
      // Continue walking through characters after the bracket
      if (current !== null) {
        for (let i = afterBracket; i < chars.length && current !== null; i++) {
          current = current.children.get(chars[i]) || null;
          if (current === null) break;
          
          // Check if this position marks a valid word ending
          if (current.phoneme !== null) {
            // Found a compound! Track it as the longest so far
            matchLength = i - afterBracket + 1;
          }
        }
      }
      
      // If we found a compound word, use it with the furigana reading replacing the kanji
      // This ensures that 来「き」た becomes "きた" not "来た" for phoneme conversion
      if (matchLength > 0) {
        const compoundEndIdx = charPositions[afterBracket + matchLength];
        // 🔥 KEY FIX: Use the furigana READING instead of kanji!
        const compound = reading + text.substring(charPositions[afterBracket], compoundEndIdx);
        segments.push({
          type: SegmentType.NORMAL_TEXT,
          text: compound,
          reading: '',
          originalPos: kanjiStartIdx
        });
        pos = afterBracket + matchLength;
        usedCompound = true;
      }
    }
    
    if (!usedCompound) {
      // No compound found, use the furigana hint
      segments.push({
        type: SegmentType.FURIGANA_HINT,
        text: kanji,
        reading: reading,
        originalPos: kanjiStartIdx
      });
      pos = bracketClose + 1;
    }
  }
  
  return segments;
}

/**
 * Convert with word segmentation support
 * Optimized algorithm with TextSegment-based furigana processing:
 * 1) Parse text into segments with furigana hints extracted
 * 2) Segment into words using the structured segments
 * 3) Convert each word to phonemes
 * Returns phonemes with spaces between words
 * 
 * BLAZING FAST: Uses optimized UTF-16 processing throughout
 */
function convertWithSegmentation(converter: PhonemeConverter, text: string, segmenter: WordSegmenter): string {
  // 🔥 STEP 1: Parse furigana hints into structured segments
  // 健太「けんた」はバカ → [TextSegment("健太", "けんた"), TextSegment("はバカ")]
  // 見「み」て → [TextSegment("見て")] (compound word detected)
  const segments = parseFuriganaSegments(text, segmenter);
  
  // 🔥 STEP 2: Segment into words using structured segments with phoneme fallback
  // Furigana segments are treated as atomic units
  const words = segmenter.segmentFromSegments(segments, converter.getRoot());
  
  // 🔥 STEP 3: Convert each word to phonemes with particle handling
  const result: string[] = [];
  for (let i = 0; i < words.length; i++) {
    if (i > 0) result.push(' ');  // Add space between words
    
    // Special handling for the topic particle は → "wa"
    if (words[i] === 'は') {
      result.push('wa');
    } else {
      result.push(converter.convert(words[i]));
    }
  }
  
  return result.join('');
}

/**
 * Convert with word segmentation and detailed information
 * Includes furigana hint processing for proper name handling
 * BLAZING FAST: Uses optimized UTF-16 processing and structured segments
 */
function convertDetailedWithSegmentation(converter: PhonemeConverter, text: string, segmenter: WordSegmenter): ConversionResult {
  // 🔥 STEP 1: Parse furigana hints into structured segments
  const segments = parseFuriganaSegments(text, segmenter);
  
  // 🔥 STEP 2: Segment into words using structured segments with phoneme fallback
  const words = segmenter.segmentFromSegments(segments, converter.getRoot());
  
  // 🔥 STEP 3: Convert each word to phonemes with particle handling
  const allMatches: Match[] = [];
  const allUnmatched: string[] = [];
  const phonemeParts: string[] = [];
  let byteOffset = 0;
  
  for (let i = 0; i < words.length; i++) {
    if (i > 0) phonemeParts.push(' ');  // Add space between words
    
    // Special handling for the topic particle は → "wa"
    if (words[i] === 'は') {
      phonemeParts.push('wa');
      // Add to matches for consistency
      allMatches.push({
        original: words[i],
        phoneme: 'wa',
        startIndex: byteOffset
      });
    } else {
      const wordResult = converter.convertDetailed(words[i]);
      
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
    }
    
    byteOffset += words[i].length;
  }
  
  return {
    phonemes: phonemeParts.join(''),
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

export { 
  PhonemeConverter, 
  WordSegmenter, 
  TrieNode, 
  Match, 
  ConversionResult, 
  TextSegment, 
  SegmentType,
  parseFuriganaSegments,
  convertWithSegmentation,
  convertDetailedWithSegmentation
};

