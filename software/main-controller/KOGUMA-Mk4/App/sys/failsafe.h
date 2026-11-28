/*
 * failsafe.h
 * フェイルセーフ(中身は failsafe.c)。ToraNeko.Mk3 の App/sys/failsafe.h から。止めたわけとハードの見張りを足した
 */
#ifndef SYS_FAILSAFE_H
#define SYS_FAILSAFE_H

#include <stdbool.h>

/* 止めたわけ */
typedef enum {
  FAILSAFE_REASON_NONE = 0,     /* 止めていない */
  FAILSAFE_REASON_CONTROL,      /* 位置・角度のずれ、速さの異常(ctrl/control.c。わけの細かい所は control_get_failsafe_reason()) */
  FAILSAFE_REASON_OVERCURRENT,  /* モーターの電流が大きすぎた(ctrl/current_ctrl.c) */
  FAILSAFE_REASON_MOTOR_FAULT,  /* MP6551 が異常を知らせた(nFAULT) */
  FAILSAFE_REASON_ENCODER,      /* エンコーダの読み取りのエラーが続いた */
  FAILSAFE_REASON_STOP_COMMAND, /* コマンドの stop */
} failsafe_reason_t;

bool failsafe_is_stopped(void);
void failsafe_clear(void);
void failsafe_stop(void);
void failsafe_stop_with_reason(failsafe_reason_t reason);
failsafe_reason_t failsafe_get_reason(void);
const char *failsafe_get_reason_name(failsafe_reason_t reason);
void failsafe_check_hardware(void);

#endif /* SYS_FAILSAFE_H */
