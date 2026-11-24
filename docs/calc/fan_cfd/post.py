"""吸引ファンの流体の計算(make_case.py・run_case.sh)の結果から、機体の下の負圧・漏れる空気の量・羽根を回す力を出す(2026-11-24)。
使い方: python3 docs/calc/fan_cfd/post.py <計算のフォルダ>[@くり返しの回] [...](回を書かなければ最後の回)
このパッケージの OpenFOAM は関数オブジェクト(forces など)が動かないので、書き出したメッシュと場(ASCII)を読んで自分で計算する:
  - 負圧: 機体の下の部屋(フレームの穴の下、半径 7.5mm、z −3.5〜1.5mm)のセルの体積平均の圧力
  - 流量: 入口(漏れの穴の外の大気)の面を通る流量 phi の合計
  - 回す力(トルク): 羽根の面にかかる圧力と、壁の摩擦(壁関数の nut を使う)を、z 軸まわりに足す
  - 吸引の力 = 負圧 × 68 × 34mm(スカートで囲った面。docs/spec.md の 600g = 2.54kPa と同じ面積)
  - 電力 = トルク × 角速度(羽根を回す仕事。モーターの損失は入れない)"""
import os
import re
import sys
import numpy as np

RHO = 1.2                     # 空気の密度 [kg/m³]
NU = 1.5e-5
AREA_SUCTION = 68e-3 * 34e-3  # 吸引する面 [m²]
OMEGA = 35000 * 2 * np.pi / 60


def body(path):
    """OpenFOAM のファイルの中身(コメントと見出しの FoamFile を除く)"""
    text = open(path).read()
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
    text = re.sub(r'//[^\n]*', '', text)
    i = text.find('FoamFile')
    if i >= 0:
        j = text.index('}', i)
        text = text[j + 1:]
    return text


def read_list(text, start=0):
    """text の start から後ろにある最初の「N ( ... )」のリストを読む。(中身の文字列, 終わりの位置)"""
    mt = re.compile(r'(\d+)\s*\(').search(text, start)
    n = int(mt.group(1))
    i = mt.end()
    depth = 1
    j = i
    while depth > 0:
        c = text[j]
        if c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
        j += 1
    return n, text[i:j - 1], j


def read_vectors(s):
    return np.array(s.replace('(', ' ').replace(')', ' ').split(), float).reshape(-1, 3)


def read_mesh(case):
    pm = os.path.join(case, 'constant/polyMesh')
    _, s, _ = read_list(body(os.path.join(pm, 'points')))
    pts = read_vectors(s)
    _, s, _ = read_list(body(os.path.join(pm, 'faces')))
    faces = [list(map(int, f.split())) for f in re.findall(r'\d+\(([^)]*)\)', s)]
    _, s, _ = read_list(body(os.path.join(pm, 'owner')))
    owner = np.array(s.split(), int)
    _, s, _ = read_list(body(os.path.join(pm, 'neighbour')))
    neigh = np.array(s.split(), int)
    btext = body(os.path.join(pm, 'boundary'))
    patches = {}
    for mt in re.finditer(r'(\w+)\s*\{[^}]*?nFaces\s+(\d+);\s*startFace\s+(\d+);', btext):
        patches[mt.group(1)] = (int(mt.group(3)), int(mt.group(2)))
    return pts, faces, owner, neigh, patches


def face_geometry(pts, faces):
    """面の中心と面積ベクトル(多角形を、頂点の平均の点からの三角形に分けて足す)"""
    nf = len(faces)
    cf = np.zeros((nf, 3))
    sf = np.zeros((nf, 3))
    by_n = {}
    for i, f in enumerate(faces):
        by_n.setdefault(len(f), []).append(i)
    for n, idx in by_n.items():
        idx = np.array(idx)
        v = pts[np.array([faces[i] for i in idx])]           # (k, n, 3)
        c0 = v.mean(axis=1)
        a = v - c0[:, None, :]
        b = np.roll(v, -1, axis=1) - c0[:, None, :]
        tri_s = 0.5 * np.cross(a, b)                          # 三角形の面積ベクトル
        tri_c = (v + np.roll(v, -1, axis=1) + c0[:, None, :]) / 3
        s = tri_s.sum(axis=1)
        mag = np.linalg.norm(tri_s, axis=2)
        w = mag / mag.sum(axis=1, keepdims=True)
        cf[idx] = (tri_c * w[:, :, None]).sum(axis=1)
        sf[idx] = s
    return cf, sf


def cell_geometry(cf, sf, owner, neigh, ncell):
    """セルの体積(発散の定理)と、中心のおおよその位置(面の中心の平均)"""
    vol = np.zeros(ncell)
    dotv = (cf * sf).sum(axis=1) / 3
    np.add.at(vol, owner, dotv)
    np.add.at(vol, neigh, -dotv[:len(neigh)])
    cc = np.zeros((ncell, 3))
    cnt = np.zeros(ncell)
    np.add.at(cc, owner, cf)
    np.add.at(cnt, owner, 1)
    np.add.at(cc, neigh, cf[:len(neigh)])
    np.add.at(cnt, neigh, 1)
    return vol, cc / cnt[:, None]


def read_field(case, time, name, ncell):
    """場の内部の値(セルごと)と、境界の値の文字列の辞書"""
    text = body(os.path.join(case, time, name))
    i = text.index('internalField')
    if text[i:i + 40].split()[1].startswith('uniform'):
        raise SystemExit(f'{name} が uniform のまま')
    n, s, end = read_list(text, i)
    if '(' in s:
        val = read_vectors(s)
    else:
        val = np.array(s.split(), float)
    return val, text[end:]


def boundary_values(btext, patch, vector=False):
    i = btext.index(patch)
    j = btext.index('value', i)
    if btext[j:j + 30].split()[1].startswith('uniform'):
        return None
    n, s, _ = read_list(btext, j)
    if vector:
        return read_vectors(s)
    return np.array(s.split(), float)


def latest_time(case):
    times = []
    for d in os.listdir(case):
        try:
            if float(d) > 0:
                times.append((float(d), d))
        except ValueError:
            pass
    return max(times)[1]


def analyse(case):
    t = None
    if '@' in case:                       # 「フォルダ@くり返し」で、その回の結果を見る
        case, t = case.split('@')
    pts, faces, owner, neigh, patches = read_mesh(case)
    ncell = max(owner.max(), neigh.max()) + 1
    cf, sf = face_geometry(pts, faces)
    vol, cc = cell_geometry(cf, sf, owner, neigh, ncell)
    if t is None:
        t = latest_time(case)
    p, _ = read_field(case, t, 'p', ncell)
    U, _ = read_field(case, t, 'U', ncell)
    _, nut_b = read_field(case, t, 'nut', ncell)
    _, phi_b = read_field(case, t, 'phi', len(neigh))
    # 1. 部屋の負圧
    r = np.hypot(cc[:, 0], cc[:, 1])
    ch = (r < 7.0e-3) & (cc[:, 2] > -3.5e-3) & (cc[:, 2] < 1.5e-3)
    p_ch = RHO * (p[ch] * vol[ch]).sum() / vol[ch].sum()
    # 2. 流量(入口から入る量。phi は外向きが正)
    q_in = -boundary_values(phi_b, 'inlet').sum()
    # 3. 羽根のトルク
    s0, n = patches['impeller']
    idx = np.arange(s0, s0 + n)
    own = owner[idx]
    f_p = RHO * p[own][:, None] * sf[idx]                      # 流れが壁を押す力(面積ベクトルは流れの外向き = 壁の中へ)
    area = np.linalg.norm(sf[idx], axis=1)
    nrm = sf[idx] / area[:, None]
    uw = np.cross(np.array([0, 0, OMEGA]), cf[idx])           # 壁の速さ
    du = U[own] - uw
    du_t = du - (du * nrm).sum(axis=1)[:, None] * nrm
    dist = np.abs(((cc[own] - cf[idx]) * nrm).sum(axis=1))
    nut_w = boundary_values(nut_b, 'impeller')
    if nut_w is None:
        nut_w = np.zeros(n)
    f_v = RHO * (NU + nut_w)[:, None] * du_t / dist[:, None] * area[:, None]   # 摩擦(流れが壁を引っ張る向き)
    def tz(f):
        return (cf[idx, 0] * f[:, 1] - cf[idx, 1] * f[:, 0]).sum()
    t_p = tz(f_p)
    t_v = tz(f_v)
    torque = -(t_p + t_v)                                     # モーターが出すトルク(回る向きが正)
    return dict(case=os.path.basename(case.rstrip('/')), time=t, cells=ncell, p_ch=p_ch, q=q_in, t_p=-t_p, t_v=-t_v, torque=torque,
                power=torque * OMEGA, suction_g=-p_ch * AREA_SUCTION / 9.81 * 1000)


if __name__ == '__main__':
    for case in sys.argv[1:]:
        d = analyse(case)
        print(f"{d['case']}(くり返し {d['time']}、セル {d['cells']}): 機体の下の圧力 {d['p_ch']:.0f}Pa → 吸引 {d['suction_g']:.0f}g、"
              f"漏れる空気 {d['q'] * 6e4:.2f} L/min、トルク {d['torque'] * 1e3:.3f} mN·m(圧力 {d['t_p'] * 1e3:.3f}・摩擦 {d['t_v'] * 1e3:.3f})、"
              f"羽根を回す仕事 {d['power']:.2f}W")
