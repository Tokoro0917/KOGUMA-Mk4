/*
 * boot_uart.c — ブートローダの UART(USART1、PB6 = 送る、PB7 = 受ける、115200)
 *
 * 走るプログラムと同じ USART1・同じ速さ。有線(TP1)と BLE(HY0020)の両方がこの 1 本につながっている(docs/ble.md の 9 章)。
 * 受ける: 1 文字ごとの割り込みで、リングバッファに入れる(Flash を消す・書く間も取りこぼさないように)。
 * 送る: 短い返事だけなので、送り終わるまで待つ HAL の関数で送る。
 */
#include <string.h>
#include "stm32h5xx_hal.h"
#include "boot_uart.h"

#define RX_RING_SIZE 2048U

UART_HandleTypeDef huart1;                  /* stm32h5xx_it.c の割り込みからも使う */
static uint8_t rx_byte;                     /* 割り込みで 1 文字ずつ受ける所 */
static uint8_t rx_ring[RX_RING_SIZE];
static volatile uint32_t rx_head = 0;       /* 次に書く場所(割り込みが進める) */
static volatile uint32_t rx_tail = 0;       /* 次に読む場所(boot_uart_get_byte が進める) */

/* USART1 のピンを決める(HAL_UART_Init から呼ばれる) */
void HAL_UART_MspInit(UART_HandleTypeDef *huart)
{
	GPIO_InitTypeDef gpio = {0};

	if (huart->Instance != USART1) {
		return;
	}
	__HAL_RCC_USART1_CLK_ENABLE();
	__HAL_RCC_GPIOB_CLK_ENABLE();
	gpio.Pin = GPIO_PIN_6 | GPIO_PIN_7;   /* PB6 と PB7 の 2 本(HAL の決まった書き方) */
	gpio.Mode = GPIO_MODE_AF_PP;
	gpio.Pull = GPIO_NOPULL;              /* UART_RX は基板の R101 で引き上げてある */
	gpio.Speed = GPIO_SPEED_FREQ_LOW;
	gpio.Alternate = GPIO_AF7_USART1;     /* DS14258 の表15: PB6・PB7 の AF7 が USART1 */
	HAL_GPIO_Init(GPIOB, &gpio);
	HAL_NVIC_SetPriority(USART1_IRQn, 0, 0);
	HAL_NVIC_EnableIRQ(USART1_IRQn);
}

void boot_uart_init(void)
{
	huart1.Instance = USART1;
	huart1.Init.BaudRate = 115200;
	huart1.Init.WordLength = UART_WORDLENGTH_8B;
	huart1.Init.StopBits = UART_STOPBITS_1;
	huart1.Init.Parity = UART_PARITY_NONE;
	huart1.Init.Mode = UART_MODE_TX_RX;
	huart1.Init.HwFlowCtl = UART_HWCONTROL_NONE;
	huart1.Init.OverSampling = UART_OVERSAMPLING_16;
	huart1.Init.OneBitSampling = UART_ONE_BIT_SAMPLE_DISABLE;
	huart1.Init.ClockPrescaler = UART_PRESCALER_DIV1;
	huart1.AdvancedInit.AdvFeatureInit = UART_ADVFEATURE_NO_INIT;
	HAL_UART_Init(&huart1);
	HAL_UART_Receive_IT(&huart1, &rx_byte, 1);   /* 1 文字受けたら HAL_UART_RxCpltCallback */
}

void boot_uart_deinit(void)
{
	HAL_NVIC_DisableIRQ(USART1_IRQn);
	HAL_UART_DeInit(&huart1);
	__HAL_RCC_USART1_CLK_DISABLE();
}

/* 1 文字受けた(割り込みの中): リングバッファに入れて、次の 1 文字を待つ */
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
	if (huart->Instance != USART1) {
		return;
	}
	uint32_t next = rx_head + 1U;

	if (next >= RX_RING_SIZE) {
		next = 0;
	}
	if (next != rx_tail) {   /* いっぱいなら捨てる(fw の行は CRC で確かめるので、送り直しになるだけ) */
		rx_ring[rx_head] = rx_byte;
		rx_head = next;
	}
	HAL_UART_Receive_IT(&huart1, &rx_byte, 1);
}

/* 受けるときのエラー(ノイズ、@flash で UART_RX が L のままだった、など): 気にせず受け直す */
void HAL_UART_ErrorCallback(UART_HandleTypeDef *huart)
{
	if (huart->Instance != USART1) {
		return;
	}
	HAL_UART_Receive_IT(&huart1, &rx_byte, 1);
}

int boot_uart_get_byte(uint8_t *byte)
{
	if (rx_tail == rx_head) {
		return 0;
	}
	*byte = rx_ring[rx_tail];
	uint32_t next = rx_tail + 1U;

	if (next >= RX_RING_SIZE) {
		next = 0;
	}
	rx_tail = next;
	return 1;
}

void boot_uart_send(const char *text)
{
	HAL_UART_Transmit(&huart1, (const uint8_t *)text, (uint16_t)strlen(text), 100);
}
