# KOGUMA MK4 の STM32H562 のブートローダ(Flash の先頭 64KB)。ビルド: cmake --preset Debug && cmake --build --preset Debug
cmake_minimum_required(VERSION 3.22)
project(KOGUMA-Mk4-bootloader C ASM)

set(HAL Drivers/STM32H5xx_HAL_Driver)

add_executable(${PROJECT_NAME}
    App/boot_main.c
    App/boot_uart.c
    App/boot_flash.c
    App/boot_lines.c
    App/base64.c
    App/crc32.c
    Core/Src/stm32h5xx_it.c
    Core/Src/system_stm32h5xx.c
    Core/Src/crt_stubs.c
    Core/Startup/startup_stm32h562xx.s
    ${HAL}/Src/stm32h5xx_hal.c
    ${HAL}/Src/stm32h5xx_hal_cortex.c
    ${HAL}/Src/stm32h5xx_hal_rcc.c
    ${HAL}/Src/stm32h5xx_hal_rcc_ex.c
    ${HAL}/Src/stm32h5xx_hal_gpio.c
    ${HAL}/Src/stm32h5xx_hal_uart.c
    ${HAL}/Src/stm32h5xx_hal_uart_ex.c
    ${HAL}/Src/stm32h5xx_hal_flash.c
    ${HAL}/Src/stm32h5xx_hal_flash_ex.c
    ${HAL}/Src/stm32h5xx_hal_pwr.c
    ${HAL}/Src/stm32h5xx_hal_pwr_ex.c
    ${HAL}/Src/stm32h5xx_hal_dma.c
    ${HAL}/Src/stm32h5xx_hal_dma_ex.c
    ${HAL}/Src/stm32h5xx_hal_exti.c
)

target_include_directories(${PROJECT_NAME} PRIVATE
    App
    Core/Inc
    ${HAL}/Inc
    Drivers/CMSIS/Device/ST/STM32H5xx/Include
    Drivers/CMSIS/Include
)

target_compile_definitions(${PROJECT_NAME} PRIVATE STM32H562xx USE_HAL_DRIVER)

# 自分で書いた所(App/)だけ警告を全部見る
set_source_files_properties(App/boot_main.c App/boot_uart.c App/boot_flash.c App/boot_lines.c App/base64.c App/crc32.c
    PROPERTIES COMPILE_OPTIONS "-Wall;-Wextra")

target_link_options(${PROJECT_NAME} PRIVATE
    -T${CMAKE_SOURCE_DIR}/STM32H562RGVX_BOOT.ld
    -Wl,-Map=${PROJECT_NAME}.map
)

# .hex と .bin も作る(STM32CubeProgrammer・pyOCD で書く)
add_custom_command(TARGET ${PROJECT_NAME} POST_BUILD
    COMMAND ${CMAKE_OBJCOPY} -O ihex $<TARGET_FILE:${PROJECT_NAME}> ${PROJECT_NAME}.hex
    COMMAND ${CMAKE_OBJCOPY} -O binary $<TARGET_FILE:${PROJECT_NAME}> ${PROJECT_NAME}.bin
)
