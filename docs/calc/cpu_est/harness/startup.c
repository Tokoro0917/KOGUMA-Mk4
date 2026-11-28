/*
 * startup.c
 * QEMU (mps2-an500 = Cortex-M7, mps2-an505 = Cortex-M33) で動かすための最小の起動コード。
 * - ベクタテーブル(初めのスタックの番地と Reset_Handler だけ使う)
 * - .data を写し、.bss を 0 にし、FPU を使えるようにしてから main を呼ぶ
 * - semihosting(bkpt 0xAB)で文字を出し、QEMU を終わらせる
 */
#include <stdint.h>

extern uint32_t _sidata, _sdata, _edata, _sbss, _ebss, _estack;
extern uint32_t _sdma, _edma, _saxi, _eaxi;
int main(void);

void Reset_Handler(void);
void Default_Handler(void);

__attribute__((section(".isr_vector"), used))
const void *const g_vectors[16] = {
  &_estack,
  (const void *)Reset_Handler,
  (const void *)Default_Handler,  /* NMI */
  (const void *)Default_Handler,  /* HardFault */
  (const void *)Default_Handler,  /* MemManage */
  (const void *)Default_Handler,  /* BusFault */
  (const void *)Default_Handler,  /* UsageFault */
  (const void *)Default_Handler,  /* SecureFault (M33) */
  0, 0, 0,
  (const void *)Default_Handler,  /* SVC */
  (const void *)Default_Handler,  /* DebugMon */
  0,
  (const void *)Default_Handler,  /* PendSV */
  (const void *)Default_Handler,  /* SysTick */
};

/* semihosting の呼び出し(QEMU の -semihosting で使える) */
static int semihost_call(int op, const void *arg)
{
  register int r0 __asm__("r0") = op;
  register const void *r1 __asm__("r1") = arg;
  __asm__ volatile("bkpt 0xAB" : "+r"(r0) : "r"(r1) : "memory");
  return r0;
}

void bench_puts(const char *text)
{
  semihost_call(0x04, text);  /* SYS_WRITE0 */
}

void bench_exit(int code)
{
  (void)code;
  semihost_call(0x18, (const void *)0x20026);    /* SYS_EXIT(32 ビットでは r1 に理由を直接入れる: ADP_Stopped_ApplicationExit) */
  while (1) {
  }
}

void Default_Handler(void)
{
  bench_puts("FAULT\n");
  bench_exit(3);
}

void Reset_Handler(void)
{
  uint32_t *src = &_sidata;
  uint32_t *dst = &_sdata;
  while (dst < &_edata) {
    *dst = *src;
    dst++;
    src++;
  }
  dst = &_sbss;
  while (dst < &_ebss) {
    *dst = 0;
    dst++;
  }
  dst = &_sdma;
  while (dst < &_edma) {
    *dst = 0;
    dst++;
  }
  dst = &_saxi;
  while (dst < &_eaxi) {
    *dst = 0;
    dst++;
  }
  /* FPU を使えるようにする(CPACR の CP10・CP11 を全部許す) */
  volatile uint32_t *cpacr = (volatile uint32_t *)0xE000ED88;
  *cpacr = *cpacr | (0xFu << 20);
  __asm__ volatile("dsb\n isb");
  int code = main();
  bench_exit(code);
}
