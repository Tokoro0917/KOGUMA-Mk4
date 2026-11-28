/*
 * buzzer.c
 * ブザー(TIM17 の CH1、PB9)を鳴らす。MK4 で足したもの
 *
 * ■ しくみ
 * TIM17 は 1MHz(1 カウント = 1µs)で数える(Core/Src/tim.c)。数える長さ(ARR + 1)を 1 周期の µs にし、
 * その半分のあいだ H を出す(duty 50%)と、その高さの音が鳴る。2kHz なら 1 周期 500µs → ARR = 499、CCR = 250。
 *
 * ■ 長さ
 * buzzer_beep() は鳴らし始めて、止める時刻を覚えてすぐ戻る(待たない)。
 * 止めるのは buzzer_update()(4kHz の処理から毎回呼ぶ。sys/scheduler.c)。
 */
#include "drv/buzzer.h"

#include "drv/timebase.h"
#include "main.h"
#include "tim.h"

#define BUZZER_TIMER_CLOCK_HZ 1000000  /* TIM17 が数える速さ [Hz] */

static volatile bool s_mute = false;         /* true なら鳴らさない(パラメータで切れる) */
static volatile bool s_sounding = false;     /* 今鳴っているか */
static volatile uint32_t s_stop_at_ms = 0;   /* 止める時刻 [ms] */

/* 起動時に呼ぶ。鳴らさずに PWM を動かしておく(CCR = 0 なので音は出ない) */
void buzzer_init(void)
{
  __HAL_TIM_SET_COMPARE(&htim17, TIM_CHANNEL_1, 0);
  HAL_TIM_PWM_Start(&htim17, TIM_CHANNEL_1);
}

/* true なら、これから鳴らさない(鳴っていれば止める) */
void buzzer_set_mute(bool mute)
{
  s_mute = mute;
  if (mute) {
    buzzer_stop();
  }
}

/* frequency_hz [Hz] の音を length_ms [ms] 鳴らす(待たずに戻る) */
void buzzer_beep(uint32_t frequency_hz, uint32_t length_ms)
{
  if (s_mute || frequency_hz == 0) {
    return;
  }
  uint32_t period_count = BUZZER_TIMER_CLOCK_HZ / frequency_hz;  /* 1 周期のカウント数 */
  __HAL_TIM_SET_AUTORELOAD(&htim17, period_count - 1);
  __HAL_TIM_SET_COMPARE(&htim17, TIM_CHANNEL_1, period_count / 2);
  s_stop_at_ms = timebase_get_ms() + length_ms;
  s_sounding = true;
}

/* すぐ止める */
void buzzer_stop(void)
{
  __HAL_TIM_SET_COMPARE(&htim17, TIM_CHANNEL_1, 0);
  s_sounding = false;
}

/* 止める時刻になっていれば止める(4kHz の処理から毎回呼ぶ) */
void buzzer_update(void)
{
  if (!s_sounding) {
    return;
  }
  /* 「今 − 止める時刻」が 0 以上なら時刻を過ぎた(int32_t にすると、時刻が 0 に戻ったときも正しく比べられる) */
  int32_t past_ms = (int32_t)(timebase_get_ms() - s_stop_at_ms);
  if (past_ms >= 0) {
    buzzer_stop();
  }
}
