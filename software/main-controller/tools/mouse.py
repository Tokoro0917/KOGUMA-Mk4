"""mouse.py — 機体をコマンドで動かす道具(無線 BLE でも、有線のシリアルでも)

ビューア(software/viewer/viewer.html)はボタンで使うもの、これはコマンドで使うもの。
Claude が作者の PC の上で動かして、書き込み → 走らせる → ログを取る → 値を直す、をくり返せるように作った(2026-11-28)。
作者がターミナルで使ってもよい。

使い方(software/main-controller で。つなぎ方の --ble・--port は、status などの前に書く。省くと --ble):
    python tools/mouse.py status                       ← 機体の状態(#STATUS)
    python tools/mouse.py --port COM5 status           ← 有線で
    python tools/mouse.py send "set turn90.entry_acc 0.7"   ← 1 行送って、返事を表示
    python tools/mouse.py send "list" --seconds 3      ← 3 秒の間、返事を表示
    python tools/mouse.py log                          ← 最新のログを取って logs/ に保存(get log)
    python tools/mouse.py log 3                        ← id 3 のログ
    python tools/mouse.py run turn_test right90 entry_acc=0.70   ← 走らせて、終わったら届くログを保存
    python tools/mouse.py listen --seconds 60          ← 60 秒の間、届いたものを表示・保存
    python tools/mouse.py fw KOGUMA-Mk4/build/Release/KOGUMA-Mk4.bin   ← プログラムを書き込む(fw.py と同じ)
    python tools/mouse.py show logs/20261128-061247_log_run.txt        ← 保存したログのまとめ(つながなくてよい)
    python tools/mouse.py show logs/… --cols t,v,v_target --from 0.5 --to 0.8 --every 10   ← 列を選んで表に
つなぎ方:
    --ble              名前が KOGUMA-MK4 の機体(--ble KOGUMA-2 で名前を指定)
    --port COM5        有線(STLINK の仮想 COM ポート)。ビューアで同じポートを開いていると使えない
いるもの: pip install bleak pyserial

届いた #BEGIN 〜 #END のかたまり(LOG・MAZE・EXPLORE など)は、ビューアと同じ名前で logs/ に保存する。
"""
import argparse
import asyncio
import os
import sys
import time
import zlib

import fw   # 同じフォルダの fw.py(つなぎ方と書き込みの手順を使う)

LOGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'logs')   # software/main-controller/logs


class BlockSaver:
    """届いた行から #BEGIN 〜 #END のかたまりを見つけて、logs/ にファイルで保存する"""

    def __init__(self):
        self.lines = None       # かたまりの途中なら、そこまでの行。外なら None
        self.name = ''          # ファイルの名前(#BEGIN を見たときに決める)
        self.saved = []         # 保存したファイル

    def add(self, line):
        if line.startswith('#BEGIN '):
            self.lines = [line]
            self.name = self.make_name(line)
        elif self.lines is not None:
            self.lines.append(line)
            if line.startswith('#END'):
                self.save()

    def make_name(self, begin_line):
        """ビューアと同じ形の名前: 20261128-061247_log_run.txt(LOG のときだけ種類を付ける)"""
        words = begin_line.split()
        block_type = words[1].lower()                 # log・maze・explore など
        kind = ''
        for word in words[2:]:
            if word.startswith('kind='):
                kind = '_' + word[5:]
        return time.strftime('%Y%m%d-%H%M%S') + '_' + block_type + kind + '.txt'

    def save(self):
        os.makedirs(LOGS_DIR, exist_ok=True)
        path = os.path.join(LOGS_DIR, self.name)
        # 同じ秒に 2 つ届いたときは、後ろに _2 を付ける
        number = 2
        while os.path.exists(path):
            path = os.path.join(LOGS_DIR, self.name.replace('.txt', f'_{number}.txt'))
            number = number + 1
        with open(path, 'w', encoding='utf-8', newline='\n') as f:
            f.write('\n'.join(self.lines) + '\n')
        rows = len(self.lines) - 3                    # #BEGIN・列の名前・#END を除いた行の数(だいたい)
        print(f'[保存しました] {os.path.relpath(path)}({rows} 行)')
        self.saved.append(path)
        self.lines = None


async def open_link(args):
    """--ble か --port でつなぐ"""
    if args.port:
        print(f'有線でつなぎます: {args.port}({args.baud})')
        return fw.SerialLink(args.port, args.baud)
    link = fw.BleLink()
    await link.open(args.ble)
    return link


async def receive(link, saver, timeout_s, until):
    """timeout_s 秒の間、届いた行を表示して、かたまりを保存する。
    until が与えられていれば、その文字で始まる行が来たところで止まる。止まった行(なければ None)を返す"""
    end = time.time() + timeout_s
    while time.time() < end:
        line = await link.read_line(end - time.time())
        if line is None:
            break
        line = line.replace('\x11', '').replace('\x13', '')    # XON・XOFF が混ざっても消す
        saver.add(line)
        # かたまりの中身(数千行)は表示しない。#BEGIN と #END だけ
        if saver.lines is None or line.startswith('#BEGIN'):
            print(line)
        if until is not None and line.startswith(until):
            return line
    return None


async def command_send(link, saver, text, timeout_s, until):
    """1 行送って、返事を待つ"""
    print('>', text)
    await link.send(text + '\n')
    reply = await receive(link, saver, timeout_s, until)
    if until is not None and reply is None:
        print(f'[{timeout_s} 秒待ったが「{until}」が来ない]')
        return False
    return True


async def command_fw(link, path):
    """プログラムを書き込む(fw.py の main と同じ手順)"""
    image = open(path, 'rb').read()
    crc = zlib.crc32(image)
    header = f'fw begin {len(image)} {crc:08x}\n'
    print(f'{path}: {len(image)} バイト、CRC32 {crc:08x}')
    start = time.time()
    await fw.enter_bootloader(link, header)
    await fw.send_image(link, image)
    await link.send('fw end\n')
    reply = await fw.wait_for(link, '#OK fw end', 10.0)
    if reply != '#OK fw end':
        print(f'最後の確かめで失敗: {reply}(もう一度動かせば書き直せる)')
        return False
    print(f'書けました({time.time() - start:.1f} 秒)')
    # 走るプログラムが起動して #STATUS を送ってくるのを待つ
    reply = await fw.wait_for(link, '#STATUS', 5.0)
    if reply is None:
        print('[走るプログラムから #STATUS が来ない]')
        return False
    print(reply)
    return True


def read_blocks(path):
    """ファイルから #BEGIN 〜 #END のかたまりを全部読む。1 つずつ {'head': …, 'columns': […], 'rows': [[…], …]}"""
    blocks = []
    block = None
    for line in open(path, encoding='utf-8', errors='replace'):
        line = line.strip()
        if line.startswith('#BEGIN '):
            block = {'head': line, 'columns': None, 'rows': []}
        elif block is not None and line.startswith('#END'):
            blocks.append(block)
            block = None
        elif block is not None and line:
            cells = line.split(',')
            if block['columns'] is None:
                block['columns'] = cells
            else:
                block['rows'].append(cells)
    return blocks


def to_number(text):
    """数にする(数でなければ None)"""
    try:
        return float(text)
    except ValueError:
        return None


def show_summary(block):
    """列ごとに、はじめ・おわり・最小・最大・平均を表示する"""
    columns = block['columns'] or []
    rows = block['rows']
    print(block['head'])
    print(f'{len(rows)} 行、{len(columns)} 列')
    # 日本語の字は 2 文字分の幅なので、そのぶん幅を小さくしてそろえる
    print(f'{"列":<13}{"はじめ":>8}{"おわり":>8}{"最小":>9}{"最大":>9}{"平均":>9}')
    for column_index in range(len(columns)):
        values = []
        for row in rows:
            if column_index < len(row):
                value = to_number(row[column_index])
                if value is not None:
                    values.append(value)
        if len(values) == 0:
            print(f'{columns[column_index]:<14}(数でない)')
            continue
        average = sum(values) / len(values)
        print(f'{columns[column_index]:<14}{values[0]:>11.4g}{values[-1]:>11.4g}'
              f'{min(values):>11.4g}{max(values):>11.4g}{average:>11.4g}')


def show_table(block, wanted, time_from, time_to, every):
    """選んだ列だけを、CSV の形で表示する(t が time_from〜time_to の行を、every 行に 1 行)"""
    columns = block['columns'] or []
    indexes = []
    for name in wanted:
        if name not in columns:
            sys.exit(f'列 {name} がない。ある列: {",".join(columns)}')
        indexes.append(columns.index(name))
    time_index = -1
    if 't' in columns:
        time_index = columns.index('t')
    print(','.join(wanted))
    count = 0       # 0 のときに表示する。every になったら 0 に戻す
    for row in block['rows']:
        if time_index >= 0:
            t = to_number(row[time_index])
            if t is not None and time_from is not None and t < time_from:
                continue
            if t is not None and time_to is not None and t > time_to:
                continue
        if count == 0:
            cells = []
            for index in indexes:
                cells.append(row[index])
            print(','.join(cells))
        count = count + 1
        if count >= every:
            count = 0


def command_show(args):
    """保存したログを表示する(機体にはつながない)"""
    blocks = read_blocks(args.file)
    if len(blocks) == 0:
        sys.exit('#BEGIN 〜 #END のかたまりがない')
    if args.block > len(blocks):
        sys.exit(f'かたまりは {len(blocks)} 個しかない')
    if args.cols:
        show_table(blocks[args.block - 1], args.cols.split(','), args.time_from, args.time_to, args.every)
        return
    if len(blocks) > 1:
        print(f'かたまりが {len(blocks)} 個ある(--block で選べる)')
        for number in range(len(blocks)):
            print(f'  {number + 1}: {blocks[number]["head"]}({len(blocks[number]["rows"])} 行)')
        print()
    show_summary(blocks[args.block - 1])


async def main():
    parser = argparse.ArgumentParser(description='KOGUMA MK4 をコマンドで動かす')
    parser.add_argument('--ble', nargs='?', const='KOGUMA-MK4', default='KOGUMA-MK4', help='無線で(名前。初めは KOGUMA-MK4)')
    parser.add_argument('--port', help='有線で(COM5、/dev/ttyACM0 など)')
    parser.add_argument('--baud', type=int, default=115200, help='有線の速さ(初めは 115200)')
    sub = parser.add_subparsers(dest='command', required=True)

    sub.add_parser('status', help='機体の状態')
    p = sub.add_parser('send', help='1 行送って、返事を表示')
    p.add_argument('text')
    p.add_argument('--until', help='この文字で始まる行が来るまで待つ(初めは #OK・#ERR・#STATUS のどれか)')
    p.add_argument('--seconds', type=float, default=3.0, help='待つ長さ(秒)')
    p = sub.add_parser('log', help='ログを取って保存(get log)')
    p.add_argument('id', nargs='?')
    p = sub.add_parser('run', help='走らせて、終わったら届くログを保存')
    p.add_argument('words', nargs='+', help='run のあとに付けるもの(turn_test right90 entry_acc=0.70 など)')
    p.add_argument('--seconds', type=float, default=180.0, help='待つ長さ(秒)')
    p = sub.add_parser('listen', help='届いたものを表示・保存')
    p.add_argument('--seconds', type=float, default=30.0)
    p = sub.add_parser('fw', help='プログラムを書き込む')
    p.add_argument('bin')
    p = sub.add_parser('show', help='保存したログを表示(つながない)')
    p.add_argument('file')
    p.add_argument('--block', type=int, default=1, help='ファイルにかたまりが何個もあるとき、何番目か')
    p.add_argument('--cols', help='表にする列(カンマで区切る)')
    p.add_argument('--from', dest='time_from', type=float, help='t がこの秒から')
    p.add_argument('--to', dest='time_to', type=float, help='t がこの秒まで')
    p.add_argument('--every', type=int, default=1, help='何行に 1 行を表示するか')
    args = parser.parse_args()

    if args.command == 'show':
        command_show(args)
        return

    link = await open_link(args)
    saver = BlockSaver()
    ok = True
    if args.command == 'status':
        ok = await command_send(link, saver, 'status', 3.0, '#STATUS')
    elif args.command == 'send':
        until = args.until
        if until is None:
            # 何も言われなければ、#OK・#ERR・#STATUS のどれかが来るまで(来なければ --seconds の間)
            until = '#'
        ok = await command_send(link, saver, args.text, args.seconds, until)
        if args.until is None:
            ok = True       # list のように # で始まらない返事もあるので、来なくても失敗にしない
    elif args.command == 'log':
        text = 'get log'
        if args.id is not None:
            text = 'get log ' + args.id
        ok = await command_send(link, saver, text, 60.0, '#END LOG')
    elif args.command == 'run':
        ok = await command_send(link, saver, 'run ' + ' '.join(args.words), args.seconds, '#END LOG')
    elif args.command == 'listen':
        await receive(link, saver, args.seconds, None)
    elif args.command == 'fw':
        ok = await command_fw(link, args.bin)
    await link.close()
    if not ok:
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
