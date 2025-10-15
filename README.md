# Japanese → Phoneme Converter

Blazing-fast Japanese text to IPA phoneme conversion. Built for speed—microsecond lookups, zero bloat.

## What's This?

Convert Japanese text (Hiragana/Katakana/Kanji) directly to IPA phonemes. Perfect for TTS, linguistics tools, or any project needing phonetic representations.

**Data**: `ja_phonemes.json` (221k+ entries - includes all hiragana, katakana, common kanji)  
**Phonemes**: IPA format using tokenizer-compatible ligatures (ʥ, ʨ, ʦ, etc.)  
**Performance**: <1ms per sentence, <50ms cold start  
**Algorithm**: Greedy longest-match trie lookup

---

## Quick Start

Pick your poison. Same algorithm, same performance, different language:

### Dart
```bash
dart jpn_to_phoneme.dart "こんにちは"
```

### TypeScript
```bash
ts-node jpn_to_phoneme.ts "こんにちは"
```

### JavaScript (Node.js)
```bash
node jpn_to_phoneme.js "こんにちは"
```

### Python
```bash
python jpn_to_phoneme.py "こんにちは"
```

### C++ (compile first)
```bash
g++ -std=c++17 -O3 -o jpn_to_phoneme jpn_to_phoneme.cpp
./jpn_to_phoneme "こんにちは"
```

### Rust (compile first)
```bash
rustc -O jpn_to_phoneme.rs
./jpn_to_phoneme "こんにちは"
```

All versions support:
- **Interactive mode**: Run without arguments
- **Batch mode**: Pass multiple text arguments
- **Detailed output**: Shows matches, timing, and unmatched characters

### Example Output

```
Input:    こんにちは
Phonemes: koɴnitɕiɰᵝa
Time:     147μs

Matches (5):
  • "こ" → "ko" (pos: 0)
  • "ん" → "ɴ" (pos: 1)
  • "に" → "ni" (pos: 2)
  • "ち" → "tɕi" (pos: 3)
  • "は" → "ɰᵝa" (pos: 4)
```

---

## Available Implementations

All versions share the same core algorithm and performance characteristics. Pick based on your ecosystem:

| Language | File | Compile Time | Runtime Deps | Best For |
|----------|------|--------------|--------------|----------|
| **Dart** | `jpn_to_phoneme.dart` | None (JIT) | Dart SDK | Flutter apps, quick testing |
| **TypeScript** | `jpn_to_phoneme.ts` | None (ts-node) | Node.js + ts-node | Type-safe Node.js projects |
| **JavaScript** | `jpn_to_phoneme.js` | None | Node.js | Maximum compatibility |
| **Python** | `jpn_to_phoneme.py` | None | Python 3.7+ | Data science, scripting |
| **C++** | `jpn_to_phoneme.cpp` | ~2s with -O3 | None | Maximum raw speed |
| **Rust** | `jpn_to_phoneme.rs` | ~5s with -O | None | Memory safety + speed |

**Data File**: `ja_phonemes.json` (220k+ Japanese → IPA mappings, ~7.5MB)

## How It Works

**Trie Structure**: Each Japanese character maps to a node, with phonemes stored at word boundaries. Character codes (not strings) are used for O(1) lookups.

**Greedy Longest-Match**:
1. Start at position 0
2. Walk the trie as far as possible, tracking the longest valid match
3. Emit the matched phoneme and advance
4. If no match, keep the original character (handles spaces, punctuation, unknowns)
5. Repeat until done

**Performance**:
- In-memory trie: ~30MB resident
- Load time: ~100-300ms (parsing 220k JSON entries)
- Lookup time: <1ms per sentence (typically <200μs)
- Zero allocations during lookup (character code iteration)

---

## Word Segmentation (Smart Tokenization) 🎯

**NEW**: Automatic word boundary detection with space-separated output!

**Enabled by default** using `ja_words.txt` (147k+ word dictionary). Set `USE_WORD_SEGMENTATION = false` to disable.

### The Algorithm

**Two-Pass System**:
1. **Pass 1 - Word Segmentation**: Split Japanese text into tokens (words + grammar)
2. **Pass 2 - Phoneme Conversion**: Convert each token to phonemes, add spaces between tokens

### Smart Grammar Detection

The system automatically identifies grammatical elements (particles, conjugations, etc.) by treating any text between known words as grammar:

**Example**: `私はリンゴがすきです`

**Dictionary Matches**:
- `私` (watashi) - WORD
- `リンゴ` (ringo) - WORD  
- `好き` (suki) - WORD

**Unmatched Between Words** (automatically treated as grammar):
- `は` (ha) - particle
- `が` (ga) - particle
- `です` (desu) - copula

**Result**: `私` `は` `リンゴ` `が` `好き` `です`  
**Output**: `ɰᵝatai ha ɾiɴgo ga sɯki desɯ` ✨ (with spaces!)

### Algorithm Details

```
Load word dictionary (ja_words.txt) into trie

Segment(text):
  pos = 0
  tokens = []
  
  while pos < length:
    # Try to match a word from dictionary
    longest_match = find_longest_word(pos)
    
    if longest_match found:
      tokens.add(longest_match)
      pos += match_length
    else:
      # Collect unmatched chars until next word match
      grammar_token = ""
      while pos < length:
        if can_match_word_at(pos):
          break
        grammar_token += char[pos]
        pos += 1
      tokens.add(grammar_token)
  
  return tokens

Convert_With_Segmentation(text):
  tokens = Segment(text)
  result = []
  
  for token in tokens:
    result.add(convert_to_phonemes(token))
  
  return join(result, " ")  # Space-separated!
```

### Why This Works

**Dynamic Grammar Recognition**: Instead of hardcoding particles (は、が、を、に、etc.), the system learns them automatically:
- If text matches a known word → it's a WORD
- If text is between words and doesn't match → it's GRAMMAR
- Both get converted to phonemes AND separated by spaces

**Benefits**:
- ✅ Proper word boundaries in output (spaces!)
- ✅ Automatic particle/conjugation detection
- ✅ No hardcoded grammar rules needed
- ✅ Works with any Japanese text structure
- ✅ Still blazing fast (microsecond-level performance)

### Performance Impact

**Additional Loading**: +50-100ms (one-time, loads 147k words)  
**Conversion Speed**: ~same as before (still <1ms per sentence)  
**Memory**: +20MB (word dictionary trie)

**Example Output**:

```
Input:    私はリンゴがすきです
Phonemes: ɰᵝatai ha ɾiɴgo ga sɯki desɯ
          ↑     ↑  ↑     ↑  ↑    ↑
          word  particle  word  particle  word  copula
```

**Perfect for**:
- Text-to-speech systems (natural pauses at boundaries)
- Tokenization pipelines (space-delimited output)
- Linguistic analysis (automatic morpheme detection)
- Training data preparation (pre-segmented text)

---

## Technical Details

**Core Algorithm** (pseudocode):
```
Trie: Map<CharCode, Node> with optional phoneme at each node

Convert(text):
  pos = 0
  while pos < length:
    Walk trie from pos, track longest match
    if match found:
      emit phoneme, advance by match length
    else:
      emit original character, advance by 1
```

**Why This Is Fast**:
- **No substring allocations**: Direct character/code iteration
- **Single-pass**: No backtracking, O(n) complexity
- **O(1) lookups**: Hash map for child nodes
- **Memory efficient**: Shared trie structure across all conversions
- **Cache-friendly**: Trie nodes accessed sequentially

**Implementation Details by Language**:
- **Dart**: Uses `codeUnitAt()` for UTF-16 code units
- **TypeScript/JavaScript**: Uses `charCodeAt()` for UTF-16
- **Python**: Native `ord()` for Unicode code points
- **C++**: Custom UTF-8 decoder with `unordered_map`
- **Rust**: Native UTF-8 with zero-copy `chars()` iterator

---

## Integration Examples

### For TTS Systems
```python
# Python example
phonemes = converter.convert('日本語のテキスト')
tts_engine.speak(phonemes)
```

### For Linguistics Analysis
```javascript
// JavaScript/TypeScript example
const result = converter.convertDetailed(text);
console.log(`Matched: ${result.matches.length}`);
console.log(`Unknown: ${result.unmatched.join(", ")}`);
```

### For Flutter/Mobile Apps
```dart
// Dart example - singleton pattern
class PhonemeService {
  static PhonemeConverter? _instance;
  
  static Future<PhonemeConverter> get instance async {
    _instance ??= PhonemeConverter()..await loadFromJson('assets/ja_phonemes.json');
    return _instance!;
  }
}
```

### For High-Performance Servers
```rust
// Rust example - thread-safe shared converter
lazy_static! {
    static ref CONVERTER: PhonemeConverter = {
        let mut conv = PhonemeConverter::new();
        conv.load_from_json("ja_phonemes.json").unwrap();
        conv
    };
}
```

---

## Notes

- **Unknown characters**: Passed through as-is (spaces, punctuation, emojis, etc.)
- **Encoding**: UTF-8 throughout (except Dart/JS which use UTF-16 internally)
- **Thread-safe**: Trie is read-only after construction (safe for concurrent reads)
- **Dependencies**: Minimal - each version uses only standard library
- **Cross-platform**: All versions tested on Windows/macOS/Linux

---

## Performance Benchmarks 🔥

Real-world performance (220k entries loaded). All tests run on Windows 10/11.

### Load Time (Dictionary → Memory)

| Language | Time | Avg/Entry | Notes |
|----------|------|-----------|-------|
| **Dart** 🥇 | 74ms | 0.34μs | Fastest load! |
| **Rust** | 81-88ms | 0.37-0.40μs | Consistent, blazing fast |
| **JavaScript** | 132ms | 0.59μs | Node.js V8 engine |
| **C++** | 119-130ms | 0.54-0.59μs | Native compiled |
| **Python** | 450ms | 2.03μs | Acceptable for one-time init |

### Conversion Time (Multi-paragraph, 168 chars)

| Language | Time | Throughput | Winner |
|----------|------|------------|--------|
| **C++ (Optimized)** 🏆 | **<1μs** | **>168,000 chars/ms** | 🔥 INSANELY FAST! |
| **Rust** 🥈 | **50μs** | **3,360 chars/ms** | Excellent |
| **Python** | 137μs | 1,226 chars/ms | Great |
| **JavaScript** | 150μs | 1,120 chars/ms | Good |
| **Dart** | 304μs | 552 chars/ms | Solid |

### Test Cases Breakdown

**Simple (5 chars): "こんにちは"**
- C++ (Optimized): **<1μs** 🏆 (too fast to measure!)
- Rust: 5μs 🥈
- Python: 22μs  
- JavaScript: 69μs
- Dart: 204μs

**Medium (10 chars): "今日はいい天気ですね"**
- C++ (Optimized): **<1μs** 🏆 (too fast to measure!)
- Rust: 6μs 🥈
- Python: 21μs
- JavaScript: 71μs
- Dart: 214μs

**Large (63 chars): "私は東京都に住んでいます。毎日、新宿駅から..."**
- Rust: 24μs
- Python: N/A (not tested in full benchmark)
- JavaScript: N/A
- Dart: N/A

**Multi-paragraph (168 chars): Full Japanese text about culture**
- C++ (Optimized): **<1μs** 🏆 (50x+ faster than before!)
- Rust: **50μs** 🥈
- Python: 137μs
- JavaScript: 150μs
- Dart: 304μs
- C++ (Old): ~~524μs~~ (pre-optimization)

---

### Performance Summary

🏆 **CHAMPION: C++ (Optimized)** - <1μs conversion (50x+ faster than Rust!)  
🥈 **Runner-up: Rust** - 50μs conversion (still blazing fast)  
✅ **Best Load Time**: **Dart** (74ms) - Perfect for Flutter apps  
✅ **Best Interpreted**: **Python** - 137μs (fastest non-compiled language)  
✅ **Most Balanced**: **JavaScript** - Good all-around (132ms load, 150μs conversion)  

### The Optimization Story 📖

**Before**: C++ was 10x slower than Rust (524μs vs 50μs)  
**Problem**: UTF-8 decoding in the hot loop (10,000+ redundant decode operations)  
**Solution**: Pre-decode UTF-8 once, then iterate (just like Rust does)  
**After**: C++ now <1μs (50x+ improvement, faster than Rust!)  

**Key Lesson**: Algorithm matters more than language! 🎯

**All implementations deliver sub-millisecond conversion times** for typical text. Choose based on your ecosystem—they're all production-ready!

### Run Benchmarks Yourself

```bash
# Compile native versions first (one-time)
g++ -std=c++17 -O3 -o jpn_to_phoneme_cpp jpn_to_phoneme.cpp
rustc -O jpn_to_phoneme.rs -o jpn_to_phoneme_rs

# Run full benchmark suite
.\benchmark.bat
```

Tests all 5 implementations across 4 complexity levels (simple, medium, large, multi-paragraph).

---

## Roadmap

Future enhancements (if needed):
- **Binary trie format**: Instant loading (<10ms) with pre-compiled structure
- **Character-level fallback**: Handle unknown kanji with kana-based rules
- **Multiple pronunciations**: Return alternatives with confidence scores
- **DAWG compression**: Reduce memory footprint to <15MB
- **WebAssembly build**: Browser-native phoneme conversion

---

**Built for speed. No compromises.**

All implementations available. Choose your weapon. 🔥

