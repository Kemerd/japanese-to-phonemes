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
.\jpn_to_phoneme_cpp.exe "こんにちは" >nul 2>&1
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: おはようございます
.\jpn_to_phoneme_cpp.exe "おはようございます" >nul 2>&1
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: ありがとうございます
.\jpn_to_phoneme_cpp.exe "ありがとうございます" >nul 2>&1
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: さようなら
.\jpn_to_phoneme_cpp.exe "さようなら" >nul 2>&1
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: おやすみなさい
.\jpn_to_phoneme_cpp.exe "おやすみなさい" >nul 2>&1
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)

REM Common phrases
set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: いただきます
.\jpn_to_phoneme_cpp.exe "いただきます" >nul 2>&1
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: ごちそうさまでした
.\jpn_to_phoneme_cpp.exe "ごちそうさまでした" >nul 2>&1
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: お願いします
.\jpn_to_phoneme_cpp.exe "お願いします" >nul 2>&1
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: すみません
.\jpn_to_phoneme_cpp.exe "すみません" >nul 2>&1
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: はい、わかりました
.\jpn_to_phoneme_cpp.exe "はい、わかりました" >nul 2>&1
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)

REM Simple sentences
set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: 私は学生です
.\jpn_to_phoneme_cpp.exe "私は学生です" >nul 2>&1
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: 今日は良い天気ですね
.\jpn_to_phoneme_cpp.exe "今日は良い天気ですね" >nul 2>&1
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: これは何ですか
.\jpn_to_phoneme_cpp.exe "これは何ですか" >nul 2>&1
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: どこに行きますか
.\jpn_to_phoneme_cpp.exe "どこに行きますか" >nul 2>&1
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: 日本語を勉強しています
.\jpn_to_phoneme_cpp.exe "日本語を勉強しています" >nul 2>&1
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)

REM Questions and answers
set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: お名前は何ですか
.\jpn_to_phoneme_cpp.exe "お名前は何ですか" >nul 2>&1
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: いくらですか
.\jpn_to_phoneme_cpp.exe "いくらですか" >nul 2>&1
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: 何時に会いましょうか
.\jpn_to_phoneme_cpp.exe "何時に会いましょうか" >nul 2>&1
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: どうやって行きますか
.\jpn_to_phoneme_cpp.exe "どうやって行きますか" >nul 2>&1
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: 誰と一緒に来ましたか
.\jpn_to_phoneme_cpp.exe "誰と一緒に来ましたか" >nul 2>&1
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)

REM Complex sentences
set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: 日本は美しい国です
.\jpn_to_phoneme_cpp.exe "日本は美しい国です" >nul 2>&1
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: 春には桜が咲きます
.\jpn_to_phoneme_cpp.exe "春には桜が咲きます" >nul 2>&1
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: 夏は海で泳ぎたいです
.\jpn_to_phoneme_cpp.exe "夏は海で泳ぎたいです" >nul 2>&1
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: 秋は紅葉がきれいです
.\jpn_to_phoneme_cpp.exe "秋は紅葉がきれいです" >nul 2>&1
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: 冬は雪が降ります
.\jpn_to_phoneme_cpp.exe "冬は雪が降ります" >nul 2>&1
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)

REM Actions and activities
set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: 毎日走っています
.\jpn_to_phoneme_cpp.exe "毎日走っています" >nul 2>&1
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: 本を読むのが好きです
.\jpn_to_phoneme_cpp.exe "本を読むのが好きです" >nul 2>&1
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: 音楽を聴いています
.\jpn_to_phoneme_cpp.exe "音楽を聴いています" >nul 2>&1
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: 映画を見に行きましょう
.\jpn_to_phoneme_cpp.exe "映画を見に行きましょう" >nul 2>&1
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: 友達と話しました
.\jpn_to_phoneme_cpp.exe "友達と話しました" >nul 2>&1
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)

REM Food and eating
set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: お寿司が食べたいです
.\jpn_to_phoneme_cpp.exe "お寿司が食べたいです" >nul 2>&1
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: ラーメンは美味しいですね
.\jpn_to_phoneme_cpp.exe "ラーメンは美味しいですね" >nul 2>&1
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: コーヒーを一杯ください
.\jpn_to_phoneme_cpp.exe "コーヒーを一杯ください" >nul 2>&1
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: お水をもらえますか
.\jpn_to_phoneme_cpp.exe "お水をもらえますか" >nul 2>&1
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: とても辛いです
.\jpn_to_phoneme_cpp.exe "とても辛いです" >nul 2>&1
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)

REM Emotions and feelings
set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: 嬉しいです
.\jpn_to_phoneme_cpp.exe "嬉しいです" >nul 2>&1
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: 悲しい気持ちです
.\jpn_to_phoneme_cpp.exe "悲しい気持ちです" >nul 2>&1
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: 楽しかったです
.\jpn_to_phoneme_cpp.exe "楽しかったです" >nul 2>&1
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: 疲れました
.\jpn_to_phoneme_cpp.exe "疲れました" >nul 2>&1
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: お腹が空きました
.\jpn_to_phoneme_cpp.exe "お腹が空きました" >nul 2>&1
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)

REM Complex and long sentences
set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: 明日の朝、早く起きなければなりません
.\jpn_to_phoneme_cpp.exe "明日の朝、早く起きなければなりません" >nul 2>&1
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: 駅まで歩いて行くことができます
.\jpn_to_phoneme_cpp.exe "駅まで歩いて行くことができます" >nul 2>&1
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: 彼は日本語が上手ですね
.\jpn_to_phoneme_cpp.exe "彼は日本語が上手ですね" >nul 2>&1
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: この本を読んでみてください
.\jpn_to_phoneme_cpp.exe "この本を読んでみてください" >nul 2>&1
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: もう一度言っていただけますか
.\jpn_to_phoneme_cpp.exe "もう一度言っていただけますか" >nul 2>&1
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)

REM Mixed hiragana, katakana, kanji
set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: コンピューターを使っています
.\jpn_to_phoneme_cpp.exe "コンピューターを使っています" >nul 2>&1
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: インターネットで調べました
.\jpn_to_phoneme_cpp.exe "インターネットで調べました" >nul 2>&1
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: スマートフォンが壊れました
.\jpn_to_phoneme_cpp.exe "スマートフォンが壊れました" >nul 2>&1
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: テレビを見ながら食べます
.\jpn_to_phoneme_cpp.exe "テレビを見ながら食べます" >nul 2>&1
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)

set /a COUNT+=1
echo [%COUNT%/%TOTAL%] Testing: プログラミングを勉強したいです
.\jpn_to_phoneme_cpp.exe "プログラミングを勉強したいです" >nul 2>&1
if !errorlevel! equ 0 (echo   ✓ Pass) else (echo   ✗ FAIL)

echo.
echo ════════════════════════════════════════════════════════════
echo   All %TOTAL% tests completed!
echo ════════════════════════════════════════════════════════════
echo.

REM Now run one detailed test to show actual output
echo Running detailed output test with sample sentence:
echo.
.\jpn_to_phoneme_cpp.exe "日本は美しい国です。春には桜が咲き、夏は海で泳ぎ、秋は紅葉を楽しみ、冬は雪景色を眺めます。"

endlocal

