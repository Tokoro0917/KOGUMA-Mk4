/*
 * buzzer.h
 * ブザー(TIM17 の PWM、PB9)。MK4 で足したもの(ToraNeko にはない。KOGUMA にはある)
 */
#ifndef DRV_BUZZER_H
#define DRV_BUZZER_H

#include <stdbool.h>
#include <stdint.h>

void buzzer_init(void);
void buzzer_set_mute(bool mute);
void buzzer_beep(uint32_t frequency_hz, uint32_t length_ms);
void buzzer_stop(void);
void buzzer_update(void);

#endif /* DRV_BUZZER_H */
