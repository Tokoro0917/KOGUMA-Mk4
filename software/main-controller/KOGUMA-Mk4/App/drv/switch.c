/*
 * switch.c
 * スイッチ SW2 の読み取り(ToraNeko.Mk3 の App/drv/switch.c から。MK4 は SW2、押すと L)
 *
 * SW2 は PC14(ラベル SW)。外付けの 10kΩ で引き上げてあり、押すと Low、離すと High(ToraNeko とは逆)。
 * ピン名(SW_GPIO_Port、SW_Pin)は Core/Inc/main.h にある。
 * チャタリング（押した瞬間に High と Low が何回か入れ替わること）は、読む側（sys/ui.c）で取り除く。
 */
#include "drv/switch.h"

#include "main.h"

/* 今、スイッチが押されていれば true */
bool switch_is_pressed(void)
{
  if (HAL_GPIO_ReadPin(SW_GPIO_Port, SW_Pin) == GPIO_PIN_RESET) {
    return true;
  }
  return false;
}
