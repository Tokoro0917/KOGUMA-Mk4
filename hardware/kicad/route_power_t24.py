"""タイヤ24mm のメイン基板(KOGUMA-Mk4_t24)の、電池の電圧の部分(BAT+・VBAT・PGND)を配線する(2026-11-25、ユーザー: 全部の配線はしない。電池の電圧の部分を引いて)。
2026-11-26: 作者が配線を全部やることになったので、作り直す順には入れていない(参考に残す)。使うなら place_main_t24.py のあとに走らせる。使い方(リポジトリの一番上で):
    /usr/bin/python3.12 hardware/kicad/route_power_t24.py            → 保存してある配線(KOGUMA-Mk4_t24/power_route.ses)を入れる
    /usr/bin/python3.12 hardware/kicad/route_power_t24.py reroute    → 自動配線をやり直してから入れる(部品の位置を変えたとき)

やること(順に):
  1. 裏の面の後ろ(x ≤ −9)に PGND のベタを入れる。モーター・ファンの大きい電流が戻る道を太く短くし、マイコンの GND とは NT1 の1点でつなぐ
  2. (reroute のときだけ)基板を Specctra の DSN に書き出し、BAT+・VBAT・PGND の3本だけを残して、自動配線(Freerouting)にかける。
     ほかのネットのパッドはよける物として残る。PGND のパッドは、短い線とビアで裏のベタへつなぐ。線の太さはネットクラスの Power(0.6mm)
  3. 自動配線の結果(SES)を基板に取り込む
  4. 自動で引けなかった4か所を、手で決めた線・ビアでつなぐ(下の fix_by_hand)
  5. ベタを塗り直して保存する
reroute には Freerouting 2.4.1(Maven Central の app.freerouting:freerouting の executable jar)と Java 25 が要る。
置き場所は環境の変数 FREEROUTING_JAR と JAVA25 で教える(なければ下の決まった所)。
"""
import os, re, sys, subprocess
import pcbnew

ROOT = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(ROOT, 'KOGUMA-Mk4_t24', 'KOGUMA-Mk4_t24.kicad_pcb')
SES = os.path.join(ROOT, 'KOGUMA-Mk4_t24', 'power_route.ses')
POWER_NETS = ('/電源/BAT+', 'VBAT', 'PGND')
MM = pcbnew.FromMM
OX, OY = 150.0, 100.0          # 機体の (x, y) → KiCad の (OX + x, OY − y)


def P(x, y):
    """機体の座標(x 前、y 左、mm)を KiCad の座標にする"""
    return pcbnew.VECTOR2I(MM(OX + x), MM(OY - y))


def add_pgnd_zone(b):
    """裏の面の後ろ(x ≤ −9)に PGND のベタを足す。外形・穴・ほかのネットは KiCad がよけて塗る"""
    z = pcbnew.ZONE(b)
    z.SetLayer(pcbnew.B_Cu)
    z.SetNet(b.FindNet('PGND'))
    z.SetZoneName('PGND_rear')
    z.SetLocalClearance(MM(0.25))
    z.SetMinThickness(MM(0.25))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetThermalReliefGap(MM(0.25))
    z.SetThermalReliefSpokeWidth(MM(0.5))
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    outline = z.Outline()
    outline.NewOutline()
    for x, y in ((-35, 40), (-9.0, 40), (-9.0, -40), (-35, -40)):     # 機体の座標の四角(外形で切られる)
        outline.Append(MM(OX + x), MM(OY - y))
    b.Add(z)


def reroute(b):
    """DSN を書き出し、電池の電圧の3本だけを残して Freerouting にかけ、SES を作り直す"""
    work = os.path.join(ROOT, 'KOGUMA-Mk4_t24', 'power_route_work')
    os.makedirs(work, exist_ok=True)
    dsn_all = os.path.join(work, 'all.dsn')
    dsn = os.path.join(work, 'power_only.dsn')
    pcbnew.ExportSpecctraDSN(b, dsn_all)
    text = open(dsn_all).read()
    i = text.index('(network')
    # network の中の (net 名前 (pins ...)) のうち、電池の電圧の3本だけを残す。ほかのネットを消すと、そのパッドはよける物になる
    def keep_power(m):
        if m.group(1) in POWER_NETS:
            return m.group(0)
        return ''
    text = text[:i] + re.sub(r'\n\s*\(net ("[^"]*"|\S+)\n\s*\(pins[^)]*\)\n\s*\)', keep_power, text[i:])
    open(dsn, 'w').write(text)
    jar = os.environ.get('FREEROUTING_JAR', os.path.join(work, 'freerouting.jar'))
    java = os.environ.get('JAVA25', '/usr/lib/jvm/java-25-openjdk-amd64/bin/java')
    subprocess.run([java, '-jar', jar, '-de', dsn, '-do', SES, '-mp', '60', '-mt', '3'], check=True)


def fix_by_hand(b):
    """自動配線で引けなかった4か所(2026-11-25 の結果)を、手で決めた線・ビアでつなぐ。部品の位置を変えたら見直す"""
    F = pcbnew.F_Cu

    def track(net, pts, width):
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(b)
            t.SetStart(P(x0, y0))
            t.SetEnd(P(x1, y1))
            t.SetWidth(MM(width))
            t.SetLayer(F)
            t.SetNet(b.FindNet(net))
            b.Add(t)

    def via(net, x, y):
        v = pcbnew.PCB_VIA(b)
        v.SetPosition(P(x, y))
        v.SetWidth(MM(0.8))                             # ネットクラスの Power のビア(0.8 / 0.4mm)
        v.SetDrill(MM(0.4))
        v.SetNet(b.FindNet(net))
        b.Add(v)

    # 1. BAT+: 電源スイッチの R1 の2番(上の面)と、真下の Q1 の2番(裏の面)をビアでつなぐ
    via('/電源/BAT+', -18.85, 5.30)
    track('/電源/BAT+', [(-18.85, 5.30), (-18.51, 5.25)], 0.4)
    # 2. PGND: DC-DC の入力のコンデンサ C5 の2番から、裏の PGND のベタへビア
    via('PGND', -26.75, -7.75)
    track('PGND', [(-26.75, -8.8), (-26.75, -7.75)], 0.6)
    # 3. PGND: モータードライバ U3 の9番(PGND)から右へ出してビア(U2 は自動配線で同じ形になった)
    track('PGND', [(-11.6, 6.25), (-10.26, 6.25)], 0.25)
    via('PGND', -10.26, 6.25)
    # 4. VBAT: DC-DC U1 の1番と3番を、2番(つながない)の外側を回ってつなぐ。
    #    C5 の2番と U1 の2番の間(0.78mm)の真ん中を 0.35mm で通す(DC-DC の入力は 0.5A くらいなので足りる)
    track('VBAT', [(-24.7, -6.25), (-25.64, -6.25), (-25.64, -8.5), (-24.7, -8.5)], 0.35)


def main():
    b = pcbnew.LoadBoard(PCB)
    if any(t.GetNetname() in POWER_NETS for t in b.GetTracks()):
        sys.exit('もう電池の電圧の配線が入っている。place_main_t24.py から作り直してから走らせる')
    add_pgnd_zone(b)
    if 'reroute' in sys.argv[1:]:
        reroute(b)
    print('SES の取り込み', pcbnew.ImportSpecctraSES(b, SES))
    fix_by_hand(b)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    b.Save(PCB)
    n_track = sum(1 for t in b.GetTracks() if t.GetClass() == 'PCB_TRACK')
    n_via = sum(1 for t in b.GetTracks() if t.GetClass() == 'PCB_VIA')
    print('電池の電圧の配線: 線', n_track, '本、ビア', n_via, '個')


if __name__ == '__main__':
    main()
