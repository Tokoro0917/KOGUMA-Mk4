/*
 * trace_plugin.c
 * QEMU TCG プラグイン: 印を付けた区間だけ、実行した命令の番地と、メモリの読み書き(番地・大きさ)を記録する。
 *
 * 区間の印: ベンチのプログラムが、決まった番地 (markaddr + 4 * (2 * id)) に書くと区間 id の始まり、
 * (markaddr + 4 * (2 * id + 1)) に書くと終わり。
 * 出力 (out=ファイル):
 *   B <id>            区間の始まり
 *   I <pc>            命令を 1 つ実行した (16 進)
 *   M <addr> <L|S> <bytes>   直前の命令のメモリの読み書き
 *   E <id>            区間の終わり
 *
 * 使い方: qemu-system-arm ... -plugin ./libtrace.so,markaddr=0x20000000,out=trace.txt
 */
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "qemu-plugin.h"

QEMU_PLUGIN_EXPORT int qemu_plugin_version = QEMU_PLUGIN_VERSION;

static uint64_t mark_addr = 0;
static FILE *out_file = NULL;
static int active = 0;

static void on_insn(unsigned int vcpu, void *udata)
{
  (void)vcpu;
  if (active) {
    fprintf(out_file, "I %" PRIx64 "\n", (uint64_t)(uintptr_t)udata);
  }
}

static void on_mem(unsigned int vcpu, qemu_plugin_meminfo_t info, uint64_t vaddr, void *udata)
{
  (void)vcpu;
  (void)udata;
  int is_store = qemu_plugin_mem_is_store(info);
  if (is_store && vaddr >= mark_addr && vaddr < mark_addr + 0x400) {
    unsigned idx = (unsigned)((vaddr - mark_addr) / 4);
    unsigned id = idx / 2;
    if ((idx % 2) == 0) {
      active = 1;
      fprintf(out_file, "B %u\n", id);
    } else {
      active = 0;
      fprintf(out_file, "E %u\n", id);
    }
    return;
  }
  if (active) {
    unsigned bytes = 1u << qemu_plugin_mem_size_shift(info);
    fprintf(out_file, "M %" PRIx64 " %c %u\n", vaddr, is_store ? 'S' : 'L', bytes);
  }
}

static void on_tb_trans(qemu_plugin_id_t id, struct qemu_plugin_tb *tb)
{
  (void)id;
  size_t n = qemu_plugin_tb_n_insns(tb);
  for (size_t i = 0; i < n; i++) {
    struct qemu_plugin_insn *insn = qemu_plugin_tb_get_insn(tb, i);
    uint64_t pc = qemu_plugin_insn_vaddr(insn);
    qemu_plugin_register_vcpu_insn_exec_cb(insn, on_insn, QEMU_PLUGIN_CB_NO_REGS, (void *)(uintptr_t)pc);
    qemu_plugin_register_vcpu_mem_cb(insn, on_mem, QEMU_PLUGIN_CB_NO_REGS, QEMU_PLUGIN_MEM_RW, NULL);
  }
}

static void on_plugin_exit(qemu_plugin_id_t id, void *p)
{
  (void)id;
  (void)p;
  if (out_file) {
    fclose(out_file);
  }
}

QEMU_PLUGIN_EXPORT int qemu_plugin_install(qemu_plugin_id_t id, const qemu_info_t *info, int argc, char **argv)
{
  (void)info;
  const char *out_name = "trace.txt";
  for (int i = 0; i < argc; i++) {
    if (strncmp(argv[i], "markaddr=", 9) == 0) {
      mark_addr = strtoull(argv[i] + 9, NULL, 0);
    } else if (strncmp(argv[i], "out=", 4) == 0) {
      out_name = argv[i] + 4;
    }
  }
  out_file = fopen(out_name, "w");
  if (!out_file) {
    return -1;
  }
  setvbuf(out_file, NULL, _IOFBF, 1 << 20);
  qemu_plugin_register_vcpu_tb_trans_cb(id, on_tb_trans);
  qemu_plugin_register_atexit_cb(id, on_plugin_exit, NULL);
  return 0;
}
