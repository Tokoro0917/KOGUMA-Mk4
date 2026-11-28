/* USER CODE BEGIN Header */
/* stm32h5xx_it.h — 割り込みの入口の宣言(中身は ../Src/stm32h5xx_it.c) */
/* USER CODE END Header */
#ifndef __STM32H5xx_IT_H
#define __STM32H5xx_IT_H

#ifdef __cplusplus
extern "C" {
#endif

void NMI_Handler(void);
void HardFault_Handler(void);
void MemManage_Handler(void);
void BusFault_Handler(void);
void UsageFault_Handler(void);
void SVC_Handler(void);
void DebugMon_Handler(void);
void PendSV_Handler(void);
void SysTick_Handler(void);
void ADC2_IRQHandler(void);
void TIM6_IRQHandler(void);
void USART1_IRQHandler(void);

#ifdef __cplusplus
}
#endif

#endif /* __STM32H5xx_IT_H */
