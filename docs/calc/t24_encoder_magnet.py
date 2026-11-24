"""エンコーダの磁石がつくる磁界と、MT6835 が要る磁界の比べ(2026-11-24、ユーザー「磁石の磁束密度と IC の要求が合っているか。ToraNeko で磁力が足りないと言われている」)。
使い方: python3 docs/calc/t24_encoder_magnet.py → 数字と docs/img/tire24/encoder_magnet.png
やり方:
  - 磁石は直径方向に着磁した円柱(残留磁束密度 Br、ネオジム N35〜N52 で 1.17〜1.45T)。磁化 M は横向きなので、
    磁極は円柱の側面に M·cosφ で分布する。その磁極から出る磁界を、側面を細かく分けて足し合わせる(鉄などは近くにないとして)
  - MT6835(TSSOP-16)は、磁界の横向き(IC の面に平行)の成分の向きを、パッケージの真ん中で測る。要るのは
    「IC の表面で 30mT 以上」(MT6835 Rev1.3 の 6 章 Bpk)。磁界を測る素子は表面から Z = 0.21〜0.37mm の深さ(13 章)
  - ToraNeko.Mk3 の AS5047P は、ホールの素子(円の上、直径 約 2.2mm)で縦向き(IC の面に垂直)の成分を測る。
    要るのは 35〜70mT(AS5047P のデータシートの値。ここでは比べのために使う)
  - 磁石を鉄の中(軸受の内輪・平行ピン)に入れると、磁石の外の磁界は弱くなる。この計算には入れていない(実際は計算より弱い)"""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams['font.family'] = 'IPAGothic'


def field(D_mm, t_mm, Br_T, points):
    """直径 D、厚さ t の直径方向に着磁(+x)した円柱(軸は z、面は z = -t〜0)が、points (N, 3) [mm] につくる磁束密度 [T](3 成分)"""
    R = D_mm / 2
    nphi, nz = 360, 60
    phi = (np.arange(nphi) + 0.5) * 2 * np.pi / nphi
    z = -t_mm + (np.arange(nz) + 0.5) * t_mm / nz
    P, Z = np.meshgrid(phi, z, indexing='ij')
    src = np.stack([R * np.cos(P), R * np.sin(P), Z], axis=-1).reshape(-1, 3)
    sigma = np.cos(P).reshape(-1)                      # 磁極の面密度 / M
    dA = R * (2 * np.pi / nphi) * (t_mm / nz)
    out = []
    for p in points:
        d = p[None, :] - src
        r3 = np.linalg.norm(d, axis=1)**3
        out.append((sigma[:, None] * d / r3[:, None]).sum(axis=0) * dA)
    return np.array(out) * Br_T / (4 * np.pi)         # B = μ0·H、M = Br / μ0


def b_inplane_center(D, t, Br, gap):
    """磁石の面から gap [mm] の、軸の上の横向きの磁界 [mT]"""
    b = field(D, t, Br, np.array([[0.0, 0.0, gap]]))[0]
    return np.hypot(b[0], b[1]) * 1000


def b_vertical_hall(D, t, Br, gap, r_hall=1.1):
    """AS5047P のホールの素子(軸から r_hall の円の上)での縦向きの磁界の一番大きい値 [mT]"""
    b = field(D, t, Br, np.array([[r_hall, 0.0, gap]]))[0]
    return abs(b[2]) * 1000


if __name__ == '__main__':
    BR = {'N35': 1.17, 'N42': 1.29, 'N52': 1.43}
    print('MT6835(横向き、軸の上): IC の表面で 30mT 以上が要る')
    rows = []
    for D, t, note in ((3, 1, '今(ToraNeko と同じ、φ3 × 1)'), (3, 2, 'φ3 × 2'), (4, 2, 'φ4 × 2'), (5, 2, 'φ5 × 2'), (6, 2.5, 'φ6 × 2.5(AS5047P の推奨に近い)')):
        for gap in (0.5, 1.0):
            vals = {k: b_inplane_center(D, t, br, gap) for k, br in BR.items()}
            die = {k: b_inplane_center(D, t, br, gap + 0.29) for k, br in BR.items()}
            rows.append((note, gap, vals, die))
            print(f'  {note}、すき間 {gap}mm: IC の表面 ' + ' / '.join(f'{k} {v:.0f}' for k, v in vals.items()) +
                  ' mT、素子(0.29mm 深い) ' + ' / '.join(f'{k} {v:.0f}' for k, v in die.items()) + ' mT')
    print('ToraNeko の AS5047P(縦向き、ホールの素子 r 1.1mm): 35mT 以上が要る')
    for gap in (0.5, 0.78):
        print(f'  φ3 × 1、すき間 {gap}mm: ' + ' / '.join(f'{k} {b_vertical_hall(3, 1, br, gap):.0f}' for k, br in BR.items()) + ' mT')
    # 図: すき間と磁界(N42)
    gaps = np.linspace(0.2, 2.0, 37)
    fig, ax = plt.subplots(figsize=(9, 5.5))
    for D, t, c in ((3, 1, 'r'), (3, 2, 'orange'), (4, 2, 'g'), (5, 2, 'b'), (6, 2.5, 'purple')):
        b = [b_inplane_center(D, t, BR['N42'], g) for g in gaps]
        ax.plot(gaps, b, color=c, label=f'φ{D} × {t}(N42)')
    ax.axhline(30, color='k', ls='--')
    ax.text(1.55, 32, 'MT6835 の下限 30mT', fontsize=9)
    ax.axvline(0.5, color='gray', ls=':')
    ax.text(0.52, 5, 'MK4・ToraNeko の\nすき間 0.5mm', fontsize=8, color='gray')
    ax.set_xlabel('磁石の面から IC の表面までのすき間 [mm]')
    ax.set_ylabel('IC の表面の横向きの磁界 [mT]')
    ax.set_ylim(0, 300)
    ax.grid(alpha=.3)
    ax.legend()
    ax.set_title('直径方向に着磁した円柱の磁石の、軸の上の磁界(鉄が近くにないとき)')
    fig.savefig('docs/img/tire24/encoder_magnet.png', dpi=110, bbox_inches='tight')
