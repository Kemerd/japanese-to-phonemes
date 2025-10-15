#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Japanese to Phoneme Converter - Python Edition
Blazing fast IPA phoneme conversion using optimized trie structure
"""

import json
import sys
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import io

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CONFIGURATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Enable word segmentation to add spaces between words in output
# Uses ja_words.txt for Japanese word boundaries
USE_WORD_SEGMENTATION = True

# Force UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


@dataclass
class Match:
    """Individual match from Japanese text to phoneme"""
    original: str
    phoneme: str
    start_index: int
    
    def __str__(self) -> str:
        return f'"{self.original}" → "{self.phoneme}" (pos: {self.start_index})'


@dataclass
class ConversionResult:
    """Detailed conversion result with match information"""
    phonemes: str
    matches: List[Match]
    unmatched: List[str]


class TrieNode:
    """
    High-performance trie node for phoneme lookup
    Uses dictionary for O(1) character code access
    """
    
    def __init__(self):
        # Map character codes to child nodes for instant lookup
        self.children: Dict[int, 'TrieNode'] = {}
        
        # Phoneme value if this node represents end of a word
        self.phoneme: Optional[str] = None


class PhonemeConverter:
    """
    Ultra-fast phoneme converter using trie data structure
    Achieves microsecond-level lookups for typical text
    """
    
    def __init__(self):
        self.root = TrieNode()
        self.entry_count = 0
    
    def load_from_json(self, file_path: str) -> None:
        """
        Build trie from JSON dictionary file
        Optimized for fast construction from large datasets
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f'🔥 Loading {len(data)} entries into trie...')
        start_time = time.perf_counter()
        
        # Insert each entry into the trie
        for key, value in data.items():
            self._insert(key, value)
            self.entry_count += 1
            
            # Progress indicator for large datasets
            if self.entry_count % 50000 == 0:
                print(f'\r   Processed: {self.entry_count} entries', end='', flush=True)
        
        elapsed = (time.perf_counter() - start_time) * 1000
        print(f'\n✅ Loaded {self.entry_count} entries in {elapsed:.0f}ms')
        print(f'   Average: {(elapsed * 1000 / self.entry_count):.2f}μs per entry')
    
    def _insert(self, text: str, phoneme: str) -> None:
        """
        Insert a Japanese text -> phoneme mapping into the trie
        Uses character codes for maximum performance
        """
        current = self.root
        
        # Traverse/build trie using character codes
        for char in text:
            char_code = ord(char)
            
            # Create child node if doesn't exist
            if char_code not in current.children:
                current.children[char_code] = TrieNode()
            current = current.children[char_code]
        
        # Mark end of word with phoneme value
        current.phoneme = phoneme
    
    def convert(self, japanese_text: str) -> str:
        """
        Greedy longest-match conversion algorithm
        Tries to match the longest possible substring at each position
        """
        result = []
        pos = 0
        
        while pos < len(japanese_text):
            # Try to find longest match starting at current position
            match_length = 0
            matched_phoneme = None
            
            current = self.root
            
            # Walk the trie as far as possible
            i = pos
            while i < len(japanese_text) and current is not None:
                char_code = ord(japanese_text[i])
                current = current.children.get(char_code)
                
                if current is None:
                    break
                
                # If this node has a phoneme, it's a valid match
                if current.phoneme is not None:
                    match_length = i - pos + 1
                    matched_phoneme = current.phoneme
                
                i += 1
            
            if match_length > 0:
                # Found a match - add phoneme and advance position
                result.append(matched_phoneme)
                pos += match_length
            else:
                # No match found - keep original character and continue
                # This handles spaces, punctuation, unknown characters
                result.append(japanese_text[pos])
                pos += 1
        
        return ''.join(result)
    
    def convert_detailed(self, japanese_text: str) -> ConversionResult:
        """
        Convert with detailed matching information for debugging
        """
        matches = []
        unmatched = []
        result = []
        pos = 0
        
        while pos < len(japanese_text):
            match_length = 0
            matched_phoneme = None
            
            current = self.root
            
            # Walk the trie as far as possible
            i = pos
            while i < len(japanese_text) and current is not None:
                char_code = ord(japanese_text[i])
                current = current.children.get(char_code)
                
                if current is None:
                    break
                
                if current.phoneme is not None:
                    match_length = i - pos + 1
                    matched_phoneme = current.phoneme
                
                i += 1
            
            if match_length > 0:
                # Found a match
                matches.append(Match(
                    original=japanese_text[pos:pos + match_length],
                    phoneme=matched_phoneme,
                    start_index=pos,
                ))
                result.append(matched_phoneme)
                pos += match_length
            else:
                # No match found
                char = japanese_text[pos]
                unmatched.append(char)
                result.append(char)
                pos += 1
        
        return ConversionResult(
            phonemes=''.join(result),
            matches=matches,
            unmatched=unmatched,
        )


class WordSegmenter:
    """
    Word segmenter using longest-match algorithm with word dictionary
    Splits Japanese text into words for better phoneme spacing
    
    SMART SEGMENTATION: Words are matched from dictionary, and any
    unmatched sequences between words are treated as grammatical elements
    (particles, conjugations, etc.) and given their own space.
    """
    
    def __init__(self):
        self.root = TrieNode()
        self.word_count = 0
    
    def load_from_file(self, file_path: str) -> None:
        """Load word list from text file (one word per line)"""
        print('🔥 Loading word dictionary for segmentation...')
        start_time = time.perf_counter()
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                word = line.strip()
                if word:
                    self._insert_word(word)
                    self.word_count += 1
                    
                    if self.word_count % 50000 == 0:
                        print(f'\r   Loaded: {self.word_count} words', end='', flush=True)
        
        elapsed = (time.perf_counter() - start_time) * 1000
        print(f'\n✅ Loaded {self.word_count} words in {elapsed:.0f}ms')
    
    def _insert_word(self, word: str) -> None:
        """Insert a word into the trie"""
        current = self.root
        
        for char in word:
            char_code = ord(char)
            if char_code not in current.children:
                current.children[char_code] = TrieNode()
            current = current.children[char_code]
        
        # Mark end of word (use empty string as marker)
        current.phoneme = ""
    
    def segment(self, text: str) -> List[str]:
        """
        Segment text into words using longest-match algorithm
        
        Example: 私はリンゴがすきです
        - Matches: 私, リンゴ, すき
        - Grammar (unmatched): は, が, です
        - Result: [私, は, リンゴ, が, すき, です]
        """
        words = []
        pos = 0
        
        while pos < len(text):
            # Skip spaces in input
            if text[pos] in ' \t\n\r':
                pos += 1
                continue
            
            # Try to find longest word match starting at current position
            match_length = 0
            current = self.root
            
            i = pos
            while i < len(text) and current is not None:
                char_code = ord(text[i])
                current = current.children.get(char_code)
                
                if current is None:
                    break
                
                # If this node marks end of word, it's a valid match
                if current.phoneme is not None:
                    match_length = i - pos + 1
                
                i += 1
            
            if match_length > 0:
                # Found a word match - extract it
                words.append(text[pos:pos + match_length])
                pos += match_length
            else:
                # No match found - this is likely a grammatical element
                # Collect all consecutive unmatched characters as a single token
                grammar_start = pos
                
                # Keep collecting characters until we find another word match
                while pos < len(text):
                    # Skip spaces
                    if text[pos] in ' \t\n\r':
                        break
                    
                    # Try to match a word starting from current position
                    lookahead_match = 0
                    lookahead = self.root
                    
                    for i in range(pos, len(text)):
                        char_code = ord(text[i])
                        lookahead = lookahead.children.get(char_code)
                        
                        if lookahead is None:
                            break
                        
                        if lookahead.phoneme is not None:
                            lookahead_match = i - pos + 1
                    
                    # If we found a word match, stop here
                    if lookahead_match > 0:
                        break
                    
                    # Otherwise, this character is part of the grammar sequence
                    pos += 1
                
                # Extract the grammar token
                if pos > grammar_start:
                    words.append(text[grammar_start:pos])
        
        return words


def convert_with_segmentation(converter: PhonemeConverter, text: str, segmenter: WordSegmenter) -> str:
    """Convert with word segmentation support"""
    # First pass: segment into words
    words = segmenter.segment(text)
    
    # Second pass: convert each word to phonemes
    result = []
    for word in words:
        result.append(converter.convert(word))
    
    return ' '.join(result)  # Space-separated!


def convert_detailed_with_segmentation(converter: PhonemeConverter, text: str, segmenter: WordSegmenter) -> ConversionResult:
    """Convert with word segmentation and detailed information"""
    # First pass: segment into words
    words = segmenter.segment(text)
    
    # Second pass: convert each word to phonemes
    all_matches = []
    all_unmatched = []
    phoneme_parts = []
    byte_offset = 0
    
    for word in words:
        word_result = converter.convert_detailed(word)
        
        # Adjust match positions to account for original text position
        for match in word_result.matches:
            match.start_index += byte_offset
            all_matches.append(match)
        
        phoneme_parts.append(word_result.phonemes)
        all_unmatched.extend(word_result.unmatched)
        byte_offset += len(word)
    
    return ConversionResult(
        phonemes=' '.join(phoneme_parts),
        matches=all_matches,
        unmatched=all_unmatched,
    )


def main():
    """Main entry point for standalone execution"""
    print('╔══════════════════════════════════════════════════════════╗')
    print('║  Japanese → Phoneme Converter (Python)                  ║')
    print('║  Blazing fast IPA phoneme conversion                    ║')
    print('╚══════════════════════════════════════════════════════════╝\n')
    
    # Check if JSON file exists
    import os
    if not os.path.exists('ja_phonemes.json'):
        print('❌ Error: ja_phonemes.json not found in current directory')
        print('   Please ensure the phoneme dictionary is present.')
        sys.exit(1)
    
    # Initialize converter and load dictionary
    converter = PhonemeConverter()
    converter.load_from_json('ja_phonemes.json')
    
    # Initialize word segmenter if enabled
    segmenter = None
    if USE_WORD_SEGMENTATION:
        import os
        if os.path.exists('ja_words.txt'):
            segmenter = WordSegmenter()
            try:
                segmenter.load_from_file('ja_words.txt')
                print('   💡 Word segmentation: ENABLED (spaces will separate words)')
            except Exception as e:
                print(f'⚠️  Warning: Could not load word dictionary: {e}')
                print('   Continuing without word segmentation...')
                segmenter = None
        else:
            print('   💡 Word segmentation: DISABLED (ja_words.txt not found)')
    
    print('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n')
    
    args = sys.argv[1:]
    
    # Handle command-line arguments
    if not args:
        # Interactive mode
        print('💡 Usage: python jpn_to_phoneme.py "日本語テキスト"')
        print('   Or enter Japanese text interactively:\n')
        
        while True:
            try:
                text = input('Japanese text (or "quit" to exit): ').strip()
                
                if not text:
                    continue
                
                if text.lower() in ('quit', 'exit'):
                    print('\n👋 Goodbye!')
                    break
                
                # Perform conversion with timing
                start_time = time.perf_counter()
                if segmenter:
                    result = convert_detailed_with_segmentation(converter, text, segmenter)
                else:
                    result = converter.convert_detailed(text)
                elapsed = (time.perf_counter() - start_time) * 1_000_000
                
                # Display results
                print('\n┌─────────────────────────────────────────')
                print(f'│ Input:    {text}')
                print(f'│ Phonemes: {result.phonemes}')
                print(f'│ Time:     {elapsed:.0f}μs')
                print('└─────────────────────────────────────────')
                
                # Show detailed matches if requested
                if result.matches:
                    print(f'\n  Matches ({len(result.matches)}):')
                    for match in result.matches:
                        print(f'    • {match}')
                
                if result.unmatched:
                    print(f'\n  ⚠️  Unmatched characters: {", ".join(result.unmatched)}')
                
                print()
            except (EOFError, KeyboardInterrupt):
                print('\n\n👋 Goodbye!')
                break
    else:
        # Batch mode - convert all arguments
        for text in args:
            # Perform conversion with timing
            start_time = time.perf_counter()
            if segmenter:
                result = convert_detailed_with_segmentation(converter, text, segmenter)
            else:
                result = converter.convert_detailed(text)
            elapsed_us = (time.perf_counter() - start_time) * 1_000_000
            elapsed_ms = elapsed_us / 1000
            
            # Display results
            print('┌─────────────────────────────────────────')
            print(f'│ Input:    {text}')
            print(f'│ Phonemes: {result.phonemes}')
            print(f'│ Time:     {elapsed_us:.0f}μs ({elapsed_ms:.0f}ms)')
            print('└─────────────────────────────────────────')
            
            # Show detailed matches
            if result.matches:
                print(f'\n  ✅ Matches ({len(result.matches)}):')
                for match in result.matches:
                    print(f'    • {match}')
            
            if result.unmatched:
                print(f'\n  ⚠️  Unmatched characters: {", ".join(result.unmatched)}')
            
            print()
        
        print('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n')
        print('✨ Conversion complete!')


if __name__ == '__main__':
    main()

