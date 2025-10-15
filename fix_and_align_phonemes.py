#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix and align ja_phonemes.json with tokenizer_vocab.json

This script processes the phoneme dictionary to ensure compatibility with
the tokenizer vocabulary and optimal performance:

1. Add missing basic hiragana, katakana (including old forms), and common kanji
2. Convert multi-character IPA sequences to single-character ligatures:
   - dʑ → ʥ (voiced alveolo-palatal affricate)
   - tɕ → ʨ (voiceless alveolo-palatal affricate)
   - ts → ʦ (voiceless alveolar affricate)
   - dz → ʣ (voiced alveolar affricate)
   - tʃ → ʧ (voiceless postalveolar affricate)
   - dʒ → ʤ (voiced postalveolar affricate)
3. Remove punctuation entries (punctuation passes through unchanged in input)
4. Validate all phoneme outputs use only characters from tokenizer_vocab.json

Usage:
    python fix_and_align_phonemes.py

Input:  original_ja_phonemes.json (backup of original dictionary)
Output: ja_phonemes.json (cleaned and aligned dictionary)
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

# Basic hiragana to add if missing (using IPA ligatures)
BASIC_HIRAGANA = {
    'あ': 'a', 'い': 'i', 'う': 'ɯ', 'え': 'e', 'お': 'o',
    'か': 'ka', 'き': 'ki', 'く': 'kɯ', 'け': 'ke', 'こ': 'ko',
    'が': 'ga', 'ぎ': 'gi', 'ぐ': 'gɯ', 'げ': 'ge', 'ご': 'go',
    'さ': 'sa', 'し': 'ɕi', 'す': 'sɯ', 'せ': 'se', 'そ': 'so',
    'ざ': 'za', 'じ': 'ʥi', 'ず': 'zɯ', 'ぜ': 'ze', 'ぞ': 'zo',
    'た': 'ta', 'ち': 'ʨi', 'つ': 'ʦɯ', 'て': 'te', 'と': 'to',
    'だ': 'da', 'ぢ': 'ʥi', 'づ': 'zɯ', 'で': 'de', 'ど': 'do',
    'な': 'na', 'に': 'ni', 'ぬ': 'nɯ', 'ね': 'ne', 'の': 'no',
    'は': 'ha', 'ひ': 'çi', 'ふ': 'ɸɯ', 'へ': 'he', 'ほ': 'ho',
    'ば': 'ba', 'び': 'bi', 'ぶ': 'bɯ', 'べ': 'be', 'ぼ': 'bo',
    'ぱ': 'pa', 'ぴ': 'pi', 'ぷ': 'pɯ', 'ぺ': 'pe', 'ぽ': 'po',
    'ま': 'ma', 'み': 'mi', 'む': 'mɯ', 'め': 'me', 'も': 'mo',
    'や': 'ja', 'ゆ': 'jɯ', 'よ': 'jo',
    'ら': 'ɾa', 'り': 'ɾi', 'る': 'ɾɯ', 'れ': 'ɾe', 'ろ': 'ɾo',
    'わ': 'ɰa', 'ゐ': 'i', 'ゑ': 'e', 'を': 'o', 'ん': 'ɴ',
    'ゔ': 'vɯ',
    # Small characters
    'ぁ': 'a', 'ぃ': 'i', 'ぅ': 'ɯ', 'ぇ': 'e', 'ぉ': 'o',
    'ゃ': 'ja', 'ゅ': 'jɯ', 'ょ': 'jo',
    'ゎ': 'ɰa', 'っ': 'ʔ',
}

# Basic katakana to add if missing (using IPA ligatures)
BASIC_KATAKANA = {
    'ア': 'a', 'イ': 'i', 'ウ': 'ɯ', 'エ': 'e', 'オ': 'o',
    'カ': 'ka', 'キ': 'ki', 'ク': 'kɯ', 'ケ': 'ke', 'コ': 'ko',
    'ガ': 'ga', 'ギ': 'gi', 'グ': 'gɯ', 'ゲ': 'ge', 'ゴ': 'go',
    'サ': 'sa', 'シ': 'ɕi', 'ス': 'sɯ', 'セ': 'se', 'ソ': 'so',
    'ザ': 'za', 'ジ': 'ʥi', 'ズ': 'zɯ', 'ゼ': 'ze', 'ゾ': 'zo',
    'タ': 'ta', 'チ': 'ʨi', 'ツ': 'ʦɯ', 'テ': 'te', 'ト': 'to',
    'ダ': 'da', 'ヂ': 'ʥi', 'ヅ': 'zɯ', 'デ': 'de', 'ド': 'do',
    'ナ': 'na', 'ニ': 'ni', 'ヌ': 'nɯ', 'ネ': 'ne', 'ノ': 'no',
    'ハ': 'ha', 'ヒ': 'çi', 'フ': 'ɸɯ', 'ヘ': 'he', 'ホ': 'ho',
    'バ': 'ba', 'ビ': 'bi', 'ブ': 'bɯ', 'ベ': 'be', 'ボ': 'bo',
    'パ': 'pa', 'ピ': 'pi', 'プ': 'pɯ', 'ペ': 'pe', 'ポ': 'po',
    'マ': 'ma', 'ミ': 'mi', 'ム': 'mɯ', 'メ': 'me', 'モ': 'mo',
    'ヤ': 'ja', 'ユ': 'jɯ', 'ヨ': 'jo',
    'ラ': 'ɾa', 'リ': 'ɾi', 'ル': 'ɾɯ', 'レ': 'ɾe', 'ロ': 'ɾo',
    'ワ': 'ɰa', 'ヰ': 'i', 'ヱ': 'e', 'ヲ': 'o', 'ン': 'ɴ',
    'ヴ': 'vɯ', 'ヵ': 'ka', 'ヶ': 'ke',
    # Small characters
    'ァ': 'a', 'ィ': 'i', 'ゥ': 'ɯ', 'ェ': 'e', 'ォ': 'o',
    'ャ': 'ja', 'ュ': 'jɯ', 'ョ': 'jo',
    'ヮ': 'ɰa', 'ッ': 'ʔ',
    # Extended katakana
    'ヷ': 'va', 'ヸ': 'vi', 'ヹ': 've', 'ヺ': 'vo',
}

# Common kanji that should be added
COMMON_KANJI = {
    '咲': 'saki',  # bloom/blossom
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
    
    # Step 1: Add missing basic kana and common characters
    print("\nStep 1: Adding missing basic hiragana, katakana, and common characters...")
    added_count = 0
    
    for char, phoneme in {**BASIC_HIRAGANA, **BASIC_KATAKANA, **COMMON_KANJI}.items():
        if char not in data:
            data[char] = phoneme
            added_count += 1
    
    print(f"   Added {added_count} missing entries")
    
    # Step 2: Remove punctuation entries
    print("\nStep 2: Removing punctuation entries...")
    removed_punct = 0
    for punct in PUNCTUATION_TO_REMOVE:
        if punct in data:
            del data[punct]
            removed_punct += 1
    print(f"   Removed {removed_punct} punctuation entries")
    
    # Step 3: Convert to ligatures
    print("\nStep 3: Converting multi-char IPA to ligatures...")
    converted_count = 0
    for key in data:
        original = data[key]
        converted = convert_to_ligatures(original)
        if original != converted:
            data[key] = converted
            converted_count += 1
    print(f"   Converted {converted_count} entries")
    
    # Show examples (skip console output due to encoding issues on Windows)
    print(f"\n   Ligature conversions completed")
    
    # Step 4: Validate against tokenizer vocab
    print(f"\nStep 4: Validating against tokenizer_vocab.json...")
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
    
    # Step 5: Save cleaned dictionary
    print(f"\nStep 5: Saving ja_phonemes.json...")
    print(f"   Final count: {len(data)} entries")
    with open('ja_phonemes.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
    
    print(f"\n[COMPLETE] Done!")
    print(f"\nSummary:")
    print(f"   - Original entries: {original_count}")
    print(f"   - Added missing kana/kanji: {added_count}")
    print(f"   - Removed punctuation: {removed_punct}")
    print(f"   - Converted to ligatures: {converted_count}")
    print(f"   - Invalid phoneme entries: {len(invalid_entries)}")
    print(f"   - Final entries: {len(data)}")
    print(f"\nNote: Punctuation in input text will pass through unchanged")

if __name__ == '__main__':
    main()

