@echo off
chcp 65001 > nul
echo ========================================
echo Testing jpn_to_phoneme.cpp with furigana hints
echo ========================================
echo.

REM Test each sentence from test_sentences.txt
echo Test 1: その男、昨日「きのう」来「き」たよね？
jpn_to_phoneme_cpp.exe "その男「おとこ」、昨日「きのう」来「き」たよね？"
echo Expected: sono otoko kinoɯ kita jone？
echo.

echo Test 2: あの男「おとこ」は昨日「きのう」来「き」ました。
jpn_to_phoneme_cpp.exe "あの男「おとこ」は昨日「きのう」来「き」ました。"
echo Expected: ano otoko wa kinoɯ ki maɕita 。
echo.

echo Test 3: あの男「おとこ」さんは昨日「きのう」来「き」られました。
jpn_to_phoneme_cpp.exe "あの男「おとこ」さんは昨日「きのう」来「き」られました。"
echo Expected: ano otoko saɴ wa kinoɯ koɾaɾe maɕita 。
echo.

echo Test 4: それ、今日「きょう」食「た」べる？
jpn_to_phoneme_cpp.exe "それ、今日「きょう」食「た」べる？"
echo Expected: sore 、 kijoɯ tabeɾɯ ？
echo.

echo Test 5: それは今日「きょう」食「た」べますか
jpn_to_phoneme_cpp.exe "それは今日「きょう」食「た」べますか"
echo Expected: sore wa kijoɯ tabemaɕɯ ka
echo.

echo Test 6: 拓真「たくま」、今晩「こんばん」ゲームしようぜ
jpn_to_phoneme_cpp.exe "拓真「たくま」、今晩「こんばん」ゲームしようぜ"
echo Expected: takɯma 、 koɴbaɴ geːmɯ ɕijoɯ ze
echo.

echo Test 7: 拓真「たくま」は今晩「こんばん」ゲームをします
jpn_to_phoneme_cpp.exe "拓真「たくま」は今晩「こんばん」ゲームをします"
echo Expected: takɯma wa koɴbaɴ geːmɯ o ɕimasɯ
echo.

echo Test 8: もうご飯食べた？お腹すいたよ
jpn_to_phoneme_cpp.exe "もうご飯食べた？お腹すいたよ"
echo Expected: moɯ gohaɴ tabeta ？ onaka sɯita jo
echo.

echo Test 9: 田中「たなか」、何「なに」食べる？
jpn_to_phoneme_cpp.exe "田中「たなか」、何「なに」食べる？"
echo Expected: tanaka 、 nani tabeɾɯ ？
echo.

echo Test 10: 健太「けんた」、昼「ひる」にゲームしよ！
jpn_to_phoneme_cpp.exe "健太「けんた」、昼「ひる」にゲームしよ！"
echo Expected: keɴta 、 çiɾɯ ni geːmɯ ɕijo！
echo.

echo Test 11: 健太「けんた」、昼ご飯「ひるごはん」何「なに」食べる？
jpn_to_phoneme_cpp.exe "健太「けんた」、昼ご飯「ひるごはん」何「なに」食べる？"
echo Expected: keɴta 、 çiɾɯgohaɴ nani tabeɾɯ ？
echo.

echo Test 12: 健太「けんた」、夜「よる」は空気「くうき」がすごく冷たいよ
jpn_to_phoneme_cpp.exe "健太「けんた」、夜「よる」は空気「くうき」がすごく冷たいよ"
echo Expected: keɴta 、 joɾɯ wa kɯɯki ga sɯgokɯ ʦɯmetai jo
echo.

echo Test 13: 智也「ともや」、今夜「こんや」の月「つき」すごく大きいよ
jpn_to_phoneme_cpp.exe "智也「ともや」、今夜「こんや」の月「つき」すごく大きいよ"
echo Expected: tomoja 、 koɴja no ʦɯki sɯgokɯ ookii jo
echo.

echo ========================================
echo Testing complete!
echo ========================================
pause

