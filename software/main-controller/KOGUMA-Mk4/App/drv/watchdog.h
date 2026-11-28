/*
 * watchdog.h
 * ウォッチドッグ(IWDG、約 50ms)。中身は watchdog.c
 */
#ifndef DRV_WATCHDOG_H
#define DRV_WATCHDOG_H

#include <stdbool.h>

void watchdog_start(void);
void watchdog_refresh(void);
bool watchdog_was_reset(void);

#endif /* DRV_WATCHDOG_H */
