/*
 * uart.c
 * PC・BLE との通信(USART1。PB6 TX → STLINK の仮想 COM ポートと HY0020、PB7 RX ← TP1 と HY0020)
 * ToraNeko.Mk3 の App/drv/uart.c から。MK4 では DMA を使わず割り込みで送り、受けるのを足した(2026-11-28)
 *
 * ■ 送る(ToraNeko と同じ考え)
 * UART は 1 文字送るのに約 87µs(115200bps)かかる。送り終わるまで待っていると、制御の処理が遅れてしまう。
 *   1. uart_write() は、送りたい文字を「送信待ちバッファ」に入れるだけで、すぐに戻る
 *   2. HAL_UART_Transmit_IT() が、バッファの文字を 1 文字ずつ割り込みで UART に渡す(CPU はそのあいだ別のことをする)
 *   3. 渡し終わると HAL_UART_TxCpltCallback() が呼ばれるので、残りがあれば続きを送る
 * ToraNeko は 2 を DMA でしていた。H562 の DMA(GPDMA)は設定が難しいので、割り込みにした。
 * 1 回に渡すのは UART_SEND_CHUNK 文字まで(下の XOFF が来たとき、すぐ止まれるように)。
 *
 * ■ 受ける(MK4 で足した)
 * HAL_UART_Receive_IT() で 1 文字ずつ受け、HAL_UART_RxCpltCallback() で「受信バッファ」(リングバッファ)に入れて、
 * 次の 1 文字を受ける準備をする。メインの処理(sys/cmd.c)が uart_read_char() で 1 文字ずつ取り出す。
 *
 * ■ stop(走っているあいだも止められるように)
 * 走っているあいだ、メインの処理は走る手順の中にいて、受けた行を読まない。そこで、受けた 1 文字ごとに(割り込みの中で)
 * 「今の行が stop だけか」を見て、そうなら印を立てる。4kHz の処理(sys/scheduler.c)が uart_take_stop_request() で
 * 印を見て、モーターを止める。stop の行は、ほかの行と同じく受信バッファにも入る(sys/cmd.c が #OK stop を返す)。
 *
 * ■ XON・XOFF(docs/ble.md の 4.4)
 * BLE の HY0020 は、PC へ送りきれずにたまってくると XOFF(0x13)を送ってくる。来たら送るのを止め、
 * XON(0x11)が来たら続ける。この 2 文字は受信バッファには入れない(テキストには出てこない文字)。
 * 有線のときは来ないので、そのまま流れる。
 *
 * ■ リングバッファ
 * 配列を輪のように使う。書き込み位置と読み出し位置があり、どちらも配列の最後まで進んだら 0 に戻る。
 * 2 つが同じ位置なら空。「書き込み位置の次が読み出し位置」なら一杯(1 文字ぶんは使わない)。
 *
 * ■ 割り込み禁止
 * バッファの位置は、通常の処理と割り込みの両方から書き換える。途中で割り込みが入って
 * 同時に書き換えると壊れるので、書き換えている間だけ割り込みを禁止する。
 *   - 禁止する前の状態を覚えておき、終わったら元に戻す(すでに禁止されている場所から呼ばれても、
 *     勝手に許可しないため。例: 割り込みを禁止した中で printf を呼んだとき)
 *   - 長い文字列でも、禁止するのは 16 文字ずつにする(20kHz・4kHz の処理を長く待たせないため)
 *
 * ■ printf は割り込みの中で使わない
 * printf(newlib)は割り込みの中から呼ぶことを考えて作られていない。割り込みの中でログを出すときは
 * uart_write() を直接使う。
 */
#include "drv/uart.h"

#include <stdbool.h>
#include <stdio.h>

#include "usart.h"

#define UART_BUF_SIZE 4096      /* 送信待ちバッファの大きさ [文字]。115200bps で約 0.36 秒分 */
#define UART_RX_BUF_SIZE 1024   /* 受信バッファの大きさ [文字](1 行は長くても 300 文字くらい) */
#define UART_CHUNK_SIZE 16      /* 割り込みを禁止して一度に入れる文字数 */
#define UART_SEND_CHUNK 64      /* HAL に一度に渡す文字数の上限 */
#define CHAR_XON  0x11          /* 送ってよい */
#define CHAR_XOFF 0x13          /* 送るのを止めて */

static uint8_t s_buf[UART_BUF_SIZE];
static uint8_t s_rx_buf[UART_RX_BUF_SIZE];
static uint8_t s_rx_char;  /* HAL が 1 文字を受ける置き場所 */

/* 下の変数は、通常の処理と割り込みの両方から読み書きするので volatile を付ける
 * (volatile: コンパイラに「いつ書き換わるかわからないので、毎回メモリから読むこと」と伝える) */
static volatile uint32_t s_write_pos = 0;     /* 次に文字を入れる位置 */
static volatile uint32_t s_send_pos = 0;      /* 次に送る文字の位置 */
static volatile uint32_t s_sending_len = 0;   /* 送信中の文字数。0 なら止まっている */
static volatile uint32_t s_dropped_count = 0; /* バッファが一杯で捨てた文字数(累計) */
static volatile bool s_paused = false;        /* XOFF が来て、送るのを止めているか */
static volatile uint32_t s_rx_write_pos = 0;  /* 受信バッファの、次に入れる位置(割り込みが進める) */
static volatile uint32_t s_rx_read_pos = 0;   /* 受信バッファの、次に取り出す位置(メインの処理が進める) */
static volatile uint32_t s_rx_dropped_count = 0;  /* 受信バッファが一杯で捨てた文字数(累計) */
static volatile uint32_t s_rx_error_count = 0;    /* 受けるときのエラー(取りこぼしなど)の回数(累計) */
static volatile int s_line_length = 0;            /* 今の行の、ここまでの文字数(stop を見つけるため) */
static volatile bool s_line_is_stop = true;       /* 今の行が、ここまで "stop" の始めと同じか */
static volatile bool s_stop_request = false;      /* stop の行を受けた印 */

/* 送信が止まっていて、送る文字が残っていれば、送信を始める。
 * 割り込みを禁止した状態で呼ぶこと */
static void start_sending(void)
{
  if (s_sending_len != 0) {
    return;  /* 送信中。終わったら HAL_UART_TxCpltCallback からまた呼ばれる */
  }
  if (s_paused) {
    return;  /* XOFF が来ている。XON が来たら、また呼ばれる */
  }
  if (s_send_pos == s_write_pos) {
    return;  /* 送る文字がない */
  }

  /* HAL は配列の連続した範囲しか送れないので、送る範囲が配列の最後をまたぐときは、
   * まず配列の最後までを送る。残り(配列の先頭側)は、送り終わったあとに送る */
  uint32_t len;
  if (s_write_pos > s_send_pos) {
    len = s_write_pos - s_send_pos;
  } else {
    len = UART_BUF_SIZE - s_send_pos;
  }
  if (len > UART_SEND_CHUNK) {
    len = UART_SEND_CHUNK;
  }

  s_sending_len = len;
  if (HAL_UART_Transmit_IT(&huart1, &s_buf[s_send_pos], len) != HAL_OK) {
    s_sending_len = 0;  /* 送信を始められなかった。次の uart_write でやり直す */
  }
}

/* 次の 1 文字を受ける準備をする(受けたら HAL_UART_RxCpltCallback が呼ばれる) */
static void start_receiving(void)
{
  if (HAL_UART_Receive_IT(&huart1, &s_rx_char, 1) != HAL_OK) {
    s_rx_error_count = s_rx_error_count + 1;
  }
}

/* 起動時に呼ぶ */
void uart_init(void)
{
  /* printf は通常、文字を溜めてからまとめて出す。ここではすぐ uart_write に渡すように設定する
   * (溜める処理はこのファイルのバッファで行う)。
   * こうすると printf は 1 文字ずつ _write を呼ぶ(1 回の printf で 20〜30 回)が、1 回あたりは
   * バッファに 1 文字入れるだけなので軽い。行ごとに溜める設定(_IOLBF)にすると、改行が来るまで
   * 送られない文字が残ったり、printf 用の共通のバッファを割り込みと取り合ったりするので使わない */
  setvbuf(stdout, NULL, _IONBF, 0);
  start_receiving();
}

/* 文字を最大 count 文字、送信待ちバッファに入れる。割り込みを禁止した状態で呼ぶこと。
 * バッファが一杯で入らなかった文字は捨てて数える */
static void put_chars(const uint8_t *data, uint32_t count)
{
  for (uint32_t i = 0; i < count; i++) {
    uint32_t next_pos = s_write_pos + 1;
    if (next_pos >= UART_BUF_SIZE) {
      next_pos = 0;
    }
    if (next_pos == s_send_pos) {
      /* バッファが一杯。残りの文字は捨てる */
      s_dropped_count = s_dropped_count + (count - i);
      return;
    }
    s_buf[s_write_pos] = data[i];
    s_write_pos = next_pos;
  }
}

/* 文字を送信待ちバッファに入れる。すぐに戻る(送信の完了は待たない)。割り込みの中から呼んでもよい */
void uart_write(const uint8_t *data, uint32_t len)
{
  uint32_t done = 0;  /* 入れ終わった文字数 */
  while (done < len) {
    uint32_t count = len - done;
    if (count > UART_CHUNK_SIZE) {
      count = UART_CHUNK_SIZE;
    }

    /* 割り込みを禁止する前の状態(PRIMASK)を覚えておき、終わったら元に戻す */
    uint32_t primask = __get_PRIMASK();
    __disable_irq();
    put_chars(&data[done], count);
    start_sending();
    __set_PRIMASK(primask);

    done = done + count;
  }
}

/* 送信待ちバッファの空き [文字]。
 * s_send_pos は送信完了の割り込みで進む(空きが増える)。読んでいるあいだに進んでも、
 * 空きを少なめに数えるだけなので困らない(割り込みは禁止しない) */
static uint32_t get_free_count(void)
{
  uint32_t write_pos = s_write_pos;
  uint32_t send_pos = s_send_pos;
  uint32_t used;
  if (write_pos >= send_pos) {
    used = write_pos - send_pos;
  } else {
    used = UART_BUF_SIZE - send_pos + write_pos;
  }
  /* バッファは「書き込み位置の次が送信位置」になったら一杯(1 文字ぶんは使わない) */
  return UART_BUF_SIZE - 1 - used;
}

/* 送信待ちバッファに count 文字ぶんの空きができるまで待つ。
 * 出力(迷路・走行ログ)のように、たくさんの文字を続けて送るときに、
 * バッファが一杯になって文字を捨てないように、1 行ずつ書く前に呼ぶ。
 * 割り込みの中から呼んではいけない(送信完了の割り込みが来ないと、空きが増えないため) */
void uart_wait_free(uint32_t count)
{
  while (get_free_count() < count) {
    /* 送り終わって、空きが増えるのを待つ(XOFF のあいだは XON が来るまで待つ) */
  }
}

/* バッファが一杯で捨てた文字数(累計)。0 でなければ、ログの量が多すぎる */
uint32_t uart_get_dropped_count(void)
{
  return s_dropped_count;
}

/* 受信バッファから 1 文字取り出す。あれば *ch に入れて true、なければ false。メインの処理から呼ぶ */
bool uart_read_char(uint8_t *ch)
{
  if (s_rx_read_pos == s_rx_write_pos) {
    return false;
  }
  *ch = s_rx_buf[s_rx_read_pos];
  uint32_t next_pos = s_rx_read_pos + 1;
  if (next_pos >= UART_RX_BUF_SIZE) {
    next_pos = 0;
  }
  s_rx_read_pos = next_pos;
  return true;
}

/* 受信バッファが一杯で捨てた文字数と、受けるときのエラーの回数(累計。動作確認用) */
uint32_t uart_get_rx_dropped_count(void)
{
  return s_rx_dropped_count;
}

uint32_t uart_get_rx_error_count(void)
{
  return s_rx_error_count;
}

/* 今の行が "stop" かを 1 文字ずつ調べる(割り込みの中。先頭のコメントの「stop」) */
static void check_stop_line(uint8_t ch)
{
  const char stop_text[4] = {'s', 't', 'o', 'p'};
  if (ch == '\n' || ch == '\r') {
    if (s_line_is_stop && s_line_length == 4) {
      s_stop_request = true;
    }
    s_line_length = 0;
    s_line_is_stop = true;
    return;
  }
  if (s_line_length >= 4 || ch != stop_text[s_line_length]) {
    s_line_is_stop = false;
  }
  s_line_length = s_line_length + 1;
}

/* stop の行を受けていたら true(印は消す)。4kHz の処理から呼ぶ */
bool uart_take_stop_request(void)
{
  if (!s_stop_request) {
    return false;
  }
  s_stop_request = false;
  return true;
}

/* 受けた 1 文字を処理する(割り込みの中)。XON・XOFF なら送るのを止める・続ける。ほかは受信バッファに入れる */
static void on_char_received(uint8_t ch)
{
  if (ch == CHAR_XOFF) {
    s_paused = true;
    return;
  }
  if (ch == CHAR_XON) {
    s_paused = false;
    start_sending();
    return;
  }
  check_stop_line(ch);
  uint32_t next_pos = s_rx_write_pos + 1;
  if (next_pos >= UART_RX_BUF_SIZE) {
    next_pos = 0;
  }
  if (next_pos == s_rx_read_pos) {
    s_rx_dropped_count = s_rx_dropped_count + 1;  /* 一杯。捨てる */
    return;
  }
  s_rx_buf[s_rx_write_pos] = ch;
  s_rx_write_pos = next_pos;
}

/* 1 文字受けたときに HAL から呼ばれる(割り込みの中) */
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
  if (huart->Instance != USART1) {
    return;
  }
  on_char_received(s_rx_char);
  start_receiving();
}

/* 送信が終わったときに HAL から呼ばれる(割り込みの中) */
void HAL_UART_TxCpltCallback(UART_HandleTypeDef *huart)
{
  if (huart->Instance != USART1) {
    return;
  }

  uint32_t primask = __get_PRIMASK();
  __disable_irq();

  /* 送り終わった分だけ送信位置を進める */
  s_send_pos = s_send_pos + s_sending_len;
  if (s_send_pos >= UART_BUF_SIZE) {
    s_send_pos = 0;
  }
  s_sending_len = 0;

  /* 残りがあれば続きを送る */
  start_sending();

  __set_PRIMASK(primask);
}

/* UART でエラー(受けた文字を読む前に次が来た、ノイズなど)が起きたときに HAL から呼ばれる(割り込みの中)。
 * HAL は受けるのを止めるので、もう一度受ける準備をする。送信中なら送信も止まっているので、
 * 送信中だった分は捨てて(捨てた数に数える)、残りの送信を続ける。同じ分を送り直さないのは、
 * エラーが続いたときに割り込みが止まらなくなるのを防ぐため */
void HAL_UART_ErrorCallback(UART_HandleTypeDef *huart)
{
  if (huart->Instance != USART1) {
    return;
  }

  uint32_t primask = __get_PRIMASK();
  __disable_irq();

  s_rx_error_count = s_rx_error_count + 1;
  if (huart->gState == HAL_UART_STATE_READY && s_sending_len != 0) {
    s_dropped_count = s_dropped_count + s_sending_len;
    s_send_pos = s_send_pos + s_sending_len;
    if (s_send_pos >= UART_BUF_SIZE) {
      s_send_pos = 0;
    }
    s_sending_len = 0;
    start_sending();
  }
  if (huart->RxState == HAL_UART_STATE_READY) {
    start_receiving();
  }

  __set_PRIMASK(primask);
}

/* printf が文字を出すときに呼ぶ関数。
 * Core/Src/syscalls.c にも同じ名前の関数があるが、そちらは「ほかに定義があればそちらを使う」
 * 指定(weak)になっているので、こちらが使われる */
int _write(int file, char *ptr, int len)
{
  (void)file;  /* 使わない引数(警告を消すため) */
  /* printf からは char の並びで来るが、uart_write は uint8_t(0〜255 の数)の並びで受け取るので、型を読み替えて渡す。
   * どちらも 1 文字 1 バイトなので、中身は変わらない */
  uart_write((const uint8_t *)ptr, len);
  return len;
}
