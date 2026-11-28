/*
 * stm32_uart.c — STM32 との UART(HY0020 の P0.08 = 受ける、P0.06 = 送る)
 *
 * やること:
 *   1. STM32 から届いた文字を行に区切る。`@` の行は at_lines.c へ、ほかの行は BLE で PC へ(ble_link.c)
 *   2. PC から届いた行を STM32 に送る。有線(TP1)が送っている間は待つ(P0.04 で UART_RX を見る。docs/ble.md の 9 章)
 *   3. PC へ送る待ちの列があふれそうなら、STM32 に XOFF を送って止めてもらう(docs/ble.md の 4.4)
 *   4. @reset・@flash のときに、STM32 の NRST(P0.07)と UART_RX(P0.06)を L にする
 *
 * つなぎ方(回路図 ui.kicad_sch の U5):
 *   P0.06 → D99(ダイオード)→ STM32 の UART_RX。L に引くだけ(R101 で引き上げ)。有線の TP1 も同じ線を D100 で引く
 *   P0.08 ← STM32 の UART_TX
 *   P0.04 ← STM32 の UART_RX(見るだけ。有線が送っているかを知る)
 *   P0.07 → D101 → STM32 の NRST(L に引くだけ)
 *
 * UART は Zephyr の「非同期の API」(DMA で受ける)を使う。1 バイトごとの割り込みだと、BLE の電波の処理と重なったときに
 * 文字を取りこぼすことがあるため。受けた文字は、割り込みの中ではリングバッファに写すだけにして、行に区切るのはスレッドでやる。
 */
#include <string.h>
#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/drivers/uart.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/pm/device.h>
#include <zephyr/sys/ring_buffer.h>
#include <zephyr/logging/log.h>

#include "koguma_ble.h"

LOG_MODULE_REGISTER(stm32_uart, LOG_LEVEL_INF);

#define XON_CHAR 0x11                /* 送ってよい */
#define XOFF_CHAR 0x13               /* 送るのを止めて */
#define XOFF_FILL_PERCENT 75         /* PC へ送る待ちの列がこれを超えたら XOFF */
#define XON_FILL_PERCENT 25          /* これを下回ったら XON */
#define LINE_MAX 600                 /* 1 行の長さの上限(fw の行は約 270 文字)。超えたらそこで区切る */
#define WIRED_IDLE_US 100            /* 有線が送っていないとみなす、UART_RX が H のままの時間 */
#define RX_DMA_SIZE 256              /* DMA で受ける 1 回分の大きさ(2 つを交互に使う) */
#define RX_IDLE_TIMEOUT_US 200       /* 文字が途切れてこの時間たったら、受けた分を渡す */

/* ---- ピン(app.overlay の zephyr,user の中に書いてある) ---- */
static const struct device *const uart_dev = DEVICE_DT_GET(DT_NODELABEL(uart0));
static const struct gpio_dt_spec stm32_nrst = GPIO_DT_SPEC_GET(DT_PATH(zephyr_user), stm32_nrst_gpios);
static const struct gpio_dt_spec uart_rx_watch = GPIO_DT_SPEC_GET(DT_PATH(zephyr_user), uart_rx_watch_gpios);
static const struct gpio_dt_spec uart_tx_pin = GPIO_DT_SPEC_GET(DT_PATH(zephyr_user), uart_tx_gpios);

/* ---- リングバッファ(Zephyr の ring_buf)。割り込みとスレッドの両方が触るので、spinlock で守る ---- */
RING_BUF_DECLARE(from_stm32_raw, 1024);      /* STM32 から受けたままの文字(割り込み → 受けるスレッド)。1Mbaud でも約 11ms 分 */
RING_BUF_DECLARE(to_stm32_from_pc, 6144);    /* PC から STM32 へ送る文字(BLE → 送るスレッド)。PC は書き込みのとき 4KB(文字で約 5.6KB)ごとに返事を待つので、それが入る大きさ */
RING_BUF_DECLARE(to_stm32_own, 512);         /* nRF52832 が作った行(@link up など) */
static struct k_spinlock ring_lock;

/* ---- 受ける側の DMA のバッファ(2 つを交互に渡す) ---- */
static uint8_t rx_dma_buf[2][RX_DMA_SIZE];
static int rx_dma_next = 0;                   /* 次に渡すバッファの番号(0 か 1) */
static volatile bool rx_stopping = false;     /* @flash で、わざと受けるのを止めているとき true */

/* ---- スレッドを起こす合図 ---- */
static K_SEM_DEFINE(rx_data_sem, 0, 1);      /* 受けた文字がある */
static K_SEM_DEFINE(tx_work_sem, 0, 1);      /* 送るものがある */
static K_SEM_DEFINE(tx_done_sem, 0, 1);      /* 1 回の送信が終わった */
static K_SEM_DEFINE(rx_disabled_sem, 0, 1);  /* 受けるのが止まった */

static bool xoff_sent = false;               /* STM32 に XOFF を送ってある(XON をまだ送っていない) */

/* リングバッファに入れる(spinlock の中で)。入った大きさを返す */
static uint32_t ring_put(struct ring_buf *ring, const uint8_t *data, uint32_t length)
{
	k_spinlock_key_t key = k_spin_lock(&ring_lock);
	uint32_t put = ring_buf_put(ring, data, length);

	k_spin_unlock(&ring_lock, key);
	return put;
}

/* リングバッファから 1 文字取る。取れたら true */
static bool ring_get_byte(struct ring_buf *ring, uint8_t *byte)
{
	k_spinlock_key_t key = k_spin_lock(&ring_lock);
	uint32_t got = ring_buf_get(ring, byte, 1);

	k_spin_unlock(&ring_lock, key);
	return got == 1;
}

/* UART のできごとの割り込み(Zephyr の非同期の API から呼ばれる)。
 * 受けた分をリングバッファに写すだけで、すぐ戻る(行に区切るのは rx_thread) */
static void uart_event(const struct device *dev, struct uart_event *evt, void *user_data)
{
	ARG_UNUSED(user_data);

	if (evt->type == UART_RX_RDY) {
		/* 受けた文字: DMA のバッファの offset から len バイト */
		uint32_t put = ring_put(&from_stm32_raw, evt->data.rx.buf + evt->data.rx.offset, evt->data.rx.len);

		if (put < evt->data.rx.len) {
			LOG_WRN("STM32 から受けた %u バイトを捨てた(受けるスレッドが遅れている)", evt->data.rx.len - put);
		}
		k_sem_give(&rx_data_sem);
	} else if (evt->type == UART_RX_BUF_REQUEST) {
		/* 今のバッファがいっぱいになる前に、次のバッファを渡しておく(2 つを交互に) */
		uart_rx_buf_rsp(dev, rx_dma_buf[rx_dma_next], RX_DMA_SIZE);
		rx_dma_next = rx_dma_next + 1;
		if (rx_dma_next >= 2) {
			rx_dma_next = 0;
		}
	} else if (evt->type == UART_RX_DISABLED) {
		/* 受けるのが止まった。わざと止めたのでなければ(ノイズで止まったなど)、すぐ受け直す */
		if (rx_stopping) {
			k_sem_give(&rx_disabled_sem);
		} else {
			uart_rx_enable(dev, rx_dma_buf[0], RX_DMA_SIZE, RX_IDLE_TIMEOUT_US);
			rx_dma_next = 1;
		}
	} else if (evt->type == UART_TX_DONE || evt->type == UART_TX_ABORTED) {
		k_sem_give(&tx_done_sem);
	}
}

/* 受けるのを始める(起動のときと、@flash のあと) */
static void start_receiving(void)
{
	rx_dma_next = 1;
	int err = uart_rx_enable(uart_dev, rx_dma_buf[0], RX_DMA_SIZE, RX_IDLE_TIMEOUT_US);

	if (err != 0) {
		LOG_ERR("uart_rx_enable に失敗 (%d)", err);
	}
}

/* 文字を STM32 に送り、送り終わるまで待つ(DMA で送る。送る文字の配列は送り終わるまで変えない) */
static void send_and_wait(const uint8_t *data, size_t length)
{
	if (length == 0) {
		return;
	}
	int err = uart_tx(uart_dev, data, length, SYS_FOREVER_US);

	if (err != 0) {
		LOG_ERR("uart_tx に失敗 (%d)", err);
		return;
	}
	k_sem_take(&tx_done_sem, K_FOREVER);
}

/* 有線(TP1)が送っていない(UART_RX が 100µs ずっと H)まで待つ。
 * 割り込みを使わず、P0.04 を短い間隔で読む(1Mbaud だと端の数が多く、割り込みでは重いため) */
static void wait_wired_idle(void)
{
	uint32_t idle_cycles = k_us_to_cyc_ceil32(WIRED_IDLE_US);

	while (true) {
		uint32_t start = k_cycle_get_32();
		bool saw_low = false;

		while (k_cycle_get_32() - start < idle_cycles) {
			if (gpio_pin_get_dt(&uart_rx_watch) == 0) {
				saw_low = true;
				break;
			}
		}
		if (!saw_low) {
			return;
		}
		k_sleep(K_USEC(200));   /* 有線が送っている。少し待ってから見直す */
	}
}

/* PC へ送る待ちの列の埋まり方を見て、STM32 に XOFF・XON を送る */
static void update_flow_control(void)
{
	static uint8_t flow_char;   /* DMA で送るので、送り終わるまで残る所に置く */
	int fill = ble_link_queue_fill_percent();

	if (!xoff_sent && fill > XOFF_FILL_PERCENT) {
		flow_char = XOFF_CHAR;
		wait_wired_idle();
		send_and_wait(&flow_char, 1);
		xoff_sent = true;
	} else if (xoff_sent && fill < XON_FILL_PERCENT) {
		flow_char = XON_CHAR;
		wait_wired_idle();
		send_and_wait(&flow_char, 1);
		xoff_sent = false;
	}
}

/* 受けるスレッド: STM32 から受けた文字を行に区切る。`@` の行は at_lines.c へ、ほかは PC へ */
static void rx_thread(void *p1, void *p2, void *p3)
{
	static char line[LINE_MAX + 1];   /* 最後に '\0' を置く分 +1 */
	int line_length = 0;
	uint8_t byte;

	while (true) {
		k_sem_take(&rx_data_sem, K_FOREVER);
		while (ring_get_byte(&from_stm32_raw, &byte)) {
			if (byte == XON_CHAR || byte == XOFF_CHAR) {
				continue;   /* 流れの制御の文字はテキストには出てこない。捨てる */
			}
			line[line_length] = (char)byte;
			line_length = line_length + 1;
			if (byte != '\n' && line_length < LINE_MAX) {
				continue;   /* 行の途中 */
			}
			/* 1 行そろった(または長すぎるのでここで区切る) */
			line[line_length] = '\0';
			if (line[0] == '@') {
				at_line_from_stm32(line);
			} else {
				ble_link_queue_to_pc((const uint8_t *)line, line_length);
			}
			line_length = 0;
		}
	}
}

/* 送るスレッド: nRF52832 の行、PC から届いた行を STM32 に送る。XON・XOFF もここで送る。
 * 行の途中で有線とまざらないように、1 行ずつ、有線が止まっているのを確かめてから送る */
static void tx_thread(void *p1, void *p2, void *p3)
{
	static uint8_t line[LINE_MAX + 1];       /* PC からの行。DMA で送るので static(送り終わるまで変えない) */
	static uint8_t own_line[LINE_MAX + 1];   /* nRF52832 が作った行(PC からの行と別の配列にする。PC の行を溜めている途中でも送れるように) */
	int line_length = 0;
	uint8_t byte;

	while (true) {
		/* 送るものがなくても 5ms ごとに起きて、XON を送るかどうかを見る */
		k_sem_take(&tx_work_sem, K_MSEC(5));
		update_flow_control();

		/* 1. nRF52832 が作った行(@link up など)を先に送る */
		int own_length = 0;
		while (own_length < LINE_MAX && ring_get_byte(&to_stm32_own, &byte)) {
			own_line[own_length] = byte;
			own_length = own_length + 1;
		}
		if (own_length > 0) {
			wait_wired_idle();
			send_and_wait(own_line, own_length);
		}

		/* 2. PC から届いた文字を 1 行ずつ */
		while (ring_get_byte(&to_stm32_from_pc, &byte)) {
			line[line_length] = byte;
			line_length = line_length + 1;
			if (byte != '\n' && line_length < LINE_MAX) {
				continue;
			}
			if (line[0] == '@') {
				/* nRF52832 あての行: STM32 には送らない */
				line[line_length] = '\0';
				at_line_from_pc((const char *)line);
			} else {
				wait_wired_idle();
				send_and_wait(line, line_length);
			}
			line_length = 0;
			update_flow_control();
		}
	}
}

K_THREAD_STACK_DEFINE(rx_stack, 2048);
K_THREAD_STACK_DEFINE(tx_stack, 2048);
static struct k_thread rx_thread_data;
static struct k_thread tx_thread_data;

int stm32_uart_start(void)
{
	if (!device_is_ready(uart_dev)) {
		LOG_ERR("UART が使えない");
		return -ENODEV;
	}
	/* NRST へのピン: H(ダイオード D101 で止まるので、STM32 には何もしない) */
	gpio_pin_configure_dt(&stm32_nrst, GPIO_OUTPUT_HIGH);
	/* UART_RX を見るピン: 入力(R101 で引き上げてあるので、中のプルアップは使わない) */
	gpio_pin_configure_dt(&uart_rx_watch, GPIO_INPUT);

	uart_callback_set(uart_dev, uart_event, NULL);
	start_receiving();

	k_thread_create(&rx_thread_data, rx_stack, K_THREAD_STACK_SIZEOF(rx_stack), rx_thread, NULL, NULL, NULL,
			5, 0, K_NO_WAIT);
	k_thread_create(&tx_thread_data, tx_stack, K_THREAD_STACK_SIZEOF(tx_stack), tx_thread, NULL, NULL, NULL,
			6, 0, K_NO_WAIT);
	return 0;
}

size_t stm32_uart_queue_from_pc(const uint8_t *data, size_t length)
{
	uint32_t put = ring_put(&to_stm32_from_pc, data, length);

	k_sem_give(&tx_work_sem);
	return length - put;
}

void stm32_uart_send_own_line(const char *line)
{
	ring_put(&to_stm32_own, (const uint8_t *)line, strlen(line));
	k_sem_give(&tx_work_sem);
}

void stm32_reset(void)
{
	gpio_pin_set_dt(&stm32_nrst, 0);   /* L: D101 を通して NRST を引く */
	k_sleep(K_MSEC(10));
	gpio_pin_set_dt(&stm32_nrst, 1);   /* H: ダイオードで止まる(放す) */
}

/* STM32 をブートローダの書き込みの待ちに入れる(docs/ble.md の 6.2 の 2):
 *   UART_RX を L にしたまま NRST を 10ms L → 放してから 50ms 後に UART_RX を放す。
 *   ブートローダは、起動して 1ms の間 UART_RX が L なら書き込みの待ちに入る。
 * UART_RX を L にするには、UART の送る端子(P0.06)を UART から外して、ふつうの出力の L にする。
 * この関数は送るスレッドから呼ばれる(PC からの @flash の行)ので、送っている途中ではない */
void stm32_enter_bootloader(void)
{
	/* 1. 受けるのを止める(止まったという知らせを待つ) */
	rx_stopping = true;
	uart_rx_disable(uart_dev);
	k_sem_take(&rx_disabled_sem, K_MSEC(100));

	/* 2. UART を眠らせる(ピンが UART から外れる)→ P0.06 をふつうの出力の L に */
	pm_device_action_run(uart_dev, PM_DEVICE_ACTION_SUSPEND);
	gpio_pin_configure_dt(&uart_tx_pin, GPIO_OUTPUT_LOW);

	/* 3. NRST を 10ms L → 放す。ブートローダが UART_RX の L を見る */
	stm32_reset();
	k_sleep(K_MSEC(50));

	/* 4. P0.06 を放し(入力に)、UART を起こす(ピンが UART に戻る)→ また受ける */
	gpio_pin_configure_dt(&uart_tx_pin, GPIO_INPUT);
	pm_device_action_run(uart_dev, PM_DEVICE_ACTION_RESUME);
	rx_stopping = false;
	start_receiving();
	LOG_INF("STM32 をブートローダの書き込みの待ちに入れた");
}
