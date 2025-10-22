#![allow(unused)]

use embassy_sync::mutex::Mutex;
use embassy_sync::channel::Channel;
use embassy_sync::signal::Signal;
use embassy_sync::blocking_mutex::raw::CriticalSectionRawMutex;
use embassy_time::Instant;
use embassy_time::Timer;
use esp_storage::FlashStorage;
use static_cell::StaticCell;
use loadcell::hx711::HX711;
use loadcell::LoadCell;
use esp_hal::gpio::{Input, Output};
use esp_hal::delay::Delay;
use alloc::format;
use crate::datapoint::DataOpcode;
use crate::calibration_mem::CalibrationMem;
use crate::utils::{debug_info, debug_warn};

#[derive(Copy, Clone, Debug)]
pub enum MeasurementCommand {
    Start,
    Stop,
    Tare,
}

// signal to start ot stop weight measurements
pub static MEASUREMENT_CMD: Signal<CriticalSectionRawMutex, MeasurementCommand> = Signal::new();
// channel to send measurement data to BLE task
pub static MEASUREMENT_DATA: Channel<CriticalSectionRawMutex, DataOpcode, 4> = Channel::new();

// Extend HX711
pub struct HX711BB<'a, Output, Input> {
    load_cell: HX711<Output, Input, Delay>,
    calibration_memory: CalibrationMem<'a>,
    start_time: Instant,
    _first_meas: i32,
    calibration_value: f32,
    _delay: Delay,
}

impl HX711BB<'static, Output<'static>, Input<'static>> {
    pub fn new(
        flash: FlashStorage<'static>,
        hx_clk: Output<'static>,
        hx_data: Input<'static>
    ) -> Self {
        let calibration_mem = CalibrationMem::new(flash);
        let delay = Delay::new();
        let hx711 = HX711::new(hx_clk, hx_data, delay);
        let calibration_val = calibration_mem.calib;
        let new = Self {
            load_cell: hx711,
            calibration_memory: calibration_mem,
            start_time: Instant::now(),
            _first_meas: 0i32,
            calibration_value: calibration_val,
            _delay: Delay::new(),
        };
        new
    }

    pub fn start_now(&mut self) {
        self.start_time = Instant::now();
    }

    pub async fn get_weight_packet(&mut self) -> DataOpcode {
        while !self.load_cell.is_ready() {
            Timer::after_millis(1).await;
        }
        if let Ok(weight) = self.load_cell.read_scaled() {
            let timestamp = self.start_time.elapsed().as_micros() as u32;
            return DataOpcode::Weight(weight, timestamp);
        } else {
            DataOpcode::Weight(0f32, 0u32)
        }
    }

    pub fn tare(&mut self, num_samples: usize) {
        self.load_cell.tare(num_samples);
    }

    pub fn is_ready(&mut self) -> bool {
        self.load_cell.is_ready()
    }

    pub fn set_scale(&mut self, cal_value: f32) {
        self.load_cell.set_scale(cal_value);
    }

    pub fn init_calibration(&mut self) {
        self._first_meas = self.load_cell.read().unwrap();
    }

    pub fn calibrate(&mut self) {
        let second_meas = self.load_cell.read().unwrap();
        self.calibration_value = 10.0 / ((second_meas - self._first_meas) as f32);
        debug_info(&format!("Load sensor calibrated with value {:?}", self.calibration_value));
        self.calibration_memory.set_calibration(self.calibration_value);
    }

    pub fn set_scale_from_memory(&mut self) {
        self.load_cell.set_scale(self.calibration_value);
        debug_info(&format!("Load sensor calibrated at {:?}", self.calibration_value));
    }
}

// StaticCell for load_sensor
pub static LOAD_SENSOR: StaticCell<Mutex<CriticalSectionRawMutex, HX711BB<Output<'static>, Input<'static>>>> = StaticCell::new();

mod task;
pub use task::start_measurement_task;
pub use task::run_calibration;

