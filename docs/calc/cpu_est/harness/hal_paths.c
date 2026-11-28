/*
 * hal_paths.c
 * CubeMX の初めの作り(HAL)で割り込みを受けたときに通る道すじを、本物の HAL のコードで動かして測る。
 * レジスタは RAM の「にせのレジスタ」なので、割り込みの印(フラグ)は、呼ぶ前にベンチが自分で立てる。
 *   50 ADC の DMA の終わり(TC): HAL_DMA_IRQHandler → ADC_DMAConvCplt → HAL_ADC_ConvCpltCallback
 *   51 ADC の DMA の半分(HT):   HAL_DMA_IRQHandler → ADC_DMAHalfConvCplt → HAL_ADC_ConvHalfCpltCallback
 *   52 HAL_SPI_TransmitReceive_DMA(6 バイト)を始める
 *   53 SPI の受け側 DMA の終わり(TC) → SPI_DMATransmitReceiveCplt(EOT の割り込みを許す)
 *   54 SPI の受け側 DMA の半分(HT)
 *   55 SPI の送り側 DMA の終わり(TC)
 *   56 SPI の EOT の割り込み: HAL_SPI_IRQHandler → SPI_CloseTransfer → HAL_SPI_TxRxCpltCallback
 *   57 EXTI: HAL_GPIO_EXTI_IRQHandler → コールバック
 *   58 HAL_IncTick(SysTick、1kHz)
 *   59 LL で 4kHz の割り込みを起こす(NVIC_SetPendingIRQ)
 * コールバックの中身(20kHz の処理など)は bench.c の区間で別に測るので、ここでは「どの割り込みか」を調べるだけ。
 */
#include <stdint.h>

#include "bench_mark.h"

static void bench_puthex(uint32_t value)
{
  char text[12];
  const char *digits = "0123456789ABCDEF";
  for (int i = 0; i < 8; i++) {
    text[7 - i] = digits[value % 16];
    value = value / 16;
  }
  text[8] = 10;
  text[9] = 0;
  bench_puts(text);
}

#if defined(MK4_H7)
#include "stm32h7xx_hal.h"
#else
#include "stm32h5xx_hal.h"
#endif

extern uint16_t g_adc2_buffer[];
DMA_BUF static uint8_t s_spi_tx[8];
DMA_BUF static uint8_t s_spi_rx[8];

ADC_HandleTypeDef hadc2;
DMA_HandleTypeDef hdma_adc2;
SPI_HandleTypeDef hspi2;
DMA_HandleTypeDef hdma_spi2_rx;
DMA_HandleTypeDef hdma_spi2_tx;
volatile uint32_t g_callback_count = 0;

#if defined(MK4_H7)
uint32_t SystemCoreClock = 400000000;
uint32_t SystemD2Clock = 200000000;
#else
uint32_t SystemCoreClock = 250000000;
#endif

/* HAL のコールバック(CubeMX の作りでは、ここから MK4 の処理を呼ぶ) */
void HAL_ADC_ConvCpltCallback(ADC_HandleTypeDef *hadc)
{
  if (hadc->Instance == ADC2) {
    g_callback_count = g_callback_count + 1;
  }
}

void HAL_SPI_TxRxCpltCallback(SPI_HandleTypeDef *hspi)
{
  if (hspi->Instance == SPI2) {
    g_callback_count = g_callback_count + 1;
  }
}

#if defined(MK4_H7)
void HAL_GPIO_EXTI_Callback(uint16_t GPIO_Pin)
#else
void HAL_GPIO_EXTI_Rising_Callback(uint16_t GPIO_Pin)
#endif
{
  if (GPIO_Pin == GPIO_PIN_2) {
    g_callback_count = g_callback_count + 1;
  }
}

#if defined(MK4_H7)
/* H7: DMA の stream の割り込みの印を立てる(HAL が調べる LISR・HISR) */
static void set_dma_flag(DMA_HandleTypeDef *hdma, uint32_t flag_bit0)
{
  volatile uint32_t *isr = (volatile uint32_t *)hdma->StreamBaseAddress;  /* LISR か HISR(HAL の DMA_Base_Registers の先頭) */
  *isr = flag_bit0 << (hdma->StreamIndex & 0x1FU);
}
#define FLAG_TC 0x20U
#define FLAG_HT 0x10U

static void init_dma(DMA_HandleTypeDef *hdma, DMA_Stream_TypeDef *stream, uint32_t request, uint32_t direction,
                     uint32_t size, uint32_t mode)
{
  hdma->Instance = stream;
  hdma->Init.Request = request;
  hdma->Init.Direction = direction;
  hdma->Init.PeriphInc = DMA_PINC_DISABLE;
  hdma->Init.MemInc = DMA_MINC_ENABLE;
  hdma->Init.PeriphDataAlignment = size;
  hdma->Init.MemDataAlignment = size;
  hdma->Init.Mode = mode;
  hdma->Init.Priority = DMA_PRIORITY_HIGH;
  hdma->Init.FIFOMode = DMA_FIFOMODE_DISABLE;
  if (HAL_DMA_Init(hdma) != HAL_OK) {
    bench_puts("HAL_DMA_Init failed\n");
  }
}

static void setup(void)
{
  init_dma(&hdma_adc2, DMA1_Stream0, DMA_REQUEST_ADC2, DMA_PERIPH_TO_MEMORY, DMA_PDATAALIGN_HALFWORD, DMA_CIRCULAR);
  init_dma(&hdma_spi2_rx, DMA1_Stream1, DMA_REQUEST_SPI2_RX, DMA_PERIPH_TO_MEMORY, DMA_PDATAALIGN_BYTE, DMA_NORMAL);
  init_dma(&hdma_spi2_tx, DMA1_Stream2, DMA_REQUEST_SPI2_TX, DMA_MEMORY_TO_PERIPH, DMA_PDATAALIGN_BYTE, DMA_NORMAL);
}
#else
/* H5: GPDMA の channel の割り込みの印を立てる(HAL が調べる CSR) */
static void set_dma_flag(DMA_HandleTypeDef *hdma, uint32_t flag)
{
  hdma->Instance->CSR = flag;
  /* GPDMA 全体の「どの channel が割り込みを出しているか」(MISR)も立てる。HAL は最初にこれを見る */
  DMA_TypeDef *dma = (DMA_TypeDef *)((uint32_t)hdma->Instance & ~0xFFFU);
  dma->MISR = 1U << (((uint32_t)hdma->Instance & 0xFFFU) - 0x50U) / 0x80U;
  if (flag == DMA_FLAG_TC) {
    hdma->Instance->CBR1 = 0;  /* 本物は、送り終わると残りの数が 0 になる */
  }
}
#define FLAG_TC DMA_FLAG_TC
#define FLAG_HT DMA_FLAG_HT

static void init_dma(DMA_HandleTypeDef *hdma, DMA_Channel_TypeDef *channel, uint32_t request, uint32_t direction,
                     uint32_t width_src, uint32_t width_dest, uint32_t src_inc, uint32_t dest_inc)
{
  channel->CCR = 0;  /* にせのレジスタ: LL のベンチで立てた EN を消す(本物は DMA の終わりで 0 になる) */
  hdma->Instance = channel;
  hdma->Init.Request = request;
  hdma->Init.BlkHWRequest = DMA_BREQ_SINGLE_BURST;
  hdma->Init.Direction = direction;
  hdma->Init.SrcInc = src_inc;
  hdma->Init.DestInc = dest_inc;
  hdma->Init.SrcDataWidth = width_src;
  hdma->Init.DestDataWidth = width_dest;
  hdma->Init.Priority = DMA_HIGH_PRIORITY;
  hdma->Init.SrcBurstLength = 1;
  hdma->Init.DestBurstLength = 1;
  hdma->Init.TransferAllocatedPort = DMA_SRC_ALLOCATED_PORT0 | DMA_DEST_ALLOCATED_PORT1;
  hdma->Init.TransferEventMode = DMA_TCEM_BLOCK_TRANSFER;
  hdma->Init.Mode = DMA_NORMAL;
  if (HAL_DMA_Init(hdma) != HAL_OK) {
    bench_puts("HAL_DMA_Init failed\n");
  }
}

static void setup(void)
{
  init_dma(&hdma_adc2, GPDMA1_Channel0, GPDMA1_REQUEST_ADC2, DMA_PERIPH_TO_MEMORY,
           DMA_SRC_DATAWIDTH_HALFWORD, DMA_DEST_DATAWIDTH_HALFWORD, DMA_SINC_FIXED, DMA_DINC_INCREMENTED);
  init_dma(&hdma_spi2_rx, GPDMA1_Channel1, GPDMA1_REQUEST_SPI2_RX, DMA_PERIPH_TO_MEMORY,
           DMA_SRC_DATAWIDTH_BYTE, DMA_DEST_DATAWIDTH_BYTE, DMA_SINC_FIXED, DMA_DINC_INCREMENTED);
  init_dma(&hdma_spi2_tx, GPDMA1_Channel2, GPDMA1_REQUEST_SPI2_TX, DMA_MEMORY_TO_PERIPH,
           DMA_SRC_DATAWIDTH_BYTE, DMA_DEST_DATAWIDTH_BYTE, DMA_SINC_INCREMENTED, DMA_DINC_FIXED);
}
#endif

/* ADC2 を DMA で動かす(CubeMX の作りと同じに HAL_ADC_Start_DMA を使う) */
static void start_adc(void)
{
  __HAL_LINKDMA(&hadc2, DMA_Handle, hdma_adc2);
  hadc2.Instance = ADC2;
#if defined(MK4_H7)
  hadc2.Init.ConversionDataManagement = ADC_CONVERSIONDATA_DMA_CIRCULAR;
#else
  hadc2.Init.DMAContinuousRequests = ENABLE;
#endif
  hadc2.Init.ContinuousConvMode = DISABLE;
  hadc2.Init.Overrun = ADC_OVR_DATA_OVERWRITTEN;
  hadc2.State = HAL_ADC_STATE_READY;
  ADC2->ISR = ADC_ISR_ADRDY;          /* にせのレジスタ: 「準備ができた」にしておく */
  ADC2->CFGR = ADC_CFGR_EXTEN_0;      /* タイマーの合図で変換する */
  if (HAL_ADC_Start_DMA(&hadc2, (uint32_t *)g_adc2_buffer, 5) != HAL_OK) {
    bench_puts("HAL_ADC_Start_DMA failed\n");
  }
}

static void init_spi(void)
{
  hspi2.Instance = SPI2;
  hspi2.Init.Mode = SPI_MODE_MASTER;
  hspi2.Init.Direction = SPI_DIRECTION_2LINES;
  hspi2.Init.DataSize = SPI_DATASIZE_8BIT;
  hspi2.Init.CLKPolarity = SPI_POLARITY_HIGH;
  hspi2.Init.CLKPhase = SPI_PHASE_2EDGE;
  hspi2.Init.NSS = SPI_NSS_SOFT;
  hspi2.Init.BaudRatePrescaler = SPI_BAUDRATEPRESCALER_8;
  hspi2.Init.FirstBit = SPI_FIRSTBIT_MSB;
  hspi2.Init.TIMode = SPI_TIMODE_DISABLE;
  hspi2.Init.CRCCalculation = SPI_CRCCALCULATION_DISABLE;
  hspi2.Init.CRCPolynomial = 0x7;
  hspi2.Init.NSSPMode = SPI_NSS_PULSE_DISABLE;
  hspi2.Init.NSSPolarity = SPI_NSS_POLARITY_LOW;
  hspi2.Init.FifoThreshold = SPI_FIFO_THRESHOLD_01DATA;
  hspi2.Init.MasterSSIdleness = SPI_MASTER_SS_IDLENESS_00CYCLE;
  hspi2.Init.MasterInterDataIdleness = SPI_MASTER_INTERDATA_IDLENESS_00CYCLE;
  hspi2.Init.MasterReceiverAutoSusp = SPI_MASTER_RX_AUTOSUSP_DISABLE;
  hspi2.Init.MasterKeepIOState = SPI_MASTER_KEEP_IO_STATE_ENABLE;
  hspi2.Init.IOSwap = SPI_IO_SWAP_DISABLE;
  if (HAL_SPI_Init(&hspi2) != HAL_OK) {
    bench_puts("HAL_SPI_Init failed\n");
  }
  __HAL_LINKDMA(&hspi2, hdmarx, hdma_spi2_rx);
  __HAL_LINKDMA(&hspi2, hdmatx, hdma_spi2_tx);
}

void hal_paths_run(void)
{
  setup();
  start_adc();
  init_spi();

  for (int i = 0; i < 4; i++) {
    set_dma_flag(&hdma_adc2, FLAG_HT);
    BENCH_BEGIN(51);
    HAL_DMA_IRQHandler(&hdma_adc2);
    BENCH_END(51);
    set_dma_flag(&hdma_adc2, FLAG_TC);
    BENCH_BEGIN(50);
    HAL_DMA_IRQHandler(&hdma_adc2);
    BENCH_END(50);
  }

  for (int i = 0; i < 4; i++) {
    BENCH_BEGIN(52);
    HAL_StatusTypeDef status = HAL_SPI_TransmitReceive_DMA(&hspi2, s_spi_tx, s_spi_rx, 6);
    BENCH_END(52);
    if (status != HAL_OK) {
      bench_puts("HAL_SPI_TransmitReceive_DMA failed\n");
      bench_puthex(status);
      bench_puthex(hspi2.State);
      bench_puthex(hdma_spi2_rx.State);
      bench_puthex(hdma_spi2_tx.State);
      bench_puthex(hspi2.ErrorCode);
    }
    set_dma_flag(&hdma_spi2_tx, FLAG_TC);
    BENCH_BEGIN(55);
    HAL_DMA_IRQHandler(&hdma_spi2_tx);
    BENCH_END(55);
    set_dma_flag(&hdma_spi2_rx, FLAG_HT);
    BENCH_BEGIN(54);
    HAL_DMA_IRQHandler(&hdma_spi2_rx);
    BENCH_END(54);
    set_dma_flag(&hdma_spi2_rx, FLAG_TC);
    BENCH_BEGIN(53);
    HAL_DMA_IRQHandler(&hdma_spi2_rx);
    BENCH_END(53);
    SPI2->SR = SPI_SR_EOT;
    BENCH_BEGIN(56);
    HAL_SPI_IRQHandler(&hspi2);
    BENCH_END(56);
  }

  for (int i = 0; i < 4; i++) {
#if defined(MK4_H7)
    EXTI->PR1 = GPIO_PIN_2;
#else
    EXTI->RPR1 = GPIO_PIN_2;
#endif
    BENCH_BEGIN(57);
    HAL_GPIO_EXTI_IRQHandler(GPIO_PIN_2);
    BENCH_END(57);
    BENCH_BEGIN(58);
    HAL_IncTick();
    BENCH_END(58);
  }
  if (g_callback_count != 4 + 4 + 4) {
    bench_puts("WARNING: HAL callback count differs\n");
  }
}
