/*
 * bench_mark.h
 * 測る区間の印。g_mark[] は QEMU のプラグイン(plugin/trace_plugin.c)が見張る番地に置く。
 * BENCH_BEGIN(id) から BENCH_END(id) までに実行した命令とメモリの読み書きが記録される。
 */
#ifndef BENCH_MARK_H
#define BENCH_MARK_H

#include <stdint.h>

extern volatile uint32_t g_mark[256];

#define BENCH_BEGIN(id) (g_mark[2 * (id)] = 1)
#define BENCH_END(id)   (g_mark[2 * (id) + 1] = 1)

void bench_puts(const char *text);
void bench_exit(int code);

/* DMA の配列(H725 では SRAM1・2、キャッシュしない所。docs/firmware_memory.md) */
#define DMA_BUF __attribute__((section(".dma_buf"), aligned(32)))
/* ログの配列(H725 では AXI SRAM) */
#define AXI_BUF __attribute__((section(".axi_buf")))

#endif
