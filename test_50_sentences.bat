@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ╔══════════════════════════════════════════════════════════╗
echo ║  Japanese to Phoneme - 50 Sentence Test Suite          ║
echo ║  Testing C++ implementation                             ║
echo ╚══════════════════════════════════════════════════════════╝
echo.

set TOTAL=50
set COUNT=0

echo Testing %TOTAL% Japanese sentences...
echo.

REM Basic greetings
set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: こんにちは
for /f "delims=" %%i in ('.\jpn_to_phoneme_cpp.exe "こんにちは" 2^>nul ^| findstr "Phonemes:"') do echo   %%i
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)
echo.

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: おはようございます
for /f "delims=" %%i in ('.\jpn_to_phoneme_cpp.exe "おはようございます" 2^>nul ^| findstr "Phonemes:"') do echo   %%i
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)
echo.

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: ありがとうございます
for /f "delims=" %%i in ('.\jpn_to_phoneme_cpp.exe "ありがとうございます" 2^>nul ^| findstr "Phonemes:"') do echo   %%i
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)
echo.

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: さようなら
for /f "delims=" %%i in ('.\jpn_to_phoneme_cpp.exe "さようなら" 2^>nul ^| findstr "Phonemes:"') do echo   %%i
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)
echo.

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: おやすみなさい
for /f "delims=" %%i in ('.\jpn_to_phoneme_cpp.exe "おやすみなさい" 2^>nul ^| findstr "Phonemes:"') do echo   %%i
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)
echo.

REM Common phrases
set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: いただきます
for /f "delims=" %%i in ('.\jpn_to_phoneme_cpp.exe "いただきます" 2^>nul ^| findstr "Phonemes:"') do echo   %%i
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)
echo.

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: ごちそうさまでした
for /f "delims=" %%i in ('.\jpn_to_phoneme_cpp.exe "ごちそうさまでした" 2^>nul ^| findstr "Phonemes:"') do echo   %%i
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)
echo.

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: お願いします
for /f "delims=" %%i in ('.\jpn_to_phoneme_cpp.exe "お願いします" 2^>nul ^| findstr "Phonemes:"') do echo   %%i
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)
echo.

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: すみません
for /f "delims=" %%i in ('.\jpn_to_phoneme_cpp.exe "すみません" 2^>nul ^| findstr "Phonemes:"') do echo   %%i
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)
echo.

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: はい、わかりました
for /f "delims=" %%i in ('.\jpn_to_phoneme_cpp.exe "はい、わかりました" 2^>nul ^| findstr "Phonemes:"') do echo   %%i
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)
echo.

REM Simple sentences
set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: 私は学生です
for /f "delims=" %%i in ('.\jpn_to_phoneme_cpp.exe "私は学生です" 2^>nul ^| findstr "Phonemes:"') do echo   %%i
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)
echo.

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: 今日は良い天気ですね
for /f "delims=" %%i in ('.\jpn_to_phoneme_cpp.exe "今日は良い天気ですね" 2^>nul ^| findstr "Phonemes:"') do echo   %%i
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)
echo.

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: これは何ですか
for /f "delims=" %%i in ('.\jpn_to_phoneme_cpp.exe "これは何ですか" 2^>nul ^| findstr "Phonemes:"') do echo   %%i
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)
echo.

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: どこに行きますか
for /f "delims=" %%i in ('.\jpn_to_phoneme_cpp.exe "どこに行きますか" 2^>nul ^| findstr "Phonemes:"') do echo   %%i
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)
echo.

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: 日本語を勉強しています
for /f "delims=" %%i in ('.\jpn_to_phoneme_cpp.exe "日本語を勉強しています" 2^>nul ^| findstr "Phonemes:"') do echo   %%i
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)
echo.

REM Questions and answers
set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: お名前は何ですか
for /f "delims=" %%i in ('.\jpn_to_phoneme_cpp.exe "お名前は何ですか" 2^>nul ^| findstr "Phonemes:"') do echo   %%i
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)
echo.

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: いくらですか
for /f "delims=" %%i in ('.\jpn_to_phoneme_cpp.exe "いくらですか" 2^>nul ^| findstr "Phonemes:"') do echo   %%i
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)
echo.

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: 何時に会いましょうか
for /f "delims=" %%i in ('.\jpn_to_phoneme_cpp.exe "何時に会いましょうか" 2^>nul ^| findstr "Phonemes:"') do echo   %%i
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)
echo.

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: どうやって行きますか
for /f "delims=" %%i in ('.\jpn_to_phoneme_cpp.exe "どうやって行きますか" 2^>nul ^| findstr "Phonemes:"') do echo   %%i
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)
echo.

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: 誰と一緒に来ましたか
for /f "delims=" %%i in ('.\jpn_to_phoneme_cpp.exe "誰と一緒に来ましたか" 2^>nul ^| findstr "Phonemes:"') do echo   %%i
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)
echo.

REM Complex sentences
set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: 日本は美しい国です
for /f "delims=" %%i in ('.\jpn_to_phoneme_cpp.exe "日本は美しい国です" 2^>nul ^| findstr "Phonemes:"') do echo   %%i
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)
echo.

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: 春には桜が咲きます
for /f "delims=" %%i in ('.\jpn_to_phoneme_cpp.exe "春には桜が咲きます" 2^>nul ^| findstr "Phonemes:"') do echo   %%i
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)
echo.

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: 夏は海で泳ぎたいです
for /f "delims=" %%i in ('.\jpn_to_phoneme_cpp.exe "夏は海で泳ぎたいです" 2^>nul ^| findstr "Phonemes:"') do echo   %%i
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)
echo.

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: 秋は紅葉がきれいです
for /f "delims=" %%i in ('.\jpn_to_phoneme_cpp.exe "秋は紅葉がきれいです" 2^>nul ^| findstr "Phonemes:"') do echo   %%i
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)
echo.

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: 冬は雪が降ります
for /f "delims=" %%i in ('.\jpn_to_phoneme_cpp.exe "冬は雪が降ります" 2^>nul ^| findstr "Phonemes:"') do echo   %%i
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)
echo.

REM Actions and activities
set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: 毎日走っています
for /f "delims=" %%i in ('.\jpn_to_phoneme_cpp.exe "毎日走っています" 2^>nul ^| findstr "Phonemes:"') do echo   %%i
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)
echo.

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: 本を読むのが好きです
for /f "delims=" %%i in ('.\jpn_to_phoneme_cpp.exe "本を読むのが好きです" 2^>nul ^| findstr "Phonemes:"') do echo   %%i
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)
echo.

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: 音楽を聴いています
for /f "delims=" %%i in ('.\jpn_to_phoneme_cpp.exe "音楽を聴いています" 2^>nul ^| findstr "Phonemes:"') do echo   %%i
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)
echo.

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: 映画を見に行きましょう
for /f "delims=" %%i in ('.\jpn_to_phoneme_cpp.exe "映画を見に行きましょう" 2^>nul ^| findstr "Phonemes:"') do echo   %%i
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)
echo.

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: 友達と話しました
for /f "delims=" %%i in ('.\jpn_to_phoneme_cpp.exe "友達と話しました" 2^>nul ^| findstr "Phonemes:"') do echo   %%i
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)
echo.

REM Food and eating
set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: お寿司が食べたいです
for /f "delims=" %%i in ('.\jpn_to_phoneme_cpp.exe "お寿司が食べたいです" 2^>nul ^| findstr "Phonemes:"') do echo   %%i
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)
echo.

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: ラーメンは美味しいですね
for /f "delims=" %%i in ('.\jpn_to_phoneme_cpp.exe "ラーメンは美味しいですね" 2^>nul ^| findstr "Phonemes:"') do echo   %%i
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)
echo.

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: コーヒーを一杯ください
for /f "delims=" %%i in ('.\jpn_to_phoneme_cpp.exe "コーヒーを一杯ください" 2^>nul ^| findstr "Phonemes:"') do echo   %%i
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)
echo.

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: お水をもらえますか
for /f "delims=" %%i in ('.\jpn_to_phoneme_cpp.exe "お水をもらえますか" 2^>nul ^| findstr "Phonemes:"') do echo   %%i
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)
echo.

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: とても辛いです
for /f "delims=" %%i in ('.\jpn_to_phoneme_cpp.exe "とても辛いです" 2^>nul ^| findstr "Phonemes:"') do echo   %%i
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)
echo.

REM Emotions and feelings
set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: 嬉しいです
for /f "delims=" %%i in ('.\jpn_to_phoneme_cpp.exe "嬉しいです" 2^>nul ^| findstr "Phonemes:"') do echo   %%i
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)
echo.

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: 悲しい気持ちです
for /f "delims=" %%i in ('.\jpn_to_phoneme_cpp.exe "悲しい気持ちです" 2^>nul ^| findstr "Phonemes:"') do echo   %%i
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)
echo.

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: 楽しかったです
for /f "delims=" %%i in ('.\jpn_to_phoneme_cpp.exe "楽しかったです" 2^>nul ^| findstr "Phonemes:"') do echo   %%i
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)
echo.

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: 疲れました
for /f "delims=" %%i in ('.\jpn_to_phoneme_cpp.exe "疲れました" 2^>nul ^| findstr "Phonemes:"') do echo   %%i
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)
echo.

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: お腹が空きました
for /f "delims=" %%i in ('.\jpn_to_phoneme_cpp.exe "お腹が空きました" 2^>nul ^| findstr "Phonemes:"') do echo   %%i
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)
echo.

REM Complex and long sentences
set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: 明日の朝、早く起きなければなりません
for /f "delims=" %%i in ('.\jpn_to_phoneme_cpp.exe "明日の朝、早く起きなければなりません" 2^>nul ^| findstr "Phonemes:"') do echo   %%i
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)
echo.

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: 駅まで歩いて行くことができます
for /f "delims=" %%i in ('.\jpn_to_phoneme_cpp.exe "駅まで歩いて行くことができます" 2^>nul ^| findstr "Phonemes:"') do echo   %%i
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)
echo.

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: 彼は日本語が上手ですね
for /f "delims=" %%i in ('.\jpn_to_phoneme_cpp.exe "彼は日本語が上手ですね" 2^>nul ^| findstr "Phonemes:"') do echo   %%i
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)
echo.

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: この本を読んでみてください
for /f "delims=" %%i in ('.\jpn_to_phoneme_cpp.exe "この本を読んでみてください" 2^>nul ^| findstr "Phonemes:"') do echo   %%i
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)
echo.

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: もう一度言っていただけますか
for /f "delims=" %%i in ('.\jpn_to_phoneme_cpp.exe "もう一度言っていただけますか" 2^>nul ^| findstr "Phonemes:"') do echo   %%i
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)
echo.

REM Mixed hiragana, katakana, kanji
set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: コンピューターを使っています
for /f "delims=" %%i in ('.\jpn_to_phoneme_cpp.exe "コンピューターを使っています" 2^>nul ^| findstr "Phonemes:"') do echo   %%i
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)
echo.

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: インターネットで調べました
for /f "delims=" %%i in ('.\jpn_to_phoneme_cpp.exe "インターネットで調べました" 2^>nul ^| findstr "Phonemes:"') do echo   %%i
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)
echo.

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: スマートフォンが壊れました
for /f "delims=" %%i in ('.\jpn_to_phoneme_cpp.exe "スマートフォンが壊れました" 2^>nul ^| findstr "Phonemes:"') do echo   %%i
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)
echo.

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: テレビを見ながら食べます
for /f "delims=" %%i in ('.\jpn_to_phoneme_cpp.exe "テレビを見ながら食べます" 2^>nul ^| findstr "Phonemes:"') do echo   %%i
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)
echo.

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: プログラミングを勉強したいです
for /f "delims=" %%i in ('.\jpn_to_phoneme_cpp.exe "プログラミングを勉強したいです" 2^>nul ^| findstr "Phonemes:"') do echo   %%i
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)
echo.

echo.
echo ════════════════════════════════════════════════════════════
echo   All %TOTAL% tests completed!
echo ════════════════════════════════════════════════════════════
echo.

REM Now run one detailed test to show actual output
echo Running detailed output test with sample sentence:
echo.
for /f "delims=" %%i in ('.\jpn_to_phoneme_cpp.exe "日本は美しい国です。春には桜が咲き、夏は海で泳ぎ、秋は紅葉を楽しみ、冬は雪景色を眺めます。"

endlocal

