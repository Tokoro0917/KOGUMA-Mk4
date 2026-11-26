# CPU の重さの見積もり(STM32H725 と STM32H562、2026-11-26)

MCU を STM32H725RG(Cortex-M7 550MHz)から STM32H562RG(Cortex-M33 250MHz)に替えるときに、
「4kHz の制御と 20kHz の電流制御が H562 で回るか」を確かめるために作った。**実機では測っていない**(誤差は ±3 割くらい)。

## やり方

1. ToraNeko.Mk3 の制御のコード(`App/ctrl/control.c`・`odometry.c`・`trajectory.c`・`wall_ctrl.c`・`wall_dist.c`、`sys/log.c`・`failsafe.c`)を**そのまま**使う。
   周期の定数だけ 4kHz・t24 の値に差し替える(`harness/override/` のヘッダ)
2. MK4 だけの処理は、ToraNeko と同じ書き方で新しく書いた(`harness/mk4_*.c`)
   - 20kHz の電流制御(mA への換算、過電流、回生の制限、PI、duty の上限、TIM1 の CCR への書き込み)
   - 壁センサの 5 つの順番、MT6835 の CRC と角度 → 速さ、IMU、4kHz に足す分(相補フィルタ、自己位置、I²t、フェイルセーフ、1kHz のログ)
3. Cortex-M7(H725)と Cortex-M33(H562)用に、3 つの最適化でコンパイルする
   - O0: 全部 `-O0`(CubeMX の Debug)
   - dbg: `ctrl/` だけ `-O2`、ほかは `-O0`(ToraNeko の Debug と同じ)
   - O2: 全部 `-O2`
4. QEMU(mps2-an500 = M7、mps2-an505 = M33)で、本物と同じ 50µs ごとの順番に動かす(直進、スラローム、前壁合わせ)。
   自分で書いたプラグイン(`plugin/trace_plugin.c`)で、印を付けた区間の命令とメモリの読み書きを全部記録する
5. 記録した命令を、コアの表でクロックに直す(`analysis/cycle_model.py`)。M33 は Cortex-M4 の TRM の表、M7 は 2 命令同時実行を簡単なスケジューラで見る。
   割り込みの入口・出口、FPU のレジスタの退避、バスの待ち(周辺・キャッシュしない RAM・Flash)も足す
6. ST の本物の HAL(H7・H5)も動かして、HAL で割り込みを受けたときの道すじも数える(`harness/hal_paths.c`)

## 結果(H562 250MHz、4kHz の制御、くわしくは `results/report.md`)

| 書き方 | 最適化 | CPU |
|---|---|---|
| 割り込みをレジスタを直接書いて受ける(LL) | dbg | **約 21%**(20〜28%) |
| 同じ | O2 | 約 14% |
| CubeMX の HAL のまま | dbg | 約 47%(44〜61%) |

- 1 回の時間(LL・dbg): 20kHz の処理 3.6µs、エンコーダ 7.3µs、IMU 2.1µs、4kHz の制御 11.3µs
- **重いのは 20kHz の処理とエンコーダの割り込み**。4kHz の制御は CPU の 4〜5% しか使わない。制御を 2kHz にしても 2〜4 ポイントしか下がらない
- 命令のキャッシュ(8KB)に割り込みのコード(8〜12KB)が入りきらない。外れる分で +5〜10% と見ている。足りなければ、速い処理を RAM に置く
- いちばん長いとき: 20kHz の処理 6〜15µs(50µs の中)、4kHz の制御が終わるまで 25〜141µs(250µs の中)
- 240MHz で使うので、上の値より 4% 重くなる

## 決めたこと

1. 20kHz の ADC の DMA、エンコーダ・IMU の SPI の DMA の割り込みは、**HAL を使わずレジスタを直接書く**(CLAUDE.md の「レジスタを直接書く 20kHz の処理」と同じ扱い。処理の流れをコメントで順に書く)
2. `ctrl/` に加えて、エンコーダと電流制御のコードも `-O2` にする
3. 割り算(1/電池の電圧、`/ CTRL_PERIOD_S`)は 1 回だけ計算して、あとは掛け算にする

## やり直し方

`run_all.sh`(必要: `gcc-arm-none-eabi`・`libnewlib-arm-none-eabi`・`qemu-system-arm`(8.2、プラグインの見出し `qemu-plugin.h` が要る)、
ToraNeko のリポジトリ(`build.py` の `TORANEKO_APP` に場所を書く)、ST の HAL・CMSIS を `../dl/` に git clone)。
記録(トレース)は 500MB ほどになるので、リポジトリには入れていない。
