/*
 * mk4_hw.c
 * MK4 の drv の層の、レジスタを直接書く所(HAL を通さない LL の書き方)。mk4_hw.h の説明を見る。
 */
#include "mk4_hw.h"

void hw_pin_high(GPIO_TypeDef *port, uint32_t pin)
{
  port->BSRR = pin;
}

void hw_pin_low(GPIO_TypeDef *port, uint32_t pin)
{
  port->BSRR = pin * 65536u;  /* 上の 16 ビットに書くと Low */
}

bool hw_pin_read(GPIO_TypeDef *port, uint32_t pin)
{
  if ((port->IDR & pin) != 0u) {
    return true;
  }
  return false;
}

void hw_set_motor_compare(uint32_t left_in1, uint32_t left_in2, uint32_t right_in1, uint32_t right_in2)
{
  TIM1->CCR1 = left_in1;
  TIM1->CCR2 = left_in2;
  TIM1->CCR3 = right_in1;
  TIM1->CCR4 = right_in2;
}

uint32_t hw_get_us(void)
{
  return TIM5->CNT;
}

void hw_wake_control_task(void)
{
  NVIC_SetPendingIRQ(MK4_TIMER_IRQ);
}

void hw_refresh_watchdog(void)
{
#if defined(MK4_H7)
  IWDG1->KR = 0xAAAAu;
#else
  IWDG->KR = 0xAAAAu;
#endif
}

void hw_clear_adc2_dma_flag(void)
{
#if defined(MK4_H7)
  DMA1->LIFCR = DMA_LIFCR_CTCIF0;           /* DMA1 の stream0 = ADC2 */
#else
  GPDMA1_Channel0->CFCR = DMA_CFCR_TCF;     /* GPDMA1 の channel0 = ADC2 */
#endif
}

#if defined(MK4_H7)
/* SPI(v2)と DMA の stream 2 つで、length バイトを送り・受ける。
 * 流れ: 1. SPI を止めて印を消す  2. 受け側の DMA に置き場所と長さを書いて動かす
 *       3. 送り側の DMA に長さを書いて動かす  4. SPI に長さ(TSIZE)を書いて動かし、送り始める */
static void spi_dma_start(SPI_TypeDef *spi, DMA_Stream_TypeDef *rx, DMA_Stream_TypeDef *tx, uint8_t *receive, uint32_t length)
{
  spi->CR1 = spi->CR1 & ~SPI_CR1_SPE;
  spi->IFCR = SPI_IFCR_EOTC | SPI_IFCR_TXTFC;
  rx->M0AR = (uint32_t)receive;
  rx->NDTR = length;
  rx->CR = rx->CR | DMA_SxCR_EN;
  spi->CFG1 = spi->CFG1 | SPI_CFG1_RXDMAEN;
  tx->NDTR = length;
  tx->CR = tx->CR | DMA_SxCR_EN;
  spi->CR2 = length;
  spi->CFG1 = spi->CFG1 | SPI_CFG1_TXDMAEN;
  spi->CR1 = spi->CR1 | SPI_CR1_SPE;
  spi->CR1 = spi->CR1 | SPI_CR1_CSTART;
}

void hw_spi2_start(uint8_t *receive, uint32_t length)
{
  spi_dma_start(SPI2, DMA1_Stream1, DMA1_Stream2, receive, length);
}

void hw_spi3_start(uint8_t *receive, uint32_t length)
{
  spi_dma_start(SPI3, DMA1_Stream3, DMA1_Stream4, receive, length);
}

/* 受け側の DMA の終わり: 印を消し、SPI の DMA を止める */
void hw_spi2_finish(void)
{
  DMA1->LIFCR = DMA_LIFCR_CTCIF1 | DMA_LIFCR_CTCIF2;
  SPI2->CFG1 = SPI2->CFG1 & ~(SPI_CFG1_RXDMAEN | SPI_CFG1_TXDMAEN);
}

void hw_spi3_finish(void)
{
  DMA1->LIFCR = DMA_LIFCR_CTCIF3;
  DMA1->HIFCR = DMA_HIFCR_CTCIF4;
  SPI3->CFG1 = SPI3->CFG1 & ~(SPI_CFG1_RXDMAEN | SPI_CFG1_TXDMAEN);
}

void hw_clear_imu_exti(void)
{
  EXTI->PR1 = IMU_INT_PIN;
}

#else
/* H562: SPI(v2、H7 と同じ)と GPDMA の channel 2 つ。流れは H7 と同じ */
static void spi_dma_start(SPI_TypeDef *spi, DMA_Channel_TypeDef *rx, DMA_Channel_TypeDef *tx, uint8_t *receive, uint32_t length)
{
  spi->CR1 = spi->CR1 & ~SPI_CR1_SPE;
  spi->IFCR = SPI_IFCR_EOTC | SPI_IFCR_TXTFC;
  rx->CDAR = (uint32_t)receive;
  rx->CBR1 = length;
  rx->CCR = rx->CCR | DMA_CCR_EN;
  spi->CFG1 = spi->CFG1 | SPI_CFG1_RXDMAEN;
  tx->CSAR = (uint32_t)receive;  /* 送るのは命令(ベンチでは受ける所と同じ番地でよい) */
  tx->CBR1 = length;
  tx->CCR = tx->CCR | DMA_CCR_EN;
  spi->CR2 = length;
  spi->CFG1 = spi->CFG1 | SPI_CFG1_TXDMAEN;
  spi->CR1 = spi->CR1 | SPI_CR1_SPE;
  spi->CR1 = spi->CR1 | SPI_CR1_CSTART;
}

void hw_spi2_start(uint8_t *receive, uint32_t length)
{
  spi_dma_start(SPI2, GPDMA1_Channel1, GPDMA1_Channel2, receive, length);
}

void hw_spi3_start(uint8_t *receive, uint32_t length)
{
  spi_dma_start(SPI3, GPDMA1_Channel3, GPDMA1_Channel4, receive, length);
}

void hw_spi2_finish(void)
{
  GPDMA1_Channel1->CFCR = DMA_CFCR_TCF;
  GPDMA1_Channel2->CFCR = DMA_CFCR_TCF;
  SPI2->CFG1 = SPI2->CFG1 & ~(SPI_CFG1_RXDMAEN | SPI_CFG1_TXDMAEN);
}

void hw_spi3_finish(void)
{
  GPDMA1_Channel3->CFCR = DMA_CFCR_TCF;
  GPDMA1_Channel4->CFCR = DMA_CFCR_TCF;
  SPI3->CFG1 = SPI3->CFG1 & ~(SPI_CFG1_RXDMAEN | SPI_CFG1_TXDMAEN);
}

void hw_clear_imu_exti(void)
{
  EXTI->RPR1 = IMU_INT_PIN;
}
#endif

void hw_bench_init(void)
{
  NFAULT_PORT->IDR = NFAULT_PIN;  /* nFAULT は High(異常なし) */
  TIM5->CNT = 1000u;
}
