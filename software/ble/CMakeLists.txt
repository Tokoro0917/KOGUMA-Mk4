# HY0020(nRF52832)のプログラム。nRF Connect SDK のアプリ(ボードは nrf52dk/nrf52832 を使う。README.md)
cmake_minimum_required(VERSION 3.20.0)

find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(koguma_mk4_ble)

target_sources(app PRIVATE
  src/main.c
  src/stm32_uart.c
  src/ble_link.c
  src/at_lines.c
)
