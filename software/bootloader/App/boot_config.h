/*
 * boot_config.h — ブートローダの決まった数(番地・大きさ・時間)。docs/ble.md の 6 章
 *
 * Flash(バンク 1、8KB のセクタ):
 *   0x08000000〜0x0800FFFF(64KB、セクタ 0〜7): このブートローダ。自分では消さない
 *   0x08010000〜0x0807FFFF(448KB、セクタ 8〜63): 走るプログラム(先頭はベクタテーブル)
 */
#ifndef BOOT_CONFIG_H
#define BOOT_CONFIG_H

#include <stdint.h>

#define APP_BASE 0x08010000U                 /* 走るプログラムの先頭(ベクタテーブル) */
#define APP_MAX_SIZE (448U * 1024U)          /* 走るプログラムの大きさの上限 */
#define APP_FIRST_SECTOR 8U                  /* 走るプログラムの最初のセクタの番号(バンク 1) */
#define SECTOR_SIZE 8192U                    /* セクタの大きさ(H562 は 8KB) */
#define PROGRAM_UNIT 16U                     /* 1 回に書く大きさ(H562 は 128 ビット = 16 バイト) */
#define FIRST_BLOCK_SIZE 1024U               /* 最後に書く先頭の部分(ベクタテーブルを含む)。boot_flash.c の説明 */

#define RAM_START 0x20000000U                /* RAM(SRAM1〜3、640KB)の範囲。走るプログラムのスタックの初めの値を確かめる */
#define RAM_END 0x200A0000U

/* 走るプログラムが「書き込みへ」を頼むときに、TAMP のバックアップレジスタ 0 に書く印("FLSH")。
 * バックアップレジスタはリセットしても消えない */
#define BOOT_REQUEST_MAGIC 0x464C5348U

#define UART_RX_LOW_CHECK_MS 1U              /* 起動して、UART_RX がこの時間ずっと L なら書き込みの待ち(nRF の @flash) */
#define WAIT_TIMEOUT_MS 10000U               /* 書き込みの待ちで、この時間なにも来なければ走るプログラムへ(正しければ) */
#define ACK_EVERY_BYTES 4096U                /* この大きさごとに「#OK fw <位置>」を返す */
#define LINE_MAX 400U                        /* 受ける 1 行の長さの上限(fw の行は約 270 文字) */

#endif
