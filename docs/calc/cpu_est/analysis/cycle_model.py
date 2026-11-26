#!/usr/bin/env python3
"""
cycle_model.py — QEMU のトレース(実行した命令の番地 + メモリの読み書き)を、コアごとのサイクルの
モデルでサイクル数に直す。

  python3 analysis/cycle_model.py m33 O2      →  results/m33_O2.json

■ 入力
  build/<core>_<cfg>/bench.elf   (逆アセンブルして、番地 → 命令・大きさ・レジスタ)
  traces/<core>_<cfg>.txt        (plugin/trace_plugin.c の出力: B id / I pc / M addr L|S size / E id)

■ モデル(3 通り: min・typ・max。数は下の PARAMS。根拠は report の「前提」)
  Cortex-M33(1 つずつ実行、3 段のパイプライン)
    Cortex-M4 の TRM の表と同じ形の足し算(M33 の TRM は表を出していないので、M4 と同じとみなす):
    ALU 1、LDR 2(LDR/STR の続きでぶつからなければ 1)、STR 1、LDRD/STRD 3、LDM/STM/PUSH/POP 1+N(+P)、
    分岐は 取る 1+P(P = 1〜2)・取らない 1、MUL/MLA 1、SDIV/UDIV 2〜12、
    VADD/VSUB/VMUL/VCVT/VMOV 1、VMLA/VFMA 3、VDIV/VSQRT 14、VLDR/VSTR 2、VPUSH/VPOP 1+N
  Cortex-M7(2 つずつ出せる、6 段)
    命令を順に並べる簡単なスケジューラ: レジスタの依存(結果が出るまでの遅れ)と、同じサイクルに
    2 つ出せる組(ALU+ALU、ALU+LD/ST、FP+LD/ST、…+分岐)を見て、出すサイクルを決める。
    max は 2 つ同時に出さない(1 つずつ)。
  メモリ: 番地で RAM の種類・周辺のバスを分け、読みの遅れと、書きのバスの占有(1 段の書きバッファ)を足す。
"""
import json
import os
import re
import subprocess
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CORES = {
    "m7": dict(code=0x00000000, ram=0x20000000, fake=0x60000000, family="h7"),
    "m33": dict(code=0x10000000, ram=0x38000000, fake=0x80000000, family="h5"),
}
# にせの周辺の場所(build.py の FAKE_SLOTS と同じ順) → バスの種類
SLOT_BUS = {
    "h7": ["apb", "apb", "ahb", "ahb", "apb", "ahb", "apb", "ahb"],   # D2_APB1, D2_APB2, D2_AHB1, D2_AHB2, D1_APB1, D1_AHB1, D3_APB1, D3_AHB1(GPIO)
    "h5": ["apb", "apb", "ahb", "ahb", "apb", "ahb", "ahb"],          # APB1, APB2, AHB1(GPDMA), AHB2(GPIO・ADC), APB3, AHB3, AHB4
}

# ---- メモリの遅れ [コアのサイクル]: (読みの遅れ, 書きのバスの占有) を min/typ/max で ----
#   H725: 400MHz のとき AXI・AHB 200MHz、APB 100MHz。550MHz でもバスの比は同じなので、同じサイクル数とする
#   H562: 250MHz、AHB・APB とも 250MHz(1:1)、SRAM は待ちなし
MEM = {
    "m7": {
        "tcm":     [(0, 0), (0, 0), (0, 0)],
        "d2sram":  [(8, 2), (12, 4), (18, 6)],     # DMA の配列(SRAM1・2、キャッシュしない)を CPU が読む
        "axisram": [(6, 2), (8, 3), (12, 4)],      # ログ(D キャッシュ OFF のとき。書きはバッファで隠れる)
        "flash":   [(8, 0), (12, 0), (18, 0)],     # 定数(リテラル・表)を D 側で読む、D キャッシュ OFF のとき
        "ahb":     [(12, 4), (18, 6), (30, 10)],   # DMA・ADC・GPIO のレジスタ
        "apb":     [(20, 6), (30, 8), (45, 14)],   # TIM・SPI・EXTI・IWDG のレジスタ
        "ppb":     [(1, 1), (2, 2), (4, 4)],       # NVIC
    },
    "m33": {
        "tcm":     [(0, 0), (0, 0), (0, 0)],       # SRAM(待ちなし)
        "d2sram":  [(0, 0), (0, 0), (0, 0)],
        "axisram": [(0, 0), (0, 0), (0, 0)],
        "flash":   [(0, 0), (0, 0), (1, 0)],       # 定数を読む: ICACHE に当たれば待ちなし(外れは別に数える)
        "ahb":     [(1, 1), (2, 1), (4, 2)],
        "apb":     [(2, 1), (3, 2), (6, 3)],
        "ppb":     [(0, 1), (1, 1), (2, 2)],
    },
}
# M7 で D キャッシュを ON にしたとき(または定数・ログを TCM に置いたとき)の差し替え
MEM_M7_DCACHE = {
    "flash":   [(0, 0), (0, 0), (2, 0)],
    "axisram": [(0, 0), (0, 0), (2, 1)],
}

CONDS = {"eq", "ne", "cs", "cc", "hs", "lo", "mi", "pl", "vs", "vc", "hi", "ls", "ge", "lt", "gt", "le", "al"}
LOAD1 = {"ldr", "ldrb", "ldrh", "ldrsb", "ldrsh", "ldrex", "ldrexb", "ldrexh", "ldrt", "ldrbt", "ldrht"}
LOAD2 = {"ldrd"}
STORE1 = {"str", "strb", "strh", "strex", "strexb", "strexh"}
STORE2 = {"strd"}
LDM = {"ldm", "ldmia", "ldmdb", "ldmfd", "pop"}
STM = {"stm", "stmia", "stmdb", "stmea", "stmfd", "push"}
VLD = {"vldr"}
VST = {"vstr"}
VLDM = {"vldm", "vldmia", "vldmdb", "vpop"}
VSTM = {"vstm", "vstmia", "vstmdb", "vpush"}
BRANCH = {"b", "bl", "blx", "bx", "cbz", "cbnz", "tbb", "tbh"}
MUL = {"mul", "muls", "mla", "mls", "smull", "umull", "smlal", "umlal", "smulbb", "smultb", "smlabb", "smmul",
       "smmla", "umaal", "smulwb", "smlad", "smuad"}
DIV = {"sdiv", "udiv"}
FP_SIMPLE = {"vadd", "vsub", "vmul", "vnmul", "vabs", "vneg", "vcvt", "vcvtr", "vcvta", "vcvtn", "vcvtp", "vcvtm",
             "vmov", "vseleq", "vselge", "vselgt", "vselvs", "vmaxnm", "vminnm", "vrinta", "vrintn", "vrintp",
             "vrintm", "vrintz", "vrintr", "vrintx", "vcmp", "vcmpe", "vmrs", "vmsr", "vcvtb", "vcvtt"}
FP_MAC = {"vmla", "vmls", "vnmla", "vnmls"}
FP_FMA = {"vfma", "vfms", "vfnma", "vfnms"}
FP_DIV = {"vdiv", "vsqrt"}
BARRIER = {"dsb", "dmb", "isb"}
ALU = {"add", "adds", "adc", "adcs", "sub", "subs", "sbc", "sbcs", "rsb", "rsbs", "mov", "movs", "movw", "movt",
       "mvn", "mvns", "and", "ands", "orr", "orrs", "orn", "orns", "eor", "eors", "bic", "bics", "lsl", "lsls",
       "lsr", "lsrs", "asr", "asrs", "ror", "rors", "rrx", "cmp", "cmn", "tst", "teq", "neg", "negs", "uxtb",
       "uxth", "sxtb", "sxth", "ubfx", "sbfx", "bfi", "bfc", "clz", "rev", "rev16", "revsh", "rbit", "adr", "addw",
       "subw", "ssat", "usat", "nop", "uxtab", "uxtah", "sxtab", "sxtah", "sel", "uadd8", "usub8", "qadd", "qsub",
       "cpsid", "cpsie", "mrs", "msr", "bkpt", "svc", "wfi", "wfe", "sev", "yield", "udf"}
KNOWN = (LOAD1 | LOAD2 | STORE1 | STORE2 | LDM | STM | VLD | VST | VLDM | VSTM | BRANCH | MUL | DIV | FP_SIMPLE |
         FP_MAC | FP_FMA | FP_DIV | BARRIER | ALU)
REG_RE = re.compile(r"\b(r1[0-5]|r[0-9]|sp|lr|pc|ip|fp|sl|sb|s[0-9]{1,2}|d[0-9]{1,2})\b")
RANGE_RE = re.compile(r"\b([sd])([0-9]{1,2})-[sd]([0-9]{1,2})\b")
ALIAS = {"ip": "r12", "fp": "r11", "sl": "r10", "sb": "r9"}


def split_mnemonic(m):
    """'movne' → ('mov', 'ne')、'vadd.f32' → ('vadd', None) と、型の '.f64' などを返す"""
    dtype = ""
    if "." in m:
        parts = m.split(".")
        m = parts[0]
        dtype = ".".join(parts[1:])
    if m in KNOWN:
        return m, None, dtype
    if re.fullmatch(r"it[te]{0,3}", m):
        return "it", None, dtype
    if len(m) > 2 and m[-2:] in CONDS and m[:-2] in KNOWN:
        return m[:-2], m[-2:], dtype
    if len(m) > 2 and m[-2:] in CONDS and re.fullmatch(r"it[te]{0,3}", m[:-2]):
        return "it", None, dtype
    return m, None, dtype


def expand_regs(text):
    regs = []
    for m in RANGE_RE.finditer(text):
        kind, a, b = m.group(1), int(m.group(2)), int(m.group(3))
        for i in range(a, b + 1):
            regs.append("%s%d" % (kind, i))
    text = RANGE_RE.sub(" ", text)
    for r in REG_RE.findall(text):
        regs.append(ALIAS.get(r, r))
    out = []
    for r in regs:
        if r.startswith("d") and r[1:].isdigit():
            n = int(r[1:])
            out += ["s%d" % (2 * n), "s%d" % (2 * n + 1)]
        else:
            out.append(r)
    return out


def fp_regs_count(text):
    return len([r for r in expand_regs(text) if r.startswith("s")])


class Insn:
    __slots__ = ("pc", "size", "base", "cond", "dtype", "ops", "dests", "srcs", "kind", "nregs", "pc_load",
                 "is_fp", "is_f64", "func")


def decode(core, elf):
    """逆アセンブルして、番地 → Insn の表を作る"""
    dis = subprocess.run(["arm-none-eabi-objdump", "-d", elf], capture_output=True, text=True).stdout
    table = {}
    func = "?"
    for line in dis.splitlines():
        m = re.match(r"^([0-9a-f]+) <(.+)>:$", line)
        if m:
            func = m.group(2)
            continue
        m = re.match(r"^\s*([0-9a-f]+):\t([0-9a-f ]+)\t(\S+)\s*(.*)$", line)
        if not m:
            continue
        pc = int(m.group(1), 16)
        raw = m.group(2).split()
        size = sum(len(x) for x in raw) // 2
        mn = m.group(3)
        ops = m.group(4).split("@")[0].split(";")[0].strip()
        ins = Insn()
        ins.pc = pc
        ins.size = size
        ins.func = func
        base, cond, dtype = split_mnemonic(mn)
        ins.base, ins.cond, ins.dtype, ins.ops = base, cond, dtype, ops
        ins.is_f64 = "f64" in dtype
        ins.is_fp = base.startswith("v")
        regs = expand_regs(ops)
        regs_nosp = [r for r in regs if r not in ("sp", "pc")]
        dests, srcs = [], []
        kind = "alu"
        nregs = 1
        ins.pc_load = False
        if base in LOAD1 or base in VLD:
            kind = "load"
            if regs:
                dests = [regs[0]]
                srcs = regs[1:]
            if regs and regs[0] == "pc":
                ins.pc_load = True
        elif base in LOAD2:
            kind = "load2"
            dests = regs[:2]
            srcs = regs[2:]
            nregs = 2
        elif base in STORE1 or base in VST:
            kind = "store"
            srcs = regs
        elif base in STORE2:
            kind = "store2"
            srcs = regs
            nregs = 2
        elif base in LDM or base in VLDM:
            kind = "ldm"
            inner = re.search(r"\{(.*)\}", ops)
            lst = expand_regs(inner.group(1)) if inner else regs
            dests = lst
            nregs = len(lst)
            if base in VLDM:
                nregs = fp_regs_count(inner.group(1) if inner else ops)
            if "pc" in lst:
                ins.pc_load = True
            if base not in ("pop", "vpop"):
                srcs = regs[:1]
        elif base in STM or base in VSTM:
            kind = "stm"
            inner = re.search(r"\{(.*)\}", ops)
            lst = expand_regs(inner.group(1)) if inner else regs
            srcs = lst
            nregs = len(lst)
            if base in VSTM:
                nregs = fp_regs_count(inner.group(1) if inner else ops)
        elif base in BRANCH:
            kind = "branch"
            srcs = regs
            if cond:
                srcs = srcs + ["flags"]
        elif base == "it":
            kind = "it"
            srcs = ["flags"]
        elif base in MUL:
            kind = "mul"
            if base in ("smull", "umull", "smlal", "umlal", "umaal"):
                dests = regs[:2]
                srcs = regs[2:]
                if base in ("smlal", "umlal", "umaal"):
                    srcs = regs
            else:
                dests = regs[:1]
                srcs = regs[1:]
        elif base in DIV:
            kind = "div"
            dests = regs[:1]
            srcs = regs[1:]
        elif base in BARRIER:
            kind = "barrier"
        elif base in ("cmp", "cmn", "tst", "teq"):
            kind = "alu"
            dests = ["flags"]
            srcs = regs
        elif base in ("vcmp", "vcmpe"):
            kind = "fp"
            dests = ["fpflags"]
            srcs = regs
        elif base == "vmrs":
            kind = "fpmov"
            srcs = ["fpflags"]
            dests = ["flags"] if "APSR" in ops else regs[:1]
        elif base == "vmov":
            core_regs = [r for r in regs if r.startswith("r") or r == "lr"]
            fp_r = [r for r in regs if r.startswith("s")]
            kind = "fpmov"
            if len(core_regs) == 2 and regs and regs[0].startswith("r"):
                dests = core_regs
                srcs = fp_r
                nregs = 2
            elif len(core_regs) == 2:
                dests = fp_r
                srcs = core_regs
                nregs = 2
            else:
                dests = regs[:1]
                srcs = regs[1:]
                if fp_r and not core_regs:
                    kind = "fp"
            if ops.split(",")[0].strip().startswith("d") and len(core_regs) == 0:
                dests = expand_regs(ops.split(",")[0])
        elif base in FP_MAC:
            kind = "fpmac"
            dests = regs[:1]
            srcs = regs
        elif base in FP_FMA:
            kind = "fpfma"
            dests = regs[:1]
            srcs = regs
        elif base in FP_DIV:
            kind = "fpdiv"
            dests = regs[:1]
            srcs = regs[1:]
        elif base.startswith("v"):
            kind = "fp"
            dests = regs[:1]
            srcs = regs[1:]
        else:
            kind = "alu"
            dests = regs[:1]
            srcs = regs[1:]
            if base in ("movt", "bfi", "bfc"):
                srcs = regs
            if base.endswith("s") and base not in ("cmp", "cmn", "tst", "teq") and base[:-1] in KNOWN:
                dests = dests + ["flags"]
        if cond:
            srcs = srcs + ["flags"]
        ins.kind = kind
        ins.nregs = max(nregs, 1)
        ins.dests = [d for d in dests if d not in ("sp", "pc")]
        ins.srcs = [s for s in srcs if s not in ("sp", "pc")]
        table[pc] = ins
    return table


def mem_category(core, addr):
    c = CORES[core]
    fam = c["family"]
    if c["code"] <= addr < c["code"] + 0x400000:
        return "flash", None
    ram = c["ram"]
    if ram <= addr < ram + 0x100000:
        return "tcm", None
    if ram + 0x110000 <= addr < ram + 0x120000:
        return "d2sram", None
    if ram + 0x180000 <= addr < ram + 0x200000:
        return "axisram", None
    if c["fake"] <= addr < c["fake"] + 0x1000000:
        slot = (addr - c["fake"]) // 0x100000
        bus = SLOT_BUS[fam][slot] if slot < len(SLOT_BUS[fam]) else "apb"
        return bus, slot
    if addr >= 0xE0000000:
        return "ppb", None
    return "tcm", None


# ---- コアの命令のサイクル(M33 の足し算のモデル)----
M33_P = [1, 1, 2]          # 分岐で取り直す分(min/typ/max)
M33_DIV = [2, 6, 12]


def m33_cost(ins, taken, prev, next_ins, level):
    k = ins.kind
    p = M33_P[level]
    if k == "alu":
        return 1
    if k == "it":
        return [0, 0, 1][level]
    if k == "load":
        if ins.pc_load:
            return 2 + p
        if prev is not None and prev.kind in ("load", "store") and level < 2:
            if not (set(ins.srcs) & set(prev.dests)):
                return 1
        return 2
    if k == "store":
        return [1, 1, 2][level]
    if k in ("load2", "store2"):
        return [2, 3, 3][level]
    if k == "ldm":
        c = 1 + ins.nregs
        if ins.pc_load:
            c += p
        return c
    if k == "stm":
        return 1 + ins.nregs
    if k == "branch":
        if ins.base in ("tbb", "tbh"):
            return 2 + p
        if taken:
            if ins.base in ("bl", "blx", "bx"):
                return 1 + [1, 2, 2][level]
            return 1 + p
        return 1
    if k == "mul":
        if ins.base in ("smull", "umull", "smlal", "umlal", "umaal"):
            return [1, 1, 2][level]
        return 1
    if k == "div":
        return M33_DIV[level]
    if k in ("fp", "fpmov"):
        c = 1
        if ins.kind == "fpmov" and ins.nregs == 2:
            c = 2
        if level == 2 and next_ins is not None and (set(next_ins.srcs) & set(ins.dests)):
            c += 1
        return c
    if k in ("fpmac", "fpfma"):
        return 3
    if k == "fpdiv":
        return 14
    if k == "barrier":
        return [2, 3, 4][level]
    return 1


# ---- M7 のスケジューラのモデル ----
M7_LAT = {
    #           min typ max (結果を使えるまでのサイクル)
    "alu":     (1, 1, 1),
    "it":      (0, 0, 1),
    "load":    (1, 2, 3),
    "load2":   (1, 2, 3),
    "ldm":     (1, 2, 3),
    "mul":     (1, 2, 3),
    "fp":      (2, 3, 4),
    "fpmov":   (1, 2, 2),
    "fpmac":   (4, 6, 7),
    "fpfma":   (3, 4, 5),
}
M7_PAIR = {  # (前の種類, 後の種類) で同じサイクルに出せる組
    ("A", "A"), ("A", "L"), ("L", "A"), ("A", "S"), ("S", "A"), ("A", "M"), ("M", "A"), ("F", "L"), ("L", "F"),
    ("F", "S"), ("S", "F"), ("A", "F"), ("F", "A"), ("A", "B"), ("L", "B"), ("S", "B"), ("F", "B"), ("M", "B"),
}
M7_PAIR_MIN_EXTRA = {("L", "L"), ("L", "S"), ("S", "L")}


def m7_class(ins):
    k = ins.kind
    if k in ("alu", "it"):
        return "A"
    if k in ("load",):
        return "L"
    if k in ("store",):
        return "S"
    if k == "mul":
        return "M"
    if k in ("fp", "fpmov", "fpmac", "fpfma"):
        return "F"
    if k == "branch":
        return "B"
    return "X"  # 2 つ同時に出せない(LDM・STM・LDRD・割り算・バリア)


class Bus:
    """1 段の書きバッファ: 前の書きがバスでまだ終わっていなければ、次の書き・読みは待つ"""

    def __init__(self):
        self.busy = defaultdict(int)

    def access(self, t, cat, is_store, params):
        read_extra, write_occ = params[cat]
        if cat in ("tcm",):
            return 0, 0
        start = max(t, self.busy[cat])
        wait = start - t
        if is_store:
            self.busy[cat] = start + write_occ
            return wait, 0
        return wait, read_extra


def mem_params(core, level, dcache):
    p = {k: v[level] for k, v in MEM[core].items()}
    if core == "m7" and dcache:
        for k, v in MEM_M7_DCACHE.items():
            p[k] = v[level]
    return p


def cost_m33(seq, level, params):
    bus = Bus()
    t = 0
    prev = None
    n = len(seq)
    for i in range(n):
        ins, taken, mems = seq[i]
        nxt = seq[i + 1][0] if i + 1 < n else None
        c = m33_cost(ins, taken, prev, nxt, level)
        stall = 0
        for (addr_cat, is_store) in mems:
            wait, extra = bus.access(t + c, addr_cat, is_store, params)
            stall += wait + extra
        t += c + stall
        prev = ins
    return t


def cost_m7(seq, level, params):
    bus = Bus()
    ready = defaultdict(int)
    last_issue = -1
    pair_open = False     # 前の命令と同じサイクルに、もう 1 つ出せるか
    prev_cls = None
    next_free = 0         # 次に出せるいちばん早いサイクル(分岐・メモリの待ちで後ろにずれる)
    for ins, taken, mems in seq:
        cls = m7_class(ins)
        dep_ready = 0
        for s in ins.srcs:
            if ready[s] > dep_ready:
                dep_ready = ready[s]
        earliest = max(next_free, dep_ready)
        can_pair = False
        if level < 2 and pair_open and earliest <= last_issue and prev_cls is not None:
            if (prev_cls, cls) in M7_PAIR or (level == 0 and (prev_cls, cls) in M7_PAIR_MIN_EXTRA):
                can_pair = True
        if can_pair:
            issue = last_issue
            pair_open = False
        else:
            issue = max(last_issue + 1, earliest)
            pair_open = True
        occupy = 1
        k = ins.kind
        if k in ("ldm", "stm"):
            occupy = [max(1, (ins.nregs + 1) // 2), max(1, (ins.nregs + 1) // 2), ins.nregs][level]
            if ins.base in ("vpush", "vpop", "vldmia", "vstmia", "vldmdb", "vstmdb", "vldm", "vstm"):
                occupy = [max(1, (ins.nregs + 1) // 2), max(1, (ins.nregs + 1) // 2), ins.nregs][level]
            pair_open = False
        elif k in ("load2", "store2"):
            occupy = [1, 1, 2][level]
            pair_open = False
        elif k == "div":
            occupy = [2, 6, 12][level]
            pair_open = False
        elif k == "fpdiv":
            lat = 14
            if ins.is_f64:
                lat = 29
            occupy = [1, lat // 2, lat][level]
            pair_open = False
        elif k == "barrier":
            occupy = [2, 4, 8][level]
            pair_open = False
        # メモリ
        mem_stall = 0
        load_extra = 0
        for (cat, is_store) in mems:
            wait, extra = bus.access(issue, cat, is_store, params)
            if is_store:
                mem_stall = max(mem_stall, wait)
            else:
                load_extra = max(load_extra, wait + extra)
        lat = M7_LAT.get(k, (1, 1, 1))[level]
        if k == "fpdiv":
            lat = 29 if ins.is_f64 else 14
        if ins.is_f64 and k in ("fp", "fpfma", "fpmac"):
            lat += 1
        done = issue + lat + load_extra
        for d in ins.dests:
            ready[d] = done
        last_issue = issue + occupy - 1
        nf = issue + occupy
        if level >= 1:
            nf = max(nf, issue + 1 + load_extra + mem_stall)  # 遅いメモリでは止まる(typ・max)
        else:
            nf = max(nf, issue + mem_stall)
        if load_extra > 0 or mem_stall > 0:
            pair_open = False
        # 分岐
        if k == "branch" or ins.pc_load:
            if taken or ins.pc_load:
                if ins.base in ("bx", "blx") or ins.pc_load or ins.base in ("tbb", "tbh"):
                    pen = [2, 4, 6][level]
                else:
                    pen = [0, 1, 2][level]
                nf = max(nf, issue + 1 + pen)
                pair_open = False
        next_free = nf
        prev_cls = cls
    return last_issue + 1


def parse_trace(path, table, core):
    """トレースを読み、区間ごとに (命令の並び) を返す。同じ並びはまとめる(数えるだけ)"""
    regions = defaultdict(list)   # id -> list of (key)
    seqs = {}                     # key -> seq
    cur_id = None
    pcs = []
    mems = []
    cur_mem = None
    with open(path) as f:
        for line in f:
            t = line[0]
            if t == "I":
                if cur_id is None:
                    continue
                pc = int(line[2:], 16)
                pcs.append(pc)
                cur_mem = []
                mems.append(cur_mem)
            elif t == "M":
                if cur_id is None or cur_mem is None:
                    continue
                parts = line.split()
                addr = int(parts[1], 16)
                cat, _slot = mem_category(core, addr)
                cur_mem.append((cat, parts[2] == "S"))
            elif t == "B":
                cur_id = int(line[2:])
                pcs = []
                mems = []
                cur_mem = None
            elif t == "E":
                key = (tuple(pcs), tuple(tuple(m) for m in mems))
                if key not in seqs:
                    seqs[key] = None
                regions[cur_id].append(key)
                cur_id = None
    return regions, seqs


def build_seq(key, table):
    pcs, mems = key
    seq = []
    n = len(pcs)
    for i in range(n):
        ins = table.get(pcs[i])
        if ins is None:
            continue
        taken = False
        if i + 1 < n:
            taken = pcs[i + 1] != pcs[i] + ins.size
        seq.append((ins, taken, mems[i]))
    # 最後の命令は区間の終わりの印(str)なので除く
    if seq:
        seq = seq[:-1]
    return seq


def analyse(core, cfg):
    elf = os.path.join(HERE, "build", "%s_%s" % (core, cfg), "bench.elf")
    table = decode(core, elf)
    regions, seqs = parse_trace(os.path.join(HERE, "traces", "%s_%s.txt" % (core, cfg)), table, core)
    variants = [("base", False)]
    if core == "m7":
        variants.append(("dcache", True))
    results = {}
    cache = {}
    for key in seqs:
        seq = build_seq(key, table)
        entry = {"n_insn": len(seq)}
        for vname, dc in variants:
            for level, lname in enumerate(["min", "typ", "max"]):
                params = mem_params(core, level, dc)
                if core == "m33":
                    c = cost_m33(seq, level, params)
                else:
                    c = cost_m7(seq, level, params)
                entry["%s_%s" % (vname, lname)] = c
        # 命令の種類と、関数ごとの命令の数
        funcs = defaultdict(int)
        n_f64 = 0
        softfloat = 0
        lines16 = set()
        lines32 = set()
        n_mem = defaultdict(int)
        for ins, taken, mems in seq:
            funcs[ins.func] += 1
            if ins.is_f64:
                n_f64 += 1
            if ins.func.startswith("__aeabi_d") or ins.func.startswith("__aeabi_f") or "df3" in ins.func or \
               "sf3" in ins.func or ins.func.startswith("__aeabi_l") or ins.func.startswith("__aeabi_ui") or \
               ins.func.startswith("__aeabi_i"):
                softfloat += 1
            lines16.add(ins.pc // 16)
            lines32.add(ins.pc // 32)
            for cat, st in mems:
                n_mem[cat + ("_w" if st else "_r")] += 1
        entry["funcs"] = dict(funcs)
        entry["n_f64"] = n_f64
        entry["n_softlib"] = softfloat
        entry["lines16"] = sorted(lines16)
        entry["lines32"] = sorted(lines32)
        entry["mem"] = dict(n_mem)
        cache[key] = entry
    # 空の区間(印だけ)の分
    empty = cache[regions[1][0]] if 1 in regions else None
    for rid, keys in regions.items():
        entries = [cache[k] for k in keys]
        r = {"count": len(entries)}
        fields = [k for k in entries[0] if k.startswith("base_") or k.startswith("dcache_")] + ["n_insn"]
        for fld in fields:
            vals = [e[fld] - (empty[fld] if empty and rid != 1 else 0) for e in entries]
            r[fld] = {"min": min(vals), "avg": sum(vals) / len(vals), "max": max(vals)}
        # いちばん長い並びの中身(関数ごと)と、通った線(ICACHE の大きさを見る)
        longest = max(entries, key=lambda e: e["n_insn"])
        r["funcs_longest"] = dict(sorted(longest["funcs"].items(), key=lambda x: -x[1])[:15])
        lines16 = set()
        lines32 = set()
        for e in entries:
            lines16.update(e["lines16"])
            lines32.update(e["lines32"])
        r["lines16_union"] = sorted(lines16)
        r["lines32_union"] = sorted(lines32)
        r["lines16_per_call_max"] = max(len(e["lines16"]) for e in entries)
        r["n_f64_max"] = max(e["n_f64"] for e in entries)
        r["n_softlib_max"] = max(e["n_softlib"] for e in entries)
        mem_avg = defaultdict(float)
        for e in entries:
            for k, v in e["mem"].items():
                mem_avg[k] += v / len(entries)
        r["mem_avg"] = dict(mem_avg)
        results[rid] = r
    out = os.path.join(HERE, "results")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "%s_%s.json" % (core, cfg)), "w") as f:
        json.dump(results, f, indent=1)
    return results


def main():
    core = sys.argv[1]
    cfg = sys.argv[2]
    res = analyse(core, cfg)
    for rid in sorted(res):
        r = res[rid]
        line = "%3d n=%5d insn=%7.1f [%d..%d]" % (rid, r["count"], r["n_insn"]["avg"], r["n_insn"]["min"],
                                                   r["n_insn"]["max"])
        line += "  cyc typ avg %.0f (min %.0f .. max %.0f)" % (r["base_typ"]["avg"], r["base_min"]["min"],
                                                              r["base_max"]["max"])
        if "dcache_typ" in r:
            line += "  dcache typ %.0f" % r["dcache_typ"]["avg"]
        print(line)


if __name__ == "__main__":
    main()
