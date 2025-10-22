use log::{info, warn};
use esp_hal::gpio::Input;
use esp_hal::delay::Delay;

pub fn debug_info (sent: &str) {
    #[cfg(debug_assertions)]
    info!("{}", sent);
}

pub fn debug_warn (sent: &str) {
    #[cfg(debug_assertions)]
    warn!("{}", sent);
}

pub fn press_for_millis(button: &Input<'_>, millis: u32) -> bool {
    let mut checks = 0u32;
    let delay = Delay::new();
    if button.is_low() {
        debug_info("Starts checking..");
        while checks < millis {
            checks += 1;
            if button.is_high() {
                return false;
            }
            delay.delay_millis(1);
        }
        debug_info("Checking done!");
        return true;
    }
    false
}
