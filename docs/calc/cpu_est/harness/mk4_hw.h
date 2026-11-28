/*
 * mk4_hw.h
 * MK4 の drv の層が直接さわるレジスタ(LL の書き方)。H725 と H562 で名前が違う所だけ、ここで分ける。
 * ベンチでは周辺のレジスタの番地を RAM の「にせのレジスタ」に置きかえてある(build.py のヘッダの書きかえ)。
 * 命令の数と、どのバス(APB・AHB)を何回読み書きしたかは、本物と同じになる。
 */
#ifndef MK4_HW_H
#define MK4_HW_H

#include <stdbool.h>
#include <stdint.h>

#if defined(MK4_H7)
#include "stm32h7xx.h"
#define MK4_TIMER_IRQ TIM6_DAC_IRQn
#else
#include "stm32h5xx.h"
#define MK4_TIMER_IRQ TIM6_IRQn
#endif

/* ピン(ベンチ用の仮の割り当て。命令の数には関係しない) */
#define WALL_LED_A_PORT GPIOB
#define WALL_LED_A_PIN  (1u << 4)
#define WALL_LED_B_PORT GPIOB
#define WALL_LED_B_PIN  (1u << 5)
#define ENC_L_CS_PORT   GPIOB
#define ENC_L_CS_PIN    (1u << 12)
#define ENC_R_CS_PORT   GPIOB
#define ENC_R_CS_PIN    (1u << 13)
#define IMU_CS_PORT     GPIOA
#define IMU_CS_PIN      (1u << 15)
#define MOTOR_EN_PORT   GPIOA
#define MOTOR_EN_PIN    (1u << 12)
#define NFAULT_PORT     GPIOC
#define NFAULT_PIN      (1u << 13)
#define IMU_INT_PIN     (1u << 2)

/* GPIO の 1 本を High・Low にする(BSRR の下の 16 ビットが High、上の 16 ビットが Low) */
void hw_pin_high(GPIO_TypeDef *port, uint32_t pin);
void hw_pin_low(GPIO_TypeDef *port, uint32_t pin);
bool hw_pin_read(GPIO_TypeDef *port, uint32_t pin);

/* TIM1 の 4 つの比較の値(左右の IN1・IN2 の duty) */
void hw_set_motor_compare(uint32_t left_in1, uint32_t left_in2, uint32_t right_in1, uint32_t right_in2);

/* TIM5(1MHz で数える)の今の値 [µs] */
uint32_t hw_get_us(void);

/* 4kHz の処理を起こす(TIM6 の割り込みの番号を借りる) */
void hw_wake_control_task(void);

/* ウォッチドッグを clear する */
void hw_refresh_watchdog(void);

/* ADC2 の DMA の終わりの印を消す(20kHz の割り込みの初め) */
void hw_clear_adc2_dma_flag(void);

/* SPI2(エンコーダ)・SPI3(IMU)の DMA の読み取りを始める・終わりの印を消す */
void hw_spi2_start(uint8_t *receive, uint32_t length);
void hw_spi2_finish(void);
void hw_spi3_start(uint8_t *receive, uint32_t length);
void hw_spi3_finish(void);

/* IMU の INT1(EXTI)の印を消す */
void hw_clear_imu_exti(void);

/* ベンチ用: にせのレジスタに初めの値を入れる */
void hw_bench_init(void);

#endif
