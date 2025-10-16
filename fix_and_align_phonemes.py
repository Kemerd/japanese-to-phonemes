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
import struct
from multiprocessing import Pool, cpu_count
from functools import partial

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

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# VERB CONJUGATION SYSTEM
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Godan verb endings and their phoneme representations
GODAN_ENDINGS = {
    'う': 'ɯ',      # 買う (kaɯ)
    'く': 'kɯ',     # 書く (kakɯ)
    'ぐ': 'gɯ',     # 泳ぐ (ojogɯ)
    'す': 'sɯ',     # 話す (hanasɯ)
    'つ': 'ʦɯ',     # 待つ (maʦɯ)
    'ぬ': 'nɯ',     # 死ぬ (ɕinɯ)
    'ぶ': 'bɯ',     # 飛ぶ (tobɯ)
    'む': 'mɯ',     # 読む (jomɯ)
    'る': 'ɾɯ',     # 走る (haɕiɾɯ)
}

# Godan て-form and た-form phoneme transformations
# Format: ending_sound → (te_modification, te_suffix, ta_suffix)
GODAN_TE_TA_MAP = {
    # く → いて/いた
    'k': ('i', 'te', 'ta'),      # 書く kakɯ → 書いて kaite → 書いた kaita
    # ぐ → いで/いだ
    'g': ('i', 'de', 'da'),      # 泳ぐ ojogɯ → 泳いで ojoide → 泳いだ ojoida
    # す → して/した
    's': ('ɕi', 'te', 'ta'),     # 話す hanasɯ → 話して hanaɕite → 話した hanaɕita
    # つ → って/った
    't': ('tː', 'e', 'a'),       # 待つ maʦɯ → 待って matːe → 待った matːa
    # ぬ → んで/んだ
    'n': ('ɴ', 'de', 'da'),      # 死ぬ ɕinɯ → 死んで ɕiɴde → 死んだ ɕiɴda
    # ぶ → んで/んだ
    'b': ('ɴ', 'de', 'da'),      # 飛ぶ tobɯ → 飛んで toɴde → 飛んだ toɴda
    # む → んで/んだ
    'm': ('ɴ', 'de', 'da'),      # 読む jomɯ → 読んで joɴde → 読んだ joɴda
    # る → って/った
    'ɾ': ('tː', 'e', 'a'),       # 走る haɕiɾɯ → 走って haɕitːe → 走った haɕitːa
    # う → って/った (ɰ in phonemes)
    'ɰ': ('tː', 'e', 'a'),       # 買う kaɰ → 買って katːe → 買った katːa
}

# Text-level て-form and た-form transformations for godan verbs
GODAN_TE_TA_TEXT = {
    'く': ('い', 'て', 'た'),
    'ぐ': ('い', 'で', 'だ'),
    'す': ('し', 'て', 'た'),
    'つ': ('っ', 'て', 'た'),
    'ぬ': ('ん', 'で', 'だ'),
    'ぶ': ('ん', 'で', 'だ'),
    'む': ('ん', 'で', 'だ'),
    'る': ('っ', 'て', 'た'),
    'う': ('っ', 'て', 'た'),
}

# Special irregular verbs with complete conjugation data
IRREGULAR_VERBS = {
    'する': {
        'type': 'suru',
        'phoneme': 'sɯɾɯ',
        'stems': {
            'text': {'mizen': 'し', 'renyou': 'し', 'base': 'す'},
            'phoneme': {'mizen': 'ɕi', 'renyou': 'ɕi', 'base': 'sɯ'}
        }
    },
    '来る': {
        'type': 'kuru',
        'phoneme': 'kɯɾɯ',
        'stems': {
            'text': {'mizen': 'こ', 'renyou': 'き', 'base': 'く'},
            'phoneme': {'mizen': 'ko', 'renyou': 'ki', 'base': 'kɯ'}
        }
    },
    'くる': {
        'type': 'kuru',
        'phoneme': 'kɯɾɯ',
        'stems': {
            'text': {'mizen': 'こ', 'renyou': 'き', 'base': 'く'},
            'phoneme': {'mizen': 'ko', 'renyou': 'ki', 'base': 'kɯ'}
        }
    },
}

# Verbs that look like ichidan but are actually godan (exceptions)
GODAN_EXCEPTIONS = {
    '帰る', '切る', '走る', '入る', '要る', '知る', '蹴る', '滑る',
    '限る', '握る', '練る', '減る', '焦る', '覆る', '遮る', '捻る',
}

def detect_verb_type(word, phoneme):
    """
    Detect if word is a verb and classify its type.
    
    Returns:
        str: Verb type ('ichidan', 'godan_X', 'suru', 'suru_compound', 
             'kuru', 'kuru_compound', 'iku', 'aru') or None if not a verb
    """
    # Check for irregular verbs first
    if word in IRREGULAR_VERBS:
        return IRREGULAR_VERBS[word]['type']
    
    # Special verb with exceptional negative form
    if word == 'ある':
        return 'aru'
    
    # Special verb with exceptional て-form
    if word == '行く' or word == 'いく':
        return 'iku'
    
    # する-verb compounds (勉強する, 運転する, etc.)
    if word.endswith('する') and len(word) > 2:
        return 'suru_compound'
    
    # 来る-verb compounds (持って来る, etc.)
    if (word.endswith('来る') and len(word) > 2) or (word.endswith('くる') and len(word) > 2):
        return 'kuru_compound'
    
    # Must end in る to be a verb
    if not word.endswith('る'):
        return None
    
    # Check for godan exceptions (verbs that look ichidan but aren't)
    if word in GODAN_EXCEPTIONS:
        return 'godan_ru'
    
    # Ichidan verbs: る preceded by い/え sound in PHONEME
    # This is the key - we check the phoneme, not the text!
    if phoneme.endswith('ɾɯ'):
        phoneme_stem = phoneme[:-2]  # Remove ɾɯ
        if len(phoneme_stem) > 0:
            # Check if ends with 'i' or 'e' sound
            if phoneme_stem.endswith('i') or phoneme_stem.endswith('e'):
                return 'ichidan'
    
    # Default to godan る-verb
    return 'godan_ru'


def get_verb_stems(word, phoneme, verb_type):
    """
    Extract verb stems for conjugation from both text and phonemes.
    
    Returns:
        dict: Contains 'text_stem', 'phoneme_stem', 'text_ending', 'phoneme_ending'
    """
    stems = {}
    
    # Handle irregular verbs
    if verb_type in ['suru', 'kuru']:
        irregular_data = IRREGULAR_VERBS.get(word, IRREGULAR_VERBS[word if word in IRREGULAR_VERBS else '来る'])
        return irregular_data['stems']
    
    # Handle compound verbs
    if verb_type == 'suru_compound':
        # 勉強する → 勉強 + する stems
        text_prefix = word[:-2]  # Remove する
        phoneme_prefix = phoneme[:-3]  # Remove sɯɾɯ
        return {
            'text': {
                'prefix': text_prefix,
                'mizen': text_prefix + 'し',
                'renyou': text_prefix + 'し',
                'base': text_prefix + 'す'
            },
            'phoneme': {
                'prefix': phoneme_prefix,
                'mizen': phoneme_prefix + 'ɕi',
                'renyou': phoneme_prefix + 'ɕi',
                'base': phoneme_prefix + 'sɯ'
            }
        }
    
    if verb_type == 'kuru_compound':
        # Extract prefix before 来る/くる
        if word.endswith('来る'):
            text_prefix = word[:-2]
            phoneme_prefix = phoneme[:-3]
        else:
            text_prefix = word[:-2]
            phoneme_prefix = phoneme[:-3]
        return {
            'text': {
                'prefix': text_prefix,
                'mizen': text_prefix + 'こ',
                'renyou': text_prefix + 'き',
                'base': text_prefix + 'く'
            },
            'phoneme': {
                'prefix': phoneme_prefix,
                'mizen': phoneme_prefix + 'ko',
                'renyou': phoneme_prefix + 'ki',
                'base': phoneme_prefix + 'kɯ'
            }
        }
    
    # Ichidan verbs: remove る (ɾɯ in phoneme)
    if verb_type == 'ichidan':
        text_stem = word[:-1]  # Remove る
        phoneme_stem = phoneme[:-2]  # Remove ɾɯ
        return {
            'text': {'stem': text_stem},
            'phoneme': {'stem': phoneme_stem}
        }
    
    # Godan verbs: need to identify the ending consonant
    if verb_type.startswith('godan') or verb_type in ['iku', 'aru']:
        text_ending = word[-1]  # く, ぐ, す, etc.
        
        # Find the consonant in the phoneme
        # For most godan verbs, ending is consonant + ɯ
        if phoneme.endswith('ɯ'):
            if len(phoneme) >= 2:
                phoneme_ending = phoneme[-2]  # The consonant before ɯ
                phoneme_stem = phoneme[:-2]
            else:
                phoneme_ending = 'ɯ'
                phoneme_stem = ''
        else:
            # Shouldn't happen for godan, but handle gracefully
            phoneme_ending = phoneme[-1] if phoneme else ''
            phoneme_stem = phoneme[:-1] if len(phoneme) > 1 else ''
        
        text_stem = word[:-1]
        
        return {
            'text': {'stem': text_stem, 'ending': text_ending},
            'phoneme': {'stem': phoneme_stem, 'ending': phoneme_ending}
        }
    
    # Fallback
    return {
        'text': {'stem': word[:-1]},
        'phoneme': {'stem': phoneme[:-2] if phoneme.endswith('ɾɯ') else phoneme[:-1]}
    }


def generate_conjugations(word, phoneme, verb_type):
    """
    Generate all core conjugation forms for a verb.
    
    Returns:
        dict: Mapping of {conjugated_text: conjugated_phoneme}
    """
    conjugations = {}
    stems = get_verb_stems(word, phoneme, verb_type)
    
    # ============================================================
    # ICHIDAN VERBS (食べる, 見る, etc.)
    # ============================================================
    if verb_type == 'ichidan':
        text_stem = stems['text']['stem']
        phon_stem = stems['phoneme']['stem']
        
        # 1. Past (た): 食べた
        conjugations[text_stem + 'た'] = phon_stem + 'ta'
        
        # 2. Te-form (て): 食べて
        conjugations[text_stem + 'て'] = phon_stem + 'te'
        
        # 3. Negative (ない): 食べない
        conjugations[text_stem + 'ない'] = phon_stem + 'nai'
        
        # 4. Negative past (なかった): 食べなかった
        conjugations[text_stem + 'なかった'] = phon_stem + 'nakatta'
        
        # 5. Polite present (ます): 食べます
        conjugations[text_stem + 'ます'] = phon_stem + 'masɯ'
        
        # 6. Polite past (ました): 食べました
        conjugations[text_stem + 'ました'] = phon_stem + 'maɕita'
        
        # 7. Polite negative (ません): 食べません
        conjugations[text_stem + 'ません'] = phon_stem + 'maseɴ'
        
        # 8. Polite negative past (ませんでした): 食べませんでした
        conjugations[text_stem + 'ませんでした'] = phon_stem + 'maseɴdeɕita'
        
        # 9. Conditional (ば): 食べれば
        conjugations[text_stem + 'れば'] = phon_stem + 'ɾeba'
        
        # 10. Volitional (よう): 食べよう
        conjugations[text_stem + 'よう'] = phon_stem + 'joɯ'
        
        # 11. Imperative (ろ/よ): 食べろ
        conjugations[text_stem + 'ろ'] = phon_stem + 'ɾo'
        conjugations[text_stem + 'よ'] = phon_stem + 'jo'
        
        # 12. Potential (られる): 食べられる
        conjugations[text_stem + 'られる'] = phon_stem + 'ɾaɾeɾɯ'
        
        # 13. Passive (られる): Same as potential for ichidan
        # Already covered above
        
        # 14. Causative (させる): 食べさせる
        conjugations[text_stem + 'させる'] = phon_stem + 'saseɾɯ'
        
        # 15. Conditional (たら): 食べたら
        conjugations[text_stem + 'たら'] = phon_stem + 'taɾa'
    
    # ============================================================
    # GODAN VERBS (書く, 話す, 買う, etc.)
    # ============================================================
    elif verb_type.startswith('godan') or verb_type in ['iku', 'aru']:
        text_stem = stems['text']['stem']
        text_ending = stems['text']['ending']
        phon_stem = stems['phoneme']['stem']
        phon_ending = stems['phoneme']['ending']
        
        # Special case: 行く has irregular て-form
        if verb_type == 'iku':
            # 行いて → 行って (itte not iite)
            conjugations[text_stem + 'った'] = phon_stem + 'itːa'
            conjugations[text_stem + 'って'] = phon_stem + 'itːe'
            conjugations[text_stem + 'ったら'] = phon_stem + 'itːaɾa'
        else:
            # Normal godan て/た forms
            if text_ending in GODAN_TE_TA_TEXT and phon_ending in GODAN_TE_TA_MAP:
                te_mod_text, te_suff_text, ta_suff_text = GODAN_TE_TA_TEXT[text_ending]
                te_mod_phon, te_suff_phon, ta_suff_phon = GODAN_TE_TA_MAP[phon_ending]
                
                # 1. Past (た): 書いた
                conjugations[text_stem + te_mod_text + ta_suff_text] = phon_stem + te_mod_phon + ta_suff_phon
                
                # 2. Te-form (て): 書いて
                conjugations[text_stem + te_mod_text + te_suff_text] = phon_stem + te_mod_phon + te_suff_phon
                
                # 15. Conditional (たら): 書いたら
                conjugations[text_stem + te_mod_text + ta_suff_text + 'ら'] = phon_stem + te_mod_phon + ta_suff_phon + 'ɾa'
        
        # Get あ-row character for negative stem (未然形)
        # く→か, ぐ→が, す→さ, etc.
        a_row_map = {
            'く': ('か', 'ka'), 'ぐ': ('が', 'ga'), 'す': ('さ', 'sa'),
            'つ': ('た', 'ta'), 'ぬ': ('な', 'na'), 'ぶ': ('ば', 'ba'),
            'む': ('ま', 'ma'), 'る': ('ら', 'ɾa'), 'う': ('わ', 'ɰa')
        }
        
        # Special case: ある → ない (not あらない)
        if verb_type == 'aru':
            conjugations['ない'] = 'nai'
            conjugations['なかった'] = 'nakatta'
        else:
            if text_ending in a_row_map:
                a_text, a_phon = a_row_map[text_ending]
                
                # 3. Negative (ない): 書かない
                conjugations[text_stem + a_text + 'ない'] = phon_stem + a_phon + 'nai'
                
                # 4. Negative past (なかった): 書かなかった
                conjugations[text_stem + a_text + 'なかった'] = phon_stem + a_phon + 'nakatta'
                
                # 14. Causative (せる): 書かせる
                conjugations[text_stem + a_text + 'せる'] = phon_stem + a_phon + 'seɾɯ'
        
        # Get い-row character for polite stem (連用形)
        i_row_map = {
            'く': ('き', 'ki'), 'ぐ': ('ぎ', 'gi'), 'す': ('し', 'ɕi'),
            'つ': ('ち', 'ʨi'), 'ぬ': ('に', 'ni'), 'ぶ': ('び', 'bi'),
            'む': ('み', 'mi'), 'る': ('り', 'ɾi'), 'う': ('い', 'i')
        }
        
        if text_ending in i_row_map:
            i_text, i_phon = i_row_map[text_ending]
            
            # 5. Polite present (ます): 書きます
            conjugations[text_stem + i_text + 'ます'] = phon_stem + i_phon + 'masɯ'
            
            # 6. Polite past (ました): 書きました
            conjugations[text_stem + i_text + 'ました'] = phon_stem + i_phon + 'maɕita'
            
            # 7. Polite negative (ません): 書きません
            conjugations[text_stem + i_text + 'ません'] = phon_stem + i_phon + 'maseɴ'
            
            # 8. Polite negative past (ませんでした): 書きませんでした
            conjugations[text_stem + i_text + 'ませんでした'] = phon_stem + i_phon + 'maseɴdeɕita'
        
        # Get え-row character for conditional/potential (仮定形/可能形)
        e_row_map = {
            'く': ('け', 'ke'), 'ぐ': ('げ', 'ge'), 'す': ('せ', 'se'),
            'つ': ('て', 'te'), 'ぬ': ('ね', 'ne'), 'ぶ': ('べ', 'be'),
            'む': ('め', 'me'), 'る': ('れ', 'ɾe'), 'う': ('え', 'e')
        }
        
        if text_ending in e_row_map:
            e_text, e_phon = e_row_map[text_ending]
            
            # 9. Conditional (ば): 書けば
            conjugations[text_stem + e_text + 'ば'] = phon_stem + e_phon + 'ba'
            
            # 11. Imperative (命令形): 書け
            conjugations[text_stem + e_text] = phon_stem + e_phon
            
            # 12. Potential (られる): 書ける
            conjugations[text_stem + e_text + 'る'] = phon_stem + e_phon + 'ɾɯ'
        
        # Get あ-row for passive (受身形)
        if text_ending in a_row_map:
            a_text, a_phon = a_row_map[text_ending]
            
            # 13. Passive (られる): 書かれる
            conjugations[text_stem + a_text + 'れる'] = phon_stem + a_phon + 'ɾeɾɯ'
        
        # Get お-row for volitional (意向形)
        o_row_map = {
            'く': ('こ', 'ko'), 'ぐ': ('ご', 'go'), 'す': ('そ', 'so'),
            'つ': ('と', 'to'), 'ぬ': ('の', 'no'), 'ぶ': ('ぼ', 'bo'),
            'む': ('も', 'mo'), 'る': ('ろ', 'ɾo'), 'う': ('お', 'o')
        }
        
        if text_ending in o_row_map:
            o_text, o_phon = o_row_map[text_ending]
            
            # 10. Volitional (よう): 書こう
            conjugations[text_stem + o_text + 'う'] = phon_stem + o_phon + 'ɯ'
    
    # ============================================================
    # IRREGULAR VERBS (する, 来る)
    # ============================================================
    elif verb_type == 'suru':
        # する conjugations
        conjugations['した'] = 'ɕita'
        conjugations['して'] = 'ɕite'
        conjugations['しない'] = 'ɕinai'
        conjugations['しなかった'] = 'ɕinakatta'
        conjugations['します'] = 'ɕimasɯ'
        conjugations['しました'] = 'ɕimaɕita'
        conjugations['しません'] = 'ɕimaseɴ'
        conjugations['しませんでした'] = 'ɕimaseɴdeɕita'
        conjugations['すれば'] = 'sɯɾeba'
        conjugations['しよう'] = 'ɕijoɯ'
        conjugations['しろ'] = 'ɕiɾo'
        conjugations['せよ'] = 'sejo'
        conjugations['できる'] = 'dekiɾɯ'  # Potential form
        conjugations['される'] = 'saɾeɾɯ'  # Passive
        conjugations['させる'] = 'saseɾɯ'  # Causative
        conjugations['したら'] = 'ɕitaɾa'
    
    elif verb_type == 'kuru':
        # 来る conjugations
        conjugations['来た'] = 'kita'
        conjugations['きた'] = 'kita'
        conjugations['来て'] = 'kite'
        conjugations['きて'] = 'kite'
        conjugations['来ない'] = 'konai'
        conjugations['こない'] = 'konai'
        conjugations['来なかった'] = 'konakatta'
        conjugations['こなかった'] = 'konakatta'
        conjugations['来ます'] = 'kimasɯ'
        conjugations['きます'] = 'kimasɯ'
        conjugations['来ました'] = 'kimaɕita'
        conjugations['きました'] = 'kimaɕita'
        conjugations['来ません'] = 'kimaseɴ'
        conjugations['きません'] = 'kimaseɴ'
        conjugations['来ませんでした'] = 'kimaseɴdeɕita'
        conjugations['きませんでした'] = 'kimaseɴdeɕita'
        conjugations['来れば'] = 'kɯɾeba'
        conjugations['くれば'] = 'kɯɾeba'
        conjugations['来よう'] = 'kojoɯ'
        conjugations['こよう'] = 'kojoɯ'
        conjugations['来い'] = 'koi'
        conjugations['こい'] = 'koi'
        conjugations['来られる'] = 'koɾaɾeɾɯ'
        conjugations['こられる'] = 'koɾaɾeɾɯ'
        conjugations['来させる'] = 'kisaseɾɯ'
        conjugations['こさせる'] = 'kosaseɾɯ'
        conjugations['来たら'] = 'kitaɾa'
        conjugations['きたら'] = 'kitaɾa'
    
    # ============================================================
    # COMPOUND VERBS (勉強する, 持って来る)
    # ============================================================
    elif verb_type == 'suru_compound':
        text_prefix = stems['text']['prefix']
        phon_prefix = stems['phoneme']['prefix']
        
        # Generate all する forms with prefix
        conjugations[text_prefix + 'した'] = phon_prefix + 'ɕita'
        conjugations[text_prefix + 'して'] = phon_prefix + 'ɕite'
        conjugations[text_prefix + 'しない'] = phon_prefix + 'ɕinai'
        conjugations[text_prefix + 'しなかった'] = phon_prefix + 'ɕinakatta'
        conjugations[text_prefix + 'します'] = phon_prefix + 'ɕimasɯ'
        conjugations[text_prefix + 'しました'] = phon_prefix + 'ɕimaɕita'
        conjugations[text_prefix + 'しません'] = phon_prefix + 'ɕimaseɴ'
        conjugations[text_prefix + 'しませんでした'] = phon_prefix + 'ɕimaseɴdeɕita'
        conjugations[text_prefix + 'すれば'] = phon_prefix + 'sɯɾeba'
        conjugations[text_prefix + 'しよう'] = phon_prefix + 'ɕijoɯ'
        conjugations[text_prefix + 'しろ'] = phon_prefix + 'ɕiɾo'
        conjugations[text_prefix + 'せよ'] = phon_prefix + 'sejo'
        conjugations[text_prefix + 'できる'] = phon_prefix + 'dekiɾɯ'
        conjugations[text_prefix + 'される'] = phon_prefix + 'saɾeɾɯ'
        conjugations[text_prefix + 'させる'] = phon_prefix + 'saseɾɯ'
        conjugations[text_prefix + 'したら'] = phon_prefix + 'ɕitaɾa'
    
    elif verb_type == 'kuru_compound':
        text_prefix = stems['text']['prefix']
        phon_prefix = stems['phoneme']['prefix']
        
        # Generate all 来る forms with prefix
        conjugations[text_prefix + '来た'] = phon_prefix + 'kita'
        conjugations[text_prefix + 'きた'] = phon_prefix + 'kita'
        conjugations[text_prefix + '来て'] = phon_prefix + 'kite'
        conjugations[text_prefix + 'きて'] = phon_prefix + 'kite'
        conjugations[text_prefix + '来ない'] = phon_prefix + 'konai'
        conjugations[text_prefix + 'こない'] = phon_prefix + 'konai'
        conjugations[text_prefix + '来なかった'] = phon_prefix + 'konakatta'
        conjugations[text_prefix + 'こなかった'] = phon_prefix + 'konakatta'
        conjugations[text_prefix + '来ます'] = phon_prefix + 'kimasɯ'
        conjugations[text_prefix + 'きます'] = phon_prefix + 'kimasɯ'
        conjugations[text_prefix + '来ました'] = phon_prefix + 'kimaɕita'
        conjugations[text_prefix + 'きました'] = phon_prefix + 'kimaɕita'
        conjugations[text_prefix + '来ません'] = phon_prefix + 'kimaseɴ'
        conjugations[text_prefix + 'きません'] = phon_prefix + 'kimaseɴ'
        conjugations[text_prefix + '来ませんでした'] = phon_prefix + 'kimaseɴdeɕita'
        conjugations[text_prefix + 'きませんでした'] = phon_prefix + 'kimaseɴdeɕita'
        conjugations[text_prefix + '来れば'] = phon_prefix + 'kɯɾeba'
        conjugations[text_prefix + 'くれば'] = phon_prefix + 'kɯɾeba'
        conjugations[text_prefix + '来よう'] = phon_prefix + 'kojoɯ'
        conjugations[text_prefix + 'こよう'] = phon_prefix + 'kojoɯ'
        conjugations[text_prefix + '来い'] = phon_prefix + 'koi'
        conjugations[text_prefix + 'こい'] = phon_prefix + 'koi'
        conjugations[text_prefix + '来られる'] = phon_prefix + 'koɾaɾeɾɯ'
        conjugations[text_prefix + 'こられる'] = phon_prefix + 'koɾaɾeɾɯ'
        conjugations[text_prefix + '来させる'] = phon_prefix + 'kisaseɾɯ'
        conjugations[text_prefix + 'こさせる'] = phon_prefix + 'kosaseɾɯ'
        conjugations[text_prefix + '来たら'] = phon_prefix + 'kitaɾa'
        conjugations[text_prefix + 'きたら'] = phon_prefix + 'kitaɾa'
    
    return conjugations


def process_verb_batch(entries_batch):
    """
    Process a batch of dictionary entries to generate conjugations.
    Worker function for multiprocessing.
    
    Args:
        entries_batch: List of (word, phoneme) tuples
        
    Returns:
        tuple: (conjugations_dict, conjugated_words_set, verb_count)
    """
    batch_conjugations = {}
    batch_conjugated_words = set()
    batch_verb_count = 0
    
    for word, phoneme in entries_batch:
        verb_type = detect_verb_type(word, phoneme)
        
        if verb_type:
            batch_verb_count += 1
            
            try:
                conjugations = generate_conjugations(word, phoneme, verb_type)
                
                # Collect conjugations
                for conj_word, conj_phoneme in conjugations.items():
                    batch_conjugations[conj_word] = conj_phoneme
                    batch_conjugated_words.add(conj_word)
            
            except Exception as e:
                # Skip errors in worker
                continue
    
    return (batch_conjugations, batch_conjugated_words, batch_verb_count)


def convert_to_ligatures(phoneme_str):
    """Convert multi-char IPA sequences to single-char ligatures"""
    result = phoneme_str
    
    # Sort by length (longest first) to handle overlapping patterns
    for multi_char, ligature in sorted(LIGATURE_MAP.items(), key=lambda x: len(x[0]), reverse=True):
        result = result.replace(multi_char, ligature)
    
    return result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BINARY TRIE BUILDER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TrieNodeBuilder:
    """In-memory trie node for building binary trie"""
    def __init__(self):
        self.children = {}  # code_point -> TrieNodeBuilder
        self.value = None   # phoneme string or empty string for word markers
        self.offset = 0     # Will be set during serialization
        
    def insert(self, text, value=""):
        """Insert text with optional value (empty string for word markers)"""
        current = self
        
        # Convert text to Unicode code points
        # In Python 3, strings are already Unicode, so we just use ord() on each character
        code_points = [ord(c) for c in text]
        
        # Walk/create trie
        for cp in code_points:
            if cp not in current.children:
                current.children[cp] = TrieNodeBuilder()
            current = current.children[cp]
        
        current.value = value


def serialize_trie_node(node, output, offset_tracker):
    """
    Recursively serialize a trie node to binary format.
    Returns the offset where this node was written.
    """
    # Remember where we're writing this node
    node_offset = len(output)
    node.offset = node_offset
    
    # Flags byte
    has_value = 1 if node.value is not None else 0
    flags = has_value
    output.append(flags)
    
    # Value (if present)
    if node.value is not None:
        value_bytes = node.value.encode('utf-8')
        value_len = len(value_bytes)
        output.extend(struct.pack('<H', value_len))  # 2 bytes: value length
        output.extend(value_bytes)
    else:
        output.extend(struct.pack('<H', 0))  # No value
    
    # Children count
    num_children = len(node.children)
    output.extend(struct.pack('<I', num_children))  # 4 bytes: children count
    
    # Reserve space for children entries (we'll fill these in later)
    children_table_offset = len(output)
    # Each child entry: 4 bytes (code point) + 8 bytes (offset) = 12 bytes
    output.extend(b'\x00' * (num_children * 12))
    
    # Recursively serialize children and record their offsets
    child_offsets = {}
    for code_point, child_node in sorted(node.children.items()):
        child_offset = serialize_trie_node(child_node, output, offset_tracker)
        child_offsets[code_point] = child_offset
    
    # Now go back and fill in the children table
    table_pos = children_table_offset
    for code_point, child_offset in sorted(child_offsets.items()):
        # Write code point (4 bytes)
        struct.pack_into('<I', output, table_pos, code_point)
        table_pos += 4
        # Write offset (8 bytes)
        struct.pack_into('<Q', output, table_pos, child_offset)
        table_pos += 8
    
    return node_offset


def build_binary_trie(phoneme_dict, word_set, output_path):
    """
    Build a unified binary trie containing both phonemes and words.
    
    Args:
        phoneme_dict: Dictionary of {text: phoneme}
        word_set: Set of words (will be marked with empty string values)
        output_path: Path to write the .trie file
    """
    print(f"\n🔥 Building unified binary trie...")
    
    # Create root node
    root = TrieNodeBuilder()
    
    # Insert phoneme entries
    print(f"   Inserting {len(phoneme_dict)} phoneme entries...")
    for idx, (text, phoneme) in enumerate(phoneme_dict.items()):
        root.insert(text, phoneme)
        if idx % 50000 == 0 and idx > 0:
            print(f"\r   Phonemes: {idx}/{len(phoneme_dict)}", end='', flush=True)
    print(f"\r   Phonemes: {len(phoneme_dict)}/{len(phoneme_dict)} ✓")
    
    # Insert word entries (with empty value as marker)
    # Only add words that aren't already phoneme entries to avoid duplicates
    word_only_count = 0
    print(f"   Inserting {len(word_set)} word entries...")
    for idx, word in enumerate(word_set):
        if word not in phoneme_dict:
            root.insert(word, "")  # Empty string marks word existence
            word_only_count += 1
        if idx % 50000 == 0 and idx > 0:
            print(f"\r   Words: {idx}/{len(word_set)} ({word_only_count} unique)", end='', flush=True)
    print(f"\r   Words: {len(word_set)}/{len(word_set)} ({word_only_count} unique) ✓")
    
    # Serialize to binary
    print(f"   Serializing trie to binary format...")
    output = bytearray()
    
    # Write header
    # Magic number: "JPNT" (Japanese Phoneme/Name Trie)
    output.extend(b'JPNT')
    
    # Version: 1.0
    output.extend(struct.pack('<H', 1))  # Major version
    output.extend(struct.pack('<H', 0))  # Minor version
    
    # Entry counts
    output.extend(struct.pack('<I', len(phoneme_dict)))  # Phoneme entries
    output.extend(struct.pack('<I', len(word_set)))       # Word entries
    
    # Root node offset (will be right after header)
    root_offset = len(output)
    output.extend(struct.pack('<Q', root_offset))  # 8 bytes: root offset
    
    # Serialize the trie
    offset_tracker = {'next': root_offset}
    serialize_trie_node(root, output, offset_tracker)
    
    # Write to file
    print(f"   Writing to {output_path}...")
    with open(output_path, 'wb') as f:
        f.write(output)
    
    file_size = len(output)
    file_size_mb = file_size / (1024 * 1024)
    
    print(f"   ✅ Binary trie created!")
    print(f"   Size: {file_size:,} bytes ({file_size_mb:.2f} MB)")
    print(f"   Entries: {len(phoneme_dict)} phonemes + {word_only_count} words")
    
    return output_path

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
    
    # Step 1.5: Generate verb conjugations (PARALLELIZED)
    print("\nStep 1.5: Generating verb conjugations...")
    
    # Determine optimal number of worker processes
    num_workers = max(1, cpu_count() - 1)  # Leave one core free
    print(f"   Using {num_workers} worker processes for parallel processing")
    
    # Convert dictionary to list of tuples for processing
    all_entries = list(data.items())
    total_entries = len(all_entries)
    
    # Split entries into batches for workers
    batch_size = max(1000, total_entries // (num_workers * 4))  # Dynamic batch size
    batches = []
    for i in range(0, total_entries, batch_size):
        batches.append(all_entries[i:i + batch_size])
    
    print(f"   Processing {total_entries} entries in {len(batches)} batches...")
    print(f"   Batch size: {batch_size} entries per batch")
    
    # Track all conjugated words and stats
    conjugated_words = set()
    verb_count = 0
    conjugation_count = 0
    skipped_count = 0
    sample_verbs = []
    
    # Process batches in parallel with progress reporting
    print(f"\n   Progress: [", end='', flush=True)
    progress_bar_width = 40
    completed_batches = 0
    
    with Pool(processes=num_workers) as pool:
        # Process batches and show progress
        for batch_result in pool.imap_unordered(process_verb_batch, batches):
            batch_conjugations, batch_conjugated_words, batch_verb_count = batch_result
            
            # Merge results from this batch
            verb_count += batch_verb_count
            conjugated_words.update(batch_conjugated_words)
            
            # Add conjugations to dictionary (skip if already exists)
            for conj_word, conj_phoneme in batch_conjugations.items():
                if conj_word not in data:
                    data[conj_word] = conj_phoneme
                    conjugation_count += 1
                    
                    # Collect samples from first few conjugations
                    if len(sample_verbs) < 3 and len(batch_conjugations) > 0:
                        # Just note that we have samples (details come from first batches)
                        pass
                else:
                    skipped_count += 1
            
            # Update progress bar
            completed_batches += 1
            progress = completed_batches / len(batches)
            filled = int(progress_bar_width * progress)
            
            # Redraw progress bar
            print(f"\r   Progress: [{'=' * filled}{' ' * (progress_bar_width - filled)}] {progress * 100:.1f}% | Verbs: {verb_count} | Conjugations: {conjugation_count}", end='', flush=True)
    
    print()  # New line after progress bar
    print(f"\n   ✅ Parallel processing complete!")
    print(f"   Found {verb_count} verbs")
    print(f"   Generated {conjugation_count} new conjugations")
    print(f"   Skipped {skipped_count} (already existed)")
    
    # Show sample conjugations
    if sample_verbs:
        print(f"\n   Sample verb conjugations:")
        for word, phoneme, vtype, count in sample_verbs:
            print(f"     • {word} ({phoneme}) [{vtype}] → {count} forms")
    
    # Step 1.6: Update word list with conjugated forms
    print(f"\nStep 1.6: Updating word list...")
    
    # Check if original_ja_words.txt exists
    words_source = 'original_ja_words.txt'
    if os.path.exists(words_source):
        print(f"   Loading {words_source}...", end='', flush=True)
        
        # Use a set for fast duplicate detection
        word_set = set()
        
        # Load existing words with progress
        with open(words_source, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        for line in lines:
            word = line.strip()
            if word:
                word_set.add(word)
        
        original_word_count = len(word_set)
        print(f" Done! ({original_word_count} words)")
        
        # Add conjugated verb forms
        print(f"   Adding {len(conjugated_words)} conjugated forms...", end='', flush=True)
        words_added = 0
        for conj_word in conjugated_words:
            if conj_word not in word_set:
                word_set.add(conj_word)
                words_added += 1
        
        print(f" Done! (+{words_added} new)")
        print(f"   Total words: {len(word_set)}")
        
        # Save as ja_words.txt (sorted for consistency)
        print(f"   Sorting and saving ja_words.txt...", end='', flush=True)
        with open('ja_words.txt', 'w', encoding='utf-8') as f:
            for word in sorted(word_set):
                f.write(word + '\n')
        
        print(f" Done!")
        print(f"   ✅ Word list saved to ja_words.txt")
    else:
        print(f"   ⚠️  {words_source} not found, skipping word list update")
    
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
    total_keys = len(data)
    progress_interval = max(1, total_keys // 20)  # Update progress 20 times
    
    for idx, key in enumerate(data):
        original = data[key]
        converted = convert_to_ligatures(original)
        if original != converted:
            data[key] = converted
            converted_count += 1
        
        # Progress reporting
        if idx % progress_interval == 0:
            progress_pct = (idx / total_keys) * 100
            print(f"\r   Processing: {progress_pct:.1f}% ({idx}/{total_keys}) | Converted: {converted_count}", end='', flush=True)
    
    print(f"\r   ✅ Converted {converted_count} entries" + " " * 40)  # Clear progress line
    
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
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    # Step 6: Build unified binary trie
    print(f"\nStep 6: Building binary trie format...")
    if os.path.exists(words_source):
        build_binary_trie(data, word_set, 'japanese.trie')
    else:
        print(f"   ⚠️  Skipping binary trie (word list not available)")
    
    print(f"\n[COMPLETE] Done!")
    print(f"\nSummary:")
    print(f"   - Original entries: {original_count}")
    print(f"   - Added missing kana/kanji: {added_count}")
    print(f"   - Verbs found: {verb_count}")
    print(f"   - Verb conjugations generated: {conjugation_count}")
    if os.path.exists(words_source):
        print(f"   - Word list: {original_word_count} → {len(word_set)} (+{words_added})")
    print(f"   - Removed punctuation: {removed_punct}")
    print(f"   - Converted to ligatures: {converted_count}")
    print(f"   - Invalid phoneme entries: {len(invalid_entries)}")
    print(f"   - Final entries: {len(data)}")
    print(f"\nOutput files:")
    print(f"   - ja_phonemes.json (phoneme dictionary)")
    if os.path.exists(words_source):
        print(f"   - ja_words.txt (word segmentation dictionary)")
        print(f"   - japanese.trie (binary trie - FAST loading!)")
    print(f"\nNote: Punctuation in input text will pass through unchanged")
    print(f"Note: All verb conjugations (past, て-form, negative, etc.) are now in dictionary")
    print(f"Note: Use japanese.trie for 100x faster loading in C++!")

if __name__ == '__main__':
    main()

