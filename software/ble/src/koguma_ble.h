/*
 * koguma_ble.h — HY0020(nRF52832)のプログラムの、ファイルどうしで使う関数の一覧
 *
 * このプログラムは「STM32 の UART」と「PC の BLE(Nordic UART Service)」の橋渡しをする。
 * 中身は見ずにそのまま渡す。`@` で始まる行だけは、ここで処理する(docs/ble.md の 4.3)。
 *
 *   stm32_uart.c … STM32 との UART。行に区切る、PC からの行を送る、XON・XOFF、@flash のときの線の操作
 *   ble_link.c   … BLE。アドバタイズ、つながる・切れる、PC へ送る、名前
 *   at_lines.c   … `@` で始まる行の処理(STM32 から・PC から)
 *   main.c       … 起動の順番
 */
#ifndef KOGUMA_BLE_H
#define KOGUMA_BLE_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

/* ---- stm32_uart.c ---- */

/* UART とピン(NRST・UART_RX を見るピン)を使えるようにし、送る・受けるのスレッドを動かす */
int stm32_uart_start(void);

/* PC から届いたデータを、STM32 に送る待ちの列に入れる(行に区切るのは送る側でやる)。入りきらなかった分は捨てて、捨てたバイト数を返す */
size_t stm32_uart_queue_from_pc(const uint8_t *data, size_t length);

/* nRF52832 が作った 1 行(`@link up` など、改行を含めて渡す)を STM32 に送る */
void stm32_uart_send_own_line(const char *line);

/* STM32 の NRST を 10ms L にする(@reset) */
void stm32_reset(void);

/* STM32 をブートローダの書き込みの待ちに入れる(@flash。docs/ble.md の 6.2) */
void stm32_enter_bootloader(void);

/* ---- ble_link.c ---- */

/* BLE を動かし、アドバタイズを始める */
int ble_link_start(void);

/* PC とつながっているか */
bool ble_link_is_connected(void);

/* STM32 から届いた 1 行(改行を含む)を、PC へ送る待ちの列に入れる。つながっていなければ捨てる */
void ble_link_queue_to_pc(const uint8_t *line, size_t length);

/* PC へ送る待ちの列が、どれだけ埋まっているか(0〜100 %)。XON・XOFF に使う */
int ble_link_queue_fill_percent(void);

/* 電波を止める(true)・戻す(false)(@quiet on・off) */
void ble_link_set_quiet(bool quiet);

/* アドバタイズの名前を変えて、Flash に残す(@name) */
void ble_link_set_name(const char *name);

/* ---- at_lines.c ---- */

/* STM32 から届いた `@` の行を処理する(行の終わりの改行は付いていてもよい) */
void at_line_from_stm32(const char *line);

/* PC から届いた `@` の行を処理する */
void at_line_from_pc(const char *line);

#endif
