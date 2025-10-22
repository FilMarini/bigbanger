#![no_std]
#![no_main]

extern crate alloc;

mod ble;
mod measurement;
mod datapoint;
mod utils;
mod calibration_mem;
use embassy_executor::Spawner;
use esp_hal::{clock::CpuClock, gpio::{Input, InputConfig, Level, Output, OutputConfig, Pull}, timer::timg::TimerGroup};
use esp_alloc as _;
use esp_backtrace as _;
use esp_storage::FlashStorage;
use utils::debug_info;
use embassy_sync::mutex::Mutex;
use measurement::{HX711BB, LOAD_SENSOR};
#[cfg(target_arch = "riscv32")]
use esp_hal::interrupt::software::SoftwareInterruptControl;

esp_bootloader_esp_idf::esp_app_desc!();

#[esp_rtos::main]
async fn main(spawner: Spawner) {
    esp_println::logger::init_logger_from_env();
    let peripherals = esp_hal::init(esp_hal::Config::default().with_cpu_clock(CpuClock::max()));
    esp_alloc::heap_allocator!(size: 72 * 1024);

    let timg0 = TimerGroup::new(peripherals.TIMG0);
    #[cfg(target_arch = "riscv32")]
    let sw_int = SoftwareInterruptControl::new(peripherals.SW_INTERRUPT);

    esp_rtos::start(
        timg0.timer0,
        #[cfg(target_arch = "riscv32")]
        sw_int.software_interrupt0,
    );

    // --- GPIO Setup ---
    let hx711_sck = Output::new(peripherals.GPIO5, Level::Low, OutputConfig::default());
    let hx711_dt = Input::new(peripherals.GPIO6, InputConfig::default());
    let calib_config = InputConfig::default().with_pull(Pull::Up);
    let calib_button = Input::new(peripherals.GPIO9, calib_config);
    let led_config = OutputConfig::default().with_pull(Pull::Down);
    let led = Output::new(peripherals.GPIO4, Level::Low, led_config);
    // --- Peripherals Setup ---
    let flash = FlashStorage::new(peripherals.FLASH);
    let mut hx711_bb = HX711BB::new(flash, hx711_sck, hx711_dt);

    // Wait for the HX711 to stabilize
    while !hx711_bb.is_ready() {
        debug_info("Waiting for HX711 to power up");
        embassy_time::Timer::after_millis(1000).await;
    }
    hx711_bb.set_scale_from_memory();
    hx711_bb.tare(32);
    embassy_time::Timer::after_millis(1000).await;
    hx711_bb.tare(32);
    debug_info("Load sensor tared!");
    let shared_hx711_bb = LOAD_SENSOR.init(Mutex::new(hx711_bb));

    // --- Start Measurement and Calibration Task ---
    spawner.spawn(measurement::start_measurement_task(shared_hx711_bb)).unwrap();
    spawner.spawn(measurement::run_calibration(shared_hx711_bb, calib_button, led, env!("TIME_TO_CALIBRATION").parse().unwrap())).unwrap();

    // --- BLE Setup ---
    ble::run_ble(peripherals.BT).await;
}
