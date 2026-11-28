"""fw.py — STM32 のプログラムを、ブートローダで書き込む(無線 BLE でも、有線のシリアルでも)。決まりは docs/ble.md の 6.3

使い方(software/main-controller で):
    python tools/fw.py KOGUMA-Mk4/build/Release/KOGUMA-Mk4.bin --ble            ← 無線(名前が KOGUMA-MK4 の機体を探す)
    python tools/fw.py KOGUMA-Mk4/build/Release/KOGUMA-Mk4.bin --ble KOGUMA-2  ← 名前を指定
    python tools/fw.py KOGUMA-Mk4/build/Release/KOGUMA-Mk4.bin --port COM5     ← 有線(STLINK の仮想 COM ポート)
いるもの: pip install bleak pyserial

手順:
  1. `fw begin <長さ> <crc>` を送る。走るプログラムが生きていれば、印を書いてリセット → ブートローダが `#BOOT ready`
     (ブートローダにいるときは、そのまま `#OK fw begin`)
  2. 返事がなければ(プログラムが壊れている・止まっている)、BLE なら `@flash` を送る → ブートローダが `#BOOT ready`
  3. ブートローダに `fw begin` を送り直す → 走るプログラムの領域を消して `#OK fw begin`
  4. `fw <位置> <base64>`(1 行 192 バイト分)を送る。4KB ごとに `#OK fw <位置>` を待つ。来なければ、その 4KB を送り直す(3 回まで)
  5. `fw end` → ブートローダが全体の CRC を確かめ、合えば `#OK fw end` で走るプログラムへ
"""
import argparse
import asyncio
import base64
import sys
import time
import zlib

LINE_BYTES = 192          # 1 行で送る大きさ(16 の倍数。base64 で 256 文字)
ACK_EVERY = 4096          # ブートローダが「#OK fw <位置>」を返す間隔
NUS_RX = '6e400002-b5a3-f393-e0a9-e50e24dcca9e'   # PC → 機体(書く)
NUS_TX = '6e400003-b5a3-f393-e0a9-e50e24dcca9e'   # 機体 → PC(通知)


class SerialLink:
    """有線(シリアル)でつなぐ"""

    def __init__(self, port, baud=115200):
        import serial
        # serial_for_url: COM5・/dev/ttyACM0 のほか、試験用の socket://localhost:5000 も開ける
        self.port = serial.serial_for_url(port, baud, timeout=0.05)
        self.buffer = b''
        self.is_ble = False

    async def send(self, text):
        self.port.write(text.encode())

    async def read_line(self, timeout_s):
        """1 行読む(timeout_s 秒で来なければ None)"""
        end = time.time() + timeout_s
        while time.time() < end:
            if b'\n' in self.buffer:
                line, self.buffer = self.buffer.split(b'\n', 1)
                return line.decode(errors='replace').strip()
            self.buffer += self.port.read(256)
            await asyncio.sleep(0)
        return None

    async def close(self):
        self.port.close()


class BleLink:
    """無線(BLE の Nordic UART Service)でつなぐ"""

    def __init__(self):
        self.lines = asyncio.Queue()
        self.buffer = b''
        self.client = None
        self.is_ble = True

    async def open(self, name):
        from bleak import BleakClient, BleakScanner
        print(f'{name} を探しています…')
        device = await BleakScanner.find_device_by_name(name, timeout=10.0)
        if device is None:
            sys.exit(f'{name} が見つからない(機体の電源、BLE の LED のゆっくり点滅を確かめる)')
        self.client = BleakClient(device)
        await self.client.connect()
        await self.client.start_notify(NUS_TX, self._on_notify)
        print('つながりました')

    def _on_notify(self, _sender, data):
        """機体から届いた分を行に区切って、列に入れる"""
        self.buffer += bytes(data)
        while b'\n' in self.buffer:
            line, self.buffer = self.buffer.split(b'\n', 1)
            self.lines.put_nowait(line.decode(errors='replace').strip())

    async def send(self, text):
        data = text.encode()
        size = self.client.mtu_size - 3            # 1 回に送れる大きさ
        for i in range(0, len(data), size):
            await self.client.write_gatt_char(NUS_RX, data[i:i + size], response=False)

    async def read_line(self, timeout_s):
        try:
            return await asyncio.wait_for(self.lines.get(), timeout_s)
        except asyncio.TimeoutError:
            return None

    async def close(self):
        await self.client.disconnect()


async def wait_for(link, wanted, timeout_s):
    """wanted で始まる行か、#ERR の行が来るまで待つ。来た行(なければ None)を返す。ほかの行は表示だけ"""
    end = time.time() + timeout_s
    while time.time() < end:
        line = await link.read_line(end - time.time())
        if line is None:
            return None
        if line.startswith(wanted) or line.startswith('#ERR'):
            return line
        if line:
            print('  (機体)', line)
    return None


async def drain(link):
    """たまっている返事を読み捨てる(送り直す前に。古い #ERR を新しい返事とまちがえないように)"""
    while await link.read_line(0.3) is not None:
        pass


async def enter_bootloader(link, header):
    """ブートローダに入れて、`fw begin` を受けてもらう(手順 1〜3)"""
    await link.send(header)
    reply = await wait_for(link, '#', 1.5)
    if reply == '#OK fw begin':
        return True                                   # もうブートローダにいた
    if reply is None or reply.startswith('#ERR'):
        if reply is not None and 'busy' in reply:
            sys.exit('機体が走っている。止まってから、もう一度')
        if not link.is_ble:
            sys.exit('返事がない。有線では @flash が使えないので、機体の電源を入れ直してから、すぐにもう一度動かす'
                     '(プログラムが壊れていれば、ブートローダが待っている)')
        print('返事がないので @flash でブートローダに入れます')
        await link.send('@flash\n')
        reply = await wait_for(link, '#BOOT ready', 3.0)
    elif not reply.startswith('#BOOT ready'):
        reply = await wait_for(link, '#BOOT ready', 3.0)
    if reply is None or not reply.startswith('#BOOT ready'):
        sys.exit('ブートローダが返事をしない')
    print('ブートローダに入りました。消しています…')
    await link.send(header)
    reply = await wait_for(link, '#OK fw begin', 10.0)
    if reply != '#OK fw begin':
        sys.exit(f'fw begin がうまくいかない: {reply}')
    return True


async def send_image(link, image):
    """中身を 4KB ずつ送る。「#OK fw <位置>」が来なければ、その 4KB を送り直す"""
    position = 0
    while position < len(image):
        # この 4KB の区切りを越えるまでの行を作る(ブートローダと同じ数え方)
        lines = []
        end = position
        while end < len(image):
            chunk = image[end:end + LINE_BYTES]
            lines.append(f'fw {end} {base64.b64encode(chunk).decode()}\n')
            end = end + len(chunk)
            if end // ACK_EVERY > position // ACK_EVERY:
                break
        for attempt in range(3):
            for line in lines:
                await link.send(line)
            reply = await wait_for(link, f'#OK fw {end}', 2.0)
            if reply == f'#OK fw {end}':
                break
            print(f'  {position} から送り直し({reply})')
            await drain(link)
        else:
            sys.exit('送り直しても返事がない')
        position = end
        print(f'\r  {position * 100 // len(image)}%  ({position} / {len(image)} バイト)', end='', flush=True)
    print()


async def main():
    parser = argparse.ArgumentParser(description='STM32 のプログラムをブートローダで書き込む')
    parser.add_argument('bin', help='書くプログラム(.bin。0x08010000 から始まるもの)')
    parser.add_argument('--ble', nargs='?', const='KOGUMA-MK4', help='無線で(名前。省くと KOGUMA-MK4)')
    parser.add_argument('--port', help='有線で(COM5、/dev/ttyACM0 など)')
    args = parser.parse_args()
    image = open(args.bin, 'rb').read()
    crc = zlib.crc32(image)
    header = f'fw begin {len(image)} {crc:08x}\n'
    print(f'{args.bin}: {len(image)} バイト、CRC32 {crc:08x}')

    if args.ble:
        link = BleLink()
        await link.open(args.ble)
    elif args.port:
        link = SerialLink(args.port)
    else:
        sys.exit('--ble か --port を付ける')

    start = time.time()
    await enter_bootloader(link, header)
    await send_image(link, image)
    await link.send('fw end\n')
    reply = await wait_for(link, '#OK fw end', 10.0)
    if reply != '#OK fw end':
        sys.exit(f'最後の確かめで失敗: {reply}(もう一度動かせば書き直せる)')
    print(f'書けました({time.time() - start:.1f} 秒)。走るプログラムが動き出します')
    await link.close()


if __name__ == '__main__':
    asyncio.run(main())
