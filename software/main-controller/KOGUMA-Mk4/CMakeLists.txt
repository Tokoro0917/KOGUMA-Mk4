cmake_minimum_required(VERSION 3.22)

#
# KOGUMA MK4 の走るプログラム(STM32H562RGV6)。ToraNeko.Mk3 の CMakeLists.txt と同じ形(2026-11-28 に手で書いた)。
# CubeMX が最初の 1 回だけ作るファイルと同じ考えで、App/ の追加はここに書く。
# ビルド: cmake --preset Debug && cmake --build --preset Debug
#

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS ON)

if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE "Debug")
endif()

set(CMAKE_PROJECT_NAME KOGUMA-Mk4)
set(CMAKE_EXPORT_COMPILE_COMMANDS TRUE)

project(${CMAKE_PROJECT_NAME})
message("Build type: " ${CMAKE_BUILD_TYPE})

enable_language(C ASM)

add_executable(${CMAKE_PROJECT_NAME})

# Core/・Drivers/(CubeMX が作る形)
add_subdirectory(cmake/stm32cubemx)

# User sources (App/). Add one file per line as each step is implemented
set(APP_SOURCES
    App/app.c
    App/ctrl/control.c
    App/ctrl/current_ctrl.c
    App/ctrl/odometry.c
    App/ctrl/run.c
    App/ctrl/side_edge.c
    App/ctrl/trajectory.c
    App/ctrl/wall_ctrl.c
    App/ctrl/wall_dist.c
    App/drv/boot.c
    App/drv/buzzer.c
    App/drv/current.c
    App/drv/encoder.c
    App/drv/fan.c
    App/drv/flash_memory.c
    App/drv/imu.c
    App/drv/led.c
    App/drv/motor.c
    App/drv/switch.c
    App/drv/timebase.c
    App/drv/uart.c
    App/drv/wall.c
    App/drv/watchdog.c
    App/maze/maze_map.c
    App/maze/search.c
    App/maze/path.c
    App/maze/dijkstra.c
    App/sys/adjust.c
    App/sys/cmd.c
    App/sys/encoder_cal.c
    App/sys/explore.c
    App/sys/failsafe.c
    App/sys/flash.c
    App/sys/goal.c
    App/sys/log.c
    App/sys/mode.c
    App/sys/motor_test.c
    App/sys/output.c
    App/sys/params.c
    App/sys/scheduler.c
    App/sys/sensor_record.c
    App/sys/venue.c
    App/sys/shortest.c
    App/sys/suction.c
    App/sys/turn_test.c
    App/sys/edge_test.c
    App/sys/sensor_view.c
    App/sys/ui.c
)

target_sources(${CMAKE_PROJECT_NAME} PRIVATE
    ${APP_SOURCES}
)

target_include_directories(${CMAKE_PROJECT_NAME} PRIVATE
    App
)

# 走るプログラムは 0x08010000 から(先頭の 64KB はブートローダ)。SystemInit() がベクタテーブルの場所(VTOR)をここにする
target_compile_definitions(${CMAKE_PROJECT_NAME} PRIVATE
    VECT_TAB_OFFSET=0x00010000U
)
target_compile_definitions(STM32_Drivers PRIVATE
    VECT_TAB_OFFSET=0x00010000U
)

# Warnings for user code only (App/); generated HAL code is left as is。
# -Wdouble-promotion(float が double になる所の警告)は付けない: printf の %f に float を渡すと必ず double になり、
# 消すには型のキャストを書くしかないため(CLAUDE.md の「printf のための型キャスト」を避ける)
set_source_files_properties(${APP_SOURCES} PROPERTIES COMPILE_OPTIONS "-Wall;-Wextra")

# 走っているあいだに時間がかかる計算(迷路の計算と、割り込みで動く制御)だけは、Debug でも速くなるようにビルドする(-O2)。
# ToraNeko の APP_FAST_SOURCES と同じ。MK4 は電流の制御(20kHz)と、それが使うドライバも入れる
set(APP_FAST_SOURCES
    App/maze/maze_map.c
    App/maze/search.c
    App/maze/path.c
    App/maze/dijkstra.c
    App/ctrl/control.c
    App/ctrl/current_ctrl.c
    App/ctrl/odometry.c
    App/ctrl/trajectory.c
    App/ctrl/wall_ctrl.c
    App/ctrl/wall_dist.c
    App/drv/current.c
    App/drv/encoder.c
    App/drv/motor.c
    App/drv/wall.c
    App/sys/scheduler.c
    App/sys/log.c
)
set_source_files_properties(${APP_FAST_SOURCES} PROPERTIES COMPILE_OPTIONS "-Wall;-Wextra;-O2")

list(REMOVE_ITEM CMAKE_C_IMPLICIT_LINK_LIBRARIES ob)

target_link_libraries(${CMAKE_PROJECT_NAME}
    stm32cubemx
)

# リンカの設定と、printf で小数(%f)を出せるようにする(ToraNeko と同じ)
target_link_options(${CMAKE_PROJECT_NAME} PRIVATE
    -T${CMAKE_SOURCE_DIR}/STM32H562RGVX_FLASH.ld
    -Wl,-Map=${CMAKE_PROJECT_NAME}.map
    -u _printf_float
)

# .hex と .bin も作る(.bin は無線・有線の書き込み tools/fw.py・ビューアで使う)
add_custom_command(TARGET ${CMAKE_PROJECT_NAME} POST_BUILD
    COMMAND ${CMAKE_OBJCOPY} -O ihex $<TARGET_FILE:${CMAKE_PROJECT_NAME}> ${CMAKE_PROJECT_NAME}.hex
    COMMAND ${CMAKE_OBJCOPY} -O binary $<TARGET_FILE:${CMAKE_PROJECT_NAME}> ${CMAKE_PROJECT_NAME}.bin
)
