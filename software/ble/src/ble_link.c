/*
 * ble_link.c — BLE の側(PC とのつながり)
 *
 * やること:
 *   1. 名前(初めは KOGUMA-MK4)を周りに知らせる電波(アドバタイズ)を 1 秒に 1 回出して、PC を待つ
 *   2. PC とつながったら、STM32 に `@link up`、切れたら `@link down` を送る(docs/ble.md の 2 章)
 *   3. PC から届いたデータ(Nordic UART Service = NUS)を、STM32 へ送る列に入れる(stm32_uart.c)
 *   4. STM32 から届いた行を、PC へ送る列に入れ、少しずつ NUS で送る
 *   5. @quiet on・off で電波を止める・戻す、@name で名前を変えて Flash に残す
 *
 * NUS は Nordic の決まった BLE のサービス(nRF Connect SDK の bt_nus)。PC は Web Bluetooth や Python(bleak)で読み書きする。
 */
#include <string.h>
#include <zephyr/kernel.h>
#include <zephyr/bluetooth/bluetooth.h>
#include <zephyr/bluetooth/conn.h>
#include <zephyr/bluetooth/hci.h>
#include <zephyr/settings/settings.h>
#include <zephyr/sys/ring_buffer.h>
#include <zephyr/logging/log.h>
#include <bluetooth/services/nus.h>

#include "koguma_ble.h"

LOG_MODULE_REGISTER(ble_link, LOG_LEVEL_INF);

#define TO_PC_BUF_SIZE 8192           /* PC へ送る待ちの列(STM32 → PC)。あふれそうなら STM32 に XOFF(stm32_uart.c) */
#define NAME_MAX 29                    /* アドバタイズに入る名前の長さの上限 */
#define ADV_INTERVAL 1600              /* アドバタイズの間隔。0.625ms の何倍か(1600 × 0.625ms = 1 秒) */

static struct bt_conn *current_conn = NULL;   /* つながっている PC(つながっていなければ NULL) */
static bool quiet = false;                     /* @quiet on で電波を止めているとき true */
static char adv_name[NAME_MAX + 1] = "KOGUMA-MK4";

RING_BUF_DECLARE(to_pc, TO_PC_BUF_SIZE);
static struct k_spinlock to_pc_lock;
static K_SEM_DEFINE(to_pc_sem, 0, 1);         /* PC へ送るものがある */

/* ---- アドバタイズ ---- */

/* アドバタイズを始める(つながっていない・電波を止めていないとき) */
static void start_advertising(void)
{
	/* 知らせる中身: 「BLE だけの機器」という印と、名前 */
	static const uint8_t flags[] = { BT_LE_AD_GENERAL | BT_LE_AD_NO_BREDR };   /* 印を 2 つ合わせた 1 バイト(Zephyr の決まり) */
	struct bt_data ad[2];

	ad[0].type = BT_DATA_FLAGS;
	ad[0].data_len = sizeof(flags);
	ad[0].data = flags;
	ad[1].type = BT_DATA_NAME_COMPLETE;
	ad[1].data_len = strlen(adv_name);
	ad[1].data = (const uint8_t *)adv_name;

	/* 聞かれたら返す中身: NUS の番号(PC がこの機体を NUS で探せるように) */
	static const uint8_t nus_uuid[] = { BT_UUID_NUS_VAL };
	struct bt_data sd[1];

	sd[0].type = BT_DATA_UUID128_ALL;
	sd[0].data_len = sizeof(nus_uuid);
	sd[0].data = nus_uuid;

	struct bt_le_adv_param param = BT_LE_ADV_PARAM_INIT(BT_LE_ADV_OPT_CONN, ADV_INTERVAL, ADV_INTERVAL, NULL);
	int err = bt_le_adv_start(&param, ad, ARRAY_SIZE(ad), sd, ARRAY_SIZE(sd));

	if (err != 0 && err != -EALREADY) {
		LOG_ERR("アドバタイズを始められない (%d)", err);
	}
}

/* アドバタイズを始め直す仕事(BLE の割り込みの中から直接は呼べないので、Zephyr の仕事の列に頼む) */
static void advertising_work_handler(struct k_work *work)
{
	ARG_UNUSED(work);
	if (quiet || current_conn != NULL) {
		return;
	}
	start_advertising();
}
static K_WORK_DEFINE(advertising_work, advertising_work_handler);

/* ---- つながる・切れる ---- */

/* PC とつながったとき(Zephyr から呼ばれる) */
static void connected(struct bt_conn *conn, uint8_t err)
{
	if (err != 0) {
		LOG_WRN("つながらなかった (%u)", err);
		return;
	}
	current_conn = bt_conn_ref(conn);
	LOG_INF("PC とつながった");
	stm32_uart_send_own_line("@link up\n");

	/* 速く送れるように頼む: 2M PHY(電波の速さ 2 倍)と、1 回に送る量を最大に。PC が断ってもそのまま動く */
	bt_conn_le_phy_update(conn, BT_CONN_LE_PHY_PARAM_2M);
	bt_conn_le_data_len_update(conn, BT_LE_DATA_LEN_PARAM_MAX);
}

/* PC と切れたとき */
static void disconnected(struct bt_conn *conn, uint8_t reason)
{
	LOG_INF("PC と切れた (0x%02x)", reason);
	if (current_conn != NULL) {
		bt_conn_unref(current_conn);
		current_conn = NULL;
	}
	stm32_uart_send_own_line("@link down\n");
}

/* つながりの後片付けが終わったとき: アドバタイズを始め直す */
static void recycled(void)
{
	k_work_submit(&advertising_work);
}

BT_CONN_CB_DEFINE(conn_callbacks) = {
	.connected = connected,
	.disconnected = disconnected,
	.recycled = recycled,
};

/* ---- データ ---- */

/* PC から NUS で届いたとき(BLE のスレッドから呼ばれる): STM32 へ送る列に入れる */
static void nus_received(struct bt_conn *conn, const uint8_t *const data, uint16_t len)
{
	ARG_UNUSED(conn);
	size_t dropped = stm32_uart_queue_from_pc(data, len);

	if (dropped > 0) {
		LOG_WRN("PC から届いた %u バイトを捨てた(STM32 へ送る列がいっぱい)", dropped);
	}
}

static struct bt_nus_cb nus_callbacks = {
	.received = nus_received,
};

/* PC へ送るスレッド: 列から少しずつ取り出して NUS で送る */
static void to_pc_thread(void *p1, void *p2, void *p3)
{
	static uint8_t chunk[244];   /* 1 回に送る量の上限(MTU 247 − 3) */

	while (true) {
		k_sem_take(&to_pc_sem, K_MSEC(10));
		while (current_conn != NULL) {
			struct bt_conn *conn = current_conn;
			uint32_t mtu = bt_nus_get_mtu(conn);   /* 今のつながりで 1 回に送れる量 */
			uint32_t want = sizeof(chunk);

			if (mtu < want) {
				want = mtu;
			}
			k_spinlock_key_t key = k_spin_lock(&to_pc_lock);
			uint32_t got = ring_buf_get(&to_pc, chunk, want);

			k_spin_unlock(&to_pc_lock, key);
			if (got == 0) {
				break;   /* 送るものがない */
			}
			/* 送る。BLE のバッファがいっぱい(-ENOMEM)なら、少し待って同じものを送り直す */
			int err = bt_nus_send(conn, chunk, got);

			while (err == -ENOMEM && current_conn != NULL) {
				k_sleep(K_MSEC(2));
				err = bt_nus_send(conn, chunk, got);
			}
			if (err != 0 && err != -ENOMEM) {
				/* PC が受け取りの準備をしていない(通知を有効にしていない)など。捨てる */
				LOG_DBG("NUS で送れない (%d)", err);
			}
		}
	}
}
K_THREAD_DEFINE(to_pc_tid, 2048, to_pc_thread, NULL, NULL, NULL, 7, 0, 0);

/* ---- 名前を Flash に残す(Zephyr の settings。キーは "koguma/name") ---- */

/* 起動のときに Flash から名前を読む(settings_load から呼ばれる) */
static int name_settings_set(const char *key, size_t len, settings_read_cb read_cb, void *cb_arg)
{
	if (strcmp(key, "name") != 0) {
		return -ENOENT;
	}
	if (len == 0 || len > NAME_MAX) {
		return -EINVAL;
	}
	int got = read_cb(cb_arg, adv_name, len);

	if (got < 0) {
		return got;
	}
	adv_name[got] = '\0';
	return 0;
}
SETTINGS_STATIC_HANDLER_DEFINE(koguma, "koguma", NULL, name_settings_set, NULL, NULL);

/* ---- ほかのファイルから使う関数 ---- */

int ble_link_start(void)
{
	int err = bt_enable(NULL);

	if (err != 0) {
		LOG_ERR("bt_enable に失敗 (%d)", err);
		return err;
	}
	settings_load();   /* 名前と、DFU の設定などを Flash から読む */
	bt_set_name(adv_name);

	err = bt_nus_init(&nus_callbacks);
	if (err != 0) {
		LOG_ERR("bt_nus_init に失敗 (%d)", err);
		return err;
	}
	start_advertising();
	LOG_INF("アドバタイズを始めた: %s", adv_name);
	return 0;
}

bool ble_link_is_connected(void)
{
	return current_conn != NULL;
}

void ble_link_queue_to_pc(const uint8_t *line, size_t length)
{
	if (current_conn == NULL) {
		return;   /* つながっていなければ捨てる(STM32 はつながっていないときは送らない決まり) */
	}
	k_spinlock_key_t key = k_spin_lock(&to_pc_lock);
	uint32_t put = ring_buf_put(&to_pc, line, length);

	k_spin_unlock(&to_pc_lock, key);
	if (put < length) {
		LOG_WRN("PC へ送る %u バイトを捨てた(列がいっぱい。XOFF が間に合わなかった)", length - put);
	}
	k_sem_give(&to_pc_sem);
}

int ble_link_queue_fill_percent(void)
{
	k_spinlock_key_t key = k_spin_lock(&to_pc_lock);
	uint32_t used = ring_buf_size_get(&to_pc);

	k_spin_unlock(&to_pc_lock, key);
	return (int)(used * 100 / TO_PC_BUF_SIZE);
}

void ble_link_set_quiet(bool on)
{
	quiet = on;
	if (on) {
		bt_le_adv_stop();
		if (current_conn != NULL) {
			bt_conn_disconnect(current_conn, BT_HCI_ERR_REMOTE_USER_TERM_CONN);
		}
		LOG_INF("電波を止めた");
	} else {
		k_work_submit(&advertising_work);
		LOG_INF("電波を戻した");
	}
}

void ble_link_set_name(const char *name)
{
	size_t length = strlen(name);

	if (length == 0 || length > NAME_MAX) {
		return;
	}
	strcpy(adv_name, name);
	bt_set_name(adv_name);
	settings_save_one("koguma/name", adv_name, length);
	/* 新しい名前で知らせ直す(つながっている間は、切れたあとから新しい名前になる) */
	if (current_conn == NULL && !quiet) {
		bt_le_adv_stop();
		start_advertising();
	}
	LOG_INF("名前を変えた: %s", adv_name);
}
