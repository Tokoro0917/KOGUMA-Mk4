"""fake_mouse.py — mouse.py・fw.py を試すための、にせの機体(PC の上で動く)

TCP の 5000 番で待ち、走るプログラムとブートローダのふりをする(docs/ble.md の 4・6 章の返事を返す)。
使い方(2 つのターミナルで):
    python tools/fake_mouse.py
    python tools/mouse.py --port socket://localhost:5000 status
    python tools/mouse.py --port socket://localhost:5000 run turn_test right90
    python tools/mouse.py --port socket://localhost:5000 fw some.bin
--drop 30 を付けると、書き込みの 30 行目を落とす(送り直しを試す)。
"""
import argparse
import base64
import math
import socket
import zlib


def sample_log(kind):
    """見本の走行ログ(1 秒分、1kHz)の行を作る"""
    lines = [f'#BEGIN LOG kind={kind} dt=0.001 n=1000 div=1', 't,x,v,v_target,w,w_target,angle,phase']
    x_mm = 0.0
    for i in range(1000):
        t = i * 0.001
        v_target = min(600.0, t * 4000.0)
        v = v_target + 10.0 * math.sin(t * 60.0)
        x_mm = x_mm + v * 0.001
        w = 0.0
        if 400 <= i < 700:
            w = 900.0 * math.sin((i - 400) / 300.0 * math.pi)
        lines.append(f'{t:.3f},{x_mm:.2f},{v:.1f},{v_target:.1f},{w:.1f},{w:.1f},0,1')
    lines.append('#END LOG')
    return lines


class FakeMouse:
    """1 行受けるごとに、返す行のリストを作る"""

    def __init__(self, drop_line):
        self.in_boot = False
        self.params = {'turn90.entry_acc': '0.65'}
        self.drop_line = drop_line
        self.line_count = 0
        self.image = bytearray()
        self.length = 0
        self.crc = 0
        self.written_until = 0
        self.gap_reported = -1

    def handle(self, line):
        if self.in_boot:
            return self.handle_boot(line)
        if line == 'status':
            return ['#STATUS state=idle batt=11.82 maze=16x16 explored=0 log=1']
        if line.startswith('set '):
            words = line.split()
            self.params[words[1]] = words[2]
            return ['#OK set ' + words[1]]
        if line == 'get params':
            result = []
            for name in self.params:
                result.append(f'{name}={self.params[name]}')
            return result + ['#OK get params']
        if line.startswith('get log'):
            return sample_log('run')
        if line.startswith('run '):
            return ['#OK run', '#EVENT run_done'] + sample_log('tune')
        if line.startswith('fw begin '):
            self.in_boot = True            # 印を書いてリセットしたふり
            return ['#BOOT ready']
        return ['#ERR unknown command: ' + line]

    def handle_boot(self, line):
        """ブートローダのふり(software/bootloader/App/boot_lines.c と同じ返事)"""
        self.line_count = self.line_count + 1
        if self.line_count == self.drop_line:
            return []                      # この行は届かなかったことにする
        if line.startswith('fw begin '):
            words = line.split()
            self.length = int(words[2])
            self.crc = int(words[3], 16)
            self.image = bytearray(self.length)
            self.written_until = 0
            return ['#OK fw begin']
        if line == 'fw end':
            if zlib.crc32(bytes(self.image)) != self.crc:
                return ['#ERR fw crc']
            self.in_boot = False           # 走るプログラムへ
            return ['#OK fw end', '#STATUS state=idle batt=11.80 maze=16x16 explored=0 log=0']
        if line.startswith('fw '):
            words = line.split()
            position = int(words[1])
            data = base64.b64decode(words[2])
            if position > self.written_until:
                if self.gap_reported == self.written_until:
                    return []
                self.gap_reported = self.written_until
                return [f'#ERR fw gap {self.written_until}']
            before = self.written_until
            self.image[position:position + len(data)] = data
            if position + len(data) > self.written_until:
                self.written_until = position + len(data)
            if self.written_until // 4096 > before // 4096 or (self.written_until == self.length and before != self.length):
                return [f'#OK fw {self.written_until}']
            return []
        if line == 'status':
            return ['#BOOT ready']
        return ['#ERR unknown command']


def main():
    parser = argparse.ArgumentParser(description='にせの機体')
    parser.add_argument('--drop', type=int, default=0, help='書き込みの何行目を落とすか(0 なら落とさない)')
    args = parser.parse_args()
    server = socket.socket()
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('localhost', 5000))
    server.listen(1)
    print('localhost:5000 で待っています')
    mouse = FakeMouse(args.drop)
    while True:
        connection, _address = server.accept()
        buffer = b''
        while True:
            data = connection.recv(4096)
            if not data:
                break
            buffer = buffer + data
            while b'\n' in buffer:
                line, buffer = buffer.split(b'\n', 1)
                for reply in mouse.handle(line.decode().strip()):
                    connection.sendall((reply + '\n').encode())
        connection.close()


if __name__ == '__main__':
    main()
