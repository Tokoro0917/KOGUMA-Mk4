#!/usr/bin/env python3
"""KOGUMA MK4 noise study: run every ngspice netlist and make the plots.

    cd docs/calc/noise
    python3 run_all.py            # run ngspice (batch) + plots + summary
    python3 run_all.py --plot     # plots only (reuse out/*.txt)

Raw simulation data goes to out/ (ignored by git), figures to fig/,
key numbers to summary.json.
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
FIG = HERE / "fig"
NETLISTS = [
    "01_tia_noise.cir",
    "02_tia_ac.cir",
    "03_tia_tran.cir",
    "04_supply_ac.cir",
    "05_ground_A.cir",
    "05_ground_B.cir",
    "06_fan_sense.cir",
    "07_motor_cm.cir",
]

# reference categorical palette (dataviz skill, light mode), fixed order
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
GRAY = "#8a8985"

VREF = 3.3
LSB16 = VREF / 65536
LSB12 = VREF / 4096
RF = 820e3

plt.rcParams.update({
    "figure.dpi": 110,
    "savefig.dpi": 110,
    "font.size": 9,
    "axes.grid": True,
    "grid.color": "#e4e3df",
    "grid.linewidth": 0.6,
    "axes.edgecolor": "#8a8985",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "lines.linewidth": 1.6,
    "legend.frameon": False,
    "legend.fontsize": 8,
})


def run_spice():
    OUT.mkdir(exist_ok=True)
    for n in NETLISTS:
        log = OUT / ("log_" + n.replace(".cir", ".txt"))
        with open(log, "w") as fh:
            r = subprocess.run(["ngspice", "-b", n], cwd=HERE, stdout=fh, stderr=subprocess.STDOUT)
        txt = log.read_text(errors="replace")
        bad = [l for l in txt.splitlines() if ("aborted" in l or "Error" in l or "error:" in l)]
        status = "OK" if (r.returncode == 0 and not bad) else "CHECK LOG"
        print(f"  {n:22s} -> {status}  ({log.name})")
        if bad:
            for l in bad[:5]:
                print("     ", l)


def load(name):
    p = OUT / name
    with open(p) as fh:
        head = fh.readline().split()
    d = np.loadtxt(p, skiprows=1)
    return {k: d[:, i] for i, k in enumerate(head)}


def db(x):
    return 20 * np.log10(np.abs(x))


def mark_freqs(ax, fs=(20e3, 50e3, 2e6, 2.4e6), labels=("20k", "50k", "2M", "2.4M")):
    for i, (f, l) in enumerate(zip(fs, labels)):
        ax.axvline(f, color=GRAY, lw=0.7, ls=":")
        ax.text(f, 0.985, " " + l + " ", transform=ax.get_xaxis_transform(),
                ha=("right" if i % 2 == 0 else "left"), va="top", fontsize=7, color="#52514e")


S = {}  # summary


# ----------------------------------------------------------------------------
# 1. TIA noise
# ----------------------------------------------------------------------------
def integ(f, s, lo, hi):
    m = (f >= lo) & (f <= hi)
    return float(np.sqrt(np.trapezoid(s[m] ** 2, f[m])))


def cds(f, s, dt, lo=10, hi=1e8):
    """rms of (sample2 - sample1) taken dt apart: |H|^2 = 2(1-cos(2 pi f dt))."""
    m = (f >= lo) & (f <= hi)
    h2 = 2 * (1 - np.cos(2 * np.pi * f[m] * dt))
    return float(np.sqrt(np.trapezoid(s[m] ** 2 * h2, f[m])))


def tia_noise():
    a = load("noise_cf0.5p.txt")
    b = load("noise_b_noen.txt")
    c = load("noise_c_noenin.txt")
    d = load("noise_d_rfonly.txt")
    f = a["frequency"]
    tot, sb, sc, sd = a["onoise_spectrum"], b["onoise_spectrum"], c["onoise_spectrum"], d["onoise_spectrum"]
    en = np.sqrt(np.clip(tot**2 - sb**2, 0, None))
    inn = np.sqrt(np.clip(sb**2 - sc**2, 0, None))
    shot = np.sqrt(np.clip(sc**2 - sd**2, 0, None))
    rf = sd

    fig, ax = plt.subplots(1, 2, figsize=(10, 3.8))
    ax[0].loglog(f, tot * 1e9, color="#0b0b0b", lw=2, label="total (Cf 0.5 pF, dark)")
    ax[0].loglog(f, rf * 1e9, color=C[0], label="R74 820k thermal (+bias net)")
    ax[0].loglog(f, en * 1e9, color=C[1], label="OPA2354 en x noise gain")
    ax[0].loglog(f, inn * 1e9, color=C[2], label="OPA2354 in")
    ax[0].loglog(f, np.maximum(shot, 1e-30) * 1e9, color=C[6], label="PD dark-current shot (0.1 nA)")
    ax[0].set_xlim(10, 1e8)
    ax[0].set_ylim(0.1, 2000)
    ax[0].set_xlabel("Frequency [Hz]")
    ax[0].set_ylabel("Output noise density [nV/rtHz]")
    ax[0].set_title("TIA output noise, contributions")
    ax[0].legend(loc="lower left")

    S["tia_noise"] = {}
    variants = [("noise_cf0.2p.txt", "Cf 0.2 pF"), ("noise_cf0.5p.txt", "Cf 0.5 pF (design)"),
                ("noise_cf0.8p.txt", "Cf 0.8 pF"), ("noise_cf1.0p.txt", "Cf 1.0 pF"),
                ("noise_adcrc.txt", "Cf 0.5 pF + 220R/1nF at ADC"),
                ("noise_ish2u.txt", "Cf 0.5 pF, lit 2 uA (shot)")]
    cols = [C[0], "#0b0b0b", C[2], C[3], C[1], C[6]]
    for (fn, lab), col in zip(variants, cols):
        v = load(fn)
        fv, sv = v["frequency"], v["onoise_spectrum"]
        m = (fv >= 10) & (fv <= 1e8)
        cum = np.sqrt(np.concatenate([[0], np.cumsum(0.5 * (sv[m][1:] ** 2 + sv[m][:-1] ** 2) * np.diff(fv[m]))]))
        ax[1].semilogx(fv[m], cum * 1e6, color=col, label=lab, lw=2 if "design" in lab else 1.4)
        r = integ(fv, sv, 10, 1e8)
        S["tia_noise"][lab] = {
            "rms_uV_10Hz_100MHz": r * 1e6,
            "rms_LSB16": r / LSB16,
            "rms_LSB12": r / LSB12,
            "in_equiv_nA_rms": r / RF * 1e9,
            "cds_dt10us_uV": cds(fv, sv, 10e-6) * 1e6,
            "cds_dt10us_LSB16": cds(fv, sv, 10e-6) / LSB16,
            "density_1kHz_nV": float(np.interp(1e3, fv, sv) * 1e9),
            "density_1MHz_nV": float(np.interp(1e6, fv, sv) * 1e9),
        }
    ax[1].set_xlim(10, 1e8)
    ax[1].set_xlabel("Upper integration limit [Hz]")
    ax[1].set_ylabel("Integrated output noise [uV rms]")
    ax[1].set_title("Cumulative rms (from 10 Hz)  -  1 LSB(16 bit) = 50 uV")
    ax[1].axhline(LSB16 * 1e6 * 10, color=GRAY, lw=0.7, ls="--")
    ax[1].text(9e7, LSB16 * 1e6 * 10 + 8, "10 LSB (16 bit)", ha="right", va="bottom", fontsize=7, color="#52514e")
    ax[1].legend(loc="upper left")
    fig.tight_layout()
    fig.savefig(FIG / "fig01_tia_noise.png")
    plt.close(fig)
    # contributions integrated
    S["tia_noise_contrib_uV"] = {
        "Rf": integ(f, rf, 10, 1e8) * 1e6,
        "en": integ(f, en, 10, 1e8) * 1e6,
        "in": integ(f, inn, 10, 1e8) * 1e6,
        "dark_shot": integ(f, shot, 10, 1e8) * 1e6,
        "total": integ(f, tot, 10, 1e8) * 1e6,
    }


# ----------------------------------------------------------------------------
# 2. TIA AC / stability and 3. step response
# ----------------------------------------------------------------------------
def tia_ac_tran():
    fig, ax = plt.subplots(1, 3, figsize=(13, 3.8))
    S["tia_ac"] = {}
    for cf, col in zip(["0.2p", "0.5p", "0.8p", "1.0p"], [C[0], "#0b0b0b", C[2], C[3]]):
        d = load(f"ac_cf{cf}.txt")
        f = d["frequency"]
        zt, tm, tp, am, ng = d["zt"], d["tm"], d["tp"], d["am"], d["ng"]
        z0 = zt[0]
        f3 = f[np.where(zt < z0 / np.sqrt(2))[0][0]]
        ic = np.where(tm < 1)[0][0]
        pm = 180 + np.degrees(tp[ic])
        S["tia_ac"][cf] = {"f3dB_kHz": f3 / 1e3, "peaking_dB": float(db(zt.max() / z0)),
                           "crossover_MHz": f[ic] / 1e6, "phase_margin_deg": float(pm),
                           "noise_gain_hf": float(np.interp(1e7, f, ng))}
        lw = 2 if cf == "0.5p" else 1.4
        ax[0].semilogx(f, db(zt), color=col, lw=lw, label=f"Cf {cf}F: f-3dB {f3/1e3:.0f} kHz, PM {pm:.0f} deg")
        if cf in ("0.2p", "0.5p"):
            ax[1].semilogx(f, db(ng), color=col, lw=lw, ls="--", label=f"1/beta (noise gain), Cf {cf}F")
    d = load("ac_cf0.5p.txt")
    ax[1].semilogx(d["frequency"], db(d["am"]), color=C[1], label="AOL (model)")
    ax[0].set_xlim(1e3, 1e8); ax[0].set_ylim(60, 125)
    ax[0].set_xlabel("Frequency [Hz]"); ax[0].set_ylabel("|Zt| [dB ohm]  (820k = 118.3)")
    ax[0].set_title("Closed-loop transimpedance")
    ax[0].legend(loc="lower left")
    ax[1].set_xlim(10, 1e9); ax[1].set_ylim(-10, 120)
    ax[1].set_xlabel("Frequency [Hz]"); ax[1].set_ylabel("[dB]")
    ax[1].set_title("Loop: AOL vs 1/beta (rate of closure)")
    ax[1].legend(loc="upper right")

    S["tia_tran"] = {}
    for cf, col in zip(["0.2p", "0.5p", "0.8p", "1.0p"], [C[0], "#0b0b0b", C[2], C[3]]):
        d = load(f"tran_cf{cf}.txt")
        t, v = d["time"], d["v(out)"]
        v0 = v[(t > 1.5e-6) & (t < 2e-6)].mean()
        v1 = v[(t > 9.5e-6) & (t < 10e-6)].mean()
        m = (t >= 2e-6) & (t < 10e-6)
        tt = t[m] - 2e-6
        e = np.abs(v[m] - v1) / abs(v1 - v0)

        def st(tol):
            bad = np.where(e > tol)[0]
            return float(tt[bad[-1]]) if len(bad) else 0.0

        os_ = float((v[m].max() - v1) / (v1 - v0) * 100)
        S["tia_tran"][cf] = {"settle_1pct_us": st(0.01) * 1e6, "settle_0.1pct_us": st(1e-3) * 1e6,
                             "settle_0.01pct_us": st(1e-4) * 1e6, "overshoot_pct": max(os_, 0.0)}
        ax[2].plot((t - 2e-6) * 1e6, v, color=col, lw=2 if cf == "0.5p" else 1.4,
                   label=f"Cf {cf}F: 1% {st(0.01)*1e6:.2f} us, OS {max(os_,0):.1f}%")
    d = load("tran_adcrc.txt")
    t, v = d["time"], d["v(adc)"]
    v0 = v[(t > 1.5e-6) & (t < 2e-6)].mean()
    v1 = v[(t > 9.5e-6) & (t < 10e-6)].mean()
    m = (t >= 2e-6) & (t < 10e-6)
    tt = t[m] - 2e-6
    e = np.abs(v[m] - v1) / abs(v1 - v0)
    S["tia_tran"]["0.5p+adcRC"] = {f"settle_{k}_us": float(tt[np.where(e > tol)[0][-1]] * 1e6)
                                   for k, tol in (("1pct", 0.01), ("0.1pct", 1e-3), ("0.01pct", 1e-4))}
    ax[2].plot((t - 2e-6) * 1e6, v, color=C[1], lw=1.2, ls="--",
               label=f"Cf 0.5pF + 220R/1nF at ADC: 1% {S['tia_tran']['0.5p+adcRC']['settle_1pct_us']:.2f} us")
    ax[2].set_xlim(-0.5, 6); ax[2].set_ylim(0, 2.1)
    ax[2].set_xlabel("Time from photocurrent step [us]"); ax[2].set_ylabel("V(out) [V]")
    ax[2].set_title("Step 0 -> 2 uA (receiver only)")
    ax[2].legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(FIG / "fig02_tia_ac_step.png")
    plt.close(fig)


# ----------------------------------------------------------------------------
# 4. Supply path
# ----------------------------------------------------------------------------
def ferrite_z(f, L=0.8e-6, Rdc=0.05, Rp=250, Cp=0.9e-12):
    w = 2 * np.pi * f
    y = 1 / (1j * w * L) + 1 / Rp + 1j * w * Cp
    return Rdc + 1 / y


def supply():
    fig, ax = plt.subplots(1, 4, figsize=(16, 3.8))
    f = np.logspace(4, 9.5, 500)
    for L, col in zip([0.5e-6, 0.8e-6, 1.2e-6], [C[0], "#0b0b0b", C[2]]):
        ax[0].loglog(f, np.abs(ferrite_z(f, L)), color=col, label=f"model, L(low f) {L*1e6:.1f} uH")
    ax[0].plot([100e6], [220], "o", ms=8, mfc="white", mec=C[1], mew=2, label="datasheet 220 ohm +-25% @100 MHz")
    ax[0].errorbar([100e6], [220], yerr=[[55], [55]], color=C[1], capsize=3, lw=1)
    ax[0].set_xlabel("Frequency [Hz]"); ax[0].set_ylabel("|Z| [ohm]")
    ax[0].set_title("BLM18PG221SN1D model")
    ax[0].legend(loc="lower right", fontsize=7)

    OLD = "2026-11-01"
    NEW = "2026-11-06"
    runs = {"old_l0.8u": (f"{OLD}: FB2 only (L 0.8 uH)", C[1], 1.6, "--"),
            "new_l0.5u": (f"{NEW}: FB2 + R80 2.2 ohm, L 0.5 uH", C[0], 1.2, "-"),
            "new_l0.8u": (f"{NEW}: FB2 + R80 2.2 ohm, L 0.8 uH", "#0b0b0b", 2, "-"),
            "new_l1.2u": (f"{NEW}: FB2 + R80 2.2 ohm, L 1.2 uH", C[2], 1.2, "-")}
    S["supply"] = {}

    def store(tag, d):
        fr = d["frequency"]
        r = S["supply"].setdefault(tag, {})
        for key, col in (("h3a", "h3a"), ("hout", "hout"), ("hvdda", "hvdda")):
            k = int(np.argmax(d[col]))
            r[f"{key}_peak_dB"] = float(db(d[col][k]))
            r[f"{key}_peak_kHz"] = float(fr[k] / 1e3)
            for x in (20e3, 40e3, 50e3, 80e3, 186e3, 2e6, 2.4e6):
                r[f"{key}_dB@{int(x/1e3)}k"] = float(db(np.interp(x, fr, d[col])))

    for tag in ("old_l0.8u", "new_l0.5u", "new_l0.8u", "new_l1.2u", "new_psrronly", "new_pdbonly", "new_c51_10u"):
        store(tag, load(f"sup_{tag}.txt"))

    for tag, (lab, col, lw, ls) in runs.items():
        d = load(f"sup_{tag}.txt")
        ax[1].semilogx(d["frequency"], db(d["h3a"]), color=col, lw=lw, ls=ls, label=lab)
    ax[1].set_xlim(1e3, 1e8); ax[1].set_ylim(-100, 20)
    ax[1].set_xlabel("Frequency [Hz]"); ax[1].set_ylabel("V(+3V3A)/V(+3V3) [dB]")
    ax[1].set_title("+3V3 ripple -> +3V3A")
    ax[1].legend(loc="lower left", fontsize=7)
    mark_freqs(ax[1])

    for tag, lab, col, lw, ls in [("old_l0.8u", f"{OLD}: total", C[1], 1.6, "--"),
                                  ("new_l0.8u", f"{NEW}: total", "#0b0b0b", 2, "-"),
                                  ("new_psrronly", f"{NEW}: via OPA2354 PSRR", C[0], 1.2, "-"),
                                  ("new_pdbonly", f"{NEW}: via PD_BIAS", C[2], 1.2, "-")]:
        d = load(f"sup_{tag}.txt")
        ax[2].semilogx(d["frequency"], db(d["hout"]), color=col, lw=lw, ls=ls, label=lab)
    ax[2].set_xlim(1e3, 1e8); ax[2].set_ylim(-120, -20)
    ax[2].set_xlabel("Frequency [Hz]"); ax[2].set_ylabel("V(TIA out)/V(+3V3) [dB]")
    ax[2].set_title("+3V3 ripple -> TIA output (dark)")
    ax[2].legend(loc="lower left", fontsize=7)
    mark_freqs(ax[2])

    for tag, lab, col, lw, ls in [("old_l0.8u", f"{OLD}: FB1 + C51 1u", C[1], 1.6, "--"),
                                  ("new_l0.8u", f"{NEW}: R51 2.2 ohm + FB1 + C51 4.7u", "#0b0b0b", 2, "-"),
                                  ("new_c51_10u", "option: C51 10u", C[2], 1.4, ":")]:
        d = load(f"sup_{tag}.txt")
        ax[3].semilogx(d["frequency"], db(d["hvdda"]), color=col, lw=lw, ls=ls, label=lab)
    ax[3].set_xlim(1e3, 1e8); ax[3].set_ylim(-80, 30)
    ax[3].set_xlabel("Frequency [Hz]"); ax[3].set_ylabel("V(VDDA)/V(+3V3) [dB]")
    ax[3].set_title("+3V3 ripple -> VDDA (ADC reference)")
    ax[3].legend(loc="lower left", fontsize=7)
    mark_freqs(ax[3])
    fig.tight_layout()
    fig.savefig(FIG / "fig03_supply_path.png")
    plt.close(fig)

    # ripple budget table (assumed source amplitudes)
    srcs = {"PWM 20 kHz (5 mVpp)": (20e3, 5e-3), "PWM 50 kHz (5 mVpp)": (50e3, 5e-3),
            "DC-DC 2 MHz (20 mVpp)": (2e6, 20e-3), "MCU SMPS 2.4 MHz (10 mVpp)": (2.4e6, 10e-3)}
    S["ripple_budget"] = {}
    for tag in ("old_l0.8u", "new_l0.8u", "new_c51_10u"):
        d = load(f"sup_{tag}.txt")
        fr = d["frequency"]
        for name, (fx, a) in srcs.items():
            out_pp = a * np.interp(fx, fr, d["hout"])
            vdda_pp = a * np.interp(fx, fr, d["hvdda"])
            S["ripple_budget"].setdefault(name, {})[tag] = {
                "tia_out_uVpp": out_pp * 1e6, "tia_out_LSB16pp": out_pp / LSB16,
                "vdda_mVpp": vdda_pp * 1e3,
                # ADC error for a 1.5 V reading caused by reference ripple
                "ref_err_at_1V5_LSB16pp": 1.5 * vdda_pp / VREF / LSB16,
            }


# ----------------------------------------------------------------------------
# 5. Ground coupling
# ----------------------------------------------------------------------------
def ground():
    def prep(fn):
        d = load(fn)
        tu = np.linspace(300e-6, 340e-6, 40001)
        o = {k: np.interp(tu, d["time"], d[k]) for k in ("vgerr", "vadc", "vref")}
        tl = np.linspace(200e-6, 400e-6, 200001)
        o["code_long"] = np.interp(tl, d["time"], d["vadc"] / d["vref"] * 65536)
        o["vref_long"] = np.interp(tl, d["time"], d["vref"])
        o["t"] = tu
        o["tl"] = tl
        return o

    base = {"a": prep("gnda_off.txt"), "bold": prep("gndb_old_off.txt"), "bnew": prep("gndb_new_off.txt")}
    code0 = {k: float(np.mean(v["vadc"] / v["vref"] * 65536)) for k, v in base.items()}
    cases = [("gnda_trace5mm.txt", "A: single GND, shared 5 mm (0.5 mm trace)", "a"),
             ("gnda_trace10mm.txt", "A: single GND, shared 10 mm (0.5 mm trace)", "a"),
             ("gnda_trace20mm.txt", "A: single GND, shared 20 mm (0.5 mm trace)", "a"),
             ("gnda_pour10mm.txt", "A: single GND, shared 10 mm (5 mm pour)", "a"),
             ("gndb_old_nt0mm.txt", "B 2026-11-01: split, NT1 at C7/C8 GND", "bold"),
             ("gndb_old_nt10mm.txt", "B 2026-11-01: NT1 10 mm off", "bold"),
             ("gndb_old_nt30mm.txt", "B 2026-11-01: NT1 30 mm off", "bold"),
             ("gndb_new_nt0mm.txt", "B 2026-11-06: split, NT1 at C7/C8 GND", "bnew"),
             ("gndb_new_nt10mm.txt", "B 2026-11-06: NT1 10 mm off", "bnew"),
             ("gndb_new_nt30mm.txt", "B 2026-11-06: NT1 30 mm off", "bnew")]
    S["ground"] = {}
    data = {}
    for fn, lab, k in cases:
        o = prep(fn)
        data[fn] = o
        ph = o["tl"] % 20e-6
        c = o["code_long"] - code0[k]
        on = (ph > 6e-6) & (ph < 11e-6)      # fan on + motor on
        off = (ph > 16e-6) & (ph < 19e-6)    # fan off, motor off
        vg = load(fn)
        tg = np.linspace(200e-6, 400e-6, 200001)
        vge = np.interp(tg, vg["time"], vg["vgerr"])
        S["ground"][fn.replace(".txt", "")] = {
            "label": lab,
            "vgnd_pp_mV": float(np.ptp(vge) * 1e3),
            "vgnd_plateau_on_mV": float(np.median(vge[on]) * 1e3),
            "vgnd_plateau_off_mV": float(np.median(vge[off]) * 1e3),
            "code_pp_LSB16": float(np.ptp(c)),
            "code_rms_LSB16": float(np.std(c)),
            "code_plateau_on_LSB16": float(np.median(c[on])),
            "code_plateau_off_LSB16": float(np.median(c[off])),
            "vdda_pp_mV": float(np.ptp(o["vref_long"]) * 1e3),
        }

    fig, ax = plt.subplots(2, 2, figsize=(12, 7))
    sel = [("gnda_trace10mm.txt", C[1]), ("gnda_pour10mm.txt", C[3]),
           ("gndb_new_nt0mm.txt", C[0]), ("gndb_new_nt10mm.txt", C[6])]
    for fn, col in sel:
        o = data[fn]
        lab = S["ground"][fn.replace(".txt", "")]["label"]
        t = (o["t"] - 300e-6) * 1e6
        ax[0, 0].plot(t, o["vgerr"] * 1e3, color=col, lw=1.2, label=lab)
        ax[0, 1].plot(t, o["vgerr"] * 1e3, color=col, lw=1.2, label=lab)
    ax[0, 0].set_ylabel("V(sensor GND) - V(MCU GND) [mV]")
    ax[0, 0].set_title("Ground difference seen by the ADC (full scale)")
    ax[0, 1].set_ylim(-10, 50)
    ax[0, 1].set_title("same, zoom (IR plateaus)")
    for a in ax[0]:
        a.set_xlabel("Time [us] (fan: ON 0-12 us, motor: ON 5-15 us, 50 kHz)")
        a.set_xlim(0, 40)
    ax[0, 0].legend(loc="upper right")
    k0 = code0
    for fn, col in sel + [("gndb_old_nt10mm.txt", C[1])]:
        o = data[fn]
        kk = [c[2] for c in cases if c[0] == fn][0]
        lab = S["ground"][fn.replace(".txt", "")]["label"]
        t = (o["tl"] - 300e-6) * 1e6
        if fn != "gndb_old_nt10mm.txt":
            ax[1, 0].plot(t, o["code_long"] - k0[kk], color=col, lw=1.0, label=lab)
        if fn.startswith("gndb"):
            ax[1, 1].plot(t, (o["vref_long"] - VREF) * 1e3, color=col, lw=1.2 if "old" in fn else 1.0,
                          ls="--" if "old" in fn else "-", label=lab)
    ax[1, 0].set_xlim(0, 40); ax[1, 0].set_ylim(-300, 2000)
    ax[1, 0].set_xlabel("Time [us]"); ax[1, 0].set_ylabel("ADC code error [LSB, 16 bit]")
    ax[1, 0].set_title("ADC code error, input ~0.97 V (1 uA lit)")
    ax[1, 0].legend(loc="upper right", fontsize=7)
    ax[1, 1].set_xlim(-100, 100); ax[1, 1].set_ylim(-60, 50)
    ax[1, 1].set_xlabel("Time [us]"); ax[1, 1].set_ylabel("VDDA - 3.3 V [mV]")
    ax[1, 1].set_title("Case B: VDDA (ADC reference), before / after")
    ax[1, 1].legend(loc="upper right", fontsize=7)
    fig.tight_layout()
    fig.savefig(FIG / "fig04_ground_coupling.png")
    plt.close(fig)

    # bar summary: rms code error
    keys = [c[0].replace(".txt", "") for c in cases]
    vals = [S["ground"][k]["code_rms_LSB16"] for k in keys]
    labs = [S["ground"][k]["label"] for k in keys]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    y = np.arange(len(keys))[::-1]
    ax.barh(y, np.maximum(vals, 0.05), height=0.6,
            color=[C[1] if k.startswith("gnda") else (GRAY if "_old_" in k else C[0]) for k in keys])
    for yi, v in zip(y, vals):
        ax.text(max(v, 0.05) * 1.1, yi, f"{v:.1f}" if v >= 0.1 else "< 0.1 (ideal in this model)", va="center", fontsize=8)
    ax.set_xscale("log"); ax.set_xlim(0.05, 5000)
    ax.set_yticks(y); ax.set_yticklabels(labs, fontsize=8)
    ax.set_xlabel("ADC code error, rms over the PWM period (unsynchronised sampling) [LSB 16 bit]")
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    fig.savefig(FIG / "fig05_ground_summary.png")
    plt.close(fig)


# ----------------------------------------------------------------------------
# 6. Fan sense and 7. motor CM
# ----------------------------------------------------------------------------
def sense():
    fig, ax = plt.subplots(1, 3, figsize=(14, 3.8))
    S["fan"] = {}
    for tag, lab, col in [("new", "2026-11-06: R43 at bulk caps + Kelvin to NT1", "#0b0b0b"),
                          ("old", "2026-11-01: 10 mm PGND shared (assumed)", C[1])]:
        d = load(f"fan_{tag}.txt")
        t, va = d["time"], d["vadc"]
        m = t > 8e-3
        fin = float(va[m].mean())
        k = 80
        sm = np.convolve(va, np.ones(k) / k, mode="same")
        res = {"vadc_final_mV": fin * 1e3, "i_est_A": fin / 0.1, "ripple_mVpp": float(np.ptp(va[m]) * 1e3),
               "ripple_LSB16pp": float(np.ptp(va[m]) / LSB16)}
        for p in (0.9, 0.99, 0.999):
            i = np.where((t > 1e-3) & (sm >= p * fin))[0][0]
            res[f"t{p*100:g}pct_ms"] = float((t[i] - 1e-3) * 1e3)
        S["fan"][tag] = res
        ax[0].plot(t * 1e3, va * 1e3, color=col, lw=1.2, label=f"{lab}: {fin/0.1:.3f} A")
        mz = (t > 8.9e-3) & (t < 8.96e-3)
        ax[1].plot((t[mz] - 8.9e-3) * 1e6, (va[mz] - fin) * 1e3, color=col, lw=1.4, label=lab)
    ax[0].axhline(100.2, color=GRAY, ls=":", lw=0.8)
    ax[0].set_xlabel("Time [ms]"); ax[0].set_ylabel("FAN_ISENSE [mV]")
    ax[0].set_title("Fan sense RC 1k/1uF: 0 -> 1 A step at 1 ms")
    ax[0].legend(loc="lower right", fontsize=7)
    ax[1].set_xlabel("Time [us]"); ax[1].set_ylabel("ripple around mean [mV]")
    ax[1].set_title("Steady-state ripple (50 kHz, D 0.6)")
    ax[1].set_ylim(-0.6, 0.85)
    ax[1].legend(loc="upper center", ncol=1, fontsize=7)

    d = load("cm_tran.txt")
    t, im, vcm = d["time"], d["imot"], d["v(cm)"]
    gain = 2350 * 1.2e-4
    icm = (vcm - 1.65) / gain
    m = (t > 250e-6) & (t < 600e-6)
    ax[2].plot(t[m] * 1e6, im[m], color=GRAY, lw=1.0, label="motor current (true)")
    ax[2].plot(t[m] * 1e6, icm[m], color="#0b0b0b", lw=1.4, label="from V(CM) (RREF 2.35k, 1 nF)")
    T = 20e-6
    kon = np.arange(260e-6, 600e-6, T)
    koff = kon + T / 2
    ax[2].plot(kon * 1e6, np.interp(kon, t, icm), "o", ms=5, color=C[1], label="ADC @ ON centre")
    ax[2].plot(koff * 1e6, np.interp(koff, t, icm), "s", ms=5, color=C[0], label="ADC @ OFF centre")
    ax[2].set_xlabel("Time [us]"); ax[2].set_ylabel("Current [A]")
    ax[2].set_title("Motor CM: centre-aligned 50 kHz, L = 30 uH (assumed)")
    ax[2].legend(loc="upper left", fontsize=7)
    fig.tight_layout()
    fig.savefig(FIG / "fig06_current_sense.png")
    plt.close(fig)

    S["cm"] = {}
    for a, b, name in [(300e-6, 400e-6, "duty0.5"), (500e-6, 600e-6, "duty0.6")]:
        mm = (t >= a) & (t < b)
        ko = np.arange(a, b, T)
        kf = ko + T / 2
        son = np.interp(ko, t, icm)
        soff = np.interp(kf, t, icm)
        S["cm"][name] = {"i_avg_true_A": float(im[mm].mean()), "i_ripple_App": float(np.ptp(im[mm])),
                         "vcm_ripple_mVpp": float(np.ptp(vcm[mm]) * 1e3),
                         "adc_on_centre_A": float(son.mean()), "adc_off_centre_A": float(soff.mean()),
                         "adc_mean_of_both_A": float(((son + soff) / 2).mean())}
    fa = load("fan_ac.txt")
    ca = load("cm_ac.txt")
    S["rc_atten_dB"] = {
        "fan_1k_1u": {f"{int(x/1e3)}k": float(db(np.interp(x, fa["frequency"], fa["hfan"]))) for x in (20e3, 40e3, 50e3, 80e3)},
        "cm_2k35_1n": {f"{int(x/1e3)}k": float(db(np.interp(x, ca["frequency"], ca["hcm"]))) for x in (20e3, 40e3, 50e3, 80e3)},
    }


def main():
    FIG.mkdir(exist_ok=True)
    if "--plot" not in sys.argv:
        print("running ngspice ...")
        run_spice()
    print("plotting ...")
    tia_noise()
    tia_ac_tran()
    supply()
    ground()
    sense()
    with open(HERE / "summary.json", "w") as fh:
        json.dump(S, fh, indent=1, ensure_ascii=False)
    print("figures:", ", ".join(sorted(p.name for p in FIG.glob("*.png"))))
    print("summary.json written")


if __name__ == "__main__":
    main()
