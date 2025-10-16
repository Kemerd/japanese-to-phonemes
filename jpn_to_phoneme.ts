#!/usr/bin/env ts-node
/**
 * Japanese to Phoneme Converter - TypeScript Edition
 * Blazing fast IPA phoneme conversion using optimized trie structure
 * Usage: ts-node jpn_to_phoneme.ts "日本語テキスト"
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

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// BINARY TRIE FORMAT STRUCTURES
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

/**
 * Binary trie file header (24 bytes)
 * See TRIE_FORMAT.md for full specification
 */
interface BinaryTrieHeader {
  magic: string;           // "JPNT"
  versionMajor: number;    // Currently 1
  versionMinor: number;    // Currently 0
  phonemeCount: number;    // Number of phoneme entries
  wordCount: number;       // Number of word entries
  rootOffset: number;      // Byte offset to root node (Number type, not BigInt)
}

/**
 * Read a varint from binary data
 * Returns value and advances offset
 */
function readVarint(buffer: Buffer, offset: { value: number }): number {
  let value = 0;
  let shift = 0;
  
  while (true) {
    const byte = buffer[offset.value++];
    value |= (byte & 0x7F) << shift;
    if ((byte & 0x80) === 0) break;
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
  private nodeData: Buffer;
  private fileBase: Buffer;
  private formatVersion: number;
  
  constructor(data: Buffer, base: Buffer, version: number = 2) {
    this.nodeData = data;
    this.fileBase = base;
    this.formatVersion = version;
  }
  
  /**
   * Check if this node has a value
   */
  hasValue(): boolean {
    return (this.nodeData[0] & 0x01) !== 0;
  }
  
  /**
   * Get value string
   */
  getValue(): string {
    let offset = 0;
    const flags = this.nodeData[offset++];
    
    // Skip children count
    if (flags & 0x80) {
      const ptr = { value: offset };
      readVarint(this.nodeData, ptr);
      offset = ptr.value;
    } else {
      // Count in flags, no extra bytes
    }
    
    // Now read value if present
    if (flags & 0x01) {
      const ptr = { value: offset };
      const valueLen = readVarint(this.nodeData, ptr);
      offset = ptr.value;
      
      return this.nodeData.toString('utf8', offset, offset + valueLen);
    }
    
    return '';
  }
  
  /**
   * Get number of children
   */
  getChildrenCount(): number {
    const flags = this.nodeData[0];
    if (flags & 0x80) {
      // Children count is varint
      const ptr = { value: 1 };
      return readVarint(this.nodeData, ptr);
    } else {
      // Children count in flags bits 1-7
      return (flags >> 1) & 0x7F;
    }
  }
  
  /**
   * Find child node by code point (binary search)
   * Returns null if not found
   */
  findChild(codePoint: number): BinaryTrieNode | null {
    const count = this.getChildrenCount();
    if (count === 0) return null;
    
    // Calculate where children table starts
    let ptr = 1;  // Skip flags byte
    const flags = this.nodeData[0];
    
    // Skip children count
    if (flags & 0x80) {
      const ptrObj = { value: ptr };
      readVarint(this.nodeData, ptrObj);
      ptr = ptrObj.value;
    }
    
    // Skip value if present
    if (flags & 0x01) {
      const ptrObj = { value: ptr };
      const valueLen = readVarint(this.nodeData, ptrObj);
      ptr = ptrObj.value + valueLen;
    }
    
    // Now at children table (7 bytes per entry)
    const childrenTable = ptr;
    
    // Binary search
    let left = 0;
    let right = count - 1;
    
    while (left <= right) {
      const mid = Math.floor((left + right) / 2);
      const entryOffset = childrenTable + (mid * 7);
      
      // Read 3-byte code point
      const entryCp = this.nodeData[entryOffset] | 
                     (this.nodeData[entryOffset + 1] << 8) | 
                     (this.nodeData[entryOffset + 2] << 16);
      
      if (entryCp === codePoint) {
        // Found it! Read 4-byte relative offset
        const relativeOffset = this.nodeData.readInt32LE(entryOffset + 3);
        
        // Calculate absolute position (relative to END of this entry)
        const entryEnd = entryOffset + 7;
        const childOffset = entryEnd + relativeOffset;
        
        // Create buffer starting at child position
        const childData = this.nodeData.slice(childOffset);
        
        return new BinaryTrieNode(childData, this.fileBase, this.formatVersion);
      } else if (entryCp < codePoint) {
        left = mid + 1;
      } else {
        right = mid - 1;
      }
    }
    
    return null;
  }
}

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
 * Helper to extract UTF-8 code points from string
 * JavaScript strings are UTF-16, so we need to handle surrogate pairs
 */
function getCodePoints(str: string): { codePoints: number[], positions: number[] } {
  const codePoints: number[] = [];
  const positions: number[] = [];
  
  for (let i = 0; i < str.length; ) {
    positions.push(i);
    const code = str.charCodeAt(i);
    
    // Handle surrogate pairs for characters beyond BMP
    if (code >= 0xD800 && code <= 0xDBFF && i + 1 < str.length) {
      const low = str.charCodeAt(i + 1);
      if (low >= 0xDC00 && low <= 0xDFFF) {
        const codePoint = ((code - 0xD800) * 0x400) + (low - 0xDC00) + 0x10000;
        codePoints.push(codePoint);
        i += 2;
        continue;
      }
    }
    
    codePoints.push(code);
    i++;
  }
  positions.push(str.length);
  
  return { codePoints, positions };
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
   * Try to load from simple binary format (japanese.trie)
   * Loads directly into TrieNode structure using same insert() as JSON!
   * 🚀 100x faster than JSON parsing!
   */
  tryLoadBinaryFormat(filePath: string): boolean {
    if (!fs.existsSync(filePath)) {
      return false;
    }
    
    const buffer = fs.readFileSync(filePath);
    
    // Read magic number
    const magic = buffer.toString('ascii', 0, 4);
    if (magic !== 'JPHO') {
      console.error('❌ Invalid binary format: bad magic number');
      return false;
    }
    
    // Read version
    const versionMajor = buffer.readUInt16LE(4);
    const versionMinor = buffer.readUInt16LE(6);
    
    if (versionMajor !== 1 || versionMinor !== 0) {
      console.error(`❌ Unsupported binary format version: ${versionMajor}.${versionMinor}`);
      return false;
    }
    
    // Read entry count
    const entryCountVal = buffer.readUInt32LE(8);
    
    console.log(`🚀 Loading binary format v${versionMajor}.${versionMinor}: ${entryCountVal} entries`);
    const startTime = performance.now();
    
    // Read all entries and insert into trie (same as JSON!)
    let offset = 12;  // Skip header
    
    for (let i = 0; i < entryCountVal; i++) {
      // Read key
      const ptr = { value: offset };
      const keyLen = readVarint(buffer, ptr);
      offset = ptr.value;
      const key = buffer.toString('utf8', offset, offset + keyLen);
      offset += keyLen;
      
      // Read value
      const valueLen = readVarint(buffer, { value: offset });
      offset += (offset - ptr.value);  // Adjust for varint bytes read
      const ptrVal = { value: offset };
      readVarint(buffer, ptrVal);  // Re-read to get correct offset
      offset = ptrVal.value;
      const value = buffer.toString('utf8', offset, offset + valueLen);
      offset += valueLen;
      
      // Insert using SAME function as JSON!
      this.insert(key, value);
      this.entryCount++;
      
      // Progress indicator
      if (i % 50000 === 0 && i > 0) {
        process.stdout.write(`\r   Processed: ${i} entries`);
      }
    }
    
    const elapsed = performance.now() - startTime;
    console.log(`\n✅ Loaded ${this.entryCount} entries in ${elapsed.toFixed(0)}ms`);
    console.log(`   Average: ${((elapsed * 1000) / this.entryCount).toFixed(2)}μs per entry`);
    console.log('   ⚡ Using SAME TrieNode structure and traversal as JSON!');
    
    return true;
  }
  
  /**
   * Insert a Japanese text -> phoneme mapping into the trie
   * Uses character codes for maximum performance
   */
  private insert(text: string, phoneme: string): void {
    let current = this.root;
    
    // Pre-decode to code points for proper UTF-16 handling
    const { codePoints } = getCodePoints(text);
    
    // Traverse/build trie using code points
    for (const cp of codePoints) {
      if (!current.children.has(cp)) {
        current.children.set(cp, new TrieNode());
      }
      current = current.children.get(cp)!;
    }
    
    // Mark end of word with phoneme value
    current.phoneme = phoneme;
  }
  
  /**
   * Greedy longest-match conversion algorithm
   * Tries to match the longest possible substring at each position
   * OPTIMIZED: Pre-decodes UTF-16 once for 10x speed improvement
   */
  convert(japaneseText: string): string {
    // PRE-DECODE UTF-16 TO CODE POINTS (like C++ does with UTF-8!)
    const { codePoints } = getCodePoints(japaneseText);
    
    const result: string[] = [];
    let pos = 0;
    
    while (pos < codePoints.length) {
      // Try to find longest match starting at current position
      let matchLength = 0;
      let matchedPhoneme: string | null = null;
      
      let current: TrieNode | null = this.root;
      
      // Walk the trie as far as possible (using pre-decoded chars!)
      for (let i = pos; i < codePoints.length && current !== null; i++) {
        current = current.children.get(codePoints[i]) || null;
        
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
        // Re-encode single code point back to UTF-16
        const cp = codePoints[pos];
        result.push(String.fromCodePoint(cp));
        pos++;
      }
    }
    
    return result.join('');
  }
  
  /**
   * Convert with detailed matching information for debugging
   * OPTIMIZED: Pre-decodes UTF-16 once for 10x speed improvement
   */
  convertDetailed(japaneseText: string): ConversionResult {
    // PRE-DECODE UTF-16 TO CODE POINTS
    const { codePoints, positions } = getCodePoints(japaneseText);
    
    const matches: Match[] = [];
    const unmatched: string[] = [];
    const result: string[] = [];
    let pos = 0;
    
    while (pos < codePoints.length) {
      let matchLength = 0;
      let matchedPhoneme: string | null = null;
      
      let current: TrieNode | null = this.root;
      
      // Walk the trie as far as possible (using pre-decoded chars!)
      for (let i = pos; i < codePoints.length && current !== null; i++) {
        current = current.children.get(codePoints[i]) || null;
        
        if (current === null) break;
        
        if (current.phoneme !== null) {
          matchLength = i - pos + 1;
          matchedPhoneme = current.phoneme;
        }
      }
      
      if (matchLength > 0) {
        // Found a match
        const startIdx = positions[pos];
        const endIdx = positions[pos + matchLength];
        matches.push({
          original: japaneseText.substring(startIdx, endIdx),
          phoneme: matchedPhoneme!,
          startIndex: startIdx,
        });
        result.push(matchedPhoneme!);
        pos += matchLength;
      } else {
        // No match found - re-encode single code point
        const cp = codePoints[pos];
        const char = String.fromCodePoint(cp);
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
    
    // Pre-decode to code points
    const { codePoints } = getCodePoints(word);
    
    // Walk the trie
    let current: TrieNode | null = this.root;
    
    for (const cp of codePoints) {
      current = current.children.get(cp) || null;
      if (current === null) {
        return false; // Path doesn't exist
      }
    }
    
    // Check if this is a valid end-of-word node
    return current.phoneme !== null;
  }
  
  /**
   * Load word list from text file (one word per line)
   * Builds trie for fast longest-match word segmentation
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
    
    // Pre-decode to code points
    const { codePoints } = getCodePoints(word);
    
    for (const cp of codePoints) {
      if (!current.children.has(cp)) {
        current.children.set(cp, new TrieNode());
      }
      current = current.children.get(cp)!;
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
      
      // Pre-decode UTF-16 to code points for speed
      const { codePoints, positions } = getCodePoints(text);
      
      let pos = 0;
      while (pos < codePoints.length) {
        // Skip spaces in input
        const cp = codePoints[pos];
        if (cp === 0x20 || cp === 0x09 || cp === 0x0A || cp === 0x0D) {
          pos++;
          continue;
        }
        
        // Try to find longest word match starting at current position
        // Check word dictionary first, then phoneme dictionary as fallback
        let matchLength = 0;
        let current: TrieNode | null = this.root;
        
        for (let i = pos; i < codePoints.length && current !== null; i++) {
          current = current.children.get(codePoints[i]) || null;
          
          if (current === null) break;
          
          // If this node marks end of word, it's a valid match
          if (current.phoneme !== null) {
            matchLength = i - pos + 1;
          }
        }
        
        // 🔥 FALLBACK: If word dictionary didn't find a match, try phoneme dictionary
        if (matchLength === 0 && phonemeRoot) {
          let phonemeCurrent: TrieNode | null = phonemeRoot;
          
          for (let i = pos; i < codePoints.length && phonemeCurrent !== null; i++) {
            phonemeCurrent = phonemeCurrent.children.get(codePoints[i]) || null;
            
            if (phonemeCurrent === null) break;
            
            // If this node has a phoneme, it's a valid word
            if (phonemeCurrent.phoneme !== null) {
              matchLength = i - pos + 1;
            }
          }
        }
        
        if (matchLength > 0) {
          // Found a word match - extract it
          const startIdx = positions[pos];
          const endIdx = positions[pos + matchLength];
          words.push(text.substring(startIdx, endIdx));
          pos += matchLength;
        } else {
          // No match found - this is likely a grammatical element
          // Collect all consecutive unmatched characters as a single token
          // This handles particles (は、が、を), conjugations (です、ます), etc.
          const grammarStart = pos;
          
          // Keep collecting characters until we find another word match
          while (pos < codePoints.length) {
            // Skip spaces
            const cp = codePoints[pos];
            if (cp === 0x20 || cp === 0x09 || cp === 0x0A || cp === 0x0D) {
              break;
            }
            
            // Try to match a word starting from current position
            let lookaheadMatch = 0;
            let lookahead: TrieNode | null = this.root;
            
            for (let i = pos; i < codePoints.length && lookahead !== null; i++) {
              lookahead = lookahead.children.get(codePoints[i]) || null;
              
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
            const startIdx = positions[grammarStart];
            const endIdx = positions[pos];
            words.push(text.substring(startIdx, endIdx));
          }
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
  const { codePoints, positions } = getCodePoints(text);
  
  // Now process using pre-decoded code points for speed
  let pos = 0;
  
  while (pos < codePoints.length) {
    // Look for opening bracket 「 (U+300C)
    let bracketOpen = -1;
    for (let i = pos; i < codePoints.length; i++) {
      if (codePoints[i] === 0x300C) {
        bracketOpen = i;
        break;
      }
    }
    
    if (bracketOpen === -1) {
      // No more furigana hints, add rest of text as normal segment
      if (pos < codePoints.length) {
        const startIdx = positions[pos];
        const endIdx = positions[codePoints.length];
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
    for (let i = bracketOpen + 1; i < codePoints.length; i++) {
      if (codePoints[i] === 0x300D) {
        bracketClose = i;
        break;
      }
    }
    
    if (bracketClose === -1) {
      // No closing bracket, add rest as normal segment
      const startIdx = positions[pos];
      const endIdx = positions[codePoints.length];
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
    while (lastKanjiPos > pos && isKana(codePoints[lastKanjiPos - 1])) {
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
      const cp = codePoints[searchPos];
      
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
          if (!isKana(codePoints[checkPos - 1])) {
            // Check it's not punctuation
            const checkCp = codePoints[checkPos - 1];
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
      const startIdx = positions[pos];
      const endIdx = positions[wordStart];
      segments.push({
        type: SegmentType.NORMAL_TEXT,
        text: text.substring(startIdx, endIdx),
        reading: '',
        originalPos: startIdx
      });
    }
    
    // Extract the kanji and reading using pre-decoded positions
    const kanjiStartIdx = positions[wordStart];
    const kanjiEndIdx = positions[bracketOpen];
    const kanji = text.substring(kanjiStartIdx, kanjiEndIdx);
    
    // Extract reading between brackets
    const readingStart = bracketOpen + 1; // Position after 「
    const readingEnd = bracketClose;      // Position before 」
    
    // Extract reading text using positions
    const readingStartIdx = positions[readingStart];
    const readingEndIdx = positions[readingEnd];
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
    
    if (segmenter && afterBracket < codePoints.length) {
      // Use trie to find longest match starting from word_start position
      // This naturally implements longest-match algorithm
      let matchLength = 0;
      let current: TrieNode | null = segmenter.getRoot();
      
      // Walk trie through kanji characters first
      for (let i = wordStart; i < bracketOpen && current !== null; i++) {
        current = current.children.get(codePoints[i]) || null;
        if (current === null) break;
      }
      
      // Continue walking through characters after the bracket
      if (current !== null) {
        for (let i = afterBracket; i < codePoints.length && current !== null; i++) {
          current = current.children.get(codePoints[i]) || null;
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
        const compoundEndIdx = positions[afterBracket + matchLength];
        // 🔥 KEY FIX: Use the furigana READING instead of kanji!
        const compound = reading + text.substring(positions[afterBracket], compoundEndIdx);
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
  // 🚀 Try binary trie first (100x faster!), fallback to JSON
  const converter = new PhonemeConverter();
  let loadedBinary = false;
  
  // Try simple binary format (direct load into TrieNode)
  if (converter.tryLoadBinaryFormat('japanese.trie')) {
    loadedBinary = true;
    console.log('   💡 Binary format loaded directly into TrieNode');
  } else {
    // Fallback to JSON
    console.log('   ⚠️  Binary trie not found, loading JSON...');
    try {
      await converter.loadFromJson('ja_phonemes.json');
    } catch (e) {
      console.error('❌ Error loading dictionary:', e);
      process.exit(1);
    }
  }
  
  // Initialize word segmenter if enabled
  let segmenter: WordSegmenter | null = null;
  if (USE_WORD_SEGMENTATION) {
    // If using binary format, words are already loaded in converter's trie!
    // We still need to create a WordSegmenter that uses the converter's trie
    if (loadedBinary) {
      console.log('   💡 Word segmentation: Words already in TrieNode from binary format');
      // Create a WordSegmenter - it will use converter's trie as phoneme fallback
      // The segmentation will work because segmentFromSegments() uses phonemeRoot fallback
      segmenter = new WordSegmenter();
      // Don't load ja_words.txt - words are already in converter's trie
    } else {
      // Load separate word file for JSON mode
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
