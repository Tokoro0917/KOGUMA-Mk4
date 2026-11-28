/*
 * run_params.h
 * 探索の動きの値（速さ、スラローム、その場旋回、区画の大きさ）。ctrl/run.c と sys/adjust.c が使う
 * ToraNeko.Mk3 の App/config/run_params.h から。クラシック（1 区画 180mm）と MK4（タイヤ 24mm の機体 t24）に直した（2026-11-28）
 *
 * 調整の動き（モード2）と探索（モード0）で同じ値を使うので、ここに 1 か所にまとめる。
 *
 * ■ MK4 で、まだ実機で決めていない値（2026-11-28）
 * 区画の大きさと、そこから計算で決まる距離はクラシックの寸法から決め直した。速さは KOGUMA MK3（クラシック）の値を
 * 参考に、控えめにした。「仮。実機で合わせる」と書いた値（スタートの位置、前壁補正・横壁合わせの距離、吸引・グリップの値）は、
 * MK4 の実機で測って直す。ToraNeko で実機で確かめた日付の入ったコメントは、ToraNeko（ハーフ）での話。
 */
#ifndef CONFIG_RUN_PARAMS_H
#define CONFIG_RUN_PARAMS_H

/* ---- 区画と、スタートの位置 ---- */

#define HALF_CELL_MM 90.0f   /* 区画の半分 [mm]（クラシックの 1 区画は 180mm。ToraNeko のハーフは 45mm） */
#define CELL_MM      180.0f  /* 1 区画 [mm]（柱の中心から次の柱の中心まで） */

/* スタート区画で、機体のお尻を後ろの壁に付けて置いたとき、タイヤの軸が区画のまん中から何 mm 後ろにあるか。
 * 壁の内側は区画のまん中から 84mm 後ろ（区画の半分 90mm − 壁の厚さの半分 6mm）、
 * 機体の後ろの端はフレームの後ろの辺で、タイヤの軸から 50mm 後ろ（docs/calc/frame/design.py の XE。
 * フレームは前後 100mm で、軸はそのまん中）なので、84 − 50 = 34mm。仮。実機で合わせる
 * （ToraNeko は 42 − 32 = 10mm） */
#define START_OFFSET_MM 34.0f

/* ---- 探索の直進 ---- */

/* 探索の速さ [mm/s]。KOGUMA MK3 の吸引なしの探索（Move.c の Robot_Maze_Sula_Action）と同じ 500mm/s。
 * 1 区画 180mm を 0.36 秒（ToraNeko はハーフの 90mm を 300mm/s で 0.3 秒） */
#define SEARCH_SPEED_MM_S  500.0f
/* 探索の加速度 [mm/s²]。止まったところから 41.7mm で 500mm/s になり、区画の半分 90mm で十分に止まれる
 * （MK3 は 5000mm/s²。実機の前なので控えめにした） */
#define SEARCH_ACCEL_MM_S2 3000.0f

/* ---- 全面探索（モード0 No.5・6。2026-11-21。sys/explore.c） ----
 * ゴールのあとに動く回数の上限。1 回は 1 区画（既知区間加速でまとめて走ったときも 1 回と数える）。
 * これだけ動いたら、見に行く区画が残っていてもスタートへ戻る。
 * 探索の速さ（500mm/s）で 1 区画 0.36 秒、曲がる・U ターンを入れて 1 回 0.4〜0.7 秒くらいなので、400 回で 2.5〜4.5 分くらいの見込み
 * （ToraNeko は 2026-11-21 の大会で、作者が 1000 から 400 にした。クラシックの 16×16 は区画が 256 個なので、400 回でもふつうは見終わる）。
 * 大会の持ち時間に合わせて減らす */
#define FULL_SEARCH_MAX_MOVES 400

/* ---- 既知区間加速（探索 No.4・6。見たことのある区画がまっすぐ 2 区画以上続くところ）（仮） ---- */

#define KNOWN_MAX_SPEED_MM_S 1000.0f  /* 最高速 [mm/s] */
#define KNOWN_ACCEL_MM_S2    3000.0f  /* 加速度 [mm/s²]（500 → 1000mm/s に 125mm。上げて戻すのに 250mm なので、2 区画（360mm）あれば上げて戻せる） */

/* ---- 探索のスラローム（小回り 90°） ---- */

#define SLALOM_ANGLE_DEG    90.0f    /* 曲がる角度 [deg] */
/* 最高の角速度と角加速度。ToraNeko（ハーフ、300mm/s、600deg/s、8000deg/s²）と同じ形を、区画の大きさ 2 倍に広げ、
 * 500mm/s で曲がるようにした値（形を 2 倍にすると角速度は 1/2、角加速度は 1/4。速さを k 倍にすると角速度は k 倍、角加速度は k² 倍。
 * 600 × 1/2 × 5/3 = 500deg/s、8000 × 1/4 ×（5/3）² ≒ 5556 → 5500deg/s²）。
 * 横向きの加速度はいちばん大きいとき 500mm/s × 500deg/s ≒ 4360mm/s²（吸引なし。MK3 は 500mm/s・最高 700deg/s で約 6100mm/s²） */
#define SLALOM_OMEGA_DEG_S  500.0f   /* 最高の角速度 [deg/s] */
#define SLALOM_ALPHA_DEG_S2 5500.0f  /* 角加速度 [deg/s²] */
/* 前距離・後距離 [mm]（曲がる前・後の直進）。500mm/s、500deg/s、5500deg/s² なら、曲がるあいだに
 * 前へ 81.3mm、横へ 81.1mm 進むので、区画の半分 90mm から引いた値（PC で ctrl/trajectory.c を回して計算。test/test_trajectory.c の [6]）。
 * 実機で合わせる（ToraNeko は 2026-10-24 に実機で、計算の値のまま左の区画のまん中で止まった） */
#define SLALOM_PRE_MM  8.7f
#define SLALOM_POST_MM 8.9f

/* ---- 最短走行（モード1）の直進。曲がるところは探索と同じスラローム（500mm/s） ---- */

/* No.1：探索と同じ速さ（道を確かめる） */
#define SHORTEST1_MAX_SPEED_MM_S 500.0f   /* 直進の最高速 [mm/s] */
#define SHORTEST1_ACCEL_MM_S2    3000.0f  /* 直進の加速度 [mm/s²] */
/* No.2（ToraNeko は 600mm/s・2000mm/s²。クラシックは直進が長いので上げた。吸引なし） */
#define SHORTEST2_MAX_SPEED_MM_S 1000.0f
#define SHORTEST2_ACCEL_MM_S2    3000.0f
/* No.3（ToraNeko は 1000mm/s・3000mm/s²。吸引なしなので、加速度は下の「グリップの上限」で抑えられる） */
#define SHORTEST3_MAX_SPEED_MM_S 1500.0f
#define SHORTEST3_ACCEL_MM_S2    3000.0f

/* ---- 最短走行（モード1）No.4・5：大回り・斜めのターンで、ターンごとの速さ（config/turn_params.h）で曲がる ----
 * 吸引して走る（ToraNeko は吸引 5.0V では 10000mm/s² まで滑らなかった。モード4 の加速度テスト）。
 * ターンは 800mm/s（ゆるいターン）・600mm/s（きついターン）なので、最高速はそれより速くする。
 * MK4（クラシック）では、直進・斜めの速さと加速度は ToraNeko の値のまま（KOGUMA MK3 は最高 6000mm/s・20000mm/s² で走っていたので、
 * クラシックとしては控えめ。実機で確かめてから上げる）。
 * No.4 はまず確かめる用（加速度は滑らない値の半分くらい）、No.5 はもう一段速くしたもの */

/* No.4 */
#define SHORTEST4_MAX_SPEED_MM_S      1000.0f  /* 縦横の直進の最高速 [mm/s] */
#define SHORTEST4_ACCEL_MM_S2         4000.0f  /* 縦横の直進の加速度 [mm/s²] */
#define SHORTEST4_DIAG_MAX_SPEED_MM_S 800.0f   /* 斜めの直進の最高速 [mm/s]（斜めは柱が近いので、縦横より遅くする） */
#define SHORTEST4_DIAG_ACCEL_MM_S2    4000.0f  /* 斜めの直進の加速度 [mm/s²] */
/* No.5 */
#define SHORTEST5_MAX_SPEED_MM_S      1500.0f
#define SHORTEST5_ACCEL_MM_S2         6000.0f
#define SHORTEST5_DIAG_MAX_SPEED_MM_S 1200.0f
#define SHORTEST5_DIAG_ACCEL_MM_S2    6000.0f
/* No.4〜12 の吸引の電圧 [V]（2026-11-10。No. ごとに変えられるようにした。No.1〜3 は吸引しない）。
 * 仮。ToraNeko のファンの値のまま。MK4 のファン（NFP-D8620、電池 3S）で吸引の力を測ってから決め直す。
 * 上限は drv/fan.c の FAN_LIMIT_V（7.0V）。ToraNeko の 2026-11-10 の吸引の力のテストで、5V 130g、6V 150g、7V 170g。
 * 6V・7V はファンのモーターの定格（3.7V）の 2 倍近いので、熱くなりやすい。続けて何回も走らせない。
 * 吸引を強くすると摩擦も増える（config/ctrl_gains.h の FF_SUCTION_FRICTION_V は 5V で決めた値）。
 * ターンの前距離・後距離も、走るときと同じ電圧で合わせる（config/turn_params.h の TURN_TEST_SUCTION_V） */
#define SHORTEST4_SUCTION_V 5.0f
#define SHORTEST5_SUCTION_V 5.0f
#define SHORTEST6_SUCTION_V 5.0f
#define SHORTEST7_SUCTION_V 5.0f
#define SHORTEST8_SUCTION_V 5.0f
#define SHORTEST9_SUCTION_V 7.0f  /* 組 5 のターンは横向きの加速度が大きいので、いちばん強く吸う（ファンの定格の 2 倍近いので、続けて走らせない） */
#define SHORTEST10_SUCTION_V 7.0f  /* No.9 と同じ */
#define SHORTEST11_SUCTION_V 7.0f  /* No.9 と同じ */
#define SHORTEST12_SUCTION_V 7.0f  /* No.9 と同じ */

/* No.6（2026-11-10）：ターンは組 2（7 つとも 1000mm/s。config/turn_params.h の T1000_…）。直進は No.5 と同じ。
 * 斜めの直進の最高速は、ターンの速さ（1000mm/s）より速くする */
#define SHORTEST6_MAX_SPEED_MM_S      1500.0f
#define SHORTEST6_ACCEL_MM_S2         6000.0f
#define SHORTEST6_DIAG_MAX_SPEED_MM_S 1200.0f
#define SHORTEST6_DIAG_ACCEL_MM_S2    6000.0f

/* No.7（2026-11-11）：ターンは組 3（ゆるいターン 1200mm/s・きついターン 1000mm/s。config/turn_params.h の T1200_…）。
 * 直進・斜めの直進は No.6 と同じ。斜めの直進の最高速は、斜め出 45° の速さ（1200mm/s）と同じにした */
#define SHORTEST7_MAX_SPEED_MM_S      1500.0f
#define SHORTEST7_ACCEL_MM_S2         6000.0f
#define SHORTEST7_DIAG_MAX_SPEED_MM_S 1200.0f
#define SHORTEST7_DIAG_ACCEL_MM_S2    6000.0f

/* No.8（2026-11-21 の大会で作者の依頼で決めた）：ターンは No.7 と同じ組 3（ゆるいターン 1200mm/s・きついターン 1000mm/s）で、
 * 直進・斜めだけ速くする。加速度 10000mm/s² は、2026-11-03 の加速度テスト（吸引 5V、そのときの吸引の力 55g）で滑らなかったいちばん大きい値。
 * 今の吸引の力（5V で 130g）でのグリップの上限は約 17300mm/s² なので、まだ余裕がある。
 * 1000mm/s から 2000mm/s まで上げて戻すのに約 300mm（クラシックで 1.7 区画くらい）要るので、短い直進では 2000mm/s まで届かない。
 * （はじめはターンを組 1 にしていて、2026-11-21 の 16:28 にその形で 2000mm/s まで出て完走した） */
#define SHORTEST8_MAX_SPEED_MM_S      2000.0f
#define SHORTEST8_ACCEL_MM_S2         10000.0f
#define SHORTEST8_DIAG_MAX_SPEED_MM_S 1500.0f
#define SHORTEST8_DIAG_ACCEL_MM_S2    8000.0f

/* No.9（2026-11-21 の大会で作者の依頼で決めた）：直進・斜めは No.8 と同じ。ターンは組 5（ゆるいターン 1300mm/s・きついターン 1100mm/s。
 * config/turn_params.h の T1300_…）。横向きの加速度が 5.0V の吸引の見込みを超えるので、7.0V で吸う（上の SHORTEST9_SUCTION_V） */
#define SHORTEST9_MAX_SPEED_MM_S      2000.0f
#define SHORTEST9_ACCEL_MM_S2         10000.0f
#define SHORTEST9_DIAG_MAX_SPEED_MM_S 1500.0f
#define SHORTEST9_DIAG_ACCEL_MM_S2    8000.0f

/* No.10（2026-11-21 の大会で作者の依頼で足した）：ターンと吸引（7.0V）は No.9 と同じ組 5。直進・斜めをもっと速くする。
 * 7.0V の吸引でのグリップの上限は約 21700mm/s² なので、加速度 12000mm/s² はその内側。モーターが出せる加速度は、
 * 2500mm/s でも約 32000mm/s² の見込み（ctrl/trajectory.c）。1100mm/s から 2500mm/s まで上げて戻すのに約 420mm（クラシックで 2.3 区画くらい）要る */
#define SHORTEST10_MAX_SPEED_MM_S      2500.0f
#define SHORTEST10_ACCEL_MM_S2         12000.0f
#define SHORTEST10_DIAG_MAX_SPEED_MM_S 1800.0f
#define SHORTEST10_DIAG_ACCEL_MM_S2    10000.0f

/* No.11（2026-11-21 の大会で作者の依頼で足した）：直進・斜めは No.10 と同じ。ターンは組 6（ゆるいターン 1400mm/s・きついターン 1200mm/s。
 * config/turn_params.h の T1400_…）。吸引 7.0V。きついターンは 7.0V の吸引でも滑り始める見込みを超える */
#define SHORTEST11_MAX_SPEED_MM_S      2500.0f
#define SHORTEST11_ACCEL_MM_S2         12000.0f
#define SHORTEST11_DIAG_MAX_SPEED_MM_S 1800.0f
#define SHORTEST11_DIAG_ACCEL_MM_S2    10000.0f

/* No.12（2026-11-21 の大会で作者の依頼で足した）：ターンと吸引（7.0V）は No.11 と同じ組 6。直進・斜めをもっと速くする。
 * 加速度 14000mm/s² は、7.0V の吸引でのグリップの上限（約 21700mm/s²）の内側。モーターが出せる加速度は、3000mm/s で約 26000mm/s² の見込み
 * （ただし 2026-11-16 にログから求め直した係数だと、それより 3 割くらい小さい）。1200mm/s から 3000mm/s まで上げて戻すのに約 540mm（クラシックで 3 区画くらい）要る */
#define SHORTEST12_MAX_SPEED_MM_S      3000.0f
#define SHORTEST12_ACCEL_MM_S2         14000.0f
#define SHORTEST12_DIAG_MAX_SPEED_MM_S 2100.0f
#define SHORTEST12_DIAG_ACCEL_MM_S2    12000.0f

/* ゴールにターンで入って終わるときに止まる加速度 [mm/s²] と、止まるまでの距離の上限 [mm]。
 * ゴールの区画のまん中から次の区画の境目までは 90mm なので、80mm 以内で止まる。6000mm/s² で 80mm なら 980mm/s から止まれる
 * （ToraNeko はハーフで 45mm・40mm）。
 * 2026-11-10 から、最短走行はゴールに入ってからもう 1 区画進んで止まる（sys/shortest.c の「■ ゴールで止まるところ」）ので、
 * これを使うのは、もう 1 区画進めないとき（ふつうは起きない）だけ */
#define SHORTEST_STOP_ACCEL_MM_S2  6000.0f
#define SHORTEST_STOP_DISTANCE_MM  80.0f

/* ---- 探索の前壁補正（ctrl/run.c。2026-10-28） ----
 * 区画の入口で、その区画に前の壁があるとき、前センサで測った壁までの距離が FRONT_WALL_AT_ENTRY_MM からずれていれば、
 * そのぶん、曲がり始め（スラロームの前距離）と、区画のまん中で止まる位置を直す。
 * 走るうちに前後の位置がずれても、前に壁がある区画で毎回もとに戻る。 */

/* 補正を実際にかけるか（1 かける、0 かけない）。0 でも、かけるはずだった量は測って、モード7 No.1 で出す。
 * ToraNeko では 2026-11-03 に 1 にした：前の表を測って直したあと、探索 1 回で 15 回の平均 +1.6mm（−7.0〜+9.3mm）。
 * 同じ場所では前の走りと似たずれが出たので、読み違いではなく本当の前後のずれと考えた。
 * 有効にして探索すると、作者が見て「だいぶ良くなった」（2026-11-03。測ったずれは平均 +2.0mm、−7.0〜+14.8mm。
 * 同じ 2 区画でいつも +8〜+15mm と大きく出る。その前の壁の読み方がずれているらしい）。
 * うまくいかないとき（次の区画で測ったずれが大きくなるなど）は 0 に戻す */
#define FRONT_CORRECTION_ENABLE 1
/* 区画の入口の辺にいるときの、前の壁までの距離 [mm]（区画の半分 90 + 区画のまん中から壁の面まで 84。ToraNeko は 45 + 42 = 87）。
 * 前のセンサ（タイヤの軸の 20.8mm 前）から壁までは約 153mm と遠いので、前の距離の表（ctrl/wall_dist.c）をこの距離まで測っておく */
#define FRONT_WALL_AT_ENTRY_MM   174.0f
/* 左前と右前の距離がこれ以上違うときは、近いほうだけを使う [mm]（2026-11-03）。
 * 探索のログで、片側に横の壁がないと、その側の前センサだけが 10〜17mm 遠く読んでいた（向きのずれは 2° 以下なので、
 * 斜めを向いたせいではない）。前の表は横の壁がある状態で測っていて、横の壁から返ってくる光の分が足りないと、
 * 遠く読む。近いほうは横の壁の光が足りているので、そちらを使う。違いが小さいときは、これまでどおり 2 つの平均 */
#define FRONT_CORRECTION_SENSOR_GAP_MM 6.0f  /* 仮（ToraNeko の値）。MK4 の前のセンサで実機で合わせる */
#define FRONT_CORRECTION_LIMIT_MM 5.0f  /* 直す量の上限 [mm]（センサの読み違いで大きく直さないように。ToraNeko は 1 回ごとのばらつきが ±5mm ほどあったので、2026-11-03 に 10 → 5。仮。実機で合わせる） */

/* ---- 壁切れ（ctrl/run.c・ctrl/side_edge.c。2026-10-28 に作り、2026-11-04 に柱も使えるように作り直した） ----
 * 探索の 1 区画の直進と、最短走行の縦横の直進で、横のセンサで見つけた壁の終わり・柱の端から区画の境目を求め、
 * 思っていた境目とのずれだけ、今の直進の残りの距離を直す。端の見つけ方と、端から境目までの距離は ctrl/side_edge.c。
 * 前は「壁あり」のしきい値を切ったところで見ていた（左 53.5・右 56.0mm で見つかった。しきい値が左右でちがうので
 * 左右で 3mm ちがった）。柱だけの山は低くしきい値に届かないので、山の半分で見るようにした（ctrl/side_edge.c）。 */
#define WALL_EDGE_ENABLE      1      /* 探索で、直進の残りを直すか（1 直す、0 測るだけ。測った量はモード7 No.1 で出す） */
/* 最短走行で、直進の残りを直すか。2026-11-04 に、測るだけで最短走行 No.4 を 3 回走らせ、ずれが 950〜1170mm/s でも
 * 0〜3mm と小さかった（logs/20261104-150708・150735・215001 の result）ので 1 にした */
#define FAST_WALL_EDGE_ENABLE 1
#define WALL_EDGE_WINDOW_MM   20.0f  /* いちばん近い境目から、これ以上ずれていたら、読み違いとして使わない [mm]（仮。ToraNeko の値。境目どうしは 180mm 離れている） */

/* ---- 探索の横壁合わせ（sys/explore.c・ctrl/run.c。2026-11-02） ----
 * 走っていて、区画の入口で横の壁が SIDE_TOO_CLOSE_MM より近いとわかったら、その区画のまん中で止まり、
 * 近すぎた側の壁のほうへ 90° 回って前壁合わせをし、元の向きに戻ってから探索を続ける（左右のずれと向きを直す）。 */

/* 横壁合わせをするか（1 する、0 しない）。0 でも、近すぎた回数と、いちばん近かった距離は測って、モード7 No.1 で出す。
 * ToraNeko では 2026-11-03 に 1 にした：横の表（L・R）を測った値にしたあと、探索で毎回 1 回ずつ 30.0〜31.7mm まで近づいていた
 * （ターンのあとに横へずれたところ）。読み違いではなく本当に近かったので、止まって直す */
#define SIDE_ALIGN_ENABLE 1
/* 横の壁がこれより近ければ「近すぎる」[mm]（区画のまん中で 84mm。20mm 寄っている。KOGUMA MK3 の Side_Too_Close_mm と同じ）。
 * 機体の幅は 70mm（半分 35mm）なので、64mm のとき、機体の横と壁のすきまは 29mm。仮。実機で合わせる
 * （ToraNeko はハーフで 32mm（まん中の 42mm から 10mm）） */
#define SIDE_TOO_CLOSE_MM 64.0f

/* ---- 吸引（drv/fan.c。2026-10-28） ---- */

/* 吸引ファンにかける電圧 [V]（仮。ToraNeko の値のまま。MK4 のファンで決め直す。
 * ToraNeko では 2026-11-02 に 2.0 → 5.0。上限は drv/fan.c の FAN_LIMIT_V（2026-11-10 から 7.0V））。
 * 2026-11-02 に作者が測った：5.0V で吸引の力 55g（機体 26g の約 2.1 倍。はかりの皿の上に浮かせて、表示が 55g 減った）。
 * 押しつける力は 26 + 55 = 81g なので、滑らずに出せる加速度は吸引なしの約 3.1 倍（μ = 0.8 なら約 2.5G） */
#define SUCTION_VOLTAGE_V 5.0f
#define SUCTION_RAMP_MS   500   /* 0 から SUCTION_VOLTAGE_V まで上げるのにかける時間 [ms]（急に回して電池の電圧が落ちないように） */

/* 吸引の力のテスト（モード6 No.4。2026-11-10）：1.0V から 1V ずつ 7.0V まで、1 段 5 秒ずつ回す。
 * 2026-11-10 に作者が測った（袋を貼り直し、一次スカートも変えたあと）：
 * 1V 10g、2V 50g、3V 80g、4V 110g、5V 130g、6V 150g、7V 170g（はかりの表示が減った分）。
 * 3V から上は 1V で約 20〜30g ずつ、電圧にほぼ比例して増える（電圧の 2 乗ではない。MODES.md のモード6 No.4） */
#define SUCTION_TEST_STEP_V   1.0f  /* 1 段で上げる電圧 [V] */
#define SUCTION_TEST_STEPS    7     /* 段の数（7 段目が 7.0V。drv/fan.c の上限 FAN_LIMIT_V と同じ。LED も 7 個） */
#define SUCTION_TEST_HOLD_MS  5000  /* 1 段を回す時間 [ms]（はかりの表示が落ち着いてから読めるように） */

/* ---- グリップの上限（最短走行の直進の加速度。2026-11-11。sys/shortest.c の grip_accel_limit_mm_s2()） ----
 * 吸引すると床に押しつけられて、滑りにくくなる。滑り始める加速度は、だいたい
 *   滑り始める加速度 = 吸引なしで滑り始める加速度 ×（機体の重さ + 吸引の力）÷ 機体の重さ
 * （2026-11-03 の加速度テストで、吸引 55g のとき、この式で約 11000mm/s²、測ると 12000mm/s² から滑り始めた）。
 * 最短走行の直進の加速度（No. ごとの SHORTEST*_ACCEL_MM_S2・*_DIAG_ACCEL_MM_S2）は、これに GRIP_MARGIN をかけた値を超えないようにする。
 * 吸引の力は、その No. の吸引の電圧から、下の表（2026-11-10 に測った）で出す（あいだは直線でつなぐ。7V より上は 7V の値）。
 * 今の値だと、吸引なしで約 2900、5V で約 17300、7V で約 21700mm/s²。
 * 仮。ここの値はどれも ToraNeko（26g、ミニッツのタイヤ）で測ったもの。MK4 の機体の重さは config/robot_params.h の ROBOT_MASS_G。
 * タイヤ・吸引の力が違うので、MK4 でモード4（加速度テスト）とモード6 No.4（吸引の力）を測ってから決め直す */
#define GRIP_NO_SUCTION_SLIP_MM_S2 3600.0f  /* 吸引なしで滑り始める加速度 [mm/s²]（2026-11-03 の加速度テスト。μ 約 0.37） */
#define GRIP_MARGIN                0.8f     /* 滑り始める加速度の何割まで使うか */
#define SUCTION_FORCE_1V_G  10.0f   /* 吸引の電圧ごとの吸引の力 [g]（2026-11-10 に測った。上の SUCTION_TEST の説明） */
#define SUCTION_FORCE_2V_G  50.0f
#define SUCTION_FORCE_3V_G  80.0f
#define SUCTION_FORCE_4V_G  110.0f
#define SUCTION_FORCE_5V_G  130.0f
#define SUCTION_FORCE_6V_G  150.0f
#define SUCTION_FORCE_7V_G  170.0f

/* ---- その場旋回 ---- */

#define PIVOT_OMEGA_DEG_S  720.0f   /* 最高の角速度 [deg/s]（KOGUMA は 2000。まずゆっくり） */
#define PIVOT_ALPHA_DEG_S2 7200.0f  /* 角加速度 [deg/s²]（KOGUMA は 50000。まずゆっくり） */

/* ---- 前壁合わせ ---- */

#define ALIGN_TIME_MS 500  /* 前壁合わせを続ける時間 [ms]（KOGUMA の Alignment_TIME と同じ 0.5 秒） */

/* ---- 止まるとき ---- */

#define STOP_SETTLE_MS 100  /* 区画のまん中で止まってから、制御を続けて待つ時間 [ms]（ぴたりと止めるため） */

/* ---- 探索でスタートに戻ったとき、お尻を後ろの壁に当てる（ctrl/run.c の run_search_back_to_wall()。2026-11-10） ----
 * 区画のまん中で北を向いたあと、速さの制御をしながら、まっすぐ後ろへゆっくり下がり、お尻を後ろの壁に押し当てる。
 * まん中から壁までは 34mm（START_OFFSET_MM）なので、それより BACK_TO_WALL_PRESS_MM だけ多く下がるように頼む。
 * 壁に当たって止まると、頼んだ位置との差（数 mm）の分だけ制御が後ろへ押し続けるので、お尻が壁に沿って、向きもそろう。
 * 2026-11-10 に最初は電圧を直接かけていたが、左右の摩擦の違いで片方のタイヤしか回らなかったので、速さの制御にした */
#define BACK_TO_WALL_SPEED_MM_S 50.0f   /* 下がる速さ [mm/s] */
#define BACK_TO_WALL_ACCEL_MM_S2 1000.0f  /* 速くする・遅くする加速度 [mm/s²] */
#define BACK_TO_WALL_PRESS_MM   3.0f    /* 壁まで（START_OFFSET_MM）より多く下がるように頼む分 [mm]（押し当てる強さ） */
#define BACK_TO_WALL_PRESS_MS   200     /* 下がり終わってから、押し当てたまま待つ時間 [ms] */

#endif /* CONFIG_RUN_PARAMS_H */
