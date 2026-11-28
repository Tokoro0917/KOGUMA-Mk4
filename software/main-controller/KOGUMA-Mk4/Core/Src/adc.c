/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file    adc.c
  * @brief   ADC1・ADC2 の設定(../../CUBEMX_SETUP.md の 5 章。2026-11-28 に DMA から injected に変えた)
  ******************************************************************************
  * ■ 読み方(DMA を使わない)
  * 20kHz ごとに読むもの(壁センサ 4 本、モーターの電流 2 本と CMS 2 本)は、どちらの ADC も
  * 「injected」の組(4 本まで。結果は 4 つの JDR レジスタに別々に入る)にして、TIM1 の TRGO で同時に起動する。
  * 4 本の変換が終わると ADC2 の割り込み(JEOS)が来るので、そこで 8 つの値を読む(drv/current.c・drv/wall.c、
  * sys/scheduler.c)。結果のレジスタが分かれているので、DMA も、読み終わるまでの待ちも要らない。
  * 5 本目のもの(ファンの電流 = ADC1、電池 = ADC2)は「regular」の組にして、20kHz の処理の中で次の変換を
  * ソフトで起動し、次の回に結果を読む(ゆっくり変わる値なので、50µs 古くてよい)。
  *
  * ■ 時間
  * ADC の時計は 240MHz ÷ 4 = 60MHz。1 本 = 12.5(サンプル)+ 12.5(変換)= 25 クロック ≒ 0.42µs。4 本で約 1.7µs
  ******************************************************************************
  */
/* USER CODE END Header */

#include "adc.h"

/* USER CODE BEGIN 0 */

/* USER CODE END 0 */

ADC_HandleTypeDef hadc1;
ADC_HandleTypeDef hadc2;

/* ADC 1 つの共通の設定(12 ビット、regular は 1 本をソフトで起動) */
static void adc_common_init(ADC_HandleTypeDef *hadc, ADC_TypeDef *instance)
{
  hadc->Instance = instance;
  hadc->Init.ClockPrescaler = ADC_CLOCK_ASYNC_DIV4;
  hadc->Init.Resolution = ADC_RESOLUTION_12B;
  hadc->Init.DataAlign = ADC_DATAALIGN_RIGHT;
  hadc->Init.ScanConvMode = ADC_SCAN_ENABLE;
  hadc->Init.EOCSelection = ADC_EOC_SEQ_CONV;  /* 割り込みは 4 本の変換が全部終わったときに 1 回(JEOS) */
  hadc->Init.LowPowerAutoWait = DISABLE;
  hadc->Init.ContinuousConvMode = DISABLE;
  hadc->Init.NbrOfConversion = 1;
  hadc->Init.DiscontinuousConvMode = DISABLE;
  hadc->Init.ExternalTrigConv = ADC_SOFTWARE_START;
  hadc->Init.ExternalTrigConvEdge = ADC_EXTERNALTRIGCONVEDGE_NONE;
  hadc->Init.SamplingMode = ADC_SAMPLING_MODE_NORMAL;
  hadc->Init.DMAContinuousRequests = DISABLE;
  hadc->Init.Overrun = ADC_OVR_DATA_OVERWRITTEN;
  hadc->Init.OversamplingMode = DISABLE;
  if (HAL_ADC_Init(hadc) != HAL_OK) {
    Error_Handler();
  }
}

/* regular の組の 1 本目を設定する */
static void regular_channel(ADC_HandleTypeDef *hadc, uint32_t channel, uint32_t sampling_time)
{
  ADC_ChannelConfTypeDef sConfig = {0};

  sConfig.Channel = channel;
  sConfig.Rank = ADC_REGULAR_RANK_1;
  sConfig.SamplingTime = sampling_time;
  sConfig.SingleDiff = ADC_SINGLE_ENDED;
  sConfig.OffsetNumber = ADC_OFFSET_NONE;
  sConfig.Offset = 0;
  if (HAL_ADC_ConfigChannel(hadc, &sConfig) != HAL_OK) {
    Error_Handler();
  }
}

/* injected の組の 1 本を設定する(4 本とも TIM1 の TRGO の立ち上がりで起動) */
static void injected_channel(ADC_HandleTypeDef *hadc, uint32_t channel, uint32_t rank)
{
  ADC_InjectionConfTypeDef sConfigInjected = {0};

  sConfigInjected.InjectedChannel = channel;
  sConfigInjected.InjectedRank = rank;
  sConfigInjected.InjectedSamplingTime = ADC_SAMPLETIME_12CYCLES_5;
  sConfigInjected.InjectedSingleDiff = ADC_SINGLE_ENDED;
  sConfigInjected.InjectedOffsetNumber = ADC_OFFSET_NONE;
  sConfigInjected.InjectedOffset = 0;
  sConfigInjected.InjectedNbrOfConversion = 4;
  sConfigInjected.InjectedDiscontinuousConvMode = DISABLE;
  sConfigInjected.AutoInjectedConv = DISABLE;
  sConfigInjected.QueueInjectedContext = DISABLE;
  sConfigInjected.ExternalTrigInjecConv = ADC_EXTERNALTRIGINJEC_T1_TRGO;
  sConfigInjected.ExternalTrigInjecConvEdge = ADC_EXTERNALTRIGINJECCONV_EDGE_RISING;
  sConfigInjected.InjecOversamplingMode = DISABLE;
  if (HAL_ADCEx_InjectedConfigChannel(hadc, &sConfigInjected) != HAL_OK) {
    Error_Handler();
  }
}

/* ADC1: injected = 壁センサ FL・L・R・FR、regular = ファンの電流 */
void MX_ADC1_Init(void)
{
  adc_common_init(&hadc1, ADC1);
  regular_channel(&hadc1, ADC_CHANNEL_9, ADC_SAMPLETIME_12CYCLES_5);   /* PB0 FAN_ISENSE */
  injected_channel(&hadc1, ADC_CHANNEL_10, ADC_INJECTED_RANK_1);        /* PC0 WALL_FL */
  injected_channel(&hadc1, ADC_CHANNEL_11, ADC_INJECTED_RANK_2);        /* PC1 WALL_L */
  injected_channel(&hadc1, ADC_CHANNEL_12, ADC_INJECTED_RANK_3);        /* PC2 WALL_R */
  injected_channel(&hadc1, ADC_CHANNEL_13, ADC_INJECTED_RANK_4);        /* PC3 WALL_FR */
}

/* ADC2: injected = 左右のモーターの電流・CMS、regular = 電池の電圧 */
void MX_ADC2_Init(void)
{
  adc_common_init(&hadc2, ADC2);
  /* 電池は 47k・10k の分圧を C9 10nF で受けているので、サンプルの時間を長めに */
  regular_channel(&hadc2, ADC_CHANNEL_5, ADC_SAMPLETIME_47CYCLES_5);   /* PB1 BATT */
  injected_channel(&hadc2, ADC_CHANNEL_4, ADC_INJECTED_RANK_1);        /* PC4 MOT_L_I */
  injected_channel(&hadc2, ADC_CHANNEL_18, ADC_INJECTED_RANK_2);       /* PA4 MOT_R_I */
  injected_channel(&hadc2, ADC_CHANNEL_8, ADC_INJECTED_RANK_3);        /* PC5 MOT_L_CMS */
  injected_channel(&hadc2, ADC_CHANNEL_15, ADC_INJECTED_RANK_4);       /* PA3 MOT_R_CMS */
}

/* アナログの入力のピンにする */
static void analog_pin(GPIO_TypeDef *port, uint16_t pin)
{
  GPIO_InitTypeDef GPIO_InitStruct = {0};

  GPIO_InitStruct.Pin = pin;
  GPIO_InitStruct.Mode = GPIO_MODE_ANALOG;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  HAL_GPIO_Init(port, &GPIO_InitStruct);
}

/* ADC の時計・ピン・割り込みを設定する(HAL_ADC_Init から呼ばれる) */
void HAL_ADC_MspInit(ADC_HandleTypeDef *adcHandle)
{
  /* ADC1・ADC2 は時計が 1 つ(ADC12)。2 回入れても問題ない */
  __HAL_RCC_ADC_CLK_ENABLE();
  __HAL_RCC_GPIOA_CLK_ENABLE();
  __HAL_RCC_GPIOB_CLK_ENABLE();
  __HAL_RCC_GPIOC_CLK_ENABLE();
  if (adcHandle->Instance == ADC1) {
    analog_pin(WALL_FL_GPIO_Port, WALL_FL_Pin);
    analog_pin(WALL_L_GPIO_Port, WALL_L_Pin);
    analog_pin(WALL_R_GPIO_Port, WALL_R_Pin);
    analog_pin(WALL_FR_GPIO_Port, WALL_FR_Pin);
    analog_pin(FAN_ISENSE_GPIO_Port, FAN_ISENSE_Pin);
    /* ADC1 の割り込みは使わない(ADC2 と同時に終わるので、ADC2 の割り込みの中で読む) */
  } else if (adcHandle->Instance == ADC2) {
    analog_pin(MOT_L_I_GPIO_Port, MOT_L_I_Pin);
    analog_pin(MOT_R_I_GPIO_Port, MOT_R_I_Pin);
    analog_pin(MOT_L_CMS_GPIO_Port, MOT_L_CMS_Pin);
    analog_pin(MOT_R_CMS_GPIO_Port, MOT_R_CMS_Pin);
    analog_pin(BATT_GPIO_Port, BATT_Pin);
    /* 20kHz の処理の割り込み。いちばん高い優先度(0) */
    HAL_NVIC_SetPriority(ADC2_IRQn, 0, 0);
    HAL_NVIC_EnableIRQ(ADC2_IRQn);
  }
}

/* USER CODE BEGIN 1 */

/* USER CODE END 1 */
