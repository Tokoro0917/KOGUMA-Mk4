/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file    spi.c
  * @brief   SPI1(IMU)・SPI2(エンコーダ)の設定(../../CUBEMX_SETUP.md の 6 章)
  ******************************************************************************
  * どちらもモード 3(CPOL = High、CPHA = 2 Edge)、8 ビット、MSB から。CS は GPIO(main.h の IMU_CS・ENC_L_CS・ENC_R_CS)。
  * SPI の時計は PLL1Q の 120MHz。SPI1 は ÷16 = 7.5MHz(LSM6DSR は 10MHz まで)、SPI2 は ÷8 = 15MHz(MT6835 は 16.6MHz まで)。
  * 2026-11-28: DMA は使わない(4kHz の処理の中で、HAL_SPI_TransmitReceive で読む。drv/imu.c・drv/encoder.c)。
  * MasterKeepIOState を ENABLE にするのは、送っていない間もクロックのピンを H(モード 3 の休みの形)に保つため。
  ******************************************************************************
  */
/* USER CODE END Header */

#include "spi.h"

/* USER CODE BEGIN 0 */

/* USER CODE END 0 */

SPI_HandleTypeDef hspi1;
SPI_HandleTypeDef hspi2;

/* SPI 1 つを、モード 3・8 ビットのマスターにする */
static void spi_mode3_init(SPI_HandleTypeDef *hspi, SPI_TypeDef *instance, uint32_t prescaler)
{
  hspi->Instance = instance;
  hspi->Init.Mode = SPI_MODE_MASTER;
  hspi->Init.Direction = SPI_DIRECTION_2LINES;
  hspi->Init.DataSize = SPI_DATASIZE_8BIT;
  hspi->Init.CLKPolarity = SPI_POLARITY_HIGH;
  hspi->Init.CLKPhase = SPI_PHASE_2EDGE;
  hspi->Init.NSS = SPI_NSS_SOFT;
  hspi->Init.BaudRatePrescaler = prescaler;
  hspi->Init.FirstBit = SPI_FIRSTBIT_MSB;
  hspi->Init.TIMode = SPI_TIMODE_DISABLE;
  hspi->Init.CRCCalculation = SPI_CRCCALCULATION_DISABLE;
  hspi->Init.CRCPolynomial = 0x7;
  hspi->Init.NSSPMode = SPI_NSS_PULSE_DISABLE;
  hspi->Init.NSSPolarity = SPI_NSS_POLARITY_LOW;
  hspi->Init.FifoThreshold = SPI_FIFO_THRESHOLD_01DATA;
  hspi->Init.TxCRCInitializationPattern = SPI_CRC_INITIALIZATION_ALL_ZERO_PATTERN;
  hspi->Init.RxCRCInitializationPattern = SPI_CRC_INITIALIZATION_ALL_ZERO_PATTERN;
  hspi->Init.MasterSSIdleness = SPI_MASTER_SS_IDLENESS_00CYCLE;
  hspi->Init.MasterInterDataIdleness = SPI_MASTER_INTERDATA_IDLENESS_00CYCLE;
  hspi->Init.MasterReceiverAutoSusp = SPI_MASTER_RX_AUTOSUSP_DISABLE;
  hspi->Init.MasterKeepIOState = SPI_MASTER_KEEP_IO_STATE_ENABLE;
  hspi->Init.IOSwap = SPI_IO_SWAP_DISABLE;
  hspi->Init.ReadyMasterManagement = SPI_RDY_MASTER_MANAGEMENT_INTERNALLY;
  hspi->Init.ReadyPolarity = SPI_RDY_POLARITY_HIGH;
  if (HAL_SPI_Init(hspi) != HAL_OK) {
    Error_Handler();
  }
}

/* SPI1: IMU(PA5 SCK・PA6 MISO・PA7 MOSI) */
void MX_SPI1_Init(void)
{
  spi_mode3_init(&hspi1, SPI1, SPI_BAUDRATEPRESCALER_16);
}

/* SPI2: エンコーダ(PA12 SCK・PB14 MISO・PB15 MOSI) */
void MX_SPI2_Init(void)
{
  spi_mode3_init(&hspi2, SPI2, SPI_BAUDRATEPRESCALER_8);
}

/* SPI のピン 1 本を AF にする(AF5。ST のピンのデータで確かめた) */
static void spi_pin(GPIO_TypeDef *port, uint16_t pin, uint8_t alternate)
{
  GPIO_InitTypeDef GPIO_InitStruct = {0};

  GPIO_InitStruct.Pin = pin;
  GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_HIGH;
  GPIO_InitStruct.Alternate = alternate;
  HAL_GPIO_Init(port, &GPIO_InitStruct);
}

/* SPI の時計とピンを設定する(HAL_SPI_Init から呼ばれる) */
void HAL_SPI_MspInit(SPI_HandleTypeDef *spiHandle)
{
  if (spiHandle->Instance == SPI1) {
    __HAL_RCC_SPI1_CLK_ENABLE();
    __HAL_RCC_GPIOA_CLK_ENABLE();
    spi_pin(IMU_SCK_GPIO_Port, IMU_SCK_Pin, GPIO_AF5_SPI1);
    spi_pin(IMU_MISO_GPIO_Port, IMU_MISO_Pin, GPIO_AF5_SPI1);
    spi_pin(IMU_MOSI_GPIO_Port, IMU_MOSI_Pin, GPIO_AF5_SPI1);
  } else if (spiHandle->Instance == SPI2) {
    __HAL_RCC_SPI2_CLK_ENABLE();
    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_GPIOB_CLK_ENABLE();
    spi_pin(ENC_SCK_GPIO_Port, ENC_SCK_Pin, GPIO_AF5_SPI2);
    spi_pin(ENC_MISO_GPIO_Port, ENC_MISO_Pin, GPIO_AF5_SPI2);
    spi_pin(ENC_MOSI_GPIO_Port, ENC_MOSI_Pin, GPIO_AF5_SPI2);
  }
}

/* USER CODE BEGIN 1 */

/* USER CODE END 1 */
