"""MK4のピンの割り当て(docs/pinmap.md)が、STM32H725RG(VFQFPN68)で本当に使えるかを確かめる

STの公開しているピン定義(STM32CubeMXと同じデータ)を使う:
  git clone --depth 1 https://github.com/STMicroelectronics/STM32_open_pin_data
  python3 docs/calc/check_pins.py STM32_open_pin_data/mcu/STM32H725RGVx.xml

確かめること:
  - ピンがこのパッケージにあるか
  - そのピンに、割り当てた機能(信号)があるか
  - 同じピンを2回使っていないか
  - 使っていないIOの一覧
"""
import sys
import xml.etree.ElementTree as ET
from collections import Counter

# (ピン, 信号 / 'GPIO_Output' / 'GPIO_Input' / 'RCC_OSC_IN' など, ネット名, 用途)
ASSIGN = [
    # モーター(MP6551 × 2)。IN1・IN2の両方をPWMにして、止めている側を0にする(減衰はどちらの向きも下側のFET)
    ('PA8',  'TIM1_CH1',  'MOT_L_IN1', '左モーター IN1(PWM)'),
    ('PA9',  'TIM1_CH2',  'MOT_L_IN2', '左モーター IN2(PWM)'),
    ('PA10', 'TIM1_CH3',  'MOT_R_IN1', '右モーター IN1(PWM)'),
    ('PA11', 'TIM1_CH4',  'MOT_R_IN2', '右モーター IN2(PWM)'),
    ('PB2',  'GPIO_Output', 'MOT_EN', 'ドライバ2個のEN1・EN2(共通。Lでスリープ)'),
    ('PC9',  'GPIO_Input',  'MOT_nFAULT', 'ドライバ2個のnFAULT(オープンドレインを共通に)'),
    ('PC4',  'ADC2_INP4',  'MOT_L_CM1', '左モーターの電流(OUT1側の下側FET)'),
    ('PC5',  'ADC2_INP8',  'MOT_L_CM2', '左モーターの電流(OUT2側の下側FET)'),
    ('PA4',  'ADC2_INP18', 'MOT_R_CM1', '右モーターの電流(OUT1側の下側FET)'),
    ('PA5',  'ADC2_INP19', 'MOT_R_CM2', '右モーターの電流(OUT2側の下側FET)'),
    # エンコーダ(AS5047P × 2、SPI2。IMUのSPI3とはSPIのモードが違うのでバスを分ける)(2026-10-17)
    ('PA12', 'SPI2_SCK',  'ENC_SCK',   'エンコーダ SPIクロック'),
    ('PB14', 'SPI2_MISO', 'ENC_MISO',  'エンコーダ MISO'),
    ('PB15', 'SPI2_MOSI', 'ENC_MOSI',  'エンコーダ MOSI'),
    ('PC6',  'GPIO_Output', 'ENC_L_CS', '左エンコーダ チップセレクト'),
    ('PC7',  'GPIO_Output', 'ENC_R_CS', '右エンコーダ チップセレクト'),
    # 壁センサ(MK3と同じ回路)
    ('PC0',  'ADC1_INP10', 'WALL_FL',  '壁センサ 左前'),
    ('PC1',  'ADC1_INP11', 'WALL_L',   '壁センサ 左'),
    ('PA6',  'ADC1_INP3',  'WALL_R',   '壁センサ 右'),
    ('PA7',  'ADC1_INP7',  'WALL_FR',  '壁センサ 右前'),
    ('PB4(NJTRST)', 'GPIO_Output', 'WALL_LED_L', '壁センサの発光 左(NJU6080のPWM端子)'),
    ('PB5',  'GPIO_Output', 'WALL_LED_R', '壁センサの発光 右(NJU6080のPWM端子)'),
    # 電源・吸引・ブザー
    ('PB1',  'ADC2_INP5', 'BATT',      '電池の電圧(分圧)'),
    ('PB8',  'TIM16_CH1', 'FAN_PWM',   '吸引ファン(PWM)'),
    ('PB0',  'ADC1_INP9', 'FAN_ISENSE', '吸引ファンの電流(シャント抵抗の電圧をRCで平均)'),
    ('PB9',  'TIM17_CH1', 'BUZZER',    'ブザー(PWM)'),
    # IMU(SPI3)
    ('PC10', 'SPI3_SCK',  'IMU_SCK',   'IMU SPIクロック'),
    ('PC11', 'SPI3_MISO', 'IMU_MISO',  'IMU MISO'),
    ('PC12', 'SPI3_MOSI', 'IMU_MOSI',  'IMU MOSI'),
    ('PA15(JTDI)', 'GPIO_Output', 'IMU_CS',  'IMU チップセレクト'),
    # 通信・デバッグ
    ('PB6',  'USART1_TX', 'UART_TX',   'PCへ(USBシリアル変換)'),
    ('PB7',  'USART1_RX', 'UART_RX',   'PCから'),
    ('PA13(JTMS/SWDIO)', 'DEBUG_JTMS-SWDIO', 'SWDIO', '書き込み・デバッグ'),
    ('PA14(JTCK/SWCLK)', 'DEBUG_JTCK-SWCLK', 'SWCLK', '書き込み・デバッグ'),
    # 表示・入力
    ('PA0',  'GPIO_Output', 'LED_MODE0', 'モード ビット0'),
    ('PA1',  'GPIO_Output', 'LED_MODE1', 'モード ビット1'),
    ('PA2',  'GPIO_Output', 'LED_MODE2', 'モード ビット2'),
    ('PA3',  'GPIO_Output', 'LED_NUM0',  'ナンバー ビット0'),
    ('PB10', 'GPIO_Output', 'LED_NUM1',  'ナンバー ビット1'),
    ('PB12', 'GPIO_Output', 'LED_NUM2',  'ナンバー ビット2'),
    ('PB13', 'GPIO_Output', 'LED_NUM3',  'ナンバー ビット3'),
    ('PC14-OSC32_IN', 'GPIO_Input', 'SW', 'スイッチ'),
    # 水晶(HSE)は付けない(2026-10-12)。内蔵のHSIからPLLで550MHzにする
]

# タイマのエンコーダモードで読むエンコーダ(A相, B相)の組。磁気式(SPI)にしたので今はない
ENCODERS = []


def main(path):
    ns = {'m': 'http://dummy.com'}
    root = ET.parse(path).getroot()
    pins = {}
    for p in root.findall('m:Pin', ns):
        if p.get('Type') == 'I/O':
            pins[p.get('Name')] = {s.get('Name') for s in p.findall('m:Signal', ns)}
    print(f"{root.get('RefName')} ({root.get('Package')}): I/O {len(pins)}本")

    ok = True
    used = Counter(a[0] for a in ASSIGN)
    for pin, n in used.items():
        if n > 1:
            print(f'NG: {pin} を{n}回使っている')
            ok = False

    for pin, sig, net, _ in ASSIGN:
        if pin not in pins:
            print(f'NG: {pin} はこのパッケージにない ({net})')
            ok = False
            continue
        if sig.startswith('GPIO_'):
            if 'GPIO' not in pins[pin]:
                print(f'NG: {pin} はGPIOにできない ({net})')
                ok = False
        elif sig not in pins[pin]:
            print(f'NG: {pin} に {sig} がない ({net})')
            ok = False

    sig_of = {net: sig for _, sig, net, _ in ASSIGN}
    for a, b in ENCODERS:
        ta, ca = sig_of[a].split('_')
        tb, cb = sig_of[b].split('_')
        if ta != tb or {ca, cb} != {'CH1', 'CH2'}:
            print(f'NG: {a}/{b} が同じタイマのCH1/CH2になっていない ({sig_of[a]}, {sig_of[b]})')
            ok = False

    # 同じタイマのチャンネルを2つの用途で使っていないか
    tch = Counter(s for _, s, _, _ in ASSIGN if s.startswith(('TIM', 'ADC')))
    for s, n in tch.items():
        if n > 1:
            print(f'NG: {s} を{n}か所で使っている')
            ok = False

    spare = [p for p in pins if p not in used]
    print(f'使う: {len(used)}本 / 残り: {len(spare)}本')
    for p in spare:
        extra = sorted(s for s in pins[p] if s.startswith(('ADC', 'TIM')) and 'EXTI' not in s)
        print(f'  残り {p}: {" ".join(extra[:6])}')
    print('結果: OK' if ok else '結果: NGあり')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1]))
