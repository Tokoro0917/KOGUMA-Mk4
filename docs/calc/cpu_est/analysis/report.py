#!/usr/bin/env python3
"""
report.py — results/<core>_<cfg>.json(区間ごとのサイクル)を組み合わせて、
1 回あたりの時間 [µs]、CPU の使用率 [%]、20kHz の割り込みのいちばん遅い終わり、4kHz の処理の応答時間を出す。

  python3 analysis/report.py > results/report.md

■ 組み合わせ方(割り込みの入口・出口の数え方)
  E   = 割り込みの入口 12 + 出口 10〜12 サイクル(Cortex-M7・M33 の TRM)
  Efp = E + FP のレジスタの退避(lazy stacking: S0〜S15・FPSCR の 17 語、入口 17 + 出口 17)。
        typ は「割り込まれた側が FP を使っていた割合 50%」として半分を足す
  LL     : 20kHz = ADC2 の DMA 1 回、エンコーダ = 左・右の DMA の終わり 2 回、IMU = EXTI + DMA 1 回
  HAL-min: CubeMX の HAL のまま。ただし NVIC で ADC1 の DMA と SPI の送り側の DMA の割り込みを切り、
           ADC の DMA の半分(HT)の割り込みを切ったもの。SPI は 1 回の読み取りで 受け HT・受け TC・EOT の 3 回
  HAL-def: CubeMX の初めの作りのまま(ADC1・ADC2 とも HT と TC、SPI は 送り TC・受け HT・受け TC・EOT の 4 回)
"""
import json
import math
import os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RATE = {"isr20k": 20000, "enc": 10000, "imu": 6660, "ctrl": 4000, "tick": 1000}
LEVELS = ["min", "typ", "max"]
ENTRY = {"min": 22, "typ": 24, "max": 24}
FPSTACK = {"min": 0, "typ": 17, "max": 34}
EXTRA_MAX_VECTOR = {"m7": 12, "m33": 8}    # max: ベクタを読むのが遅い(フラッシュ)とき
ICACHE_MISS = {"min": 6, "typ": 8, "max": 12}   # H562: 16 バイトの線を 5WS のフラッシュから読む [サイクル]
CRIT_SECTION = 150   # メインの処理が割り込みを止めるいちばん長い所(scheduler_take_stats など)の見込み [サイクル]


def load(core, cfg):
    with open(os.path.join(HERE, "results", "%s_%s.json" % (core, cfg))) as f:
        return {int(k): v for k, v in json.load(f).items()}


def cyc(r, rid, var, level, stat="avg"):
    """区間 rid の、モデル level での平均(stat=avg)か最大(stat=max)"""
    return r[rid]["%s_%s" % (var, level)][stat]


def e(level, core, fp):
    v = ENTRY[level]
    if fp:
        v += FPSTACK[level]
    if level == "max":
        v += EXTRA_MAX_VECTOR[core]
    return v


def tasks(r, core, var, level, hal, stat="avg"):
    """1 回あたりのサイクル(割り込みの入口・出口を含む)を、処理ごとに返す"""
    c = lambda rid: cyc(r, rid, var, level, stat)
    ll_start = c(60)
    t = {}
    ctrl_ids = [40, 41, 42, 43, 44]
    if stat == "avg":
        # 4kHz: ふだん = 直進・一定の速さ・壁の補正あり(41)、高め = 場面ごとの平均のいちばん大きいもの
        ctrl = c(41) if level != "max" else max(c(i) for i in ctrl_ids)
    else:
        ctrl = max(c(i) for i in ctrl_ids)
    t["ctrl"] = e(level, core, True) + ctrl
    t["tick"] = e(level, core, False) + c(58)
    if hal == "LL":
        t["isr20k"] = e(level, core, True) + c(10)
        t["enc"] = e(level, core, False) + c(11) + e(level, core, True) + c(12)
        t["imu"] = e(level, core, False) + c(13) + e(level, core, True) + c(14)
    else:
        half = 0.5 if stat == "avg" else 1.0   # エンコーダの読み取りを始めるのは 2 回に 1 回
        body = c(10) + (c(52) - ll_start) * half
        if hal == "HAL-min":
            t["isr20k"] = e(level, core, True) + c(50) + body
            spi = 3 * e(level, core, False) + c(54) + c(53) + c(56)
        else:
            t["isr20k"] = (e(level, core, True) + c(50) + body + e(level, core, False) + c(51)
                           + e(level, core, False) + c(50) + e(level, core, False) + c(51))
            spi = 4 * e(level, core, False) + c(55) + c(54) + c(53) + c(56)
        fpx = e(level, core, True) - e(level, core, False)
        t["enc"] = 2 * spi + (c(11) - ll_start + c(52)) + c(12) + fpx
        t["imu"] = e(level, core, False) + c(57) + c(52) + spi + c(14) + fpx
    return t


def icache_lines(r, rids):
    lines = set()
    for rid in rids:
        lines.update(r[rid]["lines16_union"])
    return lines


def miss_cycles_per_call(r, rid, level):
    return r[rid]["lines16_per_call_max"] * ICACHE_MISS[level]


def cpu_percent(t, mhz, ctrl_hz):
    total = 0.0
    parts = {}
    for k, v in t.items():
        rate = RATE[k]
        if k == "ctrl":
            rate = ctrl_hz
        p = v * rate / (mhz * 1e6) * 100.0
        parts[k] = p
        total += p
    return total, parts


def response_time(t_max, mhz, ctrl_hz):
    """4kHz の処理の、いちばん遅い終わり(上の優先度の割り込みに割り込まれる分を足す)[µs]"""
    hp = [("isr20k", 1e6 / RATE["isr20k"]), ("enc", 1e6 / RATE["enc"]), ("imu", 1e6 / RATE["imu"]),
          ("tick", 1e6 / RATE["tick"])]
    c_us = {k: v / mhz for k, v in t_max.items()}
    resp = c_us["ctrl"]
    for _ in range(100):
        new = c_us["ctrl"] + sum(math.ceil(resp / period) * c_us[k] for k, period in hp)
        if abs(new - resp) < 1e-6:
            break
        resp = new
        if resp > 1e6 / ctrl_hz * 4:
            break
    return resp


def fmt(x, nd=1):
    return ("%." + str(nd) + "f") % x


def main():
    out = []
    p = out.append
    platforms = [
        ("H725 400MHz D$ OFF", "m7", "base", 400),
        ("H725 400MHz D$ ON", "m7", "dcache", 400),
        ("H725 550MHz D$ ON", "m7", "dcache", 550),
        ("H562 250MHz", "m33", "base", 250),
    ]
    names = {"isr20k": "20kHz 電流", "enc": "10kHz エンコーダ", "imu": "6.66kHz IMU", "ctrl": "4kHz 制御",
             "tick": "1kHz SysTick"}
    data = {}
    for core in ("m7", "m33"):
        for cfg in ("O0", "dbg", "O2"):
            data[(core, cfg)] = load(core, cfg)

    # ---- 1. 区間ごとの命令の数とサイクル ----
    p("## 1. 区間ごとの命令の数とサイクル(割り込みの入口・出口を含まない。avg は typ のモデル、[min..max] は全部の回の min モデルの最小〜max モデルの最大)\n")
    rid_names = {10: "20kHz の処理(LL)", 11: "エンコーダ左 DMA 終わり(LL)", 12: "エンコーダ右 + 計算(LL)",
                 13: "IMU EXTI(LL)", 14: "IMU DMA 終わり + 計算(LL)", 40: "4kHz 直進・加速", 41: "4kHz 直進・一定",
                 42: "4kHz 直進・減速", 43: "4kHz スラローム", 44: "4kHz 前壁合わせ", 50: "HAL ADC DMA TC",
                 51: "HAL ADC DMA HT", 52: "HAL_SPI_TransmitReceive_DMA", 53: "HAL SPI 受け DMA TC",
                 54: "HAL SPI 受け DMA HT", 55: "HAL SPI 送り DMA TC", 56: "HAL SPI EOT", 57: "HAL EXTI",
                 58: "HAL_IncTick", 60: "LL SPI 開始"}
    for core, var in (("m7", "base"), ("m7", "dcache"), ("m33", "base")):
        label = {"m7base": "Cortex-M7(H725、D キャッシュ OFF)", "m7dcache": "Cortex-M7(H725、D キャッシュ ON)",
                 "m33base": "Cortex-M33(H562)"}[core + var]
        p("### " + label + "\n")
        p("| 区間 | 命令 -O0 | 命令 dbg | 命令 -O2 | サイクル -O0 | サイクル dbg | サイクル -O2 |")
        p("|---|---|---|---|---|---|---|")
        for rid in sorted(rid_names):
            row = [rid_names[rid]]
            for cfg in ("O0", "dbg", "O2"):
                row.append(fmt(data[(core, cfg)][rid]["n_insn"]["avg"], 0))
            for cfg in ("O0", "dbg", "O2"):
                r = data[(core, cfg)]
                row.append("%s [%s..%s]" % (fmt(cyc(r, rid, var, "typ"), 0), fmt(r[rid][var + "_min"]["min"], 0),
                                            fmt(r[rid][var + "_max"]["max"], 0)))
            p("| " + " | ".join(row) + " |")
        p("")

    # ---- 2. 処理ごとの µs(1 回) ----
    for hal in ("LL", "HAL-min", "HAL-def"):
        p("## 2. 1 回あたりの時間 [µs](割り込みの入口・出口込み、%s)。typ(min〜max)\n" % hal)
        p("| 処理 | 最適化 | " + " | ".join(pl[0] for pl in platforms) + " |")
        p("|---|---|" + "---|" * len(platforms))
        for k in ("isr20k", "enc", "imu", "ctrl"):
            for cfg in ("O0", "dbg", "O2"):
                row = [names[k], cfg]
                for (pname, core, var, mhz) in platforms:
                    r = data[(core, cfg)]
                    vals = {lv: tasks(r, core, var, lv, hal)[k] for lv in LEVELS}
                    row.append("%s (%s〜%s)" % (fmt(vals["typ"] / mhz, 2), fmt(vals["min"] / mhz, 2),
                                               fmt(vals["max"] / mhz, 2)))
                p("| " + " | ".join(row) + " |")
        p("")

    # ---- 3. CPU の使用率 ----
    p("## 3. CPU の使用率 [%](typ(min〜max)。H562 は ICACHE に当たる場合。外れの分は 5 章)\n")
    p("| 書き方 | 最適化 | 制御 | " + " | ".join(pl[0] for pl in platforms) + " |")
    p("|---|---|---|" + "---|" * len(platforms))
    summary = {}
    for hal in ("LL", "HAL-min", "HAL-def"):
        for cfg in ("O0", "dbg", "O2"):
            for ctrl_hz in (4000, 2000):
                row = [hal, cfg, "%dkHz" % (ctrl_hz // 1000)]
                for (pname, core, var, mhz) in platforms:
                    r = data[(core, cfg)]
                    vals = {}
                    for lv in LEVELS:
                        vals[lv] = cpu_percent(tasks(r, core, var, lv, hal), mhz, ctrl_hz)[0]
                    summary[(hal, cfg, ctrl_hz, pname)] = vals
                    row.append("%s (%s〜%s)" % (fmt(vals["typ"], 0), fmt(vals["min"], 0), fmt(vals["max"], 0)))
                p("| " + " | ".join(row) + " |")
    p("")

    # ---- 3b. 内わけ ----
    p("### 内わけ(typ、4kHz、[%])\n")
    p("| 書き方 | 最適化 | 機 | 20kHz | 10kHz | IMU | 4kHz | 1kHz | 計 |")
    p("|---|---|---|---|---|---|---|---|---|")
    for hal in ("LL", "HAL-min", "HAL-def"):
        for cfg in ("dbg", "O2"):
            for (pname, core, var, mhz) in platforms:
                if pname == "H725 400MHz D$ ON":
                    continue
                r = data[(core, cfg)]
                total, parts = cpu_percent(tasks(r, core, var, "typ", hal), mhz, 4000)
                p("| %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
                    hal, cfg, pname, fmt(parts["isr20k"]), fmt(parts["enc"]), fmt(parts["imu"]), fmt(parts["ctrl"]),
                    fmt(parts["tick"]), fmt(total)))
    p("")

    # ---- 4. 20kHz の割り込みのいちばん遅い終わり ----
    p("## 4. 20kHz の処理: 割り込みが来てから終わるまでのいちばん長い時間 [µs](max のモデル、いちばん長い回)\n")
    p("入口の遅れ = 割り込みを止めている所 %d サイクル + 入口 + FP の退避。HAL-def は同じ優先度の ADC1 の割り込みが先に入る分も足す。\n" % CRIT_SECTION)
    p("| 書き方 | 最適化 | " + " | ".join(pl[0] for pl in platforms) + " |")
    p("|---|---|" + "---|" * len(platforms))
    for hal in ("LL", "HAL-min", "HAL-def"):
        for cfg in ("O0", "dbg", "O2"):
            row = [hal, cfg]
            for (pname, core, var, mhz) in platforms:
                r = data[(core, cfg)]
                t = tasks(r, core, var, "max", hal, stat="max")
                worst = CRIT_SECTION + t["isr20k"]
                if hal == "HAL-def":
                    worst = CRIT_SECTION + t["isr20k"]  # ADC1 の分は tasks の中で足してある
                row.append(fmt(worst / mhz, 2))
            p("| " + " | ".join(row) + " |")
    p("")

    # ---- 4b. 4kHz の処理の応答時間 ----
    p("## 4b. 4kHz の処理の、起こされてから終わるまでのいちばん長い時間 [µs](上の割り込みに割り込まれる分込み、max のモデル。周期 250µs に入るか)\n")
    p("| 書き方 | 最適化 | " + " | ".join(pl[0] for pl in platforms) + " |")
    p("|---|---|" + "---|" * len(platforms))
    for hal in ("LL", "HAL-min", "HAL-def"):
        for cfg in ("O0", "dbg", "O2"):
            row = [hal, cfg]
            for (pname, core, var, mhz) in platforms:
                r = data[(core, cfg)]
                t = tasks(r, core, var, "max", hal, stat="max")
                row.append(fmt(response_time(t, mhz, 4000), 0))
            p("| " + " | ".join(row) + " |")
    p("")

    # ---- 5. H562 の ICACHE ----
    p("## 5. H562 の ICACHE(8KB、2-way、16 バイトの線 = 512 本)\n")
    p("| 最適化 | 周期の処理が通る線(LL) | 同(HAL を含む) | 大きさ [KB] | 1 回で通る線 20kHz / 4kHz | 全部外れたときの足し [%%](typ 8 サイクル/線、HAL-min) |")
    p("|---|---|---|---|---|---|")
    for cfg in ("O0", "dbg", "O2"):
        r = data[("m33", cfg)]
        ll = icache_lines(r, [10, 11, 12, 13, 14, 40, 41, 42, 43, 44, 58])
        allr = icache_lines(r, [10, 11, 12, 13, 14, 40, 41, 42, 43, 44, 50, 51, 52, 53, 54, 55, 56, 57, 58])
        cold = 0.0
        for rid, rate in ((10, 20000), (11, 10000), (12, 10000), (13, 6660), (14, 6660), (41, 4000),
                          (50, 20000), (52, 10000 + 6660 + 10000), (53, 2 * 10000 + 6660), (54, 2 * 10000 + 6660),
                          (56, 2 * 10000 + 6660), (57, 6660)):
            cold += miss_cycles_per_call(r, rid, "typ") * rate / 250e6 * 100
        p("| %s | %d | %d | %.1f | %d / %d | +%.0f |" % (cfg, len(ll), len(allr), len(allr) * 16 / 1024.0,
                                                       r[10]["lines16_per_call_max"], r[41]["lines16_per_call_max"],
                                                       cold))
    p("")
    print("\n".join(out))


if __name__ == "__main__":
    main()
