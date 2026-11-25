# KOGUMA MK4 — Claude 向けの作業ルール

マイクロマウス(クラシック)KOGUMA MK4 のリポジトリ。概要は [README.md](README.md)、仕様は [docs/spec.md](docs/spec.md)、ソフトの設計は [docs/software.md](docs/software.md)。

ソフトは **ToraNeko.Mk3 のファームウェア(`Tokoro0917/toraneko.mk3` の `software/main-controller/`)と同じ作り**にする(2026-11-23 決定)。この文書の「コードの書き方」も ToraNeko の `CLAUDE.md` と同じ。

## コードの書き方(最優先のルール)

コードを読むのは作者本人で、プログラミングは得意ではない。**作者が自分で読んで理解し、直せること**を何より優先する。短さ・賢さ・汎用性よりも、素直で読みやすい書き方を選ぶ。

- **素直に書く**。同じ処理が数行並ぶくらいなら、ループや表にまとめるより並べて書いたほうがよい(KOGUMA・ToraNeko のコードくらいの書き方が基準)
- **避ける書き方**。使わずに書けるなら使わない。どうしても必要なら、何をしているかをコメントで説明する
  - ビット演算(`<<`、`>>`、`&`、`|` によるフラグ操作)
  - 三項演算子(`a ? b : c`)→ `if` で書く
  - `%` による巻き戻し(リングバッファの添字など)→ `if (i >= N) { i = 0; }` で書く
  - ポインタ演算、関数ポインタ、関数のようなマクロ、共用体
  - 1行に複数の処理を詰め込む書き方
  - `printf` のための型キャスト(`(unsigned long)x` など)。arm-none-eabi-gcc では `uint32_t` はそのまま `%lu` で出せる
- MK4 で避けられない所(レジスタを直接書く 20kHz の処理、DMA の置き場所の確かめ、Flash のレコード)は、処理の流れをコメントで順に説明する
- **名前で意味がわかるようにする**。物理量には単位を付ける(`speed_mm_s`、`current_mA`、`wait_ms`、`angle_deg`)。1文字の変数は、ループの `i` と、区画の座標の `x`・`y` だけ
- **関数は短く、1つの仕事だけ**にする。関数の前に「何をする関数か」を1〜2行で書く
- **コメントは日本語**で、「何をしているか」と「なぜそうするか」を書く。ファイルの先頭には、そのファイルの役割を書く
- **難しい仕組み**(割り込み、DMA、`volatile`、割り込み禁止、キャッシュ、MPU など)を使う箇所は、処理の流れをコメントで順に説明する
- 新しい書き方や HAL の機能を初めて使ったときは、返答の中でもその説明を添える
- 名前の付け方・層の決まり(`drv` → `ctrl`・`maze` → `sys`、HAL を呼ぶのは `drv/` と `sys/scheduler.c` だけ)は [docs/software.md](docs/software.md) の 2 章と 14 章
- STM32H725 の RAM・キャッシュ・DMA は [docs/firmware_memory.md](docs/firmware_memory.md) の決まりを守る(DMA の配列は `DMA_BUF`、DMA を動かす前に `dma_check()`)

## 作業の進め方

- 返答・ドキュメント・コメントは日本語
- 作者に作業をお願いするときは、上から順にやればよい手順(どの画面で何を押すか、何が表示されれば成功か)を示す
- ファームウェアのビルドは `software/main-controller/KOGUMA-Mk4/` で `cmake --preset Debug && cmake --build --preset Debug`。push 前に必ずビルドを通す(`App/` は `-Wall -Wextra` で警告なし)
- ToraNeko・KOGUMA(`KOGUMA.MkIIl`)のコードは参照用。MK4 に持ってくるときは、機能ごとに中身を確かめてから移し、出どころ(ファイル名)をコメントに書く
- 実機の出力は `software/main-controller/logs/` に残す(ビューアで保存したもの)。値を決めるときは、まずここのデータを見る
- モードを足したり、中身・番号を変えたりしたら、`software/main-controller/README.md` の「モード一覧」と `MODES.md` を同じコミットで直す
- CubeMX の生成コード(`Core/`、`Drivers/`、`cmake/stm32cubemx/`)は `USER CODE` 欄以外を編集しない

## 回路・基板(KiCad)

- 回路図・基板は `hardware/kicad/`。変えたら ERC(エラー 0)と、DRC の回路図との食い違い 0 を確かめる
- `hardware/kicad/KOGUMA-Mk4/gen_pcb.py` は `KOGUMA-Mk4.kicad_pro` を上書きする。走らせたあとは `git checkout -- KOGUMA-Mk4.kicad_pro` で戻してから `place_caps.py` を走らせる
- タイヤ24mm 用の基板(ブランチ `claude/trusting-dirac-1tdt54`、`hardware/kicad/KOGUMA-Mk4_t24/`)は、回路図を変えたら次の順で作り直す(リポジトリの一番上で): `/usr/bin/python3.12 hardware/kicad/make_main_t24.py` → `(cd hardware/kicad/KOGUMA-Mk4 && /usr/bin/python3.12 place_caps.py t24)` → `/usr/bin/python3.12 hardware/kicad/place_main_t24.py` → `/usr/bin/python3.12 hardware/kicad/route_power_t24.py`(電池の電圧の配線) → `/usr/bin/python3.12 hardware/kicad/bom_t24.py`
- 部品を選ぶ・寸法を決めるときは、データシートで確かめ、PDF を `docs/reference/datasheets/` に保存して `docs/reference/README.md` に足す
