"""計算が落ち着いたら止める見張り役(2026-11-26、ユーザー「もっと早く計算する方法はないですか」→「①+② で進めて」)。
run_case.sh の 3 番目に auto を付けると、simpleFoam と一緒に裏で動く。
使い方: python3 docs/calc/fan_cfd/watch_steady.py <計算のフォルダ>

流れ:
  1. 100 回ごとに各プロセスが書き出す結果(processor0/<回>)を待つ
  2. 書き出されたら、その回だけ 1 つにまとめ(reconstructPar)、post.py で吸引と電力を出す
  3. 直近 3 回分(200 回のくり返しの間)で、吸引と電力の動きがどちらも 1% 以内なら、
     controlDict の stopAt を writeNow に書きかえる。simpleFoam は毎回 controlDict を読み直すので、次の回で書き出して止まる
  4. 落ち着かなくても、endTime(1500 回)で simpleFoam は止まる
決めた値: 最低 500 回は回す(はじめのうちは値が大きく動いて、たまたま 3 回そろうことがあるため)"""
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import post  # noqa: E402

CASE = sys.argv[1]
MIN_ITER = 500          # これより前では止めない
TOLERANCE = 0.01        # 直近 3 回の動きの許し(1%)
LOG = os.path.join(CASE, 'log.watch')


def written_times():
    """processor3(最後のプロセス)まで書き終わった回の一覧(小さい順)"""
    times = []
    folder = os.path.join(CASE, 'processor3')
    if not os.path.isdir(folder):
        return times
    for name in os.listdir(folder):
        if name.isdigit() and int(name) > 0:
            times.append(int(name))
    times.sort()
    return times


def solver_running():
    """simpleFoam が動いているか(run_case.sh が、simpleFoam が終わったら solver.done を作る)"""
    if os.path.exists(os.path.join(CASE, 'solver.done')):
        return False
    return True


def spread(values):
    """値の動きの大きさ(最大と最小の差 ÷ 最後の値の大きさ)"""
    return (max(values) - min(values)) / abs(values[-1])


def write_log(text):
    with open(LOG, 'a') as f:
        f.write(text + '\n')


def main():
    done = []
    suctions = []
    powers = []
    while solver_running():
        time.sleep(10)
        for t in written_times():
            if t in done:
                continue
            time.sleep(5)        # 書き出しの途中で読まないよう、少し待つ
            done.append(t)
            result = subprocess.run(['reconstructPar', '-time', str(t)], cwd=CASE,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if result.returncode != 0:
                write_log(f'{t}: まとめられなかった')
                continue
            d = post.analyse(f'{CASE}@{t}')
            suctions.append(d['suction_g'])
            powers.append(d['power'])
            write_log(f"{t}: 吸引 {d['suction_g']:.1f}g、電力 {d['power']:.3f}W")
            if t < MIN_ITER or len(suctions) < 3:
                continue
            if spread(suctions[-3:]) < TOLERANCE and spread(powers[-3:]) < TOLERANCE:
                write_log(f'{t}: 落ち着いたので止める')
                subprocess.run(['foamDictionary', '-entry', 'stopAt', '-set', 'writeNow', 'system/controlDict'],
                               cwd=CASE, stdout=subprocess.DEVNULL)
                return


main()
