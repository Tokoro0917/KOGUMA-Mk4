/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.c
  * @brief          : 起動して周辺機能を設定し、App の app_init()・app_loop() を呼ぶ
  ******************************************************************************
  * KOGUMA MK4(STM32H562RGV6、240MHz)。2026-11-28 に Claude が手で書いた(CubeMX と同じ形)。
  * 走るプログラムは 0x08010000 から(先頭の 64KB はブートローダ。software/bootloader/README.md)。
  * ベクタテーブルの場所(VTOR)は、system_stm32h5xx.c の SystemInit() が VECT_TAB_OFFSET(CMakeLists.txt で
  * 0x00010000 にしている)を使って決める。
  ******************************************************************************
  */
/* USER CODE END Header */

#include "main.h"
#include "adc.h"
#include "icache.h"
#include "spi.h"
#include "tim.h"
#include "usart.h"
#include "gpio.h"

/* USER CODE BEGIN Includes */
#include "app.h"
/* USER CODE END Includes */

void SystemClock_Config(void);
static void PeriphCommonClock_Config(void);

/* 起動したら最初に動く関数 */
int main(void)
{
  /* USER CODE BEGIN 1 */

  /* USER CODE END 1 */

  HAL_Init();  /* SysTick(1ms)と割り込みの優先度の分け方を決める */

  /* USER CODE BEGIN Init */

  /* USER CODE END Init */

  SystemClock_Config();
  PeriphCommonClock_Config();

  /* USER CODE BEGIN SysInit */

  /* USER CODE END SysInit */

  MX_GPIO_Init();
  MX_ICACHE_Init();
  MX_ADC1_Init();
  MX_ADC2_Init();
  MX_SPI1_Init();
  MX_SPI2_Init();
  MX_TIM1_Init();
  MX_TIM5_Init();
  MX_TIM16_Init();
  MX_TIM17_Init();
  MX_USART1_UART_Init();

  /* USER CODE BEGIN 2 */
  app_init();
  /* USER CODE END 2 */

  while (1) {
    /* USER CODE BEGIN 3 */
    app_loop();
    /* USER CODE END 3 */
  }
}

/* 時計の設定: HSE 10MHz → PLL1 → 240MHz(../../CUBEMX_SETUP.md の 3 章)
 *   PLL の入力  = 10MHz ÷ M(2)= 5MHz(4〜8MHz の範囲 = VCIRANGE_2)
 *   VCO         = 5MHz × N(96)= 480MHz(WIDE の範囲)
 *   SYSCLK      = 480MHz ÷ P(2)= 240MHz
 *   PLL1Q       = 480MHz ÷ Q(4)= 120MHz(SPI の時計)
 * 200MHz を超えるので、電圧のスケールを VOS0 にしてから上げる。Flash の待ちは 5 回(240MHz、VOS0) */
void SystemClock_Config(void)
{
  RCC_OscInitTypeDef RCC_OscInitStruct = {0};
  RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

  __HAL_PWR_VOLTAGESCALING_CONFIG(PWR_REGULATOR_VOLTAGE_SCALE0);
  while (!__HAL_PWR_GET_FLAG(PWR_FLAG_VOSRDY)) {
  }

  RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSE;
  RCC_OscInitStruct.HSEState = RCC_HSE_ON;
  RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
  RCC_OscInitStruct.PLL.PLLSource = RCC_PLL1_SOURCE_HSE;
  RCC_OscInitStruct.PLL.PLLM = 2;
  RCC_OscInitStruct.PLL.PLLN = 96;
  RCC_OscInitStruct.PLL.PLLP = 2;
  RCC_OscInitStruct.PLL.PLLQ = 4;
  RCC_OscInitStruct.PLL.PLLR = 2;
  RCC_OscInitStruct.PLL.PLLRGE = RCC_PLL1_VCIRANGE_2;
  RCC_OscInitStruct.PLL.PLLVCOSEL = RCC_PLL1_VCORANGE_WIDE;
  RCC_OscInitStruct.PLL.PLLFRACN = 0;
  if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK) {
    Error_Handler();
  }

  RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK | RCC_CLOCKTYPE_PCLK1
                              | RCC_CLOCKTYPE_PCLK2 | RCC_CLOCKTYPE_PCLK3;
  RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
  RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
  RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV1;
  RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV1;
  RCC_ClkInitStruct.APB3CLKDivider = RCC_HCLK_DIV1;
  if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_5) != HAL_OK) {
    Error_Handler();
  }

  /* Flash に書くときの待ち(168MHz を超えるときの値。RM0481 の Flash の章) */
  __HAL_FLASH_SET_PROGRAM_DELAY(FLASH_PROGRAMMING_DELAY_2);
}

/* 周辺機能の時計の元を決める: ADC = HCLK(240MHz。ADC の中で ÷4)、SPI1・SPI2 = PLL1Q(120MHz)、USART1 = PCLK2(240MHz) */
static void PeriphCommonClock_Config(void)
{
  RCC_PeriphCLKInitTypeDef PeriphClkInitStruct = {0};

  PeriphClkInitStruct.PeriphClockSelection = RCC_PERIPHCLK_ADCDAC | RCC_PERIPHCLK_SPI1 | RCC_PERIPHCLK_SPI2
                                           | RCC_PERIPHCLK_USART1;
  PeriphClkInitStruct.AdcDacClockSelection = RCC_ADCDACCLKSOURCE_HCLK;
  PeriphClkInitStruct.Spi1ClockSelection = RCC_SPI1CLKSOURCE_PLL1Q;
  PeriphClkInitStruct.Spi2ClockSelection = RCC_SPI2CLKSOURCE_PLL1Q;
  PeriphClkInitStruct.Usart1ClockSelection = RCC_USART1CLKSOURCE_PCLK2;
  if (HAL_RCCEx_PeriphCLKConfig(&PeriphClkInitStruct) != HAL_OK) {
    Error_Handler();
  }
}

/* USER CODE BEGIN 4 */

/* USER CODE END 4 */

/* 設定がうまくいかなかったとき。割り込みを止めて、ここで止まる(デバッガで見ると、どこから来たか分かる) */
void Error_Handler(void)
{
  /* USER CODE BEGIN Error_Handler_Debug */
  __disable_irq();
  while (1) {
  }
  /* USER CODE END Error_Handler_Debug */
}

#ifdef USE_FULL_ASSERT
void assert_failed(uint8_t *file, uint32_t line)
{
  /* USER CODE BEGIN 6 */
  (void)file;
  (void)line;
  /* USER CODE END 6 */
}
#endif /* USE_FULL_ASSERT */
