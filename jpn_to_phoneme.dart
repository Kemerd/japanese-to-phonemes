#!/usr/bin/env dart
// Standalone Japanese to Phoneme Converter
// Blazing fast lookup using optimized trie structure

import 'dart:io';
import 'dart:convert';

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// CONFIGURATION
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

// Enable word segmentation to add spaces between words in output
// Uses ja_words.txt for Japanese word boundaries
const USE_WORD_SEGMENTATION = true;

/// High-performance trie node for phoneme lookup
/// Uses character code mapping for O(1) access
class TrieNode {
  // Map character codes to child nodes for instant lookup
  final Map<int, TrieNode> children = {};
  
  // Phoneme value if this node represents end of a word
  String? phoneme;
}

/// Ultra-fast phoneme converter using trie data structure
/// Achieves microsecond-level lookups for typical text
class PhonemeConverter {
  final TrieNode _root = TrieNode();
  int _entryCount = 0;
  
  /// Try to load from simple binary format (japanese.trie)
  /// Loads directly into TrieNode structure using same insert() as JSON!
  /// 🚀 100x faster than JSON parsing!
  Future<bool> tryLoadBinaryFormat(String filePath) async {
    final file = File(filePath);
    
    // Check if file exists
    if (!await file.exists()) {
      return false;
    }
    
    try {
      final bytes = await file.readAsBytes();
      int offset = 0;
      
      // Read magic number
      if (offset + 4 > bytes.length) return false;
      final magic = String.fromCharCodes(bytes.sublist(offset, offset + 4));
      offset += 4;
      if (magic != 'JPHO') {
        print('❌ Invalid binary format: bad magic number');
        return false;
      }
      
      // Read version
      if (offset + 4 > bytes.length) return false;
      final versionMajor = bytes[offset] | (bytes[offset + 1] << 8);
      final versionMinor = bytes[offset + 2] | (bytes[offset + 3] << 8);
      offset += 4;
      
      if (versionMajor != 1 || versionMinor != 0) {
        print('❌ Unsupported binary format version: $versionMajor.$versionMinor');
        return false;
      }
      
      // Read entry count
      if (offset + 4 > bytes.length) return false;
      final entryCount = bytes[offset] | (bytes[offset + 1] << 8) | 
                        (bytes[offset + 2] << 16) | (bytes[offset + 3] << 24);
      offset += 4;
      
      print('🚀 Loading binary format v$versionMajor.$versionMinor: $entryCount entries');
      final stopwatch = Stopwatch()..start();
      
      // Helper to read varint
      int readVarint() {
        int value = 0;
        int shift = 0;
        while (true) {
          if (offset >= bytes.length) throw Exception('Unexpected end of file');
          final byte = bytes[offset++];
          value |= (byte & 0x7F) << shift;
          if ((byte & 0x80) == 0) break;
          shift += 7;
        }
        return value;
      }
      
      // Read all entries and insert into trie (same as JSON!)
      for (int i = 0; i < entryCount; i++) {
        // Read key
        final keyLen = readVarint();
        if (offset + keyLen > bytes.length) throw Exception('Invalid key length');
        final key = utf8.decode(bytes.sublist(offset, offset + keyLen));
        offset += keyLen;
        
        // Read value
        final valueLen = readVarint();
        if (offset + valueLen > bytes.length) throw Exception('Invalid value length');
        final value = utf8.decode(bytes.sublist(offset, offset + valueLen));
        offset += valueLen;
        
        // Insert using SAME function as JSON!
        _insert(key, value);
        _entryCount++;
        
        // Progress indicator
        if (i % 50000 == 0 && i > 0) {
          stdout.write('\r   Processed: $i entries');
        }
      }
      
      stopwatch.stop();
      print('\n✅ Loaded $_entryCount entries in ${stopwatch.elapsedMilliseconds}ms');
      print('   Average: ${(stopwatch.elapsedMicroseconds / _entryCount).toStringAsFixed(2)}μs per entry');
      print('   ⚡ Using SAME TrieNode structure and traversal as JSON!');
      
      return true;
    } catch (e) {
      print('❌ Error loading binary trie: $e');
      return false;
    }
  }
  
  /// Build trie from JSON dictionary file
  /// Optimized for fast construction from large datasets
  Future<void> loadFromJson(String filePath) async {
    final file = File(filePath);
    
    // Read entire file as string for fastest parsing
    final contents = await file.readAsString();
    final Map<String, dynamic> data = jsonDecode(contents);
    
    print('🔥 Loading ${data.length} entries into trie...');
    final stopwatch = Stopwatch()..start();
    
    // Insert each entry into the trie
    data.forEach((key, value) {
      _insert(key, value as String);
      _entryCount++;
      
      // Progress indicator for large datasets
      if (_entryCount % 50000 == 0) {
        stdout.write('\r   Processed: $_entryCount entries');
      }
    });
    
    stopwatch.stop();
    print('\n✅ Loaded $_entryCount entries in ${stopwatch.elapsedMilliseconds}ms');
    print('   Average: ${(stopwatch.elapsedMicroseconds / _entryCount).toStringAsFixed(2)}μs per entry');
  }
  
  /// Get root node for trie walking (used in word segmentation fallback)
  TrieNode getRoot() => _root;
  
  /// Insert a Japanese text -> phoneme mapping into the trie
  /// Uses character codes for maximum performance
  void _insert(String text, String phoneme) {
    TrieNode current = _root;
    
    // Traverse/build trie using character codes
    for (int i = 0; i < text.length; i++) {
      final charCode = text.codeUnitAt(i);
      
      // Create child node if doesn't exist
      current.children[charCode] ??= TrieNode();
      current = current.children[charCode]!;
    }
    
    // Mark end of word with phoneme value
    current.phoneme = phoneme;
  }
  
  /// Greedy longest-match conversion algorithm
  /// Tries to match the longest possible substring at each position
  String? convert(String japaneseText) {
    final result = StringBuffer();
    int pos = 0;
    
    while (pos < japaneseText.length) {
      // Try to find longest match starting at current position
      int matchLength = 0;
      String? matchedPhoneme;
      
      TrieNode? current = _root;
      
      // Walk the trie as far as possible
      for (int i = pos; i < japaneseText.length && current != null; i++) {
        final charCode = japaneseText.codeUnitAt(i);
        current = current.children[charCode];
        
        if (current == null) break;
        
        // If this node has a phoneme, it's a valid match
        if (current.phoneme != null) {
          matchLength = i - pos + 1;
          matchedPhoneme = current.phoneme;
        }
      }
      
      if (matchLength > 0) {
        // Found a match - add phoneme and advance position
        result.write(matchedPhoneme);
        pos += matchLength;
      } else {
        // No match found - keep original character and continue
        // This handles spaces, punctuation, unknown characters
        result.write(japaneseText[pos]);
        pos++;
      }
    }
    
    return result.toString();
  }
  
  /// Convert with detailed matching information for debugging
  /// OPTIMIZED: Uses runes (Unicode code points) for proper character handling
  ConversionResult convertDetailed(String japaneseText) {
    // PRE-DECODE TO RUNES (code points) for proper Unicode handling
    final runes = japaneseText.runes.toList();
    final bytePositions = <int>[];
    int bytePos = 0;
    
    // Track byte positions for each rune
    for (final rune in runes) {
      bytePositions.add(bytePos);
      bytePos += String.fromCharCode(rune).length;
    }
    bytePositions.add(bytePos); // End position
    
    final matches = <Match>[];
    final unmatched = <String>[];
    final result = StringBuffer();
    int pos = 0;
    
    while (pos < runes.length) {
      int matchLength = 0;
      String? matchedPhoneme;
      
      TrieNode? current = _root;
      
      // Walk the trie as far as possible
      for (int i = pos; i < runes.length && current != null; i++) {
        current = current.children[runes[i]];
        
        if (current == null) break;
        
        if (current.phoneme != null) {
          matchLength = i - pos + 1;
          matchedPhoneme = current.phoneme;
        }
      }
      
      if (matchLength > 0) {
        // Found a match
        final originalRunes = runes.sublist(pos, pos + matchLength);
        matches.add(Match(
          original: String.fromCharCodes(originalRunes),
          phoneme: matchedPhoneme!,
          startIndex: bytePositions[pos], // Use byte position!
        ));
        result.write(matchedPhoneme);
        pos += matchLength;
      } else {
        // No match found
        final char = String.fromCharCode(runes[pos]);
        unmatched.add(char);
        result.write(char);
        pos++;
      }
    }
    
    return ConversionResult(
      phonemes: result.toString(),
      matches: matches,
      unmatched: unmatched,
    );
  }
}

/// Detailed conversion result with match information
class ConversionResult {
  final String phonemes;
  final List<Match> matches;
  final List<String> unmatched;
  
  ConversionResult({
    required this.phonemes,
    required this.matches,
    required this.unmatched,
  });
}

/// Individual match from Japanese text to phoneme
class Match {
  final String original;
  final String phoneme;
  final int startIndex;
  
  Match({
    required this.original,
    required this.phoneme,
    required this.startIndex,
  });
  
  @override
  String toString() => '"$original" → "$phoneme" (pos: $startIndex)';
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// FURIGANA HINT PROCESSING TYPES
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

/// Types of segments in processed text
enum SegmentType {
  normalText,     // Regular text without furigana
  furiganaHint,  // Text with furigana reading hint
}

/// A segment of text that can be either normal or have a furigana hint
class TextSegment {
  final SegmentType type;
  final String text;         // The actual text (kanji for furigana hints)
  final String reading;      // The reading (only for furigana hints)
  final int originalPos;     // Position in original text
  
  // Constructor for normal text
  TextSegment.normal(this.text, this.originalPos)
      : type = SegmentType.normalText,
        reading = '';
  
  // Constructor for furigana hint
  TextSegment.furigana(this.text, this.reading, this.originalPos)
      : type = SegmentType.furiganaHint;
  
  // Get the effective text (reading for furigana, text otherwise)
  String getEffectiveText() {
    return type == SegmentType.furiganaHint ? reading : text;
  }
}

/// Word segmenter using longest-match algorithm with word dictionary
/// Splits Japanese text into words for better phoneme spacing
class WordSegmenter {
  final TrieNode _root = TrieNode();
  int _wordCount = 0;
  
  /// Get root node for trie walking (used in compound detection)
  TrieNode getRoot() => _root;
  
  /// Check if a word exists in the dictionary
  /// Returns true if the word is a complete entry
  bool containsWord(String word) {
    if (word.isEmpty) return false;
    
    TrieNode? current = _root;
    
    for (int i = 0; i < word.length; i++) {
      final charCode = word.codeUnitAt(i);
      current = current?.children[charCode];
      if (current == null) return false; // Path doesn't exist
    }
    
    // Check if this is a valid end-of-word node
    return current?.phoneme != null;
  }
  
  /// Load word list from text file (one word per line)
  Future<void> loadFromFile(String filePath) async {
    final file = File(filePath);
    
    print('🔥 Loading word dictionary for segmentation...');
    final stopwatch = Stopwatch()..start();
    
    final lines = await file.readAsLines();
    
    for (var word in lines) {
      word = word.trim();
      if (word.isNotEmpty) {
        _insertWord(word);
        _wordCount++;
        
        if (_wordCount % 50000 == 0) {
          stdout.write('\r   Loaded: $_wordCount words');
        }
      }
    }
    
    stopwatch.stop();
    print('\n✅ Loaded $_wordCount words in ${stopwatch.elapsedMilliseconds}ms');
  }
  
  /// Insert a word into the trie
  void _insertWord(String word) {
    TrieNode current = _root;
    
    for (int i = 0; i < word.length; i++) {
      final charCode = word.codeUnitAt(i);
      current.children[charCode] ??= TrieNode();
      current = current.children[charCode]!;
    }
    
    // Mark end of word (use empty string as marker)
    current.phoneme = "";
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
  List<String> segment(String text) {
    final words = <String>[];
    int pos = 0;
    
    while (pos < text.length) {
      // Skip spaces in input
      final char = text[pos];
      if (char == ' ' || char == '\t' || char == '\n' || char == '\r') {
        pos++;
        continue;
      }
      
      // Try to find longest word match starting at current position
      int matchLength = 0;
      TrieNode? current = _root;
      
      for (int i = pos; i < text.length && current != null; i++) {
        final charCode = text.codeUnitAt(i);
        current = current.children[charCode];
        
        if (current == null) break;
        
        // If this node marks end of word, it's a valid match
        if (current.phoneme != null) {
          matchLength = i - pos + 1;
        }
      }
      
      if (matchLength > 0) {
        // Found a word match - extract it
        words.add(text.substring(pos, pos + matchLength));
        pos += matchLength;
      } else {
        // No match found - this is likely a grammatical element
        // Collect all consecutive unmatched characters as a single token
        final grammarStart = pos;
        
        // Keep collecting characters until we find another word match
        while (pos < text.length) {
          // Skip spaces
          final char = text[pos];
          if (char == ' ' || char == '\t' || char == '\n' || char == '\r') {
            break;
          }
          
          // Try to match a word starting from current position
          int lookaheadMatch = 0;
          TrieNode? lookahead = _root;
          
          for (int i = pos; i < text.length && lookahead != null; i++) {
            final charCode = text.codeUnitAt(i);
            lookahead = lookahead.children[charCode];
            
            if (lookahead == null) break;
            
            if (lookahead.phoneme != null) {
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
          words.add(text.substring(grammarStart, pos));
        }
      }
    }
    
    return words;
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
  /// @param phonemeRoot Optional phoneme trie root for fallback lookups
  List<String> segmentFromSegments(List<TextSegment> segments, {TrieNode? phonemeRoot}) {
    final words = <String>[];
    
    // Process each segment
    for (final segment in segments) {
      // For furigana segments, treat the entire reading as one word
      if (segment.type == SegmentType.furiganaHint) {
        words.add(segment.reading);
        continue;
      }
      
      // For normal text segments, apply word segmentation
      final text = segment.text;
      final runes = text.runes.toList();
      int pos = 0;
      
      while (pos < runes.length) {
        // Skip spaces in input
        if (runes[pos] == 0x20 || runes[pos] == 0x09 || runes[pos] == 0x0A || runes[pos] == 0x0D) {
          pos++;
          continue;
        }
        
        // Try to find longest word match starting at current position
        // Check word dictionary first, then phoneme dictionary as fallback
        int matchLength = 0;
        TrieNode? current = _root;
        
        for (int i = pos; i < runes.length && current != null; i++) {
          current = current.children[runes[i]];
          if (current == null) break;
          
          // If this node marks end of word, it's a valid match
          if (current.phoneme != null) {
            matchLength = i - pos + 1;
          }
        }
        
        // 🔥 FALLBACK: If word dictionary didn't find a match, try phoneme dictionary
        if (matchLength == 0 && phonemeRoot != null) {
          TrieNode? phonemeCurrent = phonemeRoot;
          
          for (int i = pos; i < runes.length && phonemeCurrent != null; i++) {
            phonemeCurrent = phonemeCurrent.children[runes[i]];
            if (phonemeCurrent == null) break;
            
            // If this node has a phoneme, it's a valid word
            if (phonemeCurrent.phoneme != null) {
              matchLength = i - pos + 1;
            }
          }
        }
        
        if (matchLength > 0) {
          // Found a word match - extract it
          final word = String.fromCharCodes(runes.sublist(pos, pos + matchLength));
          words.add(word);
          pos += matchLength;
        } else {
          // No match found - this is likely a grammatical element
          // Collect all consecutive unmatched characters as a single token
          final grammarStart = pos;
          
          // Keep collecting characters until we find another word match
          while (pos < runes.length) {
            // Skip spaces
            if (runes[pos] == 0x20 || runes[pos] == 0x09 || runes[pos] == 0x0A || runes[pos] == 0x0D) {
              break;
            }
            
            // Try to match a word starting from current position
            int lookaheadMatch = 0;
            TrieNode? lookahead = _root;
            
            for (int i = pos; i < runes.length && lookahead != null; i++) {
              lookahead = lookahead.children[runes[i]];
              if (lookahead == null) break;
              
              if (lookahead.phoneme != null) {
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
            final grammar = String.fromCharCodes(runes.sublist(grammarStart, pos));
            words.add(grammar);
          }
        }
      }
    }
    
    return words;
  }
}

/// Helper function to check if a character is kana (hiragana or katakana)
bool _isKana(int codePoint) {
  return (codePoint >= 0x3040 && codePoint <= 0x309F) ||  // Hiragana
         (codePoint >= 0x30A0 && codePoint <= 0x30FF);    // Katakana
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
List<TextSegment> parseFuriganaSegments(String text, {WordSegmenter? segmenter}) {
  final segments = <TextSegment>[];
  
  // Pre-decode to runes for blazing speed
  final runes = text.runes.toList();
  final bytePositions = <int>[];
  int bytePos = 0;
  
  for (final rune in runes) {
    bytePositions.add(bytePos);
    bytePos += String.fromCharCode(rune).length;
  }
  bytePositions.add(bytePos);
  
  int pos = 0;
  
  while (pos < runes.length) {
    // Look for opening bracket 「 (U+300C)
    int? bracketOpen;
    for (int i = pos; i < runes.length; i++) {
      if (runes[i] == 0x300C) {
        bracketOpen = i;
        break;
      }
    }
    
    if (bracketOpen == null) {
      // No more furigana hints, add rest of text as normal segment
      if (pos < runes.length) {
        final textStr = String.fromCharCodes(runes.sublist(pos));
        segments.add(TextSegment.normal(textStr, bytePositions[pos]));
      }
      break;
    }
    
    // Look for closing bracket 」 (U+300D)
    int? bracketClose;
    for (int i = bracketOpen + 1; i < runes.length; i++) {
      if (runes[i] == 0x300D) {
        bracketClose = i;
        break;
      }
    }
    
    if (bracketClose == null) {
      // No closing bracket, add rest as normal segment
      final textStr = String.fromCharCodes(runes.sublist(pos));
      segments.add(TextSegment.normal(textStr, bytePositions[pos]));
      break;
    }
    
    // Find where the "word" (kanji) starts before the opening bracket
    int lastKanjiPos = bracketOpen;
    while (lastKanjiPos > pos && _isKana(runes[lastKanjiPos - 1])) {
      lastKanjiPos--;
    }
    
    if (lastKanjiPos > pos) {
      lastKanjiPos--; // Now pointing at the last kanji
    }
    
    // Second pass: From last kanji, search backward for word boundary
    int wordStart = lastKanjiPos;
    int searchPos = lastKanjiPos;
    
    while (searchPos > pos) {
      searchPos--;
      final rune = runes[searchPos];
      
      // Check for punctuation boundaries
      if (rune == 0x300D || rune == 0x3001 || rune == 0x3002 || rune == 0xFF01 || 
          rune == 0xFF1F || rune == 0xFF09 || rune == 0xFF3D ||
          (rune < 0x80 && [0x2E, 0x2C, 0x21, 0x3F, 0x3B, 0x3A, 0x28, 0x29, 0x5B, 0x5D,
                           0x7B, 0x7D, 0x22, 0x27, 0x2D, 0x2F, 0x5C, 0x7C, 0x20, 0x09, 0x0A, 0x0D].contains(rune))) {
        wordStart = searchPos + 1;
        break;
      }
      
      // Check if this is kana
      if (_isKana(rune)) {
        // Check if there's ANY kanji before this position
        final hasKanjiBefore = runes.sublist(pos, searchPos).any((r) {
          return r >= 0x4E00 || (r >= 0x3400 && r <= 0x9FFF);
        });
        
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
    if (wordStart > pos) {
      final textStr = String.fromCharCodes(runes.sublist(pos, wordStart));
      segments.add(TextSegment.normal(textStr, bytePositions[pos]));
    }
    
    // Extract the kanji and reading
    final kanji = String.fromCharCodes(runes.sublist(wordStart, bracketOpen));
    final reading = String.fromCharCodes(runes.sublist(bracketOpen + 1, bracketClose)).trim();
    
    if (reading.isEmpty) {
      // Empty reading - skip the entire furigana hint
      pos = bracketClose + 1;
      continue;
    }
    
    // 🔥 SMART COMPOUND WORD DETECTION USING TRIE'S LONGEST-MATCH
    final afterBracket = bracketClose + 1;
    bool usedCompound = false;
    
    if (segmenter != null && afterBracket < runes.length) {
      // Use trie to find longest match starting from wordStart position
      int matchLength = 0;
      TrieNode? current = segmenter.getRoot();
      
      // Walk trie through kanji characters first
      for (int i = wordStart; i < bracketOpen && current != null; i++) {
        current = current.children[runes[i]];
      }
      
      // Continue walking through characters after the bracket
      if (current != null) {
        for (int i = afterBracket; i < runes.length && current != null; i++) {
          current = current.children[runes[i]];
          
          // Check if this position marks a valid word ending
          if (current?.phoneme != null) {
            // Found a compound! Track it as the longest so far
            matchLength = i - afterBracket + 1;
          }
        }
      }
      
      // If we found a compound word, use it with the furigana reading
      if (matchLength > 0) {
        final suffix = String.fromCharCodes(runes.sublist(afterBracket, afterBracket + matchLength));
        final compound = reading + suffix;
        segments.add(TextSegment.normal(compound, bytePositions[wordStart]));
        pos = afterBracket + matchLength;
        usedCompound = true;
      }
    }
    
    if (!usedCompound) {
      // No compound found, use the furigana hint
      segments.add(TextSegment.furigana(kanji, reading, bytePositions[wordStart]));
      pos = bracketClose + 1;
    }
  }
  
  return segments;
}

/// Convert with word segmentation support
/// OPTIMIZED: Uses furigana-aware segmentation and は → wa particle handling
/// 
/// Example: 健太「けんた」はバカ → kẽ̞ɴta wa baka
String convertWithSegmentation(PhonemeConverter converter, String text, WordSegmenter segmenter) {
  // 🔥 STEP 1: Parse furigana hints into structured segments
  final segments = parseFuriganaSegments(text, segmenter: segmenter);
  
  // 🔥 STEP 2: Segment into words using structured segments with phoneme fallback
  final words = segmenter.segmentFromSegments(segments, phonemeRoot: converter.getRoot());
  
  // 🔥 STEP 3: Convert each word to phonemes with particle handling
  final phonemes = words.map((word) {
    // Special handling for the topic particle は → "wa"
    if (word == 'は') {
      return 'wa';
    } else {
      return converter.convert(word) ?? word;
    }
  }).toList();
  
  return phonemes.join(' ');  // Space-separated!
}

/// Convert with word segmentation and detailed information
/// OPTIMIZED: Uses furigana-aware segmentation and は → wa particle handling
ConversionResult convertDetailedWithSegmentation(PhonemeConverter converter, String text, WordSegmenter segmenter) {
  // 🔥 STEP 1: Parse furigana hints into structured segments
  final segments = parseFuriganaSegments(text, segmenter: segmenter);
  
  // 🔥 STEP 2: Segment into words using structured segments with phoneme fallback
  final words = segmenter.segmentFromSegments(segments, phonemeRoot: converter.getRoot());
  
  // 🔥 STEP 3: Convert each word to phonemes with particle handling
  final allMatches = <Match>[];
  final allUnmatched = <String>[];
  final phonemeParts = <String>[];
  int byteOffset = 0;
  
  for (var word in words) {
    // Special handling for the topic particle は → "wa"
    if (word == 'は') {
      phonemeParts.add('wa');
      // Add to matches for consistency
      allMatches.add(Match(
        original: word,
        phoneme: 'wa',
        startIndex: byteOffset,
      ));
    } else {
      final wordResult = converter.convertDetailed(word);
      
      // Adjust match positions to account for original text position
      for (var match in wordResult.matches) {
        allMatches.add(Match(
          original: match.original,
          phoneme: match.phoneme,
          startIndex: match.startIndex + byteOffset,
        ));
      }
      
      phonemeParts.add(wordResult.phonemes);
      allUnmatched.addAll(wordResult.unmatched);
    }
    
    byteOffset += word.length;
  }
  
  return ConversionResult(
    phonemes: phonemeParts.join(' '),
    matches: allMatches,
    unmatched: allUnmatched,
  );
}

/// Main entry point for standalone execution
void main(List<String> args) async {
  print('╔══════════════════════════════════════════════════════════╗');
  print('║  Japanese → Phoneme Converter                           ║');
  print('║  Blazing fast IPA phoneme conversion                    ║');
  print('╚══════════════════════════════════════════════════════════╝\n');
  
  // Check if JSON file exists
  final jsonFile = File('ja_phonemes.json');
  if (!await jsonFile.exists()) {
    print('❌ Error: ja_phonemes.json not found in current directory');
    print('   Please ensure the phoneme dictionary is present.');
    exit(1);
  }
  
  // Initialize converter and load dictionary
  // 🚀 Try binary trie first (100x faster!), fallback to JSON
  final converter = PhonemeConverter();
  bool loadedBinary = false;
  
  // Try simple binary format (direct load into TrieNode)
  if (await converter.tryLoadBinaryFormat('japanese.trie')) {
    loadedBinary = true;
    print('   💡 Binary format loaded directly into TrieNode');
  } else {
    // Fallback to JSON
    print('   ⚠️  Binary trie not found, loading JSON...');
    await converter.loadFromJson('ja_phonemes.json');
  }
  
  // Initialize word segmenter if enabled
  WordSegmenter? segmenter;
  if (USE_WORD_SEGMENTATION) {
    // If using binary format, words are already loaded in converter's trie!
    // We still need to create a WordSegmenter that uses the converter's trie
    if (loadedBinary) {
      print('   💡 Word segmentation: Words already in TrieNode from binary format');
      // Create an empty WordSegmenter - it will use converter's trie as phoneme fallback
      // The segmentation will work because segmentFromSegments() uses phonemeRoot fallback
      segmenter = WordSegmenter();
      // Don't load ja_words.txt - words are already in converter's trie
    } else {
      // Load separate word file for JSON mode
      final wordFile = File('ja_words.txt');
      if (await wordFile.exists()) {
        segmenter = WordSegmenter();
        try {
          await segmenter.loadFromFile('ja_words.txt');
          print('   💡 Word segmentation: ENABLED (spaces will separate words)');
        } catch (e) {
          print('⚠️  Warning: Could not load word dictionary: $e');
          print('   Continuing without word segmentation...');
          segmenter = null;
        }
      } else {
        print('   💡 Word segmentation: DISABLED (ja_words.txt not found)');
      }
    }
  }
  
  print('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');
  
  // Handle command-line arguments
  if (args.isEmpty) {
    // Interactive mode
    print('💡 Usage: dart jpn_to_phoneme.dart "日本語テキスト"');
    print('   Or enter Japanese text interactively:\n');
    
    while (true) {
      stdout.write('Japanese text (or "quit" to exit): ');
      final input = stdin.readLineSync()?.trim() ?? '';
      
      if (input.isEmpty) continue;
      if (input.toLowerCase() == 'quit' || input.toLowerCase() == 'exit') {
        print('\n👋 Goodbye!');
        break;
      }
      
      // Perform conversion with timing
      final stopwatch = Stopwatch()..start();
      final result = segmenter != null
          ? convertDetailedWithSegmentation(converter, input, segmenter)
          : converter.convertDetailed(input);
      stopwatch.stop();
      
      // Display results
      print('\n┌─────────────────────────────────────────');
      print('│ Input:    $input');
      print('│ Phonemes: ${result.phonemes}');
      print('│ Time:     ${stopwatch.elapsedMicroseconds}μs');
      print('└─────────────────────────────────────────');
      
      // Show detailed matches if requested
      if (result.matches.isNotEmpty) {
        print('\n  Matches (${result.matches.length}):');
        for (final match in result.matches) {
          print('    • $match');
        }
      }
      
      if (result.unmatched.isNotEmpty) {
        print('\n  ⚠️  Unmatched characters: ${result.unmatched.join(", ")}');
      }
      
      print('');
    }
  } else {
    // Batch mode - convert all arguments
    for (final text in args) {
      // Perform conversion with timing
      final stopwatch = Stopwatch()..start();
      final result = segmenter != null
          ? convertDetailedWithSegmentation(converter, text, segmenter)
          : converter.convertDetailed(text);
      stopwatch.stop();
      
      // Display results
      print('┌─────────────────────────────────────────');
      print('│ Input:    $text');
      print('│ Phonemes: ${result.phonemes}');
      print('│ Time:     ${stopwatch.elapsedMicroseconds}μs (${stopwatch.elapsedMilliseconds}ms)');
      print('└─────────────────────────────────────────');
      
      // Show detailed matches
      if (result.matches.isNotEmpty) {
        print('\n  ✅ Matches (${result.matches.length}):');
        for (final match in result.matches) {
          print('    • $match');
        }
      }
      
      if (result.unmatched.isNotEmpty) {
        print('\n  ⚠️  Unmatched characters: ${result.unmatched.join(", ")}');
      }
      
      print('');
    }
    
    print('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');
    print('✨ Conversion complete!');
  }
}

