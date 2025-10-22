mod gatt;
mod run;
use embassy_sync::{blocking_mutex::raw::CriticalSectionRawMutex, signal::Signal};

pub const PROGRESSOR_NAME: &str = env!("PROGRESSOR_NAME");
pub const APP_VERSION: &str = env!("APP_VERSION");
pub const DEVICE_ID: &str = env!("DEVICE_ID");

pub static BLE_CONNECTED: Signal<CriticalSectionRawMutex, bool> = Signal::new();

pub use run::run_ble;
