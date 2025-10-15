@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo.
echo ╔══════════════════════════════════════════════════════════╗
echo ║  Japanese Phoneme Converter - Performance Benchmarks    ║
echo ║  Testing Dart, Python, and JavaScript                   ║
echo ╚══════════════════════════════════════════════════════════╝
echo.

REM Test cases: Simple, Medium, Large, Multi-paragraph
set "SIMPLE=こんにちは"
set "MEDIUM=今日はいい天気ですね"
set "LARGE=私は東京都に住んでいます。毎日、新宿駅から渋谷駅まで電車で通勤しています。日本語を勉強するのはとても難しいですが、頑張ります！"
set "MULTIPARA=日本は美しい国です。春には桜が咲き、夏は海で泳ぎ、秋は紅葉を楽しみ、冬は雪景色を眺めます。四季折々の風景が楽しめるのが日本の魅力です。東京、大阪、京都など、訪れるべき都市がたくさんあります。日本料理も世界的に有名で、寿司、ラーメン、天ぷらなど、美味しい食べ物がたくさんあります。日本の文化は伝統と現代が融合していて、とても興味深いです。"

echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo [1/3] DART BENCHMARKS
echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.

echo [DART] Simple (5 chars): %SIMPLE%
dart jpn_to_phoneme.dart "%SIMPLE%"
echo.

echo [DART] Medium (10 chars): %MEDIUM%
dart jpn_to_phoneme.dart "%MEDIUM%"
echo.

echo [DART] Large (50+ chars): %LARGE%
dart jpn_to_phoneme.dart "%LARGE%"
echo.

echo [DART] Multi-paragraph (150+ chars): %MULTIPARA%
dart jpn_to_phoneme.dart "%MULTIPARA%"
echo.

echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo [2/3] PYTHON BENCHMARKS
echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.

echo [PYTHON] Simple (5 chars): %SIMPLE%
python jpn_to_phoneme.py "%SIMPLE%"
echo.

echo [PYTHON] Medium (10 chars): %MEDIUM%
python jpn_to_phoneme.py "%MEDIUM%"
echo.

echo [PYTHON] Large (50+ chars): %LARGE%
python jpn_to_phoneme.py "%LARGE%"
echo.

echo [PYTHON] Multi-paragraph (150+ chars): %MULTIPARA%
python jpn_to_phoneme.py "%MULTIPARA%"
echo.

echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo [3/3] JAVASCRIPT BENCHMARKS
echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.

echo [JAVASCRIPT] Simple (5 chars): %SIMPLE%
node jpn_to_phoneme.js "%SIMPLE%"
echo.

echo [JAVASCRIPT] Medium (10 chars): %MEDIUM%
node jpn_to_phoneme.js "%MEDIUM%"
echo.

echo [JAVASCRIPT] Large (50+ chars): %LARGE%
node jpn_to_phoneme.js "%LARGE%"
echo.

echo [JAVASCRIPT] Multi-paragraph (150+ chars): %MULTIPARA%
node jpn_to_phoneme.js "%MULTIPARA%"
echo.

echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo ✨ All benchmarks complete!
echo.
echo Summary of test cases:
echo   • Simple:         5 characters
echo   • Medium:         10 characters
echo   • Large:          50+ characters
echo   • Multi-paragraph: 150+ characters
echo.
pause

