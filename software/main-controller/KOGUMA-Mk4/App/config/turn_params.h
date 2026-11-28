/*
 * turn_params.h
 * 最短走行のターン（大回り・斜め）の値。ctrl/run.c と sys/turn_test.c（モード3）が使う
 * ToraNeko.Mk3 の App/config/turn_params.h から。クラシック（1 区画 180mm）に直した（2026-11-28）
 *
 * ■ クラシックへの直し方（2026-11-28）
 * ターンの組・名前・速さは ToraNeko と同じにした（組 1 は 800・600mm/s、組 2 は 1000mm/s …。T1000 などの名前は、その速さのまま）。
 * 区画が 2 倍の大きさなので、同じ速さで同じ形（2 倍の大きさ）に曲がると、角速度は半分になり、横向きの加速度
 * （速さ × 角速度）も ToraNeko の半分になる。KOGUMA MK3（クラシック）は 2000・2400mm/s で曲がっていたので、
 * これはクラシックとしては控えめな速さ（実機の前なので、まずここから。合わせてから速い組を足す）。
 * 角加速度は、1000mm/s で 10000deg/s² のときと同じ形になるように、10000 ×（速さ ÷ 1000）² にする
 * （ToraNeko の「500mm/s で 10000deg/s²」の形を 2 倍の大きさにしたもの。KOGUMA MK3 の大回り 90°（2000mm/s、40000deg/s²）も同じ式）。
 * 最高角速度・前距離・後距離は test/test_turn.c --calc で、クラシックの形から計算し直した（前距離・後距離の短いほうは 6mm）。
 * 実機で足す前距離・後距離（*_ADJUST_MM）と大回り 180° の幅に足す分は、ToraNeko で合わせた値なので 0 にした。どれも実機で合わせる。
 * 下の ToraNeko の日付の入ったコメント（実機で走らせた話）は、ToraNeko（ハーフ）でのこと。
 *
 * ターンは「前距離（まっすぐ）→ スラローム（前に進む速さは一定、角速度は台形）→ 後距離（まっすぐ）」。
 * 曲がる角度・始めと終わりの位置は迷路の形で決まる（test/test_turn.c の先頭のコメント）。
 *
 * ■ ターンごとの速さ（ToraNeko は 2026-11-03）
 * ターンごとに「そのターンを曲がる速さ」（*_SPEED_MM_S）と角加速度（*_ALPHA_DEG_S2）を決める。
 * 曲がると横向きに「速さ × 角速度」の加速度がかかる。ToraNeko は吸引 5.0V では 10000mm/s² を超えると滑った
 * （モード4 の加速度テスト。12000mm/s² で滑り始めた）ので、余裕をみて 8000mm/s² くらいまでにしていた。
 * クラシックでは、同じ速さで横向きの加速度が半分になる：
 *   - ゆるいターン（大回り 90°・斜め入り 45°・斜め出 45°）：800mm/s（横向きの加速度 3990〜4120mm/s²。ToraNeko は 7800〜8200mm/s²）
 *   - きついターン（大回り 180°・斜め入り 135°・斜め出 135°・V90）：600mm/s（同じく 4090〜4170mm/s²。ToraNeko は 8170〜8260mm/s²）
 * 角加速度は、1000mm/s で 10000deg/s² のときと同じ形になるように、10000 ×（速さ ÷ 1000）² にする。
 * 同じ形なので、前距離・後距離は速さによらず、ほぼ同じになる。
 *
 * ■ 決めた速さより遅く曲がるとき
 * ctrl/run.c の fast_turn() は、決めた速さより遅いときは、最高角速度を k 倍、角加速度を k² 倍にして
 * （k = 速さ ÷ 決めた速さ）、同じ形で曲がる。最短走行（sys/shortest.c）は、ターンごとの速さで曲がる。
 * ただし、上げきれないとき・ターンが続くとき・ゴールで止まるときは、遅く曲がる（sys/shortest.c の先頭のコメント）。
 *
 * ■ 値の決め方
 *   1. ターンごとの速さと角加速度を決める
 *   2. software/main-controller/test で make test_turn && ./test_turn --calc を実行し、出た行を下に貼る
 *      （最高角速度は、前距離・後距離の短いほうが 6mm になるように計算する。ToraNeko はハーフで 3mm）
 *   3. 実機でモード3 の No. ごとに走らせて、ずれる分を、下の「実機で足す前距離・後距離」（*_PRE_ADJUST_MM・
 *      *_POST_ADJUST_MM）に入れる。2 の計算の値はそのままにしておく（test_turn が、計算の値でターンの形を確かめるため）。
 *      前距離を足すと、曲がり始めが前にずれる（止まる位置が、始めの向きに進む）。後距離を足すと、曲がったあとが長くなる
 * ToraNeko は 2026-11-04 に、7 つのターンとも実機（吸引 5.0V）で合わせ終わった。MK4 は、まだ合わせていない（足す分は 0）。
 *
 * ■ ターンの組（2026-11-10。組 3 は 2026-11-11）
 * ターンの値は 3 組ある。どの組で曲がるかは、ctrl/run.c の run_fast_set_turn_set() で選ぶ。
 *   - 組 1（下の BIG90_… などの名前）：ゆるいターン 800mm/s、きついターン 600mm/s。最短走行 No.4・5 が使う
 *   - 組 2（T1000_BIG90_… などの名前。T1000 は「1000mm/s のターン」）：7 つとも 1000mm/s。最短走行 No.6 が使う
 *   - 組 3（T1200_BIG90_… などの名前）：ゆるいターン（大回り 90°・斜め入り 45°・斜め出 45°）1200mm/s、
 *     きついターン（大回り 180°・斜め入り 135°・斜め出 135°・V90°）は組 2 と同じ 1000mm/s。最短走行 No.7・No.8 が使う
 *   - 組 4（2026-11-21 の大会で足した。値は持たない）：ゆるいターンは組 2 の 1000mm/s、きついターンは組 1 の 600mm/s（今は使う No. がない）
 *   - 組 5（T1300_…。2026-11-21 の大会で足した）：ゆるいターン 1300mm/s、きついターン 1100mm/s。最短走行 No.9・No.10 が使う（吸引 7V）
 *   - 組 6（T1400_…。2026-11-21 の大会で足した）：ゆるいターン 1400mm/s、きついターン 1200mm/s。最短走行 No.11・No.12 が使う（吸引 7V）
 * モード3（ターンの調整）がどの組を走らせるかは、TURN_TEST_TURN_SET で選ぶ（下）。
 */
#ifndef CONFIG_TURN_PARAMS_H
#define CONFIG_TURN_PARAMS_H

/* 最短走行の経路を選ぶとき（maze/dijkstra.c の走る時間の見積もり）に、どのターンも曲がるとする速さ [mm/s]。
 * 本当に走るときは、ターンごとの速さ（下）で曲がる（sys/shortest.c の先頭のコメント）。ターンごとの速さより遅くする */
#define FAST_TURN_SPEED_MM_S   500.0f

#define DIAG_STEP_MM 127.28f  /* 斜めの直進の 1 つぶん [mm]（壁の辺のまん中から、となりの辺のまん中まで = 区画の半分 90 × √2。ToraNeko は 45 × √2 = 63.64） */

/* ターンごとの速さ [mm/s] と角加速度 [deg/s²]（先頭のコメント） */
#define BIG90_SPEED_MM_S    800.0f
#define BIG90_ALPHA_DEG_S2  6400.0f
#define BIG180_SPEED_MM_S   600.0f
#define BIG180_ALPHA_DEG_S2 3600.0f
#define IN45_SPEED_MM_S     800.0f
#define IN45_ALPHA_DEG_S2   6400.0f
#define IN135_SPEED_MM_S    600.0f
#define IN135_ALPHA_DEG_S2  3600.0f
#define OUT45_SPEED_MM_S    800.0f
#define OUT45_ALPHA_DEG_S2  6400.0f
#define OUT135_SPEED_MM_S   600.0f
#define OUT135_ALPHA_DEG_S2 3600.0f
#define V90_SPEED_MM_S      600.0f
#define V90_ALPHA_DEG_S2    3600.0f

/* 実機で足す前距離・後距離 [mm]（先頭のコメントの 3。計算の値に足して走る）。
 * MK4 はまだ実機で合わせていないので 0。モード3 で走らせて合わせる。
 * ToraNeko（ハーフ）では、大回り 180° を除くと、どのターンも前距離・後距離とも +1〜+10mm 足していて、引いたものはなかった
 * （曲がっているあいだにタイヤが少しずつ空回りして、計算より短く進むため。test/test_turn.c --slip の「空回りの式」）。
 * MK4 も、足す向きになる見込み。前距離を足すと、曲がり始めが前にずれる（止まる位置が、始めの向きに進む）。
 * 後距離を足すと、曲がったあとが長くなる。計算の値（下の *_PRE_MM・*_POST_MM）は変えない（test_turn がターンの形を確かめるため） */
#define BIG90_PRE_ADJUST_MM   0.0f
#define BIG90_POST_ADJUST_MM  0.0f
#define BIG180_PRE_ADJUST_MM  0.0f
#define BIG180_POST_ADJUST_MM 0.0f
/* 大回り 180° の左右の幅に足す分 [mm]。大回り 180° は、前距離・後距離では前後しか動かず、左右の幅（ふつうは 1 区画 180mm）は
 * 最高角速度だけで決まる。なので、実機で幅がずれたら、ここに足す分を入れ、test_turn --calc で、
 * 幅が「180mm + この値」になる最高角速度を計算し直して、BIG180_OMEGA_DEG_S に貼る。
 * MK4 はまだ測っていないので 0（ToraNeko は 600mm/s で 8mm 内側を走ったので 8mm 足していた） */
#define BIG180_WIDTH_ADJUST_MM 0.0f
/* 斜め出 45° の、前距離・後距離の短いほうの長さ [mm]（ほかのターンと同じ 6mm。test/test_turn.c の TURN_MARGIN_MM）。
 * 短くするほど、最高角速度が下がって大きく回る（旋回半径が大きくなる） */
#define OUT45_STRAIGHT_MIN_MM 6.0f
#define IN45_PRE_ADJUST_MM    0.0f
#define IN45_POST_ADJUST_MM   0.0f
#define IN135_PRE_ADJUST_MM   0.0f
#define IN135_POST_ADJUST_MM  0.0f
#define OUT45_PRE_ADJUST_MM   0.0f
#define OUT45_POST_ADJUST_MM  0.0f
#define OUT135_PRE_ADJUST_MM  0.0f
#define OUT135_POST_ADJUST_MM 0.0f
#define V90_PRE_ADJUST_MM     0.0f
#define V90_POST_ADJUST_MM    0.0f

/* 最高角速度・前距離・後距離（test_turn --calc の出力） */
/* 前距離・後距離の短いほう 6.0mm で計算（test/test_turn.c --calc。大回り 180° は幅 180mm） */
/* 大回り 90°（800mm/s、角加速度 6400deg/s²。横向きの加速度はいちばん大きいとき 4118mm/s²） */
#define BIG90_OMEGA_DEG_S 294.9f
#define BIG90_PRE_MM 6.0f
#define BIG90_POST_MM 6.2f
/* 大回り 180°（600mm/s、角加速度 3600deg/s²。横向きの加速度はいちばん大きいとき 4090mm/s²） */
#define BIG180_OMEGA_DEG_S 390.6f
#define BIG180_PRE_MM 6.0f
#define BIG180_POST_MM 6.0f
/* 斜め入り 45°（800mm/s、角加速度 6400deg/s²。横向きの加速度はいちばん大きいとき 4009mm/s²） */
#define IN45_OMEGA_DEG_S 287.1f
#define IN45_PRE_MM 6.0f
#define IN45_POST_MM 43.5f
/* 斜め入り 135°（600mm/s、角加速度 3600deg/s²。横向きの加速度はいちばん大きいとき 4109mm/s²） */
#define IN135_OMEGA_DEG_S 392.4f
#define IN135_PRE_MM 21.2f
#define IN135_POST_MM 6.1f
/* 斜め出 45°（800mm/s、角加速度 6400deg/s²。横向きの加速度はいちばん大きいとき 3988mm/s²） */
#define OUT45_OMEGA_DEG_S 285.6f
#define OUT45_PRE_MM 43.0f
#define OUT45_POST_MM 6.1f
/* 斜め出 135°（600mm/s、角加速度 3600deg/s²。横向きの加速度はいちばん大きいとき 4114mm/s²） */
#define OUT135_OMEGA_DEG_S 392.9f
#define OUT135_PRE_MM 6.0f
#define OUT135_POST_MM 21.7f
/* V90°（600mm/s、角加速度 3600deg/s²。横向きの加速度はいちばん大きいとき 4172mm/s²） */
#define V90_OMEGA_DEG_S 398.4f
#define V90_PRE_MM 6.0f
#define V90_POST_MM 6.2f

/* ===========================================================================
 * 組 2：7 つとも 1000mm/s のターン（ToraNeko で 2026-11-10。作者が「全部 1m/s のターン」を作りたいので足した）
 * 角加速度は、組 1 と同じく 10000 ×（速さ ÷ 1000）² = 10000deg/s²。1000mm/s のときの形なので、
 * 前距離・後距離の計算の値は組 1 とほぼ同じになり（0.25ms ごとに計算するので 0.1〜0.2mm 違う）、最高角速度が速さに比例して大きくなる。
 * 横向きの加速度（速さ × 角速度）は速さの 2 乗で増える。組 1 より、ゆるいターンは 1.56 倍（約 6200〜6400mm/s²）、
 * きついターンは 2.78 倍（約 11400〜11600mm/s²）になる（下の --calc の行。ToraNeko のハーフでは、この倍の約 12800・20700〜23000mm/s²）。
 * MK4 の吸引で滑り始める加速度は、まだ測っていない（docs/spec.md の見込みでは、吸引 400g で約 120000mm/s²）。モード3 で 1 つずつ確かめる。
 * 滑るターンは、そのターンの *_SPEED_MM_S だけを下げて、角加速度を 10000 ×（速さ ÷ 1000）² にし、--calc をやり直す
 * =========================================================================== */

/* ターンごとの速さ [mm/s] と角加速度 [deg/s²] */
#define T1000_BIG90_SPEED_MM_S    1000.0f
#define T1000_BIG90_ALPHA_DEG_S2  10000.0f
#define T1000_BIG180_SPEED_MM_S   1000.0f
#define T1000_BIG180_ALPHA_DEG_S2 10000.0f
#define T1000_IN45_SPEED_MM_S     1000.0f
#define T1000_IN45_ALPHA_DEG_S2   10000.0f
#define T1000_IN135_SPEED_MM_S    1000.0f
#define T1000_IN135_ALPHA_DEG_S2  10000.0f
#define T1000_OUT45_SPEED_MM_S    1000.0f
#define T1000_OUT45_ALPHA_DEG_S2  10000.0f
#define T1000_OUT135_SPEED_MM_S   1000.0f
#define T1000_OUT135_ALPHA_DEG_S2 10000.0f
#define T1000_V90_SPEED_MM_S      1000.0f
#define T1000_V90_ALPHA_DEG_S2    10000.0f

/* 実機で足す前距離・後距離 [mm]。まだ実機で合わせていないので、はじめは組 1 で合わせた値と同じにしてある
 * （MK4 は組 1 も 0）。モード3（TURN_TEST_TURN_SET を 2 にする）で走らせて合わせる */
#define T1000_BIG90_PRE_ADJUST_MM   BIG90_PRE_ADJUST_MM
#define T1000_BIG90_POST_ADJUST_MM  BIG90_POST_ADJUST_MM
#define T1000_BIG180_PRE_ADJUST_MM  BIG180_PRE_ADJUST_MM
#define T1000_BIG180_POST_ADJUST_MM BIG180_POST_ADJUST_MM
#define T1000_BIG180_WIDTH_ADJUST_MM BIG180_WIDTH_ADJUST_MM  /* 大回り 180° の幅に足す分（組 1 の BIG180_WIDTH_ADJUST_MM と同じ使い方） */
#define T1000_OUT45_STRAIGHT_MIN_MM  OUT45_STRAIGHT_MIN_MM   /* 斜め出 45° の前距離・後距離の短いほう（組 1 と同じ） */
#define T1000_IN45_PRE_ADJUST_MM    IN45_PRE_ADJUST_MM
#define T1000_IN45_POST_ADJUST_MM   IN45_POST_ADJUST_MM
#define T1000_IN135_PRE_ADJUST_MM   IN135_PRE_ADJUST_MM
#define T1000_IN135_POST_ADJUST_MM  IN135_POST_ADJUST_MM
#define T1000_OUT45_PRE_ADJUST_MM   OUT45_PRE_ADJUST_MM
#define T1000_OUT45_POST_ADJUST_MM  OUT45_POST_ADJUST_MM
#define T1000_OUT135_PRE_ADJUST_MM  OUT135_PRE_ADJUST_MM
#define T1000_OUT135_POST_ADJUST_MM OUT135_POST_ADJUST_MM
#define T1000_V90_PRE_ADJUST_MM     V90_PRE_ADJUST_MM
#define T1000_V90_POST_ADJUST_MM    V90_POST_ADJUST_MM

/* 最高角速度・前距離・後距離（test_turn --calc の出力の、組 2 の行） */
/* 前距離・後距離の短いほう 6.0mm で計算（test/test_turn.c --calc）。大回り 180° は幅 180mm（1 区画 + T1000_BIG180_WIDTH_ADJUST_MM） */
/* 大回り 90°（1000mm/s、角加速度 10000deg/s²。横向きの加速度はいちばん大きいとき 6432mm/s²） */
#define T1000_BIG90_OMEGA_DEG_S 368.5f
#define T1000_BIG90_PRE_MM 6.0f
#define T1000_BIG90_POST_MM 6.3f
/* 大回り 180°（1000mm/s、角加速度 10000deg/s²。横向きの加速度はいちばん大きいとき 11362mm/s²） */
#define T1000_BIG180_OMEGA_DEG_S 651.0f
#define T1000_BIG180_PRE_MM 6.0f
#define T1000_BIG180_POST_MM 6.0f
/* 斜め入り 45°（1000mm/s、角加速度 10000deg/s²。横向きの加速度はいちばん大きいとき 6257mm/s²） */
#define T1000_IN45_OMEGA_DEG_S 358.5f
#define T1000_IN45_PRE_MM 6.0f
#define T1000_IN45_POST_MM 43.6f
/* 斜め入り 135°（1000mm/s、角加速度 10000deg/s²。横向きの加速度はいちばん大きいとき 11401mm/s²） */
#define T1000_IN135_OMEGA_DEG_S 653.3f
#define T1000_IN135_PRE_MM 21.2f
#define T1000_IN135_POST_MM 6.2f
/* 斜め出 45°（1000mm/s、角加速度 10000deg/s²。横向きの加速度はいちばん大きいとき 6220mm/s²） */
#define T1000_OUT45_OMEGA_DEG_S 356.4f
#define T1000_OUT45_PRE_MM 43.0f
#define T1000_OUT45_POST_MM 6.1f
/* 斜め出 135°（1000mm/s、角加速度 10000deg/s²。横向きの加速度はいちばん大きいとき 11421mm/s²） */
#define T1000_OUT135_OMEGA_DEG_S 654.4f
#define T1000_OUT135_PRE_MM 6.0f
#define T1000_OUT135_POST_MM 21.7f
/* V90°（1000mm/s、角加速度 10000deg/s²。横向きの加速度はいちばん大きいとき 11563mm/s²） */
#define T1000_V90_OMEGA_DEG_S 662.5f
#define T1000_V90_PRE_MM 6.0f
#define T1000_V90_POST_MM 6.3f

/* 最短走行 No.6 の経路を選ぶとき（maze/dijkstra.c の走る時間の見積もり）に、どのターンも曲がるとする速さ [mm/s]。
 * 組 1 の FAST_TURN_SPEED_MM_S と同じ使い方。組 2 のターンごとの速さのいちばん遅いもの以下にする */
#define T1000_PATH_TURN_SPEED_MM_S 1000.0f

/* ===========================================================================
 * 組 3：ゆるいターン 1200mm/s・きついターン 1000mm/s（ToraNeko で 2026-11-11。作者の依頼）
 * ToraNeko では、ゆるいターンを 1000mm/s から 1200mm/s（横向きの加速度 1.44 倍）に上げ、きついターンは組 2 のままにした。
 * クラシックでは、ゆるいターンの横向きの加速度は約 9000〜9300mm/s²（下の --calc の行）。
 * きついターン 4 つは、組 2 の値（T1000_…。実機で足す分も）をそのまま使う（ctrl/run.c の fast_turn_values_set3()）。
 * ここには、ゆるいターン 3 つの値だけを置く。角加速度は、組 1・2 と同じく 10000 ×（速さ ÷ 1000）² = 14400deg/s²
 * =========================================================================== */

/* ゆるいターンの速さ [mm/s] と角加速度 [deg/s²] */
#define T1200_BIG90_SPEED_MM_S    1200.0f
#define T1200_BIG90_ALPHA_DEG_S2  14400.0f
#define T1200_IN45_SPEED_MM_S     1200.0f
#define T1200_IN45_ALPHA_DEG_S2   14400.0f
#define T1200_OUT45_SPEED_MM_S    1200.0f
#define T1200_OUT45_ALPHA_DEG_S2  14400.0f

/* 実機で足す前距離・後距離 [mm]。まだ合わせていないので、組 2 の値をそのまま使う（組 2 も、組 1 と同じ 0）。
 * モード3（TURN_TEST_TURN_SET を 3 にする）で走らせて合わせる */
#define T1200_BIG90_PRE_ADJUST_MM   T1000_BIG90_PRE_ADJUST_MM
#define T1200_BIG90_POST_ADJUST_MM  T1000_BIG90_POST_ADJUST_MM
#define T1200_IN45_PRE_ADJUST_MM    T1000_IN45_PRE_ADJUST_MM
#define T1200_IN45_POST_ADJUST_MM   T1000_IN45_POST_ADJUST_MM
#define T1200_OUT45_PRE_ADJUST_MM   T1000_OUT45_PRE_ADJUST_MM
#define T1200_OUT45_POST_ADJUST_MM  T1000_OUT45_POST_ADJUST_MM
#define T1200_OUT45_STRAIGHT_MIN_MM T1000_OUT45_STRAIGHT_MIN_MM  /* 斜め出 45° の前距離・後距離の短いほう（組 2 と同じ） */

/* 最高角速度・前距離・後距離（test_turn --calc の出力の、組 3 の行） */
/* 前距離・後距離の短いほう 6.0mm で計算（test/test_turn.c --calc。大回り 180° は幅 180mm） */
/* 大回り 90°（1200mm/s、角加速度 14400deg/s²。横向きの加速度はいちばん大きいとき 9258mm/s²） */
#define T1200_BIG90_OMEGA_DEG_S 442.1f
#define T1200_BIG90_PRE_MM 6.0f
#define T1200_BIG90_POST_MM 6.3f
/* 斜め入り 45°（1200mm/s、角加速度 14400deg/s²。横向きの加速度はいちばん大きいとき 9000mm/s²） */
#define T1200_IN45_OMEGA_DEG_S 429.7f
#define T1200_IN45_PRE_MM 6.0f
#define T1200_IN45_POST_MM 43.6f
/* 斜め出 45°（1200mm/s、角加速度 14400deg/s²。横向きの加速度はいちばん大きいとき 8961mm/s²） */
#define T1200_OUT45_OMEGA_DEG_S 427.9f
#define T1200_OUT45_PRE_MM 43.1f
#define T1200_OUT45_POST_MM 6.2f

/* 最短走行 No.7 の経路を選ぶとき（maze/dijkstra.c の走る時間の見積もり）に、どのターンも曲がるとする速さ [mm/s]。
 * 組 3 のターンごとの速さのいちばん遅いもの（きついターンの 1000mm/s）以下にする */
#define T1200_PATH_TURN_SPEED_MM_S 1000.0f

/* ===========================================================================
 * 組 5：ゆるいターン 1300mm/s・きついターン 1100mm/s（2026-11-21 の大会で作者の依頼で足した。最短走行 No.9 が使う）
 * 角加速度は、組 1〜3 と同じく 10000 ×（速さ ÷ 1000）²（1300mm/s で 16900、1100mm/s で 12100deg/s²）。
 * 横向きの加速度は、ゆるいターンで約 10500〜10900、きついターンで約 13700〜14000mm/s²（下の --calc の行）。
 * ToraNeko は、この倍の横向きの加速度になるので 7.0V で吸っていた（SHORTEST9_SUCTION_V）。前距離・後距離に足す分は、組 2 と同じ（0。合わせていない）
 * =========================================================================== */

/* ターンごとの速さ [mm/s] と角加速度 [deg/s²] */
#define T1300_BIG90_SPEED_MM_S      1300.0f
#define T1300_BIG90_ALPHA_DEG_S2      16900.0f
#define T1300_BIG180_SPEED_MM_S     1100.0f
#define T1300_BIG180_ALPHA_DEG_S2     12100.0f
#define T1300_IN45_SPEED_MM_S       1300.0f
#define T1300_IN45_ALPHA_DEG_S2       16900.0f
#define T1300_IN135_SPEED_MM_S      1100.0f
#define T1300_IN135_ALPHA_DEG_S2      12100.0f
#define T1300_OUT45_SPEED_MM_S      1300.0f
#define T1300_OUT45_ALPHA_DEG_S2      16900.0f
#define T1300_OUT135_SPEED_MM_S     1100.0f
#define T1300_OUT135_ALPHA_DEG_S2     12100.0f
#define T1300_V90_SPEED_MM_S        1100.0f
#define T1300_V90_ALPHA_DEG_S2        12100.0f

/* 実機で足す前距離・後距離 [mm]。まだ合わせていないので、組 2 の値（＝組 1 の値、0）をそのまま使う */
#define T1300_BIG90_PRE_ADJUST_MM  T1000_BIG90_PRE_ADJUST_MM
#define T1300_BIG90_POST_ADJUST_MM T1000_BIG90_POST_ADJUST_MM
#define T1300_BIG180_PRE_ADJUST_MM  T1000_BIG180_PRE_ADJUST_MM
#define T1300_BIG180_POST_ADJUST_MM T1000_BIG180_POST_ADJUST_MM
#define T1300_IN45_PRE_ADJUST_MM  T1000_IN45_PRE_ADJUST_MM
#define T1300_IN45_POST_ADJUST_MM T1000_IN45_POST_ADJUST_MM
#define T1300_IN135_PRE_ADJUST_MM  T1000_IN135_PRE_ADJUST_MM
#define T1300_IN135_POST_ADJUST_MM T1000_IN135_POST_ADJUST_MM
#define T1300_OUT45_PRE_ADJUST_MM  T1000_OUT45_PRE_ADJUST_MM
#define T1300_OUT45_POST_ADJUST_MM T1000_OUT45_POST_ADJUST_MM
#define T1300_OUT135_PRE_ADJUST_MM  T1000_OUT135_PRE_ADJUST_MM
#define T1300_OUT135_POST_ADJUST_MM T1000_OUT135_POST_ADJUST_MM
#define T1300_V90_PRE_ADJUST_MM  T1000_V90_PRE_ADJUST_MM
#define T1300_V90_POST_ADJUST_MM T1000_V90_POST_ADJUST_MM
#define T1300_BIG180_WIDTH_ADJUST_MM T1000_BIG180_WIDTH_ADJUST_MM  /* 大回り 180° の幅に足す分（組 2 と同じ） */
#define T1300_OUT45_STRAIGHT_MIN_MM  T1000_OUT45_STRAIGHT_MIN_MM   /* 斜め出 45° の前距離・後距離の短いほう（組 2 と同じ） */

/* 最高角速度・前距離・後距離（test_turn --calc の出力の、組 5 の行） */
/* 前距離・後距離の短いほう 6.0mm で計算（斜め出 45° は OUT45_STRAIGHT_MIN_MM。test/test_turn.c --calc。大回り 180° は幅 180mm） */
/* 大回り 90°（1300mm/s、角加速度 16900deg/s²。横向きの加速度はいちばん大きいとき 10864mm/s²） */
#define T1300_BIG90_OMEGA_DEG_S 478.8f
#define T1300_BIG90_PRE_MM 6.0f
#define T1300_BIG90_POST_MM 6.4f
/* 大回り 180°（1100mm/s、角加速度 12100deg/s²。横向きの加速度はいちばん大きいとき 13748mm/s²） */
#define T1300_BIG180_OMEGA_DEG_S 716.1f
#define T1300_BIG180_PRE_MM 6.0f
#define T1300_BIG180_POST_MM 6.0f
/* 斜め入り 45°（1300mm/s、角加速度 16900deg/s²。横向きの加速度はいちばん大きいとき 10556mm/s²） */
#define T1300_IN45_OMEGA_DEG_S 465.3f
#define T1300_IN45_PRE_MM 6.0f
#define T1300_IN45_POST_MM 43.6f
/* 斜め入り 135°（1100mm/s、角加速度 12100deg/s²。横向きの加速度はいちばん大きいとき 13789mm/s²） */
#define T1300_IN135_OMEGA_DEG_S 718.2f
#define T1300_IN135_PRE_MM 21.1f
#define T1300_IN135_POST_MM 6.0f
/* 斜め出 45°（1300mm/s、角加速度 16900deg/s²。横向きの加速度はいちばん大きいとき 10463mm/s²） */
#define T1300_OUT45_OMEGA_DEG_S 461.1f
#define T1300_OUT45_PRE_MM 42.8f
#define T1300_OUT45_POST_MM 6.0f
/* 斜め出 135°（1100mm/s、角加速度 12100deg/s²。横向きの加速度はいちばん大きいとき 13817mm/s²） */
#define T1300_OUT135_OMEGA_DEG_S 719.7f
#define T1300_OUT135_PRE_MM 6.0f
#define T1300_OUT135_POST_MM 21.8f
/* V90°（1100mm/s、角加速度 12100deg/s²。横向きの加速度はいちばん大きいとき 13983mm/s²） */
#define T1300_V90_OMEGA_DEG_S 728.3f
#define T1300_V90_PRE_MM 6.0f
#define T1300_V90_POST_MM 6.3f

/* 最短走行 No.9 の経路を選ぶときに、どのターンも曲がるとする速さ [mm/s]（組 5 のいちばん遅いターン 1100mm/s 以下） */
#define T1300_PATH_TURN_SPEED_MM_S 1100.0f

/* ===========================================================================
 * 組 6：ゆるいターン 1400mm/s・きついターン 1200mm/s（2026-11-21 の大会で作者の依頼で足した。最短走行 No.11・No.12 が使う）
 * 角加速度は、組 1〜5 と同じく 10000 ×（速さ ÷ 1000）²（1400mm/s で 19600、1200mm/s で 14400deg/s²）。
 * 横向きの加速度は、ゆるいターンで約 12100〜12600、きついターンで約 16400〜16600mm/s²（下の --calc の行）。
 * 前距離・後距離に足す分は、組 2 と同じ（0）
 * =========================================================================== */

/* ターンごとの速さ [mm/s] と角加速度 [deg/s²] */
#define T1400_BIG90_SPEED_MM_S      1400.0f
#define T1400_BIG90_ALPHA_DEG_S2      19600.0f
#define T1400_BIG180_SPEED_MM_S     1200.0f
#define T1400_BIG180_ALPHA_DEG_S2     14400.0f
#define T1400_IN45_SPEED_MM_S       1400.0f
#define T1400_IN45_ALPHA_DEG_S2       19600.0f
#define T1400_IN135_SPEED_MM_S      1200.0f
#define T1400_IN135_ALPHA_DEG_S2      14400.0f
#define T1400_OUT45_SPEED_MM_S      1400.0f
#define T1400_OUT45_ALPHA_DEG_S2      19600.0f
#define T1400_OUT135_SPEED_MM_S     1200.0f
#define T1400_OUT135_ALPHA_DEG_S2     14400.0f
#define T1400_V90_SPEED_MM_S        1200.0f
#define T1400_V90_ALPHA_DEG_S2        14400.0f

/* 実機で足す前距離・後距離 [mm]。まだ合わせていないので、組 2 の値（＝組 1 の値、0）をそのまま使う */
#define T1400_BIG90_PRE_ADJUST_MM  T1000_BIG90_PRE_ADJUST_MM
#define T1400_BIG90_POST_ADJUST_MM T1000_BIG90_POST_ADJUST_MM
#define T1400_BIG180_PRE_ADJUST_MM  T1000_BIG180_PRE_ADJUST_MM
#define T1400_BIG180_POST_ADJUST_MM T1000_BIG180_POST_ADJUST_MM
#define T1400_IN45_PRE_ADJUST_MM  T1000_IN45_PRE_ADJUST_MM
#define T1400_IN45_POST_ADJUST_MM T1000_IN45_POST_ADJUST_MM
#define T1400_IN135_PRE_ADJUST_MM  T1000_IN135_PRE_ADJUST_MM
#define T1400_IN135_POST_ADJUST_MM T1000_IN135_POST_ADJUST_MM
#define T1400_OUT45_PRE_ADJUST_MM  T1000_OUT45_PRE_ADJUST_MM
#define T1400_OUT45_POST_ADJUST_MM T1000_OUT45_POST_ADJUST_MM
#define T1400_OUT135_PRE_ADJUST_MM  T1000_OUT135_PRE_ADJUST_MM
#define T1400_OUT135_POST_ADJUST_MM T1000_OUT135_POST_ADJUST_MM
#define T1400_V90_PRE_ADJUST_MM  T1000_V90_PRE_ADJUST_MM
#define T1400_V90_POST_ADJUST_MM T1000_V90_POST_ADJUST_MM
#define T1400_BIG180_WIDTH_ADJUST_MM T1000_BIG180_WIDTH_ADJUST_MM  /* 大回り 180° の幅に足す分（組 2 と同じ） */
#define T1400_OUT45_STRAIGHT_MIN_MM  T1000_OUT45_STRAIGHT_MIN_MM   /* 斜め出 45° の前距離・後距離の短いほう（組 2 と同じ） */

/* 最高角速度・前距離・後距離（test_turn --calc の出力の、組 6 の行） */
/* 前距離・後距離の短いほう 6.0mm で計算（斜め出 45° は OUT45_STRAIGHT_MIN_MM。test/test_turn.c --calc。大回り 180° は幅 180mm） */
/* 大回り 90°（1400mm/s、角加速度 19600deg/s²。横向きの加速度はいちばん大きいとき 12597mm/s²） */
#define T1400_BIG90_OMEGA_DEG_S 515.5f
#define T1400_BIG90_PRE_MM 6.0f
#define T1400_BIG90_POST_MM 6.2f
/* 大回り 180°（1200mm/s、角加速度 14400deg/s²。横向きの加速度はいちばん大きいとき 16360mm/s²） */
#define T1400_BIG180_OMEGA_DEG_S 781.2f
#define T1400_BIG180_PRE_MM 6.0f
#define T1400_BIG180_POST_MM 6.0f
/* 斜め入り 45°（1400mm/s、角加速度 19600deg/s²。横向きの加速度はいちばん大きいとき 12236mm/s²） */
#define T1400_IN45_OMEGA_DEG_S 500.8f
#define T1400_IN45_PRE_MM 6.0f
#define T1400_IN45_POST_MM 43.5f
/* 斜め入り 135°（1200mm/s、角加速度 14400deg/s²。横向きの加速度はいちばん大きいとき 16410mm/s²） */
#define T1400_IN135_OMEGA_DEG_S 783.5f
#define T1400_IN135_PRE_MM 21.1f
#define T1400_IN135_POST_MM 6.2f
/* 斜め出 45°（1400mm/s、角加速度 19600deg/s²。横向きの加速度はいちばん大きいとき 12151mm/s²） */
#define T1400_OUT45_OMEGA_DEG_S 497.3f
#define T1400_OUT45_PRE_MM 42.9f
#define T1400_OUT45_POST_MM 6.1f
/* 斜め出 135°（1200mm/s、角加速度 14400deg/s²。横向きの加速度はいちばん大きいとき 16441mm/s²） */
#define T1400_OUT135_OMEGA_DEG_S 785.0f
#define T1400_OUT135_PRE_MM 6.0f
#define T1400_OUT135_POST_MM 21.7f
/* V90°（1200mm/s、角加速度 14400deg/s²。横向きの加速度はいちばん大きいとき 16631mm/s²） */
#define T1400_V90_OMEGA_DEG_S 794.1f
#define T1400_V90_PRE_MM 6.0f
#define T1400_V90_POST_MM 6.2f

/* 最短走行 No.11・12 の経路を選ぶときに、どのターンも曲がるとする速さ [mm/s]（組 6 のいちばん遅いターン 1200mm/s 以下） */
#define T1400_PATH_TURN_SPEED_MM_S 1200.0f


/* モード3（ターンの調整。sys/turn_test.c）で走らせる組（1・2・3 のどれか）。MK4 は、いちばん遅い組 1 から合わせるので 1
 * （ToraNeko は 2026-11-10 に、組 2 を合わせるため 2 にしていた）。ほかの組を走らせたいときは、その番号にして、書き込み直す */
#define TURN_TEST_TURN_SET 1

/* モード3（ターンの調整）で吸う電圧 [V]（ToraNeko で 2026-11-10。仮。MK4 のファンで決め直す）。最短走行の、その組を使う No. と同じ電圧にする
 * （組 1 なら config/run_params.h の SHORTEST4_SUCTION_V・SHORTEST5_SUCTION_V、組 2 なら SHORTEST6_SUCTION_V、
 * 組 3 なら SHORTEST7_SUCTION_V）。
 * 吸う強さで滑り方が変わり、前距離・後距離に足す分も変わるため */
#define TURN_TEST_SUCTION_V 5.0f

#endif /* CONFIG_TURN_PARAMS_H */
