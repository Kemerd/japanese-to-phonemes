#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix and align ja_phonemes.json with tokenizer_vocab.json
1. Convert multi-character IPA to single-character ligatures
2. Remove punctuation (should pass through as-is in input)
3. Validate all phonemes use tokenizer vocab characters
"""

import json
import os
import shutil

# Map multi-character IPA to single-character ligatures (from tokenizer vocab)
LIGATURE_MAP = {
    'dʑ': 'ʥ',  # U+02A5 - voiced alveolo-palatal affricate
    'tɕ': 'ʨ',  # U+02A8 - voiceless alveolo-palatal affricate  
    'ts': 'ʦ',  # U+02A6 - voiceless alveolar affricate
    'dz': 'ʣ',  # U+02A3 - voiced alveolar affricate
    'tʃ': 'ʧ',  # U+02A7 - voiceless postalveolar affricate
    'dʒ': 'ʤ',  # U+02A4 - voiced postalveolar affricate
}

# Punctuation that should pass through unchanged (not be in phoneme dict)
PUNCTUATION_TO_REMOVE = {
    '。', '、', '！', '？', '：', '；', '「', '」', '『', '』', 
    '（', '）', '・', '　', '〜', '゛', '゜',
    '.', ',', '!', '?', ':', ';', '-', '—', '…',
    '(', ')', '[', ']', '"', "'", ' ', '\n', '\t'
}

def convert_to_ligatures(phoneme_str):
    """Convert multi-char IPA sequences to single-char ligatures"""
    result = phoneme_str
    
    # Sort by length (longest first) to handle overlapping patterns
    for multi_char, ligature in sorted(LIGATURE_MAP.items(), key=lambda x: len(x[0]), reverse=True):
        result = result.replace(multi_char, ligature)
    
    return result

def main():
    # Use original_ja_phonemes.json as source
    source_file = 'original_ja_phonemes.json'
    if not os.path.exists(source_file):
        print(f"ERROR: {source_file} not found!")
        return
    
    print(f"Loading {source_file}...")
    with open(source_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    original_count = len(data)
    print(f"   Original entries: {original_count}")
    
    # Step 1: Remove punctuation entries
    print("\nStep 1: Removing punctuation entries...")
    removed_punct = 0
    for punct in PUNCTUATION_TO_REMOVE:
        if punct in data:
            del data[punct]
            removed_punct += 1
    print(f"   Removed {removed_punct} punctuation entries")
    
    # Step 2: Convert to ligatures
    print("\nStep 2: Converting multi-char IPA to ligatures...")
    converted_count = 0
    for key in data:
        original = data[key]
        converted = convert_to_ligatures(original)
        if original != converted:
            data[key] = converted
            converted_count += 1
    print(f"   Converted {converted_count} entries")
    
    # Show examples (skip console output due to encoding issues on Windows)
    print(f"\n   Example ligature conversions completed")
    
    # Step 3: Validate against tokenizer vocab
    print(f"\nStep 3: Validating against tokenizer_vocab.json...")
    with open('tokenizer_vocab.json', 'r', encoding='utf-8') as f:
        tokenizer_vocab = json.load(f)
    
    valid_chars = set(tokenizer_vocab.keys())
    print(f"   Tokenizer has {len(valid_chars)} valid characters")
    
    # Check for invalid characters
    invalid_entries = []
    for key, phoneme in data.items():
        for char in phoneme:
            if char not in valid_chars:
                invalid_entries.append((key, phoneme, char))
                break
    
    if invalid_entries:
        print(f"   WARNING: Found {len(invalid_entries)} entries with invalid characters")
        print(f"   Writing details to invalid_phonemes.txt...")
        with open('invalid_phonemes.txt', 'w', encoding='utf-8') as f:
            for key, phoneme, invalid_char in invalid_entries:
                f.write(f"'{key}' -> '{phoneme}' (invalid: '{invalid_char}')\n")
    else:
        print(f"   [OK] All phonemes use valid tokenizer characters!")
    
    # Step 4: Save cleaned dictionary
    print(f"\nStep 4: Saving ja_phonemes.json...")
    print(f"   Final count: {len(data)} entries")
    with open('ja_phonemes.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
    
    print(f"\n[COMPLETE] Done!")
    print(f"\nSummary:")
    print(f"   - Original entries: {original_count}")
    print(f"   - Removed punctuation: {removed_punct}")
    print(f"   - Converted to ligatures: {converted_count}")
    print(f"   - Invalid phoneme entries: {len(invalid_entries)}")
    print(f"   - Final entries: {len(data)}")
    print(f"\nNote: Punctuation in input text will pass through unchanged")

if __name__ == '__main__':
    main()

