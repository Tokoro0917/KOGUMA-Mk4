/*
 * switch.h
 * スイッチ SW2 の読み取り(MK4 の SW1 は電源)
 */
#ifndef DRV_SWITCH_H
#define DRV_SWITCH_H

#include <stdbool.h>

bool switch_is_pressed(void);

#endif /* DRV_SWITCH_H */
