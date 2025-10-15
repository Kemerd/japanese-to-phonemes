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

