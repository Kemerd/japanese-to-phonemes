#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix and align ja_phonemes.json with tokenizer_vocab.json

This script processes the phoneme dictionary to ensure compatibility with
the tokenizer vocabulary and optimal performance:

0. Fix particle は pronunciations (ha -> wa) in compounds like では, これは, etc.
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
import re
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
# STANDALONE KANJI READING FIXES (kun-yomi for standalone kanji)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# When kanji appear by themselves, they typically use kun-yomi (native Japanese)
# rather than on-yomi (Chinese-derived readings). This fixes common mistakes.

STANDALONE_KANJI_FIXES = {
    # ============================================================
    # NATURE & ELEMENTS (水火山川 etc.)
    # ============================================================
    "水": "mizɯ",      # water (not "sɯi")
    "火": "hi",        # fire (not "ka")
    "山": "jama",      # mountain (not "saɴ")
    "川": "kaɰa",      # river (not "seɴ")
    "森": "moɾi",      # forest (not "ɕiɴ")
    "林": "hajaɕi",    # woods (not "ɾiɴ")
    "石": "iɕi",       # stone (not "seki")
    "岩": "iɰa",       # rock/boulder (not "gaɴ")
    "崖": "gake",      # cliff (not "gai")
    "谷": "tani",      # valley (not "koku")
    "峠": "toːge",     # mountain pass
    "峰": "mine",      # peak (not "hoː")
    "坂": "saka",      # slope/hill (not "haɴ")
    "丘": "oka",       # hill (not "kjɯː")
    "野": "no",        # field/plain (not "ja")
    "原": "haɾa",      # field/plain (not "geɴ")
    "砂": "sɯna",      # sand (not "sa")
    "泥": "doɾo",      # mud (not "dei")
    "塵": "tɕiɾi",     # dust (not "ʥiɴ")
    "土": "tsɯʨi",     # soil/earth
    "地": "ʨi",        # ground (not "ʥi")
    
    # ============================================================
    # SKY, WEATHER & COSMOS (空雨雲etc.)
    # ============================================================
    "空": "soɾa",      # sky (not "kɯː")
    "雨": "ame",       # rain (not "ɯ")
    "雪": "jɯki",      # snow (not "setsɯ")
    "雲": "kɯmo",      # cloud (not "ɯɴ")
    "風": "kaze",      # wind (not "ɸɯː")
    "霧": "kiɾi",      # fog/mist (not "mɯ")
    "霜": "ɕimo",      # frost (not "soː")
    "露": "tsɯjɯ",     # dew (not "ɾo")
    "雷": "kaminaɾi",  # thunder (not "ɾai")
    "虹": "niʥi",      # rainbow (not "koː")
    "星": "hoɕi",      # star (not "sei")
    "月": "tsɯki",     # moon/month (not "gatsɯ")
    "日": "hi",        # day/sun (not "ka" or "niʨi")
    "光": "çikaɾi",    # light (not "koː")
    "影": "kage",      # shadow (not "eː")
    "闇": "jami",      # darkness (not "aɴ")
    
    # ============================================================
    # WATER & SEA (海波島etc.)
    # ============================================================
    "海": "ɯmi",       # sea (not "kai")
    "波": "nami",      # wave (not "ha")
    "潮": "ɕio",       # tide (not "ʨoː")
    "浜": "hama",      # beach (not "hiɴ")
    "岸": "kiɕi",      # shore/bank (not "gaɴ")
    "島": "ɕima",      # island (not "toː")
    "湖": "mizɯɯmi",   # lake (not "ko")
    "池": "ike",       # pond (not "ʨi")
    "沼": "nɯma",      # swamp (not "ɕoː")
    "泉": "izɯmi",     # spring/fountain (not "seɴ")
    "滝": "taki",      # waterfall (not "ɾoː")
    "流": "nagaɾe",    # flow/current (not "ɾjɯː")
    
    # ============================================================
    # TIME & SEASONS (年春夏秋冬etc.)
    # ============================================================
    "年": "toɕi",      # year (not "neɴ")
    "春": "haɾɯ",      # spring (not "ɕɯɴ")
    "夏": "natsɯ",     # summer (not "ka")
    "秋": "aki",       # autumn (not "ɕɯː")
    "冬": "ɸɯjɯ",      # winter (not "toː")
    "朝": "asa",       # morning (not "ʨoː")
    "昼": "çiɾɯ",      # noon/daytime (not "ʨɯː")
    "夜": "joɾɯ",      # night (not "ja")
    "夕": "jɯː",       # evening (not "seki")
    "宵": "joi",       # evening/night
    "今": "ima",       # now
    "昔": "mɯkaɕi",    # long ago (not "seki")
    "昨": "sakɯ",      # previous/last (not "sakɯ")
    
    # ============================================================
    # PEOPLE & RELATIONSHIPS (人男女子etc.)
    # ============================================================
    "人": "hito",      # person (not "ʥiɴ")
    "男": "otoko",     # man (not "daɴ")
    "女": "oɴna",      # woman (not "ʥo")
    "子": "ko",        # child (not "ɕi")
    "親": "oja",       # parent (not "ɕiɴ")
    "父": "ʨiʨi",      # father (not "ɸɯ")
    "母": "haha",      # mother (not "bo")
    "兄": "aɴi",       # older brother (not "kjoː")
    "弟": "otoːto",    # younger brother (not "tei")
    "姉": "aɴe",       # older sister (not "ɕi")
    "妹": "imoːto",    # younger sister (not "mai")
    "夫": "otto",      # husband (not "ɸɯ")
    "妻": "tsɯma",     # wife (not "sai")
    "嫁": "jome",      # bride/daughter-in-law (not "ka")
    "婿": "mɯko",      # groom/son-in-law (not "sei")
    "孫": "mago",      # grandchild (not "soɴ")
    "祖": "oʥi",       # ancestor (not "so")
    "友": "tomo",      # friend (not "jɯː")
    "仲": "naka",      # relationship/friendship (not "ʨɯː")
    "客": "kakɯ",      # guest (not "kjakɯ")
    "主": "nɯɕi",      # master/owner (not "ɕɯ")
    "王": "oː",        # king (already correct)
    "姫": "çime",      # princess (not "ki")
    "君": "kimi",      # you/lord (not "kɯɴ")
    
    # ============================================================
    # BODY PARTS (手足目耳etc.)
    # ============================================================
    "手": "te",        # hand (not "ɕɯ")
    "足": "aɕi",       # foot/leg (not "sokɯ")
    "指": "jɯbi",      # finger (not "ɕi")
    "爪": "tsɯme",     # nail/claw (not "soː")
    "腕": "ɯde",       # arm (not "ɰaɴ")
    "肩": "kata",      # shoulder (not "keɴ")
    "背": "se",        # back (not "hai")
    "腰": "koɕi",      # waist/lower back (not "joː")
    "腹": "haɾa",      # belly/stomach (not "ɸɯkɯ")
    "胸": "mɯne",      # chest/breast (not "kjoː")
    "目": "me",        # eye (not "mokɯ")
    "耳": "mimi",      # ear (not "ʥi")
    "鼻": "hana",      # nose (not "bi")
    "口": "kɯʨi",      # mouth (not "koː")
    "舌": "ɕita",      # tongue (not "zetsɯ")
    "歯": "ha",        # tooth (not "ɕi")
    "顔": "kao",       # face (not "gaɴ")
    "頭": "atama",     # head (not "toː")
    "首": "kɯbi",      # neck (not "ɕɯ")
    "髪": "kami",      # hair (not "hatsɯ")
    "毛": "ke",        # hair/fur (not "moː")
    "肌": "hada",      # skin (not "ki")
    "骨": "hoɴe",      # bone (not "kotsɯ")
    "肉": "nikɯ",      # meat/flesh (already correct)
    "血": "ʨi",        # blood (not "ketsɯ")
    "汗": "ase",       # sweat (not "kaɴ")
    "涙": "namida",    # tears (not "ɾɯi")
    "心": "kokoɾo",    # heart/mind (not "ɕiɴ")
    "体": "kaɾada",    # body (not "tai")
    "身": "mi",        # body/oneself (not "ɕiɴ")
    "命": "inoʨi",     # life (not "meː")
    
    # ============================================================
    # ANIMALS (犬猫馬鳥etc.)
    # ============================================================
    "犬": "inɯ",       # dog (not "keɴ")
    "猫": "neko",      # cat (not "bjoː")
    "馬": "ɯma",       # horse (not "ba")
    "牛": "ɯɕi",       # cow (not "gjɯː")
    "豚": "bɯta",      # pig (not "toɴ")
    "羊": "çitsɯʥi",   # sheep (not "joː")
    "鶏": "niɰatoɾi",  # chicken (not "kei")
    "鳥": "toɾi",      # bird (not "ʨoː")
    "鴨": "kamo",      # duck (not "oː")
    "鶴": "tsɯɾɯ",     # crane (not "kakɯ")
    "雀": "sɯzɯme",    # sparrow (not "ʥakɯ")
    "鷹": "taka",      # hawk (not "joː")
    "鷲": "ɰaɕi",      # eagle (not "ɕɯː")
    "鳩": "hato",      # pigeon/dove (not "kjɯː")
    "烏": "kaɾasɯ",    # crow (not "ɯ")
    "魚": "sakana",    # fish (not "gjo")
    "鯉": "koi",       # carp (not "ɾi")
    "鮭": "sake",      # salmon (not "kei")
    "蝦": "ebi",       # shrimp (not "ka")
    "蟹": "kani",      # crab (not "kai")
    "貝": "kai",       # shellfish (already correct)
    "蛇": "hebi",      # snake (not "ʥa")
    "蛙": "kaeɾɯ",     # frog (not "ɰa")
    "亀": "kame",      # turtle (not "ki")
    "虫": "mɯɕi",      # insect (not "ʨɯː")
    "蝶": "ʨoː",       # butterfly
    "蜂": "haʨi",      # bee/wasp (not "hoː")
    "蝉": "semi",      # cicada (not "seɴ")
    "蚊": "ka",        # mosquito (already correct)
    "蟻": "aɾi",       # ant (not "gi")
    "蜘蛛": "kɯmo",    # spider (not "ʨisɯ")
    
    # ============================================================
    # PLANTS & FOOD (花木草米etc.)
    # ============================================================
    "花": "hana",      # flower (not "ka")
    "草": "kɯsa",      # grass (not "soː")
    "葉": "ha",        # leaf (not "joː")
    "枝": "eda",       # branch (not "ɕi")
    "根": "ne",        # root (not "koɴ")
    "幹": "miki",      # trunk (not "kaɴ")
    "種": "taɴe",      # seed (not "ɕɯ")
    "実": "mi",        # fruit/nut (not "ʥitsɯ")
    "竹": "take",      # bamboo (not "ʨikɯ")
    "松": "matsɯ",     # pine (not "ɕoː")
    "杉": "sɯgi",      # cedar (not "saɴ")
    "桜": "sakɯɾa",    # cherry blossom (not "oː")
    "梅": "ɯme",       # plum (not "bai")
    "柳": "janaɡi",    # willow (not "ɾjɯː")
    "藤": "ɸɯʥi",      # wisteria (not "toː")
    "蓮": "hasɯ",      # lotus (not "ɾeɴ")
    "菊": "kikɯ",      # chrysanthemum (already correct)
    "米": "kome",      # rice (not "mai")
    "麦": "mɯɡi",      # wheat (not "bakɯ")
    "豆": "mame",      # bean (not "toː")
    "芋": "imo",       # potato (not "ɯ")
    "栗": "kɯɾi",      # chestnut (not "ɾitsɯ")
    "柿": "kaki",      # persimmon (already correct)
    "桃": "momo",      # peach (not "toː")
    "茶": "ʨa",        # tea
    "酒": "sake",      # sake/alcohol (not "ɕɯ")
    
    # ============================================================
    # COLORS (赤青白黒etc.)
    # ============================================================
    "赤": "aka",       # red (not "seki")
    "青": "ao",        # blue (not "sei")
    "白": "ɕiɾo",      # white (not "hakɯ")
    "黒": "kɯɾo",      # black (not "kokɯ")
    "黄": "ki",        # yellow (not "oː")
    "緑": "midoɾi",    # green (not "ɾjokɯ")
    "紫": "mɯɾasaki",  # purple (not "ɕi")
    "茶": "ʨa",        # brown/tea
    "灰": "çai",       # gray (not "kai")
    "桃": "momo",      # pink/peach (not "toː")
    
    # ============================================================
    # DIRECTIONS & POSITIONS (東西南北上下etc.)
    # ============================================================
    "東": "çiɡaɕi",    # east (not "toː")
    "西": "niɕi",      # west (not "sei")
    "南": "minami",    # south (not "naɴ")
    "北": "kita",      # north (not "hokɯ")
    "上": "ɯe",        # up/above (not "ʥoː")
    "下": "ɕita",      # down/below (not "ka")
    "前": "mae",       # front (not "zeɴ")
    "後": "ɯɕiɾo",     # back/behind (not "ɡo")
    "右": "miɡi",      # right (not "ɯː")
    "左": "çidaɾi",    # left (not "sa")
    "中": "naka",      # inside/middle (not "ʨɯː")
    "外": "soto",      # outside (not "ɡai")
    "内": "ɯʨi",       # inside (not "nai")
    "横": "joko",      # side (not "oː")
    "隣": "tonaɾi",    # next to (not "ɾiɴ")
    "側": "soба",      # side (not "sokɯ")
    "奥": "okɯ",       # interior/back (already correct)
    "端": "haɕi",      # edge/end (not "taɴ")
    "先": "saki",      # ahead/tip (not "seɴ")
    "底": "soko",      # bottom (not "tei")
    "頂": "itadaki",   # top/summit (not "ʨoː")
    
    # ============================================================
    # PLACES & BUILDINGS (国町村家etc.)
    # ============================================================
    "国": "kɯɴi",      # country (not "kokɯ")
    "都": "mijako",    # capital (not "to")
    "京": "kjoː",      # capital (already correct for on-yomi context)
    "町": "maʨi",      # town (not "ʨoː")
    "村": "mɯɾa",      # village (not "soɴ")
    "里": "sato",      # village/hometown (not "ɾi")
    "家": "ie",        # house (not "ka")
    "屋": "ja",        # shop/house (not "okɯ")
    "庭": "niɰa",      # garden (not "tei")
    "園": "sono",      # garden/park (not "eɴ")
    "門": "moɴ",       # gate
    "戸": "to",        # door (already correct)
    "窓": "mado",      # window (not "soː")
    "壁": "kabe",      # wall (not "heki")
    "床": "jɯka",      # floor (not "ɕoː")
    "天井": "teɴʥoː",  # ceiling (not "teɴsei")
    "屋根": "jane",    # roof (not "okɯkoɴ")
    "柱": "haɕiɾa",    # pillar (not "ʨɯː")
    "道": "miʨi",      # road/way (not "doː")
    "路": "miʨi",      # road/path (not "ɾo")
    "橋": "haɕi",      # bridge (not "kjoː")
    "坂": "saka",      # slope (not "haɴ")
    "角": "kado",      # corner (not "kakɯ")
    "街": "maʨi",      # town/street (not "ɡai")
    "市": "iʨi",       # market/city (already correct)
    "店": "mise",      # shop (not "teɴ")
    "宿": "jado",      # inn (not "ɕɯkɯ")
    "寺": "teɾa",      # temple (not "ʥi")
    "社": "jaɕiɾo",    # shrine (not "ɕa")
    "宮": "mija",      # shrine/palace (not "kjɯː")
    
    # ============================================================
    # OBJECTS & THINGS (車船本etc.)
    # ============================================================
    "車": "kɯɾɯma",    # car (not "ɕa")
    "船": "ɸɯɴe",      # ship (not "seɴ")
    "舟": "ɸɯɴe",      # boat (not "ɕɯː")
    "箱": "hako",      # box (not "soː")
    "袋": "ɸɯkɯɾo",    # bag (not "tai")
    "鞄": "kabaɴ",     # bag/briefcase (not "hoː")
    "傘": "kasa",      # umbrella (not "saɴ")
    "扇": "oːɡi",      # fan (not "seɴ")
    "鏡": "kaɡami",    # mirror (not "kjoː")
    "鍵": "kaɡi",      # key (not "keɴ")
    "刀": "katana",    # sword (not "toː")
    "剣": "tsɯɾɯɡi",   # sword (not "keɴ")
    "弓": "jɯmi",      # bow (not "kjɯː")
    "矢": "ja",        # arrow (not "ɕi")
    "槍": "jaɾi",      # spear (not "soː")
    "盾": "tate",      # shield (not "ʥɯɴ")
    "鐘": "kaɴe",      # bell (not "ɕoː")
    "鼓": "tsɯzɯmi",   # drum (not "ko")
    "笛": "ɸɯe",       # flute (not "teki")
    "琴": "koto",      # koto (not "kiɴ")
    "糸": "ito",       # thread (not "ɕi")
    "紐": "çimo",      # string/cord (not "ʨɯː")
    "縄": "naɰa",      # rope (not "ʥoː")
    "布": "nɯno",      # cloth (not "ɸɯ")
    "絹": "kinɯ",      # silk (not "keɴ")
    "綿": "ɰata",      # cotton (not "meɴ")
    "紙": "kami",      # paper (not "ɕi")
    "筆": "ɸɯde",      # brush (not "çitsɯ")
    "墨": "sɯmi",      # ink (not "bokɯ")
    "本": "hoɴ",       # book
    "巻": "maki",      # scroll/volume (not "kaɴ")
    "字": "ʥi",        # character
    "名": "na",        # name (not "mei")
    "印": "ɕiɾɯɕi",    # seal/stamp (not "iɴ")
    
    # ============================================================
    # MONEY & VALUE (金銀玉etc.)
    # ============================================================
    "金": "kaɴe",      # money/gold (not "kiɴ" or "kana")
    "銀": "ɡiɴ",       # silver (already correct in this context)
    "銅": "akaɡaɴe",   # copper (not "doː")
    "鉄": "kɯɾoɡaɴe", # iron (not "tetsɯ")
    "玉": "tama",      # ball/jewel (not "ɡjokɯ")
    "宝": "takaɾa",    # treasure (not "hoː")
    "値": "ne",        # price/value (not "ʨi")
    "価": "atai",      # value/price (not "ka")
    
    # ============================================================
    # ABSTRACT CONCEPTS (力声音etc.)
    # ============================================================
    "力": "ʨikaɾa",    # power/strength (not "ɾjokɯ")
    "声": "koe",       # voice (not "sei")
    "音": "oto",       # sound (not "oɴ")
    "響": "çibiki",    # echo/sound (not "kjoː")
    "色": "iɾo",       # color (not "ɕokɯ" or "ɕiki")
    "形": "katаʨi",    # shape (not "kei")
    "影": "kage",      # shadow/silhouette (not "eː")
    "姿": "sɯɡata",    # figure/appearance (not "ɕi")
    "気": "ki",        # spirit/energy (already correct)
    "魂": "tamaɕiː",   # soul (not "koɴ")
    "霊": "tama",      # spirit (not "ɾeː")
    "夢": "jɯme",      # dream (not "mɯ")
    "涙": "namida",    # tears (not "ɾɯi")
    "笑": "ɰaɾai",     # laugh (not "ɕoː")
    "怒": "ikaɾi",     # anger (not "do")
    "喜": "joɾokobi",  # joy (not "ki")
    "悲": "kanaɕimi",  # sadness (not "çi")
    "恋": "koi",       # love/romance (not "ɾeɴ")
    "愛": "ai",        # love (already correct)
    "憎": "nikɯɕimi",  # hatred (not "zoː")
    "恨": "ɯɾami",     # resentment (not "koɴ")
    "恐": "osoɾe",     # fear (not "kjoː")
    "驚": "odoɾoki",   # surprise (not "kjoː")
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# COMPOUND WORDS WITH SPECIAL READINGS (jukujikun & common compounds)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# These multi-kanji compounds have special readings that don't follow
# the individual kanji readings. Must be fixed as complete units.

COMPOUND_WORD_FIXES = {
    # ============================================================
    # TIME EXPRESSIONS (今日, 明日, etc.)
    # ============================================================
    "今日": "kjoː",         # kyou (not "koɴniʨi" or "imaçi")
    "明日": "aɕita",        # ashita (not "mjoːniʨi")
    "昨日": "kinoː",        # kinou (not "sakɯʥitsɯ")
    "一昨日": "otoːi",      # ototoi (not "iʨisakɯʥitsɯ")
    "明後日": "asatte",     # asatte (not "mjoːgoɴiʨi")
    "今年": "kotoɕi",       # kotoshi (not "koɴneɴ")
    "去年": "kjoneɴ",       # kyonen (not "saneɴ")
    "来年": "ɾaineɴ",       # rainen (already likely correct)
    "今朝": "kesa",         # kesa (not "koɴasa")
    "今晩": "koɴbaɴ",       # konban (already likely correct)
    "今夜": "koɴja",        # konya (not "koɴjoɾɯ")
    "毎日": "mainiʨi",      # mainichi (already likely correct)
    "毎朝": "maiasa",       # maiasa (already likely correct)
    "毎晩": "maibaɴ",       # maiban (already likely correct)
    "毎年": "maitoɕi",      # maitoshi (not "maiねɴ")
    "毎週": "maiɕɯː",       # maishuu (already likely correct)
    "毎月": "maitsɯki",     # maitsuki (not "maiɡatsɯ")
    "先月": "seɴɡetsɯ",     # sengetsu (already likely correct)
    "来月": "ɾaiɡetsɯ",     # raigetsu (already likely correct)
    "今月": "koɴɡetsɯ",     # kongetsu (already likely correct)
    "先週": "seɴɕɯː",       # senshuu (already likely correct)
    "来週": "ɾaiɕɯː",       # raishuu (already likely correct)
    "今週": "koɴɕɯː",       # konshuu (already likely correct)
    
    # ============================================================
    # FAMILY & PEOPLE (父さん, 母さん, etc.)
    # ============================================================
    "お父さん": "otoːsaɴ",  # otousan (not "oʨiʨisaɴ")
    "お母さん": "okaːsaɴ",  # okaasan (not "ohahasaɴ")
    "父さん": "toːsaɴ",     # tousan (not "ʨiʨisaɴ")
    "母さん": "kaːsaɴ",     # kaasan (not "hahasaɴ")
    "兄さん": "niːsaɴ",     # niisan (not "aɴisaɴ")
    "姉さん": "neːsaɴ",     # neesan (not "aɴesaɴ")
    "叔父さん": "oʥisaɴ",   # ojisan (uncle)
    "叔母さん": "obasaɴ",   # obasan (aunt)
    "伯父": "oʥi",          # oji (uncle)
    "伯母": "oba",          # oba (aunt)
    "祖父": "soɸɯ",         # sofu (grandfather) - or "ʥiːʥi" (jiiji)
    "祖母": "sobo",         # sobo (grandmother) - or "baːba" (baaba)
    "大人": "otoɴa",        # otona (not "dainiɴ" or "tainiɴ")
    "子供": "kodomo",       # kodomo (not "ɕikjoː")
    "子ども": "kodomo",     # kodomo (hiragana version)
    "友達": "tomodaʨi",     # tomodachi (not "jɯːtatsɯ")
    "仲間": "nakama",       # nakama (already likely correct)
    
    # ============================================================
    # COMMON JUKUJIKUN (特殊な熟字訓)
    # ============================================================
    "大人": "otoɴa",        # otona (adult)
    "今日": "kjoː",         # kyou (today)
    "明日": "aɕita",        # ashita (tomorrow)
    "昨日": "kinoː",        # kinou (yesterday)
    "紅葉": "momiʥi",       # momiji (autumn leaves, not "koːjoː")
    "時雨": "ɕiɡɯɾe",       # shigure (autumn rain, not "ʥiɯ")
    "梅雨": "tsɯjɯ",        # tsuyu (rainy season, not "baいɯ")
    "七夕": "tanabata",     # tanabata (star festival, not "ɕiʨiseki")
    "二十歳": "hatаʨi",     # hatachi (20 years old, not "niʥɯːsai")
    "二十日": "hatsɯka",    # hatsuka (20th day, not "niʥɯːniʨi")
    "一日": "tsɯitaʨi",     # tsuitachi (1st day, not "iʨiniʨi")
    "二日": "ɸɯtsɯka",      # futsuka (2nd day, not "niɴiʨi")
    "三日": "mikːa",        # mikka (3rd day, not "saɴniʨi")
    "四日": "jokːa",        # yokka (4th day, not "ɕiniʨi")
    "五日": "itsɯka",       # itsuka (5th day, not "ɡoniʨi")
    "六日": "mɯika",        # muika (6th day, not "ɾokɯniʨi")
    "七日": "nanoka",       # nanoka (7th day, not "ɕiʨiniʨi")
    "八日": "joːka",        # youka (8th day, not "haʨiniʨi")
    "九日": "kokonoka",     # kokonoka (9th day, not "kjɯːniʨi")
    "十日": "toːka",        # touka (10th day, not "ʥɯːniʨi")
    "十四日": "ʥɯːjokːa",   # juuyokka (14th day)
    "二十日": "hatsɯka",    # hatsuka (20th day)
    "一月": "iʨiɡatsɯ",     # ichigatsu (January, not "hitotsɯki")
    "二月": "niɡatsɯ",      # nigatsu (February)
    "三月": "saɴɡatsɯ",     # sangatsu (March)
    "四月": "ɕiɡatsɯ",      # shigatsu (April)
    "五月": "ɡoɡatsɯ",      # gogatsu (May)
    "六月": "ɾokɯɡatsɯ",    # rokugatsu (June)
    "七月": "ɕiʨiɡatsɯ",    # shichigatsu (July)
    "八月": "haʨiɡatsɯ",    # hachigatsu (August)
    "九月": "kɯɡatsɯ",      # kugatsu (September)
    "十月": "ʥɯːɡatsɯ",     # juugatsu (October)
    "十一月": "ʥɯːiʨiɡatsɯ", # juuichigatsu (November)
    "十二月": "ʥɯːniɡatsɯ", # juunigatsu (December)
    
    # ============================================================
    # PLACES & LOCATIONS
    # ============================================================
    "田舎": "inaka",        # inaka (countryside, not "deɴɕa")
    "都会": "tokai",        # tokai (city, not "tokai") - actually already correct
    "神社": "ʥiɴʥa",        # jinja (shrine, already likely correct)
    "お寺": "oteɾa",        # otera (temple)
    "図書館": "toɕokaɴ",    # toshokan (library, already likely correct)
    "病院": "bjoːiɴ",       # byouin (hospital, already likely correct)
    "学校": "ɡakːoː",       # gakkou (school, already likely correct)
    "会社": "kaiɕa",        # kaisha (company, already likely correct)
    "銀行": "ɡiɴkoː",       # ginkou (bank, already likely correct)
    "郵便局": "jɯːbiɴkjokɯ", # yuubinkyoku (post office)
    "交番": "koːbaɴ",       # kouban (police box, already likely correct)
    
    # ============================================================
    # NATURE COMPOUNDS
    # ============================================================
    "景色": "keɕiki",       # keshiki (scenery, not "keiɕokɯ")
    "夕焼け": "jɯːjake",    # yuuyake (sunset)
    "朝焼け": "asajake",    # asayake (sunrise)
    "夕暮れ": "jɯːɡɯɾe",    # yuugure (evening/dusk)
    "星空": "hoɕizoɾa",     # hoshizora (starry sky)
    "青空": "aozoɾa",       # aozora (blue sky)
    "台風": "taiɸɯː",       # taifuu (typhoon, already likely correct)
    "地震": "ʥiɕiɴ",        # jishin (earthquake, already likely correct)
    "雷雨": "ɾaiɯ",         # raiu (thunderstorm)
    
    # ============================================================
    # COMMON WORDS WITH SPECIAL READINGS
    # ============================================================
    "勉強": "beɴkjoː",      # benkyou (study, already likely correct)
    "電話": "deɴɰa",        # denwa (telephone, already likely correct)
    "手紙": "teɡami",       # tegami (letter, not "ɕɯɕi")
    "眼鏡": "meɡaɴe",       # megane (glasses, not "ɡaɴkjoː")
    "煙草": "tabako",       # tabako (tobacco/cigarette, not "eɴsoː")
    "果物": "kɯdamono",     # kudamono (fruit, not "kаbɯtsɯ")
    "野菜": "jasai",        # yasai (vegetables, already likely correct)
    "お土産": "omijage",    # omiyage (souvenir, not "odoɕaɴ")
    "土産": "mijage",       # miyage (souvenir)
    "為替": "kaɰase",       # kawase (exchange, not "iɾeplaceɕi")
    "相撲": "sɯmoː",        # sumou (sumo, not "soːbokɯ")
    "浴衣": "jɯkata",       # yukata (summer kimono, not "jokɯi")
    "着物": "kimono",       # kimono (not "ʨakɯbɯtsɯ")
    "迷子": "maigo",        # maigo (lost child, not "meiɕi")
    "玄関": "ɡeɴkaɴ",       # genkan (entrance, already likely correct)
    "台所": "daidokoɾo",    # daidokoro (kitchen, not "taiɕo")
    "居間": "ima",          # ima (living room, not "kjokaɴ")
    "部屋": "heja",         # heya (room, not "bɯokɯ")
    "風呂": "ɸɯɾo",         # furo (bath, not "ɸɯːɾo")
    "下手": "heta",         # heta (unskillful, not "ɡeɕɯ" or "kaɕɯ")
    "上手": "ʥoːzɯ",        # jouzu (skillful, not "ʥoːɕɯ" or "kamiて")
    "下手": "ɕimote",       # shimote (lower seat) - alternate reading
    "上手": "kamite",       # kamite (upper seat) - alternate reading
    "大丈夫": "daiʥoːbɯ",   # daijoubu (okay/fine)
    "丈夫": "ʥoːbɯ",        # joubu (sturdy/durable)
    "神様": "kamisama",     # kamisama (god/deity)
    "仏様": "hotokesama",   # hotokesama (Buddha)
    "娘": "mɯsɯme",         # musume (daughter, not "ʥoː")
    "息子": "mɯsɯko",       # musuko (son, not "sokɯɕi")
    "兄弟": "kjoːdai",      # kyoudai (siblings, not "aɴiteい")
    "姉妹": "ɕimai",        # shimai (sisters, not "ɕimai" - same!)
    "夫婦": "ɸɯːɸɯ",        # fuufu (married couple, not "ɸɯɸɯ")
    "一人": "çitoɾi",       # hitori (one person, not "iʨiniɴ")
    "二人": "ɸɯtaɾi",       # futari (two people, not "niɴiɴ")
    "三人": "saɴɴiɴ",       # sannin (three people)
    "四人": "joniɴ",        # yonin (four people)
    "五人": "ɡoniɴ",        # gonin (five people)
    "一つ": "çitots",       # hitotsu (one thing)
    "二つ": "ɸɯtats",       # futatsu (two things)
    "三つ": "mitːs",        # mittsu (three things)
    "四つ": "jotːs",        # yottsu (four things)
    "五つ": "itsɯts",       # itsutsu (five things)
    "六つ": "mɯtːs",        # muttsu (six things)
    "七つ": "nanats",       # nanatsu (seven things)
    "八つ": "jatːs",        # yattsu (eight things)
    "九つ": "kokonots",     # kokonotsu (nine things)
    "十": "toː",            # tou (ten)
    
    # ============================================================
    # ACTIONS & STATES
    # ============================================================
    "行方": "jɯkɯe",        # yukue (whereabouts, not "ɡjoːhoː" or "aɴʥoː")
    "出来る": "dekiɾɯ",     # dekiru (can do, not "ɕɯtsɯɾaiɾɯ")
    "気持ち": "kimoʨi",     # kimochi (feeling, not "kimoʨi" - same!)
    "気分": "kibɯɴ",        # kibun (mood, already likely correct)
    "具合": "ɡɯai",         # guai (condition, not "ɡɯɡoː")
    "都合": "tsɯɡoː",       # tsugou (convenience, not "toɡoː")
    "場合": "baai",         # baai (case/situation, not "bаɡoː")
    "道具": "doːɡɯ",        # dougu (tool, already likely correct)
    "家具": "kaɡɯ",         # kagu (furniture, already likely correct)
    "荷物": "nimots",       # nimotsu (luggage, already likely correct)
    "着替え": "kiɡae",      # kigae (change of clothes)
    "待合": "matɕiai",      # machiai (waiting room)
    "見本": "mihoɴ",        # mihon (sample, not "keɴhoɴ")
    "見舞い": "mimai",      # mimai (visit [sick person], not "keɴbɯ")
    "聞き手": "kikite",     # kikite (listener, not "bɯɴɕɯ")
    "話し手": "hanaɕite",   # hanashite (speaker)
    
    # ============================================================
    # BODY & HEALTH
    # ============================================================
    "風邪": "kaze",         # kaze (cold/illness, not "ɸɯːʥa")
    "怪我": "keɡa",         # kega (injury, not "kaiɡa")
    "痛み": "itami",        # itami (pain, not "tsɯːmi")
    "熱": "netsɯ",          # netsu (fever, not "atsɯ")
    "頭痛": "zɯtsɯː",       # zutsuu (headache, not "toːtsɯː")
    "腹痛": "ɸɯkɯtsɯː",     # fukutsuu (stomachache)
    "元気": "ɡeɴki",        # genki (healthy/energetic, already likely correct)
    
    # ============================================================
    # NUMBERS WITH COUNTERS (special readings)
    # ============================================================
    "一回": "ikːai",        # ikkai (one time, not "iʨikai")
    "二回": "nikai",        # nikai (two times)
    "三回": "saɴkai",       # sankai (three times)
    "何回": "naɴkai",       # nankai (how many times)
    "一番": "iʨibaɴ",       # ichiban (number one/most)
    "二番": "nibaɴ",        # niban (number two)
    "三番": "saɴbaɴ",       # sanban (number three)
    "一度": "iʨido",        # ichido (one time/once)
    "二度": "nido",         # nido (two times/twice)
    "三度": "saɴdo",        # sando (three times)
}

# Common verbs in hiragana (often missing from dictionaries since they have Kanji equivalents)
# These will automatically get conjugated by the verb system
COMMON_VERBS_HIRAGANA = {
    'いる': 'iɾɯ',      # to exist/be (animate) - ichidan
    'ある': 'aɾɯ',      # to exist/be (inanimate) - godan (already handled as special)
    'やる': 'jaɾɯ',     # to do - godan
    'なる': 'naɾɯ',     # to become - godan
    'みる': 'miɾɯ',     # to see/look - ichidan
    'きる': 'kiɾɯ',     # to wear - ichidan
    'でる': 'deɾɯ',     # to go out/exit - ichidan
    'ねる': 'neɾɯ',     # to sleep - ichidan
    'たべる': 'tabeɾɯ', # to eat - ichidan
    'のむ': 'nomɯ',     # to drink - godan
    'いく': 'ikɯ',      # to go - godan (already handled as special)
    'くる': 'kɯɾɯ',     # to come - irregular (already handled)
    'する': 'sɯɾɯ',     # to do - irregular (already handled)
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# JAPANESE NUMBERS SYSTEM
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Basic numbers 1-10 and counters
BASIC_NUMBERS = {
    # Basic digits 1-10
    '一': 'iʨi',
    '二': 'ni',
    '三': 'saɴ',
    '四': 'ɕi',      # shi (also よん yon)
    '五': 'go',
    '六': 'ɾokɯ',
    '七': 'ɕiʨi',    # shichi (also なな nana)
    '八': 'haʨi',
    '九': 'kɯ',      # ku (also きゅう kyuu)
    '十': 'ʥɯː',
    
    # Alternative readings
    'よん': 'joɴ',    # alternative for 四
    'なな': 'nana',   # alternative for 七
    'きゅう': 'kjɯː', # alternative for 九
    
    # Counters
    '百': 'çakɯ',    # hyaku (hundred)
    '千': 'seɴ',     # sen (thousand)
    '万': 'maɴ',     # man (ten thousand)
    '億': 'okɯ',     # oku (hundred million)
    '兆': 'ʨoː',     # chou (trillion)
    
    # Zero
    '零': 'ɾeː',     # rei
    'ゼロ': 'zeɾo',  # zero
}

# Hundreds (100-900)
HUNDREDS = {
    '百': 'çakɯ',           # 100 - hyaku
    '二百': 'niçakɯ',       # 200 - nihyaku
    '三百': 'saɴbjakɯ',     # 300 - sanbyaku (rendaku)
    '四百': 'joɴçakɯ',      # 400 - yonhyaku
    '五百': 'goçakɯ',       # 500 - gohyaku
    '六百': 'ɾopːjakɯ',     # 600 - roppyaku (rendaku + consonant lengthening)
    '七百': 'nanaçakɯ',     # 700 - nanahyaku
    '八百': 'hapːjakɯ',     # 800 - happyaku (consonant lengthening)
    '九百': 'kjɯːçakɯ',     # 900 - kyuuhyaku
}

# Thousands (1000-9000)
THOUSANDS = {
    '千': 'seɴ',            # 1000 - sen
    '二千': 'niseɴ',        # 2000 - nisen
    '三千': 'saɴzeɴ',       # 3000 - sanzen (rendaku)
    '四千': 'joɴseɴ',       # 4000 - yonsen
    '五千': 'goseɴ',        # 5000 - gosen
    '六千': 'ɾokɯseɴ',      # 6000 - rokusen
    '七千': 'nanaseɴ',      # 7000 - nanasen
    '八千': 'hasːeɴ',       # 8000 - hassen (consonant lengthening)
    '九千': 'kjɯːseɴ',      # 9000 - kyuusen
}

# Ten thousands (10000-90000) - 万
TEN_THOUSANDS = {
    '万': 'maɴ',            # 10,000 - man
    '一万': 'iʨimaɴ',       # 10,000 - ichiman
    '二万': 'nimaɴ',        # 20,000 - niman
    '三万': 'saɴmaɴ',       # 30,000 - sanman
    '四万': 'joɴmaɴ',       # 40,000 - yonman
    '五万': 'gomaɴ',        # 50,000 - goman
    '六万': 'ɾokɯmaɴ',      # 60,000 - rokuman
    '七万': 'nanamaɴ',      # 70,000 - nanaman
    '八万': 'haʨimaɴ',      # 80,000 - hachiman
    '九万': 'kjɯːmaɴ',      # 90,000 - kyuuman
    '十万': 'ʥɯːmaɴ',       # 100,000 - juuman
}

# Hundred thousands (100000-900000)
HUNDRED_THOUSANDS = {
    '十万': 'ʥɯːmaɴ',       # 100,000
    '二十万': 'niʥɯːmaɴ',   # 200,000
    '三十万': 'saɴʥɯːmaɴ',  # 300,000
    '四十万': 'joɴʥɯːmaɴ',  # 400,000
    '五十万': 'goʥɯːmaɴ',   # 500,000
    '六十万': 'ɾokɯʥɯːmaɴ', # 600,000
    '七十万': 'nanaʥɯːmaɴ', # 700,000
    '八十万': 'haʨiʥɯːmaɴ', # 800,000
    '九十万': 'kjɯːʥɯːmaɴ', # 900,000
}

# Millions (100万) - one million in Japanese is 百万 (hyakuman)
MILLIONS = {
    '百万': 'çakɯmaɴ',          # 1,000,000 - hyakuman
    '二百万': 'niçakɯmaɴ',      # 2,000,000
    '三百万': 'saɴbjakɯmaɴ',    # 3,000,000
    '四百万': 'joɴçakɯmaɴ',     # 4,000,000
    '五百万': 'goçakɯmaɴ',      # 5,000,000
    '六百万': 'ɾopːjakɯmaɴ',    # 6,000,000
    '七百万': 'nanaçakɯmaɴ',    # 7,000,000
    '八百万': 'hapːjakɯmaɴ',    # 8,000,000
    '九百万': 'kjɯːçakɯmaɴ',    # 9,000,000
    '千万': 'seɴmaɴ',           # 10,000,000 - senman
}

# Common compound numbers (11-99)
COMPOUND_NUMBERS = {
    # 11-19
    '十一': 'ʥɯːiʨi',
    '十二': 'ʥɯːni',
    '十三': 'ʥɯːsaɴ',
    '十四': 'ʥɯːɕi',
    '十五': 'ʥɯːgo',
    '十六': 'ʥɯːɾokɯ',
    '十七': 'ʥɯːɕiʨi',
    '十八': 'ʥɯːhaʨi',
    '十九': 'ʥɯːkɯ',
    
    # Tens (20-90)
    '二十': 'niʥɯː',
    '三十': 'saɴʥɯː',
    '四十': 'joɴʥɯː',
    '五十': 'goʥɯː',
    '六十': 'ɾokɯʥɯː',
    '七十': 'nanaʥɯː',
    '八十': 'haʨiʥɯː',
    '九十': 'kjɯːʥɯː',
}

# Currency and common number+counter combinations
NUMBER_COUNTERS = {
    '円': 'eɴ',              # yen
    # Note: Don't add specific yen amounts like 五百円 - let backtracking handle them!
    # The furigana 五百円「えん」will be split into 五百 + 円「えん」automatically
    
    # Common amounts for people
    '一人': 'çitoɾi',        # one person (hitori)
    '二人': 'ɸɯtaɾi',        # two people (futari)
    '三人': 'saɴniɴ',        # three people
    '四人': 'joniɴ',         # four people
    
    # Time - these are OK because they don't have furigana issues
    '一時': 'iʨiʥi',         # 1 o'clock
    '二時': 'niʥi',
    '三時': 'saɴʥi',
    '四時': 'joʥi',
    '五時': 'goʥi',
    '六時': 'ɾokɯʥi',
    '七時': 'ɕiʨiʥi',
    '八時': 'haʨiʥi',
    '九時': 'kɯʥi',
    '十時': 'ʥɯːʥi',
    '十一時': 'ʥɯːiʨiʥi',
    '十二時': 'ʥɯːniʥi',
}

# All numbers combined
ALL_NUMBERS = {
    **BASIC_NUMBERS,
    **HUNDREDS,
    **THOUSANDS,
    **TEN_THOUSANDS,
    **HUNDRED_THOUSANDS,
    **MILLIONS,
    **COMPOUND_NUMBERS,
    **NUMBER_COUNTERS,
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
# IMPORTANT: Keys are the actual phoneme consonants extracted from verbs!
# NOTE: Must handle BOTH multi-char sequences (before ligature conversion) AND ligatures!
GODAN_TE_TA_MAP = {
    # く → いて/いた
    'k': ('i', 'te', 'ta'),      # 書く kakɯ → 書いて kaite → 書いた kaita
    # ぐ → いで/いだ
    'g': ('i', 'de', 'da'),      # 泳ぐ ojogɯ → 泳いで ojoide → 泳いだ ojoida
    # す → して/した
    's': ('ɕi', 'te', 'ta'),     # 話す hanasɯ → 話して hanaɕite → 話した hanaɕita
    # つ → って/った (BOTH forms: before and after ligature conversion)
    'ts': ('tː', 'e', 'a'),      # 待つ matsɯ → 待って matːe → 待った matːa  (before ligature)
    'ʦ': ('tː', 'e', 'a'),       # 待つ maʦɯ → 待って matːe → 待った matːa  (after ligature)
    # ぬ → んで/んだ
    'n': ('ɴ', 'de', 'da'),      # 死ぬ ɕinɯ → 死んで ɕiɴde → 死んだ ɕiɴda
    # ぶ → んで/んだ
    'b': ('ɴ', 'de', 'da'),      # 飛ぶ tobɯ → 飛んで toɴde → 飛んだ toɴda
    # む → んで/んだ
    'm': ('ɴ', 'de', 'da'),      # 読む jomɯ → 読んで joɴde → 読んだ joɴda
    # る → って/った
    'ɾ': ('tː', 'e', 'a'),       # 走る haɕiɾɯ → 走って haɕitːe → 走った haɕitːa
    # う → って/った (ɰ not in phonemes for う-verbs, they end with just ɯ)
    'ɯ': ('tː', 'e', 'a'),       # 買う kaɯ → 買って katːe → 買った katːa
    
    # Additional ligature forms (in case they appear in future data)
    'dz': ('ɴ', 'de', 'da'),     # ず dzɯ → んで (before ligature)
    'ʣ': ('ɴ', 'de', 'da'),      # ず ʣɯ → んで (after ligature)
    'tɕ': ('tː', 'e', 'a'),      # ち tɕi → って (before ligature, rare for godan)
    'ʨ': ('tː', 'e', 'a'),       # ち ʨi → って (after ligature, rare for godan)
    'dʑ': ('ɴ', 'de', 'da'),     # じ dʑi → んで (before ligature, rare for godan)
    'ʥ': ('ɴ', 'de', 'da'),      # じ ʥi → んで (after ligature, rare for godan)
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
    
    # Check if word ends with any godan verb ending
    godan_endings = ['う', 'く', 'ぐ', 'す', 'つ', 'ぬ', 'ぶ', 'む', 'る']
    text_ending = word[-1] if word else ''
    
    if text_ending not in godan_endings:
        return None  # Not a verb
    
    # Handle る-verbs (need to distinguish ichidan from godan)
    if text_ending == 'る':
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
    
    # All other endings are godan
    return f'godan_{text_ending}'


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
                # Special case for う-verbs: they end with vowel + ɯ  
                # e.g., 買う (kaɯ), 言う (iɯ), 歌う (ɯtaɯ)
                if text_ending == 'う':
                    # For う-verbs, we use special marker 'ɯ' as the ending
                    phoneme_ending = 'ɯ'
                    phoneme_stem = phoneme[:-1]  # Keep the vowel in the stem
                else:
                    # Check for multi-character consonant sequences BEFORE ligature conversion
                    # These appear in the original phoneme data
                    multi_char_consonants = ['ts', 'dz', 'tɕ', 'dʑ', 'tʃ', 'dʒ']  # Ordered by length (all 2 chars)
                    
                    found_multi = False
                    for mc in multi_char_consonants:
                        if phoneme.endswith(mc + 'ɯ'):
                            phoneme_ending = mc
                            phoneme_stem = phoneme[:-len(mc)-1]  # Remove consonant + ɯ
                            found_multi = True
                            break
                    
                    if not found_multi:
                        # Check for single-character ligatures AFTER ligature conversion
                        ligature_consonants = ['ʦ', 'ʣ', 'ʨ', 'ʥ', 'ʧ', 'ʤ']
                        found_ligature = False
                        for lig in ligature_consonants:
                            if len(phoneme) >= 2 and phoneme[-2] == lig:
                                phoneme_ending = lig
                                phoneme_stem = phoneme[:-2]
                                found_ligature = True
                                break
                        
                        if not found_ligature:
                            # Normal single-character consonant
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
                # Skip errors in worker (should be rare with proper handling)
                continue
    
    return (batch_conjugations, batch_conjugated_words, batch_verb_count)


def fix_particle_ha_in_phoneme(kanji, phoneme):
    """
    Fix particle は (ha -> wa) in phoneme transcriptions.
    
    In Japanese, the particle は is pronounced as "wa" not "ha".
    This fixes common patterns where は acts as a particle.
    
    Common patterns:
    - では (dewa)
    - には (niwa)  
    - とは (towa)
    - ては (tewa)
    - からは (karawa)
    - それでは (soredewa)
    - これでは (koredewa)
    - etc.
    
    Args:
        kanji: The Japanese text
        phoneme: The IPA phoneme transcription
        
    Returns:
        str: Corrected phoneme transcription
    """
    # Pattern: Check if the kanji contains particle は patterns
    # We need to be careful - only fix when は is clearly a particle
    
    particle_patterns = [
        # ============================================================
        # COMPOUND PARTICLE PATTERNS (では, には, etc.)
        # ============================================================
        (r'では', r'deha', r'dewa'),        # では -> dewa
        (r'には', r'niha', r'niwa'),        # には -> niwa
        (r'とは', r'toha', r'towa'),        # とは -> towa
        (r'ては', r'teha', r'tewa'),        # ては -> tewa
        (r'からは', r'kaɾaha', r'kaɾawa'),  # からは -> karawa
        (r'までは', r'madeha', r'madewa'),  # までは -> madewa
        (r'のでは', r'nodeha', r'nodewa'),  # のでは -> nodewa
        (r'としては', r'toɕiteha', r'toɕitewa'),  # としては -> toshitewa
        (r'にしては', r'niɕiteha', r'niɕitewa'),  # にしては -> nishitewa
        (r'にあっては', r'niatːeha', r'niatːewa'),  # にあっては -> niattewa
        (r'にかけては', r'nikaketeha', r'nikaketewa'),  # にかけては -> nikaketewa
        (r'においては', r'nioiteha', r'nioitewa'),  # においては -> nioitewa
        (r'さては', r'sateha', r'satewa'),  # さては -> satewa
        (r'いっては', r'itːeha', r'itːewa'),  # いっては -> ittewa
        (r'よっては', r'jotːeha', r'jotːewa'),  # よっては -> yottewa
        (r'果ては', r'hateha', r'hatewa'),  # 果ては -> hatewa
        (r'延いては', r'çiiteha', r'çiitewa'),  # 延いては -> hiitewa
        
        # ============================================================
        # DEMONSTRATIVES + は (これは, それは, etc.)
        # ============================================================
        (r'それでは', r'soɾedeha', r'soɾedewa'),  # それでは -> soredewa
        (r'これでは', r'koɾedeha', r'koɾedewa'),  # これでは -> koredewa
        (r'あれでは', r'aɾedeha', r'aɾedewa'),  # あれでは -> aredewa
        (r'どれでは', r'doɾedeha', r'doɾedewa'),  # どれでは -> doredewa
        
        (r'それは', r'soɾeha', r'soɾewa'),  # それは -> sorewa
        (r'これは', r'koɾeha', r'koɾewa'),  # これは -> korewa
        (r'あれは', r'aɾeha', r'aɾewa'),    # あれは -> arewa
        (r'どれは', r'doɾeha', r'doɾewa'),  # どれは -> dorewa
        
        # ============================================================
        # PRONOUNS + は (私は, 僕は, etc.)
        # ============================================================
        (r'私は', r'ɰᵝataɕiha', r'ɰᵝataɕiwa'),  # 私は -> watashiwa
        (r'僕は', r'bokɯha', r'bokɯwa'),        # 僕は -> bokuwa
        (r'俺は', r'oɾeha', r'oɾewa'),          # 俺は -> orewa
        (r'彼は', r'kaɾeha', r'kaɾewa'),        # 彼は -> karewa
        (r'彼女は', r'kanoʥoha', r'kanoʥowa'),  # 彼女は -> kanojowa
        (r'誰は', r'daɾeha', r'daɾewa'),        # 誰は -> darewa
        (r'何は', r'naniha', r'naniwa'),        # 何は -> naniwa
        (r'君は', r'kimiha', r'kimiwa'),        # 君は -> kimiwa
        (r'貴方は', r'anataha', r'anatawa'),    # 貴方は -> anatawa
        (r'あなたは', r'anataha', r'anatawa'),  # あなたは -> anatawa
        
        # ============================================================
        # COMMON WORDS + は
        # ============================================================
        (r'今日は', r'kjoɯha', r'kjoɯwa'),      # 今日は -> kyouwa
        (r'明日は', r'aɕitaha', r'aɕitawa'),    # 明日は -> ashitawa
        (r'昨日は', r'kinoɯha', r'kinoɯwa'),    # 昨日は -> kinouwa
        (r'此処は', r'kokoha', r'kokowa'),      # 此処は -> kokowa
        (r'ここは', r'kokoha', r'kokowa'),      # ここは -> kokowa
        (r'其処は', r'sokoha', r'sokowa'),      # 其処は -> sokowa
        (r'そこは', r'sokoha', r'sokowa'),      # そこは -> sokowa
        (r'彼処は', r'asokoha', r'asokowa'),    # 彼処は -> asokowa
        (r'あそこは', r'asokoha', r'asokowa'),  # あそこは -> asokowa
        
        # ============================================================
        # NEGATIVE FORMS: はない and は無い (hanai -> wanai)
        # These are very common and appear in many contexts
        # ============================================================
        (r'はない', r'hanai', r'wanai'),        # はない -> wanai (kana)
        (r'は無い', r'hanai', r'wanai'),        # は無い -> wanai (kanji)
        (r'はなかった', r'hanakatta', r'wanakatta'),  # はなかった -> wanakatta
        (r'は無かった', r'hanakatta', r'wanakatta'),  # は無かった -> wanakatta
    ]
    
    # Apply each pattern
    for kanji_pattern, phoneme_old, phoneme_new in particle_patterns:
        if re.search(kanji_pattern, kanji):
            # Check if the old pattern exists in the phoneme
            if phoneme_old in phoneme:
                phoneme = phoneme.replace(phoneme_old, phoneme_new)
    
    return phoneme


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


def write_varint(output, value):
    """Write a variable-length integer (1-5 bytes for values up to 2^32)"""
    while value >= 0x80:
        output.append((value & 0x7F) | 0x80)
        value >>= 7
    output.append(value & 0x7F)


def serialize_trie_node(node, output, offset_tracker):
    """
    Recursively serialize a trie node to OPTIMIZED binary format.
    Returns the offset where this node was written.
    
    OPTIMIZED FORMAT:
    - Varint for counts/lengths (1 byte for small values)
    - 4-byte RELATIVE offsets (not absolute)
    - Compact child entries: 3-byte code point + 4-byte relative offset = 7 bytes
    """
    # Remember where we're writing this node
    node_offset = len(output)
    node.offset = node_offset
    
    # Flags byte
    has_value = 1 if node.value is not None else 0
    num_children = len(node.children)
    
    # Pack flags: bit 0 = has_value, bits 1-7 = children count if < 127
    if num_children < 127:
        flags = has_value | (num_children << 1)
        output.append(flags)
    else:
        flags = has_value | 0x80  # Bit 7 = use varint for count
        output.append(flags)
        write_varint(output, num_children)
    
    # Value (if present) - use varint for length
    if node.value is not None:
        value_bytes = node.value.encode('utf-8')
        value_len = len(value_bytes)
        write_varint(output, value_len)
        output.extend(value_bytes)
    
    # Reserve space for children entries - NOW ONLY 7 BYTES EACH!
    # Format: 3 bytes for code point (up to 0xFFFFFF) + 4 bytes relative offset
    children_table_offset = len(output)
    output.extend(b'\x00' * (num_children * 7))
    
    # Recursively serialize children and record their offsets
    child_offsets = {}
    for code_point, child_node in sorted(node.children.items()):
        child_offset = serialize_trie_node(child_node, output, offset_tracker)
        child_offsets[code_point] = child_offset
    
    # Now go back and fill in the children table with RELATIVE offsets
    table_pos = children_table_offset
    for code_point, child_offset in sorted(child_offsets.items()):
        # Calculate relative offset from END of this child entry
        entry_end = table_pos + 7
        relative_offset = child_offset - entry_end
        
        # Write code point (3 bytes - supports all Unicode)
        output[table_pos] = (code_point & 0xFF)
        output[table_pos + 1] = ((code_point >> 8) & 0xFF)
        output[table_pos + 2] = ((code_point >> 16) & 0xFF)
        
        # Write relative offset (4 bytes signed)
        struct.pack_into('<i', output, table_pos + 3, relative_offset)
        
        table_pos += 7
    
    return node_offset


def build_simple_binary_format(phoneme_dict, word_set, output_path):
    """
    Build a SIMPLE binary format that C++ can load DIRECTLY into TrieNode* structure.
    Just serialized key-value pairs - no complex tree traversal needed!
    
    Format:
    - Magic: "JPHO" (4 bytes)
    - Version: 1.0 (2 bytes + 2 bytes)
    - Entry count: uint32
    - For each entry:
      - Key length: varint
      - Key: UTF-8 bytes
      - Value length: varint  
      - Value: UTF-8 bytes
    
    C++ loads this into TrieNode* structure using same insert() logic as JSON!
    """
    print(f"\n>> Building simple binary format (direct load into TrieNode*)...")
    
    output = bytearray()
    
    # Header
    output.extend(b'JPHO')  # Magic: Japanese PHOnemes
    output.extend(struct.pack('<HH', 1, 0))  # Version 1.0
    
    # Combine phonemes and words (words have empty values)
    all_entries = {}
    all_entries.update(phoneme_dict)
    
    # Add word-only entries (not in phoneme dict)
    for word in word_set:
        if word not in all_entries:
            all_entries[word] = ""  # Empty marker for words
    
    # Write entry count
    entry_count = len(all_entries)
    output.extend(struct.pack('<I', entry_count))
    
    print(f"   Serializing {entry_count} entries...")
    
    # Write all entries
    for idx, (key, value) in enumerate(all_entries.items()):
        key_bytes = key.encode('utf-8')
        value_bytes = value.encode('utf-8')
        
        # Key length + key
        write_varint(output, len(key_bytes))
        output.extend(key_bytes)
        
        # Value length + value
        write_varint(output, len(value_bytes))
        output.extend(value_bytes)
        
        if idx % 50000 == 0 and idx > 0:
            print(f"\r   Progress: {idx}/{entry_count}", end='', flush=True)
    
    print(f"\r   Progress: {entry_count}/{entry_count} [OK]")
    
    # Write to file
    print(f"   Writing to {output_path}...")
    with open(output_path, 'wb') as f:
        f.write(output)
    
    file_size = len(output)
    file_size_mb = file_size / (1024 * 1024)
    
    print(f"   [OK] Binary format created!")
    print(f"   Size: {file_size:,} bytes ({file_size_mb:.2f} MB)")
    print(f"   Entries: {entry_count} (phonemes + words)")
    print(f"   C++ loads this DIRECTLY into TrieNode* using same insert() as JSON!")
    
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
    
    # Step 0.5: Fix particle は (ha -> wa) pronunciations
    print("\nStep 0.5: Fixing particle ha (ha -> wa) pronunciations...")
    particle_fixes = 0
    for kanji in list(data.keys()):
        original_phoneme = data[kanji]
        fixed_phoneme = fix_particle_ha_in_phoneme(kanji, original_phoneme)
        if original_phoneme != fixed_phoneme:
            data[kanji] = fixed_phoneme
            particle_fixes += 1
    print(f"   Fixed {particle_fixes} particle pronunciations (ha -> wa)")
    
    # Step 0.8: Fix standalone kanji readings (kun-yomi for standalone kanji)
    print("\nStep 0.8: Fixing standalone kanji readings (kun-yomi corrections)...")
    kanji_fixes = 0
    for kanji, correct_phoneme in STANDALONE_KANJI_FIXES.items():
        if kanji in data:
            old_phoneme = data[kanji]
            if old_phoneme != correct_phoneme:
                data[kanji] = correct_phoneme
                kanji_fixes += 1
        else:
            # Add if missing
            data[kanji] = correct_phoneme
            kanji_fixes += 1
    print(f"   Fixed/added {kanji_fixes} standalone kanji readings (水→mizu, 山→yama, etc.)")
    
    # Step 0.9: Fix compound words with special readings (jukujikun)
    print("\nStep 0.9: Fixing compound words with special readings (今日→kyou, 明日→ashita, etc.)...")
    compound_fixes = 0
    for compound, correct_phoneme in COMPOUND_WORD_FIXES.items():
        if compound in data:
            old_phoneme = data[compound]
            if old_phoneme != correct_phoneme:
                data[compound] = correct_phoneme
                compound_fixes += 1
        else:
            # Add if missing
            data[compound] = correct_phoneme
            compound_fixes += 1
    print(f"   Fixed/added {compound_fixes} compound word readings (今日→kyou, 大人→otona, etc.)")
    
    # Step 1: Add/fix missing basic kana, numbers, common characters, and verbs
    print("\nStep 1: Adding/fixing basic hiragana, katakana, numbers, common verbs, and characters...")
    added_count = 0
    numbers_added = 0
    numbers_fixed = 0
    
    # Combine all basic entries
    all_basic_entries = {
        **BASIC_HIRAGANA, 
        **BASIC_KATAKANA, 
        **COMMON_KANJI,
        **COMMON_VERBS_HIRAGANA,  # Add common verbs in hiragana
    }
    
    # Add basic kana/kanji/verbs (only if missing)
    for char, phoneme in all_basic_entries.items():
        if char not in data:
            data[char] = phoneme
            added_count += 1
    
    # OVERRIDE numbers (fix incorrect existing entries)
    # Many older dictionaries have wrong phonemes for numbers
    for char, phoneme in ALL_NUMBERS.items():
        if char not in data:
            data[char] = phoneme
            added_count += 1
            numbers_added += 1
        elif data[char] != phoneme:
            # Fix incorrect existing entry
            data[char] = phoneme
            numbers_fixed += 1
        else:
            # Already correct
            pass
    
    print(f"   Added {added_count} missing entries")
    print(f"   Fixed {numbers_fixed} incorrect number entries")
    print(f"   Numbers processed: {numbers_added + numbers_fixed} total (added {numbers_added}, fixed {numbers_fixed})")
    
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
    print(f"\n   [OK] Parallel processing complete!")
    print(f"   Found {verb_count} verbs")
    print(f"   Generated {conjugation_count} new conjugations")
    print(f"   Skipped {skipped_count} (already existed)")
    
    # Show sample conjugations
    if sample_verbs:
        print(f"\n   Sample verb conjugations:")
        for word, phoneme, vtype, count in sample_verbs:
            print(f"     • {word} ({phoneme}) [{vtype}] → {count} forms")
    
    # Step 1.6: Update word list with conjugated forms AND numbers
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
        
        # Add all numbers as words (critical for segmentation!)
        print(f"   Adding {len(ALL_NUMBERS)} number entries...", end='', flush=True)
        number_words_added = 0
        for number_word in ALL_NUMBERS.keys():
            if number_word not in word_set:
                word_set.add(number_word)
                number_words_added += 1
        print(f" Done! (+{number_words_added} new)")
        
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
        print(f"   [OK] Word list saved to ja_words.txt")
    else:
        print(f"   [WARN] {words_source} not found, skipping word list update")
    
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
    
    print(f"\r   [OK] Converted {converted_count} entries" + " " * 40)  # Clear progress line
    
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
    
    # Step 6: Build simple binary format (DIRECT load into TrieNode*)
    print(f"\nStep 6: Building simple binary format...")
    if os.path.exists(words_source):
        build_simple_binary_format(data, word_set, 'japanese.trie')
    else:
        print(f"   [WARN] Skipping binary format (word list not available)")
    
    print(f"\n[COMPLETE] Done!")
    print(f"\nSummary:")
    print(f"   - Original entries: {original_count}")
    print(f"   - Particle ha->wa fixes: {particle_fixes}")
    print(f"   - Standalone kanji fixes: {kanji_fixes} (kun-yomi corrections)")
    print(f"   - Compound word fixes: {compound_fixes} (jukujikun like 今日→kyou)")
    print(f"   - Added missing kana/kanji: {added_count}")
    print(f"   - Verbs found: {verb_count}")
    print(f"   - Verb conjugations generated: {conjugation_count}")
    if os.path.exists(words_source):
        print(f"   - Word list: {original_word_count} -> {len(word_set)} (+{words_added})")
    print(f"   - Removed punctuation: {removed_punct}")
    print(f"   - Converted to ligatures: {converted_count}")
    print(f"   - Invalid phoneme entries: {len(invalid_entries)}")
    print(f"   - Final entries: {len(data)}")
    print(f"\nOutput files:")
    print(f"   - ja_phonemes.json (phoneme dictionary)")
    if os.path.exists(words_source):
        print(f"   - ja_words.txt (word segmentation dictionary)")
        print(f"   - japanese.trie (simple binary format - direct TrieNode* load!)")
    print(f"\nNote: Particle ha -> wa fixes applied (de wa->dewa, kore wa->korewa, etc.)")
    print(f"Note: Standalone kanji use kun-yomi (水=mizu not sui, 山=yama not san, etc.)")
    print(f"Note: Compound words use special readings (今日=kyou, 大人=otona, 明日=ashita, etc.)")
    print(f"Note: Punctuation in input text will pass through unchanged")
    print(f"Note: All verb conjugations (past, te-form, negative, etc.) are now in dictionary")
    print(f"Note: Handles BOTH multi-char sequences (ts, dz, etc.) AND ligatures in verb conjugations")
    print(f"Note: Use japanese.trie for instant C++ loading (same TrieNode* structure as JSON)!")

if __name__ == '__main__':
    main()


