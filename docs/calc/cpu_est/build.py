#!/usr/bin/env python3
"""
build.py — ベンチを Cortex-M7(H725 相当)と Cortex-M33(H562 相当)で、最適化の 3 通りにビルドし、
QEMU(mps2-an500 / mps2-an505)+ TCG プラグインで動かして、区間ごとの命令の流れ(トレース)を取る。

  python3 build.py            # 全部(6 通り)
  python3 build.py m33 O2     # 1 通りだけ

出力: build/<core>_<cfg>/bench.elf, bench.dis(逆アセンブル), warnings.txt, traces/<core>_<cfg>.txt
"""
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DL = os.path.join(os.path.dirname(HERE), "dl")
TORANEKO_APP = "/home/user/tokoro0917/toraneko.mk3/software/main-controller/TORANEKO.Mk3/App"
HARNESS = os.path.join(HERE, "harness")

CORES = {
    "m7": dict(cpu="-mcpu=cortex-m7 -mfpu=fpv5-d16 -mfloat-abi=hard -mthumb", machine="mps2-an500",
               code=0x00000000, ram=0x20000000, fake=0x60000000, mcu="MK4_H7", device="STM32H725xx",
               family="h7"),
    "m33": dict(cpu="-mcpu=cortex-m33 -mfpu=fpv5-sp-d16 -mfloat-abi=hard -mthumb", machine="mps2-an505",
                code=0x10000000, ram=0x38000000, fake=0x80000000, mcu="MK4_H5", device="STM32H562xx",
                family="h5"),
}

# 最適化の組み合わせ
#   O0  : CubeMX の CMake の Debug(-O0 -g3)を全部に
#   dbg : ToraNeko の Debug の実際(CMakeLists.txt の APP_FAST_SOURCES: ctrl/* と maze/* だけ -O2、ほかは -O0)
#   O2  : 全部 -O2
CONFIGS = ["O0", "dbg", "O2"]

TORANEKO_CTRL = ["ctrl/control.c", "ctrl/odometry.c", "ctrl/trajectory.c", "ctrl/wall_ctrl.c", "ctrl/wall_dist.c"]
TORANEKO_SYS = ["sys/log.c", "sys/failsafe.c"]
MK4_CTRL = ["mk4_current.c", "mk4_control.c"]          # ctrl の層(MK4 で ctrl/ に置く予定のもの)
MK4_DRV = ["mk4_wall.c", "mk4_encoder.c", "mk4_imu.c", "mk4_hw.c"]
MK4_SYS = ["bench.c", "hal_paths.c"]                  # 割り込みの入口・HAL のコールバック(Core/・sys/ 相当)
HAL_FILES = {
    "h7": ["stm32h7xx_hal.c", "stm32h7xx_hal_dma.c", "stm32h7xx_hal_dma_ex.c", "stm32h7xx_hal_spi.c",
           "stm32h7xx_hal_spi_ex.c", "stm32h7xx_hal_adc.c", "stm32h7xx_hal_adc_ex.c", "stm32h7xx_hal_gpio.c",
           "stm32h7xx_hal_cortex.c"],
    "h5": ["stm32h5xx_hal.c", "stm32h5xx_hal_dma.c", "stm32h5xx_hal_dma_ex.c", "stm32h5xx_hal_spi.c",
           "stm32h5xx_hal_spi_ex.c", "stm32h5xx_hal_adc.c", "stm32h5xx_hal_adc_ex.c", "stm32h5xx_hal_gpio.c",
           "stm32h5xx_hal_cortex.c"],
}

# にせの周辺のレジスタ: バスの区切りごとに 1MB の場所を割り当てる(番号は analysis/cycle_model.py と同じ)
FAKE_SLOTS = {
    "h7": ["D2_APB1PERIPH_BASE", "D2_APB2PERIPH_BASE", "D2_AHB1PERIPH_BASE", "D2_AHB2PERIPH_BASE",
           "D1_APB1PERIPH_BASE", "D1_AHB1PERIPH_BASE", "D3_APB1PERIPH_BASE", "D3_AHB1PERIPH_BASE"],
    "h5": ["APB1PERIPH_BASE_NS", "APB2PERIPH_BASE_NS", "AHB1PERIPH_BASE_NS", "AHB2PERIPH_BASE_NS",
           "APB3PERIPH_BASE_NS", "AHB3PERIPH_BASE_NS", "AHB4PERIPH_BASE_NS"],
}


def run(cmd, **kw):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        print(r.stdout)
        print(r.stderr)
        raise SystemExit("failed: " + cmd)
    return r


def make_headers(core):
    """デバイスのヘッダを写し、周辺の番地を QEMU の RAM(にせのレジスタ)に置きかえる"""
    c = CORES[core]
    fam = c["family"]
    inc = os.path.join(HERE, "build", "inc_" + fam)
    os.makedirs(inc, exist_ok=True)
    devdir = os.path.join(DL, "cmsis-device-" + fam, "Include")
    for name in os.listdir(devdir):
        if name.endswith(".h"):
            shutil.copy(os.path.join(devdir, name), inc)
    dev = os.path.join(inc, c["device"].lower().replace("xx", "xx") + ".h")
    dev = os.path.join(inc, {"h7": "stm32h725xx.h", "h5": "stm32h562xx.h"}[fam])
    text = open(dev).read()
    for i, macro in enumerate(FAKE_SLOTS[fam]):
        addr = c["fake"] + i * 0x100000
        pat = re.compile(r"^#define\s+" + macro + r"\s+.*$", re.M)
        if not pat.search(text):
            raise SystemExit("macro not found: " + macro)
        text = pat.sub("#define %s (0x%08XUL) /* bench: fake peripheral slot %d */" % (macro, addr, i), text, count=1)
    open(dev, "w").write(text)
    # HAL の設定(テンプレートから、使うものだけ有効にする)
    haldir = os.path.join(DL, "stm32%sxx-hal-driver" % fam)
    tmpl = open(os.path.join(haldir, "Inc", "stm32%sxx_hal_conf_template.h" % fam)).read()
    keep = ["HAL_MODULE_ENABLED", "HAL_ADC_MODULE_ENABLED", "HAL_CORTEX_MODULE_ENABLED", "HAL_DMA_MODULE_ENABLED",
            "HAL_EXTI_MODULE_ENABLED", "HAL_GPIO_MODULE_ENABLED", "HAL_RCC_MODULE_ENABLED", "HAL_SPI_MODULE_ENABLED",
            "HAL_FLASH_MODULE_ENABLED", "HAL_PWR_MODULE_ENABLED"]

    def fix(m):
        name = m.group(1)
        if name in keep:
            return "#define " + name
        return "/* #define " + name + " */"
    tmpl = re.sub(r"^#define\s+(HAL_\w*MODULE_ENABLED)\s*$", fix, tmpl, flags=re.M)
    tmpl = re.sub(r"#define\s+USE_SPI_CRC\s+1U", "#define  USE_SPI_CRC 0U", tmpl)
    open(os.path.join(inc, "stm32%sxx_hal_conf.h" % fam), "w").write(tmpl)
    return inc


def linker_script(core, path):
    c = CORES[core]
    code = c["code"]
    ram = c["ram"]
    text = """
MEMORY
{
  CODE (rx)  : ORIGIN = 0x%08X, LENGTH = 4M
  RAM  (rwx) : ORIGIN = 0x%08X, LENGTH = 1M
  MARK (rw)  : ORIGIN = 0x%08X, LENGTH = 4K
  DMA  (rw)  : ORIGIN = 0x%08X, LENGTH = 64K
  AXI  (rw)  : ORIGIN = 0x%08X, LENGTH = 512K
}
ENTRY(Reset_Handler)
SECTIONS
{
  .isr_vector : { KEEP(*(.isr_vector)) } > CODE
  .text : { *(.text*) *(.glue_7*) *(.rodata*) . = ALIGN(4); } > CODE
  .ARM.extab : { *(.ARM.extab*) } > CODE
  .ARM.exidx : { *(.ARM.exidx*) } > CODE
  .init_array : { KEEP(*(.init_array*)) } > CODE
  .fini_array : { KEEP(*(.fini_array*)) } > CODE
  _sidata = LOADADDR(.data);
  .data : { _sdata = .; *(.data*) . = ALIGN(4); _edata = .; } > RAM AT > CODE
  .axi_buf (NOLOAD) : { _saxi = .; *(.axi_buf*) *(.bss.s_rows) . = ALIGN(4); _eaxi = .; } > AXI
  .bss (NOLOAD) : { _sbss = .; *(.bss*) *(COMMON) . = ALIGN(4); _ebss = .; } > RAM
  .mark (NOLOAD) : { *(.mark*) } > MARK
  .dma_buf (NOLOAD) : { _sdma = .; *(.dma_buf*) . = ALIGN(4); _edma = .; } > DMA
  _estack = ORIGIN(RAM) + LENGTH(RAM);
  end = _ebss;
  /DISCARD/ : { *(.ARM.attributes) }
}
""" % (code, ram, ram + 0x100000, ram + 0x110000, ram + 0x180000)
    open(path, "w").write(text)


def opt_for(cfg, group):
    if cfg == "O0":
        return "-O0"
    if cfg == "O2":
        return "-O2"
    # dbg: ToraNeko の Debug の実際
    if group in ("toraneko_ctrl", "mk4_ctrl"):
        return "-O2"
    return "-O0"


def build(core, cfg):
    c = CORES[core]
    fam = c["family"]
    out = os.path.join(HERE, "build", "%s_%s" % (core, cfg))
    os.makedirs(out, exist_ok=True)
    inc = make_headers(core)
    haldir = os.path.join(DL, "stm32%sxx-hal-driver" % fam)
    includes = " ".join("-I" + p for p in [
        os.path.join(HARNESS, "override"), HARNESS, TORANEKO_APP, inc,
        os.path.join(haldir, "Inc"), os.path.join(DL, "cmsis-core", "CMSIS", "Core", "Include")])
    defs = "-D%s -D%s -DUSE_HAL_DRIVER" % (c["mcu"], c["device"])
    common = "%s -g -ffunction-sections -fdata-sections -std=gnu11 %s %s" % (c["cpu"], defs, includes)
    warn = "-Wall -Wextra -Wdouble-promotion"
    groups = []
    groups += [("toraneko_ctrl", os.path.join(TORANEKO_APP, f), warn) for f in TORANEKO_CTRL]
    groups += [("toraneko_sys", os.path.join(TORANEKO_APP, f), warn) for f in TORANEKO_SYS]
    groups += [("mk4_ctrl", os.path.join(HARNESS, f), warn) for f in MK4_CTRL]
    groups += [("mk4_drv", os.path.join(HARNESS, f), warn) for f in MK4_DRV]
    groups += [("mk4_sys", os.path.join(HARNESS, f), warn) for f in MK4_SYS]
    groups += [("hal", os.path.join(haldir, "Src", f), "-w") for f in HAL_FILES[fam]]
    groups += [("startup", os.path.join(HARNESS, "startup.c"), warn)]
    objs = []
    warnings = []
    for group, src, w in groups:
        obj = os.path.join(out, os.path.basename(src).replace(".c", ".o"))
        opt = opt_for(cfg, group)
        if group == "startup":
            opt = "-O2"
        r = run("arm-none-eabi-gcc -c %s %s %s %s -o %s" % (common, opt, w, src, obj))
        if r.stderr.strip():
            warnings.append("== %s (%s)\n%s" % (src, opt, r.stderr))
        objs.append(obj)
    open(os.path.join(out, "warnings.txt"), "w").write("\n".join(warnings))
    ld = os.path.join(out, "link.ld")
    linker_script(core, ld)
    elf = os.path.join(out, "bench.elf")
    run("arm-none-eabi-gcc %s -nostartfiles --specs=nano.specs --specs=nosys.specs -T %s -Wl,--gc-sections "
        "-Wl,-Map=%s %s -lm -o %s" % (c["cpu"], ld, os.path.join(out, "bench.map"), " ".join(objs), elf))
    run("arm-none-eabi-objdump -d --no-show-raw-insn %s > %s" % (elf, os.path.join(out, "bench.dis")))
    run("arm-none-eabi-nm -n -S %s > %s" % (elf, os.path.join(out, "bench.nm")))
    return elf


def trace(core, cfg, elf):
    c = CORES[core]
    os.makedirs(os.path.join(HERE, "traces"), exist_ok=True)
    tr = os.path.join(HERE, "traces", "%s_%s.txt" % (core, cfg))
    mark = c["ram"] + 0x100000
    cmd = ("qemu-system-arm -M %s -nographic -semihosting-config enable=on,target=native -kernel %s "
           "-plugin %s,markaddr=0x%X,out=%s" % (c["machine"], elf, os.path.join(HERE, "plugin", "libtrace.so"),
                                                mark, tr))
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
    print("[%s %s] qemu rc=%d %s %s" % (core, cfg, r.returncode, r.stdout.strip(), r.stderr.strip()[:500]))
    return tr


def main():
    cores = list(CORES)
    cfgs = CONFIGS
    if len(sys.argv) >= 2:
        cores = [sys.argv[1]]
    if len(sys.argv) >= 3:
        cfgs = [sys.argv[2]]
    for core in cores:
        for cfg in cfgs:
            elf = build(core, cfg)
            trace(core, cfg, elf)


if __name__ == "__main__":
    main()
