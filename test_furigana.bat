@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

echo.
echo ╔══════════════════════════════════════════════════════════════════════════╗
echo ║  Japanese Phoneme Converter - Furigana Hint Test Suite                  ║
echo ║  Testing smart tokenization with furigana hints for proper names        ║
echo ╚══════════════════════════════════════════════════════════════════════════╝
echo.

REM Check if executable exists
if not exist "jpn_to_phoneme_cpp.exe" (
    echo ❌ Error: jpn_to_phoneme_cpp.exe not found
    echo    Please compile the C++ version first:
    echo    g++ -std=c++17 -O3 -o jpn_to_phoneme_cpp jpn_to_phoneme.cpp
    exit /b 1
)

REM Check if dictionary exists
if not exist "ja_phonemes.json" (
    echo ❌ Error: ja_phonemes.json not found
    exit /b 1
)

REM Check if word dictionary exists
if not exist "ja_words.txt" (
    echo ⚠️  Warning: ja_words.txt not found - segmentation will be disabled
    echo.
)

echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo 🔥 TEST 1: Basic Name WITHOUT Furigana Hint (Expected: BROKEN)
echo    Problem: Name not in dictionary gets attached to particle
echo.
jpn_to_phoneme_cpp.exe "けんたはバカ"
echo.

echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo 🔥 TEST 2: Basic Name WITH Furigana Hint (Expected: FIXED ✅)
echo    Solution: Furigana hint marks name as single unit
echo.
jpn_to_phoneme_cpp.exe "健太「けんた」はバカ"
echo.
echo Expected: keɴta wa baka
echo Result should have proper particle separation: けんた は バカ
echo.

echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo 🔥 TEST 3: Name with が Particle (Expected: ✅)
echo    Testing: Subject marker particle
echo.
jpn_to_phoneme_cpp.exe "健太「けんた」がバカ"
echo.
echo Expected: keɴta ga baka
echo.

echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo 🔥 TEST 4: Name with を Particle (Expected: ✅)
echo    Testing: Object marker particle
echo.
jpn_to_phoneme_cpp.exe "健太「けんた」を見た"
echo.
echo Expected: keɴta o mita (or similar with proper spacing)
echo.

echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo 🔥 TEST 5: Name with の Particle (Expected: ✅)
echo    Testing: Possessive particle
echo.
jpn_to_phoneme_cpp.exe "健太「けんた」の本"
echo.
echo Expected: keɴta no hoɴ
echo.

echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo 🔥 TEST 6: Multiple Names with と Particle (Expected: ✅)
echo    Testing: Multiple furigana hints in one sentence
echo.
jpn_to_phoneme_cpp.exe "健太「けんた」と「と」雪「ゆき」"
echo.
echo Expected: keɴta to jɯki (with proper spacing between all tokens)
echo.

echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo 🔥 TEST 7: Complex Sentence with Name (Expected: ✅)
echo    Testing: Name in full sentence context
echo.
jpn_to_phoneme_cpp.exe "私「わたし」は健太「けんた」が好きです"
echo.
echo Expected: wataɕi wa keɴta ga sɯki desɯ
echo All particles (は、が) should be properly separated!
echo.

echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo 🔥 TEST 8: Foreign Name in Japanese (Expected: ✅)
echo    Testing: Katakana names with furigana hints
echo.
jpn_to_phoneme_cpp.exe "ジョン「じょん」はアメリカ人です"
echo.
echo Expected: dʑoɴ wa amerika dʑiɴ desɯ
echo.

echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo 🔥 TEST 9: Name at End of Sentence (Expected: ✅)
echo    Testing: Furigana hint at different sentence positions
echo.
jpn_to_phoneme_cpp.exe "これは健太「けんた」です"
echo.
echo Expected: kore wa keɴta desɯ
echo.

echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo 🔥 TEST 10: Name with Verb (Expected: ✅)
echo    Testing: Name followed by verb
echo.
jpn_to_phoneme_cpp.exe "健太「けんた」は走る"
echo.
echo Expected: keɴta wa haɕirɯ
echo.

echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo 🔥 TEST 11: Empty Furigana (Expected: Use Original Text)
echo    Testing: Edge case with empty reading
echo.
jpn_to_phoneme_cpp.exe "健太「」はバカ"
echo.
echo Expected: Should use original kanji 健太 and convert normally
echo.

echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo 🔥 TEST 12: No Furigana (Expected: Normal Operation)
echo    Testing: Regular text without any furigana hints
echo.
jpn_to_phoneme_cpp.exe "私はリンゴが好き"
echo.
echo Expected: wataɕi wa riɴgo ga sɯki (normal conversion)
echo.

echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo 🔥 TEST 13: Dictionary Name (Expected: Works Without Furigana)
echo    Testing: Names that ARE in dictionary work fine without hints
echo.
jpn_to_phoneme_cpp.exe "東京「とうきょう」は大きい"
echo.
echo Expected: toːkjoː wa oːkiː
echo Note: 東京 is likely in dictionary, so furigana is optional here
echo.

echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo 🔥 TEST 14: Three Names in Sequence (Expected: ✅)
echo    Testing: Multiple consecutive names
echo.
jpn_to_phoneme_cpp.exe "健太「けんた」と雪「ゆき」と太郎「たろう」"
echo.
echo Expected: keɴta to jɯki to taroː
echo All と particles should be properly separated!
echo.

echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo 🔥 TEST 15: Long Sentence with Multiple Grammar Elements (Expected: ✅)
echo    Testing: Complex sentence structure
echo.
jpn_to_phoneme_cpp.exe "健太「けんた」は学校「がっこう」で雪「ゆき」に会いました"
echo.
echo Expected: All particles (は、で、に) properly separated
echo.

echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo 🔥 TEST 16: Compound Word Detection - 見る (Expected: Use Dictionary ✅)
echo    Testing: Should detect 見る as dictionary word and drop furigana
echo.
jpn_to_phoneme_cpp.exe "見「み」る"
echo.
echo Expected: Should use dictionary entry for 見る (not force み reading)
echo.

echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo 🔥 TEST 17: Compound Word Detection - 食べる (Expected: Use Dictionary ✅)
echo    Testing: Should detect 食べる as dictionary word
echo.
jpn_to_phoneme_cpp.exe "食「た」べる"
echo.
echo Expected: Should use dictionary entry for 食べる
echo.

echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo 🔥 TEST 18: Compound Word Detection - 来た (Expected: Use Dictionary ✅)
echo    Testing: Should detect 来た as dictionary word
echo.
jpn_to_phoneme_cpp.exe "来「き」た"
echo.
echo Expected: Should use dictionary entry for 来た
echo.

echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo 🔥 TEST 19: Name + Honorific (Expected: Use Furigana Hint ✅)
echo    Testing: Should NOT find 健太さん as single word, use hint
echo.
jpn_to_phoneme_cpp.exe "健太「けんた」さん"
echo.
echo Expected: keɴta saɴ (use furigana hint since 健太さん isn't a word)
echo.

echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo 🔥 TEST 20: Compound in Sentence (Expected: Smart Detection ✅)
echo    Testing: Mixed compound detection and furigana hints
echo.
jpn_to_phoneme_cpp.exe "健太「けんた」は見「み」るのが好き"
echo.
echo Expected: keɴta ha miru no ga sɯki - name uses hint, 見る uses dictionary
echo.

echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo 🔥 TEST 21: Complex Verb Form - 見ている (Expected: Use Dictionary ✅)
echo    Testing: Should detect longer compound 見ている
echo.
jpn_to_phoneme_cpp.exe "見「み」ている"
echo.
echo Expected: Should use dictionary entry for compound if found
echo.

echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo 🔥 TEST 22: Non-Compound (Expected: Use Furigana Hint ✅)
echo    Testing: Should use hint when kanji+text isn't a word
echo.
jpn_to_phoneme_cpp.exe "健太「けんた」る"
echo.
echo Expected: keɴtaru (use hint since 健太る isn't a word)
echo.

echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo 🔥 TEST 23: Reading-only Furigana in Context (Expected: Smart ✅)
echo    Testing: 見「み」てください
echo.
jpn_to_phoneme_cpp.exe "見「み」てください"
echo.
echo Expected: Should detect 見て as compound, then continue with ください
echo.

echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo ✨ FURIGANA HINT TEST SUITE COMPLETE!
echo.
echo 📊 KEY OBSERVATIONS:
echo    • Furigana hints should properly separate names from particles
echo    • Markers (‹›) should be invisible in final output
echo    • All grammar particles should be recognized intrinsically
echo    • No hardcoded particle lists needed - smart segmentation does it!
echo    • Compound word detection prioritizes dictionary over forced readings
echo    • Smart detection: kanji「reading」+text checks for compounds first
echo.
echo 🎯 SUCCESS CRITERIA:
echo    ✅ Names followed by は、が、を、の、と should have proper spacing
echo    ✅ Multiple furigana hints in one sentence should work
echo    ✅ Text without furigana hints should work normally
echo    ✅ Markers should not appear in phoneme output
echo    ✅ Compound words like 見る、食べる、来た use dictionary (not forced reading)
echo    ✅ Non-compounds like 健太さん use furigana hint (not dictionary)
echo.

pause

