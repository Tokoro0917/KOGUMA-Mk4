/*
 * boot_main.c — KOGUMA MK4 の STM32H562 のブートローダ(Flash の先頭 64KB)。決まりは docs/ble.md の 6 章
 *
 * 起動のたびに、次を順に見る(全部で約 1ms。待たない):
 *   1. TAMP のバックアップレジスタ 0 に「書き込みへ」の印がある(走るプログラムが PC の fw begin を受けて書き、リセットした)
 *   2. UART_RX(PB7)が 1ms の間ずっと L(BLE の HY0020 が @flash で引いている)
 *   3. 走るプログラムが正しくない(書いている途中で切れた、まだ書いていない)
 *   → どれかなら「書き込みの待ち」。どれでもなければ、すぐ走るプログラムへ移る(電源を入れてすぐ走れる。デバッガもそのまま使える)
 *
 * 書き込みの待ち:
 *   - 「#BOOT ready」を送り、fw の行を受けて書く(boot_lines.c)
 *   - 状態の LED 0(D114、PC11)を速く点滅させる(BLE の LED の「書き込み中」。software/main-controller/MODES.md)
 *   - 10 秒なにも来なければ、走るプログラムが正しければそちらへ移る(HY0020 がおかしくなっても機体は止まらない)
 *
 * モーター・ファンのピンは触らない(リセットのあとの入力のまま。MP6551 は中のプルダウン、ファンは R42 で止まっている)。
 * 時計は起動のままの HSI(32MHz)。速さは要らない。
 */
#include "stm32h5xx_hal.h"
#include "boot_config.h"
#include "boot_flash.h"
#include "boot_lines.h"
#include "boot_uart.h"

/* バックアップレジスタ(TAMP の BKP0R)を読み書きできるようにする。
 * バックアップ領域は書き込みが守られているので、PWR の DBP を許してから触る */
static void backup_register_enable(void)
{
	HAL_PWR_EnableBkUpAccess();   /* H5 の PWR はクロックを入れなくても使える */
	__HAL_RCC_RTCAPB_CLK_ENABLE();   /* TAMP のレジスタのクロック */
}

/* 1. 走るプログラムが「書き込みへ」を頼んでいたか。印は 1 回で消す */
static int boot_requested(void)
{
	backup_register_enable();
	if (TAMP->BKP0R == BOOT_REQUEST_MAGIC) {
		TAMP->BKP0R = 0;
		return 1;
	}
	return 0;
}

/* 2. UART_RX(PB7)が 1ms の間ずっと L か(USART1 を動かす前に、ふつうの入力として読む) */
static int uart_rx_held_low(void)
{
	GPIO_InitTypeDef gpio = {0};

	__HAL_RCC_GPIOB_CLK_ENABLE();
	gpio.Pin = GPIO_PIN_7;
	gpio.Mode = GPIO_MODE_INPUT;
	gpio.Pull = GPIO_NOPULL;   /* R101 で引き上げてある */
	HAL_GPIO_Init(GPIOB, &gpio);

	uint32_t start = HAL_GetTick();

	while (HAL_GetTick() - start <= UART_RX_LOW_CHECK_MS) {
		if (HAL_GPIO_ReadPin(GPIOB, GPIO_PIN_7) == GPIO_PIN_SET) {
			return 0;   /* 一度でも H なら、引かれていない */
		}
	}
	return 1;
}

/* UART_RX が H に戻るまで待つ(@flash のあと、HY0020 は 50ms で放す)。最大 200ms */
static void wait_uart_rx_released(void)
{
	uint32_t start = HAL_GetTick();

	while (HAL_GPIO_ReadPin(GPIOB, GPIO_PIN_7) == GPIO_PIN_RESET && HAL_GetTick() - start < 200U) {
	}
}

/* 状態の LED 0(D114、PC11)を使えるようにする。H で点灯 */
static void led_init(void)
{
	GPIO_InitTypeDef gpio = {0};

	__HAL_RCC_GPIOC_CLK_ENABLE();
	gpio.Pin = GPIO_PIN_11;
	gpio.Mode = GPIO_MODE_OUTPUT_PP;
	gpio.Pull = GPIO_NOPULL;
	gpio.Speed = GPIO_SPEED_FREQ_LOW;
	HAL_GPIO_Init(GPIOC, &gpio);
}

/* 書き込みの待ち: 行を受けて処理する。書き終わるか、10 秒なにも来なくて走るプログラムが正しければ戻る */
static void wait_for_firmware(void)
{
	static char line[LINE_MAX + 1];
	uint32_t line_length = 0;
	uint32_t last_receive_ms = HAL_GetTick();
	uint32_t last_blink_ms = HAL_GetTick();
	uint8_t byte;

	led_init();
	wait_uart_rx_released();
	boot_uart_init();
	boot_uart_send("#BOOT ready\n");

	while (1) {
		/* LED を速く点滅(0.1 秒ごとに反転) */
		if (HAL_GetTick() - last_blink_ms >= 100U) {
			last_blink_ms = HAL_GetTick();
			HAL_GPIO_TogglePin(GPIOC, GPIO_PIN_11);
		}
		/* 受けた文字を行にまとめる。XON・XOFF(0x11・0x13)と 0(@flash の L で入ることがある)は捨てる */
		while (boot_uart_get_byte(&byte)) {
			last_receive_ms = HAL_GetTick();
			if (byte == 0x11U || byte == 0x13U || byte == 0U) {
				continue;
			}
			line[line_length] = (char)byte;
			line_length = line_length + 1U;
			if (byte == '\n' || line_length >= LINE_MAX) {
				line[line_length] = '\0';
				boot_lines_handle(line);
				line_length = 0;
			}
		}
		if (boot_lines_finished()) {
			HAL_Delay(5);   /* 最後の返事を送りきる */
			return;
		}
		/* 10 秒なにも来なければ、走るプログラムが正しければそちらへ。正しくなければ、もう一度知らせて待ち続ける */
		if (HAL_GetTick() - last_receive_ms >= WAIT_TIMEOUT_MS) {
			if (boot_flash_app_is_valid()) {
				return;
			}
			last_receive_ms = HAL_GetTick();
			boot_uart_send("#BOOT ready\n");
		}
	}
}

int main(void)
{
	HAL_Init();   /* SysTick を 1ms で動かす。時計は起動のままの HSI */

	int request = boot_requested();
	int held_low = uart_rx_held_low();
	int valid = boot_flash_app_is_valid();

	if (request || held_low || !valid) {
		wait_for_firmware();
		boot_uart_deinit();
		HAL_GPIO_WritePin(GPIOC, GPIO_PIN_11, GPIO_PIN_RESET);   /* LED を消す */
	}
	boot_flash_jump_to_app();
	return 0;
}
