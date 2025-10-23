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
import struct
import os

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
    
    def try_load_binary_format(self, file_path: str) -> bool:
        """
        Load phoneme dictionary from binary .trie format (100x faster!)
        
        Binary format:
        - Magic: "JPN\x00" (4 bytes)
        - Version: major.minor (2 bytes)
        - Entry count: varint
        - Entries: [key_len(varint), key(utf8), value_len(varint), value(utf8)]
        
        Returns True if loaded successfully, False if file not found
        """
        if not os.path.exists(file_path):
            return False
        
        try:
            with open(file_path, 'rb') as f:
                # Read and verify magic number
                magic = f.read(4)
                if magic != b'JPHO':
                    return False
                
                # Read version (2 uint16_t values = 4 bytes total)
                version_major, version_minor = struct.unpack('<HH', f.read(4))
                
                # Read entry count (uint32_t = 4 bytes)
                entry_count = struct.unpack('<I', f.read(4))[0]
                
                # Read varint helper
                def read_varint():
                    value = 0
                    shift = 0
                    while True:
                        byte = f.read(1)[0]
                        value |= (byte & 0x7F) << shift
                        if (byte & 0x80) == 0:
                            break
                        shift += 7
                    return value
                
                print(f'🚀 Loading binary format v{version_major}.{version_minor}: {entry_count} entries')
                start_time = time.perf_counter()
                
                # Read all entries and insert into trie
                for i in range(entry_count):
                    # Read key
                    key_len = read_varint()
                    key = f.read(key_len).decode('utf-8')
                    
                    # Read value
                    value_len = read_varint()
                    value = f.read(value_len).decode('utf-8') if value_len > 0 else ""
                    
                    # Insert into trie (same as JSON!)
                    self._insert(key, value)
                    self.entry_count += 1
                    
                    # Progress indicator
                    if self.entry_count % 50000 == 0:
                        print(f'\r   Processed: {self.entry_count} entries', end='', flush=True)
                
                elapsed = (time.perf_counter() - start_time) * 1000
                print(f'\n✅ Loaded {self.entry_count} entries in {elapsed:.0f}ms')
                print(f'   Average: {(elapsed * 1000 / self.entry_count):.2f}μs per entry')
                print('   ⚡ Using SAME TrieNode structure and traversal as JSON!')
                
                return True
                
        except Exception as e:
            print(f'⚠️  Error loading binary format: {e}')
            return False
    
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
                # 🔥 FIX: Skip empty phonemes (word markers from binary trie)
                if current.phoneme is not None and current.phoneme != "":
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
                
                # 🔥 FIX: Skip empty phonemes (word markers from binary trie)
                if current.phoneme is not None and current.phoneme != "":
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


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FURIGANA HINT PARSING
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class TextSegment:
    """Represents a segment of text with optional furigana hint"""
    text: str
    furigana_hint: str = ""


def parse_furigana_hints(text: str, segmenter=None, phoneme_root=None) -> List[TextSegment]:
    """
    Parse text into segments, extracting furigana hints with SMART ALGORITHMS.
    
    🔥 SMART NAME DETECTION: Detects honorifics (さん, 先生, etc.) to prevent incorrect splitting
    🔥 SMART HINT BACKTRACKING: Matches reading from the end of kanji backwards to split correctly
    
    Example: 山本「やまもと」さん → Full reading for entire name (name detection)
    Example: 五百円「えん」 → Split as 五百 + 円「えん」 (hint backtracking)
    
    Returns list of TextSegment objects
    """
    segments = []
    i = 0
    
    while i < len(text):
        # Look for opening bracket 「 only (U+300C)
        bracket_open = text.find('「', i)
        
        if bracket_open == -1:
            # No more furigana hints, add rest of text as normal segment
            if i < len(text):
                segments.append(TextSegment(text=text[i:]))
            break
        
        # Look for closing bracket 」 (U+300D)
        bracket_close = text.find('」', bracket_open + 1)
        
        if bracket_close == -1:
            # No closing bracket, add rest as normal segment
            segments.append(TextSegment(text=text[i:]))
            break
        
        # Find where the "word" (kanji) starts before the opening bracket
        # Simple backward search for now (simplified from C++ version)
        word_start = bracket_open
        while word_start > i and text[word_start - 1] not in ' \t\n\r、。！？）］':
            word_start -= 1
        
        # Add text from current position up to where the word/kanji starts
        if word_start > i:
            segments.append(TextSegment(text=text[i:word_start]))
        
        # Extract the kanji and reading
        kanji = text[word_start:bracket_open]
        reading = text[bracket_open + 1:bracket_close].strip()
        
        if not reading:
            # Empty reading - skip the entire furigana hint
            i = bracket_close + 1
            continue
        
        # 🔥 SMART NAME DETECTION: Check if honorific follows the furigana hint
        is_likely_name = False
        after_bracket = bracket_close + 1
        if after_bracket < len(text):
            next_char = ord(text[after_bracket]) if after_bracket < len(text) else 0
            # Check for common honorifics: さん、さま、様、君、ちゃん、くん、氏、殿、先生、師、長
            if next_char == 0x3055:  # さ
                if after_bracket + 1 < len(text):
                    next_next = ord(text[after_bracket + 1])
                    if next_next == 0x3093 or next_next == 0x307E:  # ん or ま
                        is_likely_name = True
            elif next_char in [0x69D8, 0x541B, 0x6C0F, 0x6BBF, 0x5148, 0x5E2B, 0x9577]:
                is_likely_name = True
            elif next_char in [0x3061, 0x304F]:  # ち or く
                is_likely_name = True
            elif next_char in [0x6559, 0x8B1B]:  # 教 or 講
                is_likely_name = True
        
        # 🔥 SMART HINT BACKTRACKING: Check if reading matches from the END
        final_kanji = kanji
        final_word_start = word_start
        
        if phoneme_root and not is_likely_name and len(kanji) > 1:
            MAX_BACKTRACK = min(10, len(kanji))
            
            for try_length in range(1, MAX_BACKTRACK + 1):
                try_start = len(kanji) - try_length
                if try_start < 0:
                    break
                
                kanji_substr = kanji[try_start:]
                
                # Try to match this kanji substring in the phoneme trie
                current = phoneme_root
                found_path = True
                
                for char in kanji_substr:
                    char_code = ord(char)
                    if char_code not in current.children:
                        found_path = False
                        break
                    current = current.children[char_code]
                
                # Check if we found a valid entry
                if found_path and current.phoneme is not None and current.phoneme != "":
                    # Found a match! Check if we need to split
                    if try_length < len(kanji):
                        # Split: add prefix as normal text
                        if try_start > 0:
                            segments.append(TextSegment(text=kanji[:try_start]))
                        final_kanji = kanji_substr
                        final_word_start = word_start + try_start
                        break
                    # If try_length == len(kanji), use the whole thing
                    break
        
        # Add the furigana segment
        segments.append(TextSegment(text=final_kanji, furigana_hint=reading))
        i = bracket_close + 1
    
    return segments


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
    """
    Convert with word segmentation, furigana hints, and detailed information
    
    Supports furigana hints: 健太「けんた」はバカ
    - Hint overrides dictionary lookup for that segment
    - Rest of text uses normal segmentation + conversion
    """
    # Parse furigana hints first with smart algorithms
    segments = parse_furigana_hints(text, segmenter, converter.root)
    
    # Process each segment
    all_matches = []
    all_unmatched = []
    phoneme_parts = []
    byte_offset = 0
    
    for segment in segments:
        if segment.furigana_hint:
            # Use the furigana hint for direct conversion
            hint_result = converter.convert_detailed(segment.furigana_hint)
            
            # Create a match for the original text with hint's phoneme
            if hint_result.phonemes:
                all_matches.append(Match(
                    original=segment.text,
                    phoneme=hint_result.phonemes,
                    start_index=byte_offset
                ))
                phoneme_parts.append(hint_result.phonemes)
            
            byte_offset += len(segment.text.encode('utf-8'))
        else:
            # Normal segmentation + conversion
            words = segmenter.segment(segment.text)
            
            for word in words:
                word_result = converter.convert_detailed(word)
                
                # Adjust match positions
                for match in word_result.matches:
                    match.start_index += byte_offset
                    all_matches.append(match)
                
                phoneme_parts.append(word_result.phonemes)
                all_unmatched.extend(word_result.unmatched)
                byte_offset += len(word.encode('utf-8'))
    
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
    
    # Initialize converter and load dictionary
    # 🚀 Try binary trie first (100x faster!), fallback to JSON
    converter = PhonemeConverter()
    loaded_binary = False
    
    # Try simple binary format (direct load into TrieNode)
    if converter.try_load_binary_format('japanese.trie'):
        loaded_binary = True
        print('   💡 Binary format loaded directly into TrieNode')
    else:
        # Fallback to JSON
        if not os.path.exists('ja_phonemes.json'):
            print('❌ Error: Neither japanese.trie nor ja_phonemes.json found')
            print('   Please ensure a phoneme dictionary is present.')
            sys.exit(1)
        
        print('   ⚠️  Binary trie not found, loading JSON...')
        converter.load_from_json('ja_phonemes.json')
    
    # Initialize word segmenter if enabled
    segmenter = None
    if USE_WORD_SEGMENTATION:
        # If using binary format, words are already loaded in converter's trie!
        # We still need to create a WordSegmenter that uses the converter's trie
        if loaded_binary:
            print('   💡 Word segmentation: Words already in TrieNode from binary format')
            # Create a WordSegmenter - it will use converter's root for segmentation
            segmenter = WordSegmenter()
            # The segmenter will use converter.root for lookups
            segmenter.root = converter.root
            segmenter.word_count = converter.entry_count
        else:
            # Load separate word file for JSON mode
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

