#!/usr/bin/env dart
// Standalone Japanese to Phoneme Converter
// Blazing fast lookup using optimized trie structure

import 'dart:io';
import 'dart:convert';

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
  ConversionResult convertDetailed(String japaneseText) {
    final matches = <Match>[];
    final unmatched = <String>[];
    final result = StringBuffer();
    int pos = 0;
    
    while (pos < japaneseText.length) {
      int matchLength = 0;
      String? matchedPhoneme;
      
      TrieNode? current = _root;
      
      // Walk the trie as far as possible
      for (int i = pos; i < japaneseText.length && current != null; i++) {
        final charCode = japaneseText.codeUnitAt(i);
        current = current.children[charCode];
        
        if (current == null) break;
        
        if (current.phoneme != null) {
          matchLength = i - pos + 1;
          matchedPhoneme = current.phoneme;
        }
      }
      
      if (matchLength > 0) {
        // Found a match
        matches.add(Match(
          original: japaneseText.substring(pos, pos + matchLength),
          phoneme: matchedPhoneme!,
          startIndex: pos,
        ));
        result.write(matchedPhoneme);
        pos += matchLength;
      } else {
        // No match found
        final char = japaneseText[pos];
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
  final converter = PhonemeConverter();
  await converter.loadFromJson('ja_phonemes.json');
  
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
      final result = converter.convertDetailed(input);
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
      final result = converter.convertDetailed(text);
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

