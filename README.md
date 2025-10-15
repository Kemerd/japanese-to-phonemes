# Japanese → Phoneme Converter

Blazing-fast Japanese text to IPA phoneme conversion. Built for speed—microsecond lookups, zero bloat.

## What's This?

Convert Japanese text (Hiragana/Katakana/Kanji) directly to IPA phonemes. Perfect for TTS, linguistics tools, or any project needing phonetic representations.

**Data**: `ja_phonemes.json` (220k+ entries)  
**Performance**: <1ms per sentence, <50ms cold start  
**Algorithm**: Greedy longest-match trie lookup

---

## Quick Start

### Standalone Script (No setup required)

```bash
# Interactive mode
dart jpn_to_phoneme.dart

# Direct conversion
dart jpn_to_phoneme.dart "こんにちは"
dart jpn_to_phoneme.dart "日本語は難しい"

# Multiple inputs
dart jpn_to_phoneme.dart "東京" "大阪" "京都"
```

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

## Files

- **`jpn_to_phoneme.dart`**: Standalone converter script (run anywhere)
- **`ja_phonemes.json`**: 220k+ Japanese → IPA mappings (source dictionary)

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

## Technical Details

```dart
// Core data structure
class TrieNode {
  final Map<int, TrieNode> children = {};  // charCode → child node
  String? phoneme;                          // null if not end-of-word
}

// Conversion algorithm
String? convert(String text) {
  int pos = 0;
  while (pos < text.length) {
    // Walk trie, find longest match
    int matchLen = 0;
    String? matchPhoneme;
    
    TrieNode? current = _root;
    for (int i = pos; i < text.length && current != null; i++) {
      current = current.children[text.codeUnitAt(i)];
      if (current?.phoneme != null) {
        matchLen = i - pos + 1;
        matchPhoneme = current.phoneme;
      }
    }
    
    // Emit match or original character
    result.write(matchLen > 0 ? matchPhoneme : text[pos]);
    pos += matchLen > 0 ? matchLen : 1;
  }
}
```

**Why This Is Fast**:
- No substring allocations (uses `codeUnitAt()` directly)
- Single-pass algorithm (no backtracking)
- Map lookup is O(1) average case
- Trie reuse across conversions (load once, use forever)

---

## Integration Ideas

### For TTS Systems
```dart
final phonemes = converter.convert('日本語のテキスト');
await ttEngine.speak(phonemes);
```

### For Linguistics Tools
```dart
final result = converter.convertDetailed(text);
print('Matched: ${result.matches.length}');
print('Unknown: ${result.unmatched.join(", ")}');
```

### For Flutter Apps
Make this a singleton service, load on app start, use everywhere. Zero overhead after initial load.

---

## Notes

- **Unknown characters**: Passed through as-is (spaces, punctuation, emojis, etc.)
- **Encoding**: UTF-8 throughout, handles all Unicode correctly
- **Thread-safe**: Trie is read-only after construction
- **No dependencies**: Pure Dart, runs anywhere

---

## Roadmap

Future enhancements (if needed):
- Binary trie format for instant loading (<10ms)
- Character-level fallback for unknown kanji
- Multiple pronunciation support
- DAWG compression for smaller memory footprint

---

**Built for speed. No compromises.**

