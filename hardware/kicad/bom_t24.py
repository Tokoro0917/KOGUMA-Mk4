"""タイヤ24mm のメイン基板(KOGUMA-Mk4_t24)の部品表を作る(2026-11-23、ブランチ claude/trusting-dirac-1tdt54)
使い方(リポジトリの一番上で): /usr/bin/python3.12 hardware/kicad/bom_t24.py
  → hardware/kicad/KOGUMA-Mk4_t24/bom_t24.csv(JLCPCB の BOM の形: Comment, Designator, Footprint, LCSC Part #)、cpl_t24.csv(部品の位置)と、docs/bom_t24.md の「部品の一覧」
品番は (値, フットプリント) で引く。LCSC の番号・定格・厚さは LCSC と Samsung の製品ページで確かめた(2026-11-23)。
在庫は注文のときに JLCPCB の BOM ツールで確かめる"""
import os, csv, collections
import pcbnew
ROOT = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(ROOT, 'KOGUMA-Mk4_t24', 'KOGUMA-Mk4_t24.kicad_pcb')
# (値, フットプリントの名前) → (品番, LCSC, 高さの最大[mm], メモ)
P = {
    # ---- コンデンサ 1005 ----
    ('100n', 'C_0402_1005Metric'): ('Samsung CL05B104KO5NNNC (16V X7R)', 'C1525', 0.55, 'JLC Basic'),
    ('100n 25V', 'C_0402_1005Metric'): ('Samsung CL05A104KA5NNNC (25V X5R)', 'C100072', 0.55, 'VBAT(12.6V)'),
    ('220n 25V', 'C_0402_1005Metric'): ('Samsung CL05A224KA5NNNC (25V X5R)', 'C47129', 0.55, 'BAT+ とゲートの間'),
    ('22n 50V', 'C_0402_1005Metric'): ('FH 0402B223K500NT (50V X7R)', 'C1532', 0.55, 'JLC Basic'),
    ('10n', 'C_0402_1005Metric'): ('Samsung CL05B103KB5NNNC (50V X7R)', 'C15195', 0.55, 'JLC Basic'),
    ('1n C0G', 'C_0402_1005Metric'): ('FH 0402CG102J500NT (50V C0G ±5%)', 'C53547', 0.55, ''),
    ('220p', 'C_0402_1005Metric'): ('FH 0402CG221J500NT (50V C0G ±5%)', 'C39122', 0.55, ''),
    ('0.5p C0G', 'C_0402_1005Metric'): ('Murata GJM1555C1HR50BB01D (50V C0G ±0.1pF)', 'C76911', 0.55, '受光アンプの帰還。±0.05pF なら GJM1555C1HR50WB01D(C76912)'),
    ('1u', 'C_0402_1005Metric'): ('Samsung CL05A105KA5NQNC (25V X5R)', 'C52923', 0.55, 'JLC Basic'),
    ('2.2u 10V', 'C_0402_1005Metric'): ('Samsung CL05A225MP5NNNC (10V X5R)', 'C107370', 0.55, ''),
    ('10u', 'C_0402_1005Metric'): ('Samsung CL05A106MQ5NUNC (6.3V X5R)', 'C15525', 0.70, 'VCORE(約1.2V)だけ。厚さ 0.50±0.20。JLC Basic'),
    # ---- コンデンサ 1608(3.3V にかかる 10µF・4.7µF)----
    ('10u', 'C_0603_1608Metric'): ('Samsung CL10A106KP8NNNC (10V X5R)', 'C19702', 0.90, '厚さ 0.80±0.10。JLC Basic'),
    ('10u 10V', 'C_0603_1608Metric'): ('Samsung CL10A106KP8NNNC (10V X5R)', 'C19702', 0.90, '厚さ 0.80±0.10。JLC Basic'),
    ('4.7u 10V', 'C_0603_1608Metric'): ('Samsung CL10A475KP8NNNC (10V X5R)', 'C1705', 0.90, '厚さ 0.80±0.10'),
    # ---- コンデンサ 2012・3216 ----
    ('10u 25V', 'C_0805_2012Metric'): ('Samsung CL21A106KACLRNC (25V X5R)', 'C318687', 0.95, '**厚さ 0.85±0.10**(電池の下の C22・C32 のため。ほかも同じ品にそろえる)'),
    ('22u 10V', 'C_0805_2012Metric'): ('Samsung CL21A226MPCLRNC (10V X5R)', 'C307529', 0.95, '厚さ 0.85±0.10'),
    ('22u 25V', 'C_1206_3216Metric'): ('Samsung CL31A226KAHNNNE (25V X5R)', 'C12891', 1.80, '厚さ 1.60±0.20。電池の外に置く。JLC Basic'),
    # ---- 抵抗 1005(UNI-ROYAL 0402WGF、±1%、1/16W)----
    ('0', 'R_0402_1005Metric'): ('UNI-ROYAL 0402WGF0000TCE', 'C17168', 0.40, 'JLC Basic'),
    ('2.2', 'R_0402_1005Metric'): ('TA-I RMS04FT2R20', 'C208851', 0.40, ''),
    ('20 1%', 'R_0402_1005Metric'): ('UNI-ROYAL 0402WGF200JTCE', 'C25089', 0.40, ''),
    ('47', 'R_0402_1005Metric'): ('UNI-ROYAL 0402WGF470JTCE', 'C25118', 0.40, ''),
    ('100', 'R_0402_1005Metric'): ('UNI-ROYAL 0402WGF1000TCE', 'C25076', 0.40, 'JLC Basic'),
    ('1k', 'R_0402_1005Metric'): ('UNI-ROYAL 0402WGF1001TCE', 'C11702', 0.40, 'JLC Basic'),
    ('1.30k 1%', 'R_0402_1005Metric'): ('UNI-ROYAL 0402WGF1301TCE', 'C25866', 0.40, 'DC-DC の出力の設定'),
    ('4.7k', 'R_0402_1005Metric'): ('UNI-ROYAL 0402WGF4701TCE', 'C25900', 0.40, 'JLC Basic'),
    ('4.7k 1%', 'R_0402_1005Metric'): ('UNI-ROYAL 0402WGF4701TCE', 'C25900', 0.40, 'JLC Basic'),
    ('10k', 'R_0402_1005Metric'): ('UNI-ROYAL 0402WGF1002TCE', 'C25744', 0.40, 'JLC Basic'),
    ('10k 1%', 'R_0402_1005Metric'): ('UNI-ROYAL 0402WGF1002TCE', 'C25744', 0.40, 'JLC Basic'),
    ('47k', 'R_0402_1005Metric'): ('UNI-ROYAL 0402WGF4702TCE', 'C25792', 0.40, 'JLC Basic'),
    ('47k 1%', 'R_0402_1005Metric'): ('UNI-ROYAL 0402WGF4702TCE', 'C25792', 0.40, 'JLC Basic'),
    ('100k', 'R_0402_1005Metric'): ('UNI-ROYAL 0402WGF1003TCE', 'C25741', 0.40, 'JLC Basic'),
    ('820k', 'R_0402_1005Metric'): ('UNI-ROYAL 0402WGF8203TCE', 'C67558', 0.40, ''),
    # ---- 半導体など ----
    ('2N7002', 'SOT-23'): ('CJ 2N7002', 'C8545', 1.20, 'JLC Basic'),
    ('BAT54WS', 'D_SOD-323'): ('Jingdao BAT54WS (30V 200mA)', 'C438012', 1.10, 'JSCJ(C2991936)・LGE(C402232)の BAT54WS は 100mA なので使わない'),
}
# 品番がもう決まっている部品(docs/bom.md)。LCSC の番号はまだ確かめていない
FIXED = {'STM32H725RGVx': 'STM32H725RGV6(または RGV3)', 'MP6551GQB': 'MPS MP6551GQB', 'INA241A3': 'TI INA241A3IDDFR(SOT-23-8)',
         'OPA2354': 'TI OPA2354(VSSOP-8)', 'LSM6DSR': 'ST LSM6DSR', 'NJU6080': 'NJR NJU6080', 'NJW4615A': 'Nisshinbo NJW4615AF1-TE1', 'HY0020': 'FDK HY0020',
         'LXDC55FAAA-203': 'Murata LXDC55FAAA-203', 'AO4407A': 'AOS AO4407A', 'IRLML6344': 'Infineon IRLML6344TRPBF',
         'SMF13A': 'Littelfuse SMF13A', 'MBR230LSFT1G': 'onsemi MBR230LSFT1G', 'BLM18PG221SN1D': 'Murata BLM18PG221SN1D',
         '2.2u DFE201610E-2R2M': 'Murata DFE201610E-2R2M=P2', 'CSTNE10M0G52A000R0': 'Murata CSTNE10M0G52A000R0',
         'T521D107M025ATE040 (100u 25V)': 'KEMET T521D107M025ATE040', 'RLM12FTCMR005 (5m 1%)': 'TA-I RLM12FTCMR005', 'PMR18EZPFU10L0 (10m 1%)': 'ROHM PMR18EZPFU10L0',
         'SSSS810701': 'Alps Alpine SSSS810701', 'OPV332': 'TT Electronics (Optek) OPV332', 'SFH 229 FA': 'ams OSRAM SFH 229 FA(2025-11-28 生産終了。**予備を含めて在庫を確保**)', 'TS-1088-AR02016': 'XUNPU TS-1088-AR02016', 'SMT-0540-S-R': 'PUI Audio SMT-0540-S-R'}
# IC など品番が決まっている部品の LCSC の番号と在庫(2026-11-23、LCSC・JLCPCB の製品ページで確かめた。在庫は LCSC の数で、JLC の組み立ての在庫とは別)
LCSC = {'STM32H725RGVx': ('C5271073', 'RGV6。**LCSC の在庫 0**(RGV3 の C5271074 も 0)'), 'INA241A3': ('C6051860', '在庫 約6,470'),
        'OPA2354': ('C95502', 'OPA2354AIDGKR、在庫 約4,360'), 'LSM6DSR': ('C784817', 'LSM6DSRTR、在庫 約4,200'),
        'AO4407A': ('C16072', 'AOS のもの(UMW・MSKSEMI の同じ品番は別物)、在庫 約4,145'), 'IRLML6344': ('C53550', 'Infineon のもの、在庫 約39,800'),
        'SMF13A': ('C315998', '在庫 約3,835'), 'MBR230LSFT1G': ('C126673', '在庫 約22,400'), 'BLM18PG221SN1D': ('C80165', '在庫 約157,900'),
        '2.2u DFE201610E-2R2M': ('C337891', '在庫 約3,910'), 'RLM12FTCMR005 (5m 1%)': ('C316225', '在庫 約125,000。2026-11-26 に PMR18EZPFU5L00(LCSC の在庫 0)から替えた。±50ppm/°C、AEC-Q200'), 'PMR18EZPFU10L0 (10m 1%)': ('C308574', '在庫 約18,000(2026-11-26)(2026-11-24 に 0.1Ω 2512 から変えた。ファンのシャント R43)'),
        'SSSS810701': ('C97433', '在庫 約340'), 'SMT-0540-S-R': ('C3812104', '**LCSC の在庫 0**'), 'APTD1608LSECK/J4-PF': ('C5879215', '在庫 約660'),
        'OPV332': ('C6622198', '**LCSC の在庫 0**'), 'SFH 229 FA': ('C3211054', '**LCSC の在庫 0**'),
        'MP6551GQB': ('', '**LCSC になし**(ほかの代理店で)'), 'NJU6080': ('', '**LCSC になし**(日清紡の品番は NJU6080F1)'), 'NJW4615A': ('C3193134', 'LCSC は在庫 0・Mouser に約 2,300(2026-11-26)。NJU6080 と同じピン・同じ抵抗(在庫がない NJU6080 から 2026-11-26 に替えた)'),
        'LXDC55FAAA-203': ('', '**LCSC になし。生産終了の情報あり(未確認)。自分ではんだ付け**(2026-11-26、ユーザー。JLC の BOM・CPL には入れない)'), 'CSTNE10M0G52A000R0': ('C907976', '在庫 約2,500。2026-11-26 に CSTNE10M0G52Z000R0(LCSC になし)から替えた。仕様は同じで車載用'),
        'T521D107M025ATE040 (100u 25V)': ('', '在庫は未確認(47µF の T521V は LCSC になし)。裏の面に手ではんだ付け'), 'TS-1088-AR02016': ('C720477', 'JLC の Basic 部品、在庫 約450,000。2026-11-26 に TVAF06-A020B-R(LCSC になし)から替えた。ランドは同じ、位置決めの穴は使わない'),
        'HY0020': ('', '**LCSC になし**(DigiKey・Arrow)')}
HAND_SOLDER = ['U1']   # 自分ではんだ付けする上の面の部品(名前がぴったり同じものだけ)。U1 は LXDC55(2026-11-26、ユーザー: LXDC55 は自分ではんだ付け)
NOT_SMT = ('J1', 'J2', 'J3', 'J4', 'J5', 'J6', 'J7', 'NT1', 'TP', 'D70', 'D71', 'D72', 'D73', 'D74', 'D75', 'D76', 'D77')

def r_is_pad(refs):
    return all(r in ('J1', 'J2', 'J3', 'J4', 'J5', 'J6', 'NT1') or r.startswith('TP') for r in refs)

def main():
    b = pcbnew.LoadBoard(PCB)
    rows = collections.defaultdict(list)
    for f in b.GetFootprints():
        r = f.GetReference()
        if r.startswith('H'):
            continue
        rows[(f.GetValue(), f.GetFPIDAsString().split(':')[1], 'B' if f.IsFlipped() else 'T')].append(r)
    key = lambda s: (''.join(c for c in s if not c.isdigit()), int(''.join(c for c in s if c.isdigit()) or 0))
    out, missing = [], []
    for (v, fp, side), refs in sorted(rows.items(), key=lambda kv: key(sorted(kv[1], key=key)[0])):
        refs = sorted(refs, key=key)
        if (v, fp) in P:
            mpn, lcsc, h, memo = P[(v, fp)]
        else:
            base = v.split(' (')[0] if v.split(' (')[0] in FIXED else v
            mpn, lcsc, h, memo = (FIXED.get(v) or FIXED.get(base) or ''), '', None, ''
            base = v.split(' (')[0]
            for k in (v, base, 'APTD1608LSECK/J4-PF' if v.startswith('APTD1608') else None):
                if k in LCSC:
                    lcsc, memo = LCSC[k][0], LCSC[k][1]
                    break
            h = {'AO4407A': 1.75, 'T521D107M025ATE040 (100u 25V)': 3.1, 'RLM12FTCMR005 (5m 1%)': 0.8, 'PMR18EZPFU10L0 (10m 1%)': 0.57, 'MBR230LSFT1G': 0.98, 'BLM18PG221SN1D': 0.95}.get(v, h)
            if r_is_pad(refs):
                mpn, memo = '(基板のパッド。部品なし)', {'J1': '電池の線 BT2.0 のケーブルをはんだ付け', 'J2': 'モーターの線(裏)', 'J3': 'モーターの線(裏)', 'J4': 'ファンの線',
                                                     'J5': 'エンコーダ基板をはんだ付け', 'J6': 'エンコーダ基板をはんだ付け', 'NT1': 'PGND と GND の1点', 'TP1': '', 'TP2': '', 'TP3': ''}.get(refs[0], '')
            if refs == ['J7']:
                mpn, h, memo = '1.27mm 2 × 3 のピンヘッダ(縦、穴)。**手持ち**(2026-11-23)', 6.0, '高さ約 5mm。電池の外。JLC の BOM には入れない'
            if v.startswith('APTD1608'):
                mpn, h, memo = 'Kingbright APTD1608LSECK/J4-PF', 0.95, '1番がカソード。' + memo
            if not mpn:
                missing.append((v, fp, refs))
        out.append(dict(value=v, fp=fp, side=side, refs=refs, mpn=mpn, lcsc=lcsc, h=h, memo=memo))
    # 同じ品番の LED はまとめる
    merged = collections.OrderedDict()
    for o in out:
        k = (o['mpn'] or o['value'], o['fp'], o['side'], o['lcsc'])
        if k in merged:
            merged[k]['refs'] += o['refs']
        else:
            merged[k] = dict(o)
    out = list(merged.values())
    with open(os.path.join(ROOT, 'KOGUMA-Mk4_t24', 'bom_t24.csv'), 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['Comment', 'Designator', 'Footprint', 'LCSC Part #'])
        for o in out:
            if all(r.startswith(NOT_SMT) for r in o['refs']) or o['side'] == 'B':     # 裏の部品(C4・Q1)は手ではんだ付け(JLC は上の面だけ)
                continue
            if all(r in HAND_SOLDER for r in o['refs']):
                continue
            w.writerow([o['value'] if not o['mpn'] else o['mpn'].split(' (')[0], ','.join(o['refs']), o['fp'], o['lcsc']])
    md = ['| 部品 | 数 | 面 | 値 | 品番 | LCSC | 高さ[mm] | メモ |', '|---|---|---|---|---|---|---|---|']
    for o in out:
        md.append(f"| {' '.join(o['refs'])} | {len(o['refs'])} | {'裏' if o['side'] == 'B' else '上'} | {o['value'].split(' (')[0]} | {o['mpn']} | {o['lcsc']} | {'' if o['h'] is None else o['h']} | {o['memo']} |")
    doc = os.path.join(ROOT, '../../docs/bom_t24.md')       # 「## 部品の一覧」より下を書き直す
    t = open(doc).read()
    i = t.index('## 部品の一覧')
    open(doc, 'w').write(t[:i] + '## 部品の一覧\n\n' + '\n'.join(md) + '\n')
    return out, missing

def cpl():
    """JLCPCB の部品の位置(CPL: Designator, Mid X, Mid Y, Layer, Rotation)。kicad-cli の位置ファイルから作る。
    線のパッド・壁センサ・テストパッドなど、JLC で載せない部品は入れない。向きは JLC の画面で部品ごとに確かめて直す(ライブラリで 0° の向きが違うことがある)"""
    import subprocess, tempfile
    tmp = os.path.join(tempfile.mkdtemp(), 'pos.csv')
    subprocess.run(['kicad-cli', 'pcb', 'export', 'pos', '--format', 'csv', '--units', 'mm', '--side', 'both', '-o', tmp, PCB], check=True, capture_output=True)
    rows = list(csv.DictReader(open(tmp)))
    out = os.path.join(ROOT, 'KOGUMA-Mk4_t24', 'cpl_t24.csv')
    n = 0
    with open(out, 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['Designator', 'Mid X', 'Mid Y', 'Layer', 'Rotation'])
        for r in rows:
            ref = r['Ref']
            if ref.startswith(NOT_SMT) or ref.startswith('H') or r['Side'] != 'top':     # JLC は上の面だけ
                continue
            if ref in HAND_SOLDER:
                continue
            w.writerow([ref, r['PosX'] + 'mm', r['PosY'] + 'mm', 'Top' if r['Side'] == 'top' else 'Bottom', r['Rot']])
            n += 1
    return n

if __name__ == '__main__':
    out, missing = main()
    for o in out:
        print(len(o['refs']), o['value'], o['fp'], o['side'], o['mpn'], o['lcsc'], o['h'], ' '.join(o['refs']))
    print('品番なし:', missing)
    print('CPL の部品', cpl())
