#!/bin/sh
# run_all.sh — 全部やり直す: プラグインのビルド → 6 通りのビルドとトレース → サイクルのモデル → 表
#   必要: gcc-arm-none-eabi, libnewlib-arm-none-eabi, qemu-system-arm(8.2、プラグインあり), python3
#   HAL・CMSIS は ../dl/ に git clone(stm32h7xx-hal-driver, stm32h5xx-hal-driver, cmsis-device-h7, cmsis-device-h5, cmsis-core)
set -e
cd "$(dirname "$0")"
gcc -O2 -shared -fPIC -Wall -o plugin/libtrace.so plugin/trace_plugin.c
python3 build.py
for c in m7 m33; do for o in O0 dbg O2; do python3 analysis/cycle_model.py $c $o; done; done
python3 analysis/report.py > results/report.md
echo "results/report.md"
