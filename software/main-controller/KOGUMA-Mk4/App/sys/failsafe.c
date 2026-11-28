/*
 * failsafe.c
 * フェイルセーフで止まっているかを覚えておく。ToraNeko.Mk3 の App/sys/failsafe.c から(2026-11-28)
 *
 * 異常を見つけるのは ctrl/control.c(位置・角度のずれ、速さの異常。ToraNeko と同じ)と、
 * ここの failsafe_check_hardware()(MK4 で足した: 電流の守り、MP6551 の異常、エンコーダの読み取りのエラーが続いた)。
 * 止まったら、モーターと吸引を止めて、ログを止める(止まる直前の分が残る。docs/log.md の「直前をいつも残す」)。
 * 止まったわけは failsafe_get_reason() で読める(#STATUS とモード7 No.1 で出す)。
 */
#include "sys/failsafe.h"

#include "ctrl/current_ctrl.h"
#include "drv/encoder.h"
#include "drv/fan.h"
#include "drv/motor.h"
#include "sys/log.h"

#define ENCODER_ERROR_LIMIT 40  /* エンコーダの読み取りのエラーがこれだけ続いたら止める(4kHz で 10ms) */

/* フェイルセーフで止まっているか。割り込み(4kHz の処理)の中からも止められるようにするので volatile */
static volatile bool s_stopped = false;
static volatile failsafe_reason_t s_reason = FAILSAFE_REASON_NONE;
static volatile uint32_t s_last_encoder_errors = 0;
static volatile int s_encoder_error_ticks = 0;

/* フェイルセーフで止まっているとき true */
bool failsafe_is_stopped(void)
{
  return s_stopped;
}

/* フェイルセーフを解除する */
void failsafe_clear(void)
{
  s_stopped = false;
  s_reason = FAILSAFE_REASON_NONE;
  s_encoder_error_ticks = 0;
}

/* モーターと吸引ファンを止めて、フェイルセーフで止まった状態にする(わけは「制御」) */
void failsafe_stop(void)
{
  failsafe_stop_with_reason(FAILSAFE_REASON_CONTROL);
}

/* モーターと吸引ファンを止めて、フェイルセーフで止まった状態にする。reason は止めたわけ */
void failsafe_stop_with_reason(failsafe_reason_t reason)
{
  current_ctrl_stop();
  fan_stop();
  log_stop();
  if (!s_stopped) {
    s_reason = reason;  /* 最初に止めたわけを残す */
  }
  s_stopped = true;
}

/* 止めたわけ */
failsafe_reason_t failsafe_get_reason(void)
{
  return s_reason;
}

/* 止めたわけの名前(英数字。#STATUS に出す) */
const char *failsafe_get_reason_name(failsafe_reason_t reason)
{
  if (reason == FAILSAFE_REASON_CONTROL) {
    return "control";
  }
  if (reason == FAILSAFE_REASON_OVERCURRENT) {
    return "overcurrent";
  }
  if (reason == FAILSAFE_REASON_MOTOR_FAULT) {
    return "motor_fault";
  }
  if (reason == FAILSAFE_REASON_ENCODER) {
    return "encoder";
  }
  if (reason == FAILSAFE_REASON_STOP_COMMAND) {
    return "stop";
  }
  return "none";
}

/* エンコーダのエラーが続いているか(4kHz で毎回呼ぶ) */
static bool encoder_errors_continue(void)
{
  uint32_t errors = encoder_get_left_error_count() + encoder_get_right_error_count();
  if (errors != s_last_encoder_errors) {
    s_encoder_error_ticks = s_encoder_error_ticks + 1;
  } else {
    s_encoder_error_ticks = 0;
  }
  s_last_encoder_errors = errors;
  if (s_encoder_error_ticks >= ENCODER_ERROR_LIMIT) {
    return true;
  }
  return false;
}

/* ハードの異常を見る。4kHz の処理から毎回呼ぶ(sys/scheduler.c)。モーターを回しているときだけ止める */
void failsafe_check_hardware(void)
{
  bool encoder_bad = encoder_errors_continue();
  if (current_ctrl_is_tripped()) {
    failsafe_stop_with_reason(FAILSAFE_REASON_OVERCURRENT);
    return;
  }
  if (current_ctrl_get_mode() == CURRENT_CTRL_OFF) {
    return;
  }
  if (motor_is_fault()) {
    failsafe_stop_with_reason(FAILSAFE_REASON_MOTOR_FAULT);
    return;
  }
  if (encoder_bad) {
    failsafe_stop_with_reason(FAILSAFE_REASON_ENCODER);
  }
}
