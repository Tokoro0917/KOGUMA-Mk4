/*
 * mk4_imu.c
 * MK4 の IMU(LSM6DSR、SPI3 + DMA、約 6.66kHz)。
 * 流れ: INT1(データの準備ができた)の割り込みで imu_start_read() → SPI3 の DMA の終わりで imu_process()。
 * imu_process() の中身は ToraNeko の drv/imu.c の imu_update() の後ろ半分(SPI で読んだあと)と同じ。
 * 周期だけ IMU の更新の周期(1/6660 秒)にした。
 */
#include "drv/imu.h"

#include "bench_mark.h"
#include "mk4_hw.h"

#define READ_FLAG 0x80
#define REG_OUTZ_L_G 0x26
#define GYRO_DPS_PER_LSB 0.14f
#define ACCEL_MPS2_PER_LSB 0.0023928f
#define GYRO_Z_SIGN 1
#define OFFSET_SAMPLE_COUNT 3330
#define IMU_FREQ_HZ 6660

DMA_BUF uint8_t g_imu_rx[8];

static volatile float s_gyro_z_dps = 0.0f;
static volatile float s_angle_deg = 0.0f;
static volatile float s_accel_x_mps2 = 0.0f;
static volatile float s_accel_y_mps2 = 0.0f;
static volatile float s_gyro_offset_dps = 0.0f;
static volatile float s_offset_sum_dps = 0.0f;
static volatile int s_offset_count = 0;
static volatile bool s_offset_ready = true;
static volatile uint32_t s_sample_count = 0;

/* ToraNeko の drv/imu.c と同じ */
static int32_t to_signed(uint8_t low, uint8_t high)
{
  int32_t value = high * 256 + low;
  if (value >= 32768) {
    value = value - 65536;
  }
  return value;
}

static void measure_offset(float raw_dps)
{
  s_offset_sum_dps = s_offset_sum_dps + raw_dps;
  s_offset_count = s_offset_count + 1;
  if (s_offset_count >= OFFSET_SAMPLE_COUNT) {
    s_gyro_offset_dps = s_offset_sum_dps / OFFSET_SAMPLE_COUNT;
    s_angle_deg = 0.0f;
    s_offset_ready = true;
  }
}

/* INT1 の割り込みで呼ぶ。CS を Low にして、7 バイトの読み取りを始める */
void imu_start_read(void)
{
  hw_clear_imu_exti();
  hw_pin_low(IMU_CS_PORT, IMU_CS_PIN);
  hw_spi3_start(g_imu_rx, 7);
}

/* SPI3 の DMA の終わりで呼ぶ。角速度と加速度を読み、角度を進める */
void imu_process(void)
{
  hw_spi3_finish();
  hw_pin_high(IMU_CS_PORT, IMU_CS_PIN);
  s_sample_count = s_sample_count + 1;

  float raw_dps = GYRO_Z_SIGN * to_signed(g_imu_rx[1], g_imu_rx[2]) * GYRO_DPS_PER_LSB;
  s_accel_x_mps2 = to_signed(g_imu_rx[3], g_imu_rx[4]) * ACCEL_MPS2_PER_LSB;
  s_accel_y_mps2 = to_signed(g_imu_rx[5], g_imu_rx[6]) * ACCEL_MPS2_PER_LSB;

  if (!s_offset_ready) {
    measure_offset(raw_dps);
    return;
  }

  s_gyro_z_dps = raw_dps - s_gyro_offset_dps;
  s_angle_deg = s_angle_deg + s_gyro_z_dps / IMU_FREQ_HZ;
}

float imu_get_gyro_z_dps(void)
{
  return s_gyro_z_dps;
}

float imu_get_angle_deg(void)
{
  return s_angle_deg;
}

float imu_get_accel_x_mps2(void)
{
  return s_accel_x_mps2;
}

float imu_get_accel_y_mps2(void)
{
  return s_accel_y_mps2;
}

bool imu_is_offset_ready(void)
{
  return s_offset_ready;
}

uint32_t imu_get_sample_count(void)
{
  return s_sample_count;
}

void imu_bench_set(float omega_dps)
{
  int32_t raw = (int32_t)((omega_dps + 0.3f) / GYRO_DPS_PER_LSB);
  if (raw < 0) {
    raw = raw + 65536;
  }
  g_imu_rx[0] = 0;
  g_imu_rx[1] = (uint8_t)(raw % 256);  /* 角速度 Z */
  g_imu_rx[2] = (uint8_t)(raw / 256);
  g_imu_rx[3] = 0x10;  /* 加速度 X */
  g_imu_rx[4] = 0x02;
  g_imu_rx[5] = 0xF0;  /* 加速度 Y(マイナス) */
  g_imu_rx[6] = 0xFF;
  s_gyro_offset_dps = 0.3f;
}
