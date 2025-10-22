#![allow(unused)]

use aligned::{Aligned, A32};
use crc::{Crc, CRC_32_ISCSI};
use esp_storage::FlashStorage;
use embedded_storage::nor_flash::{NorFlash, ReadNorFlash};
use crate::utils::{debug_info, debug_warn};
use alloc::format;

const DEFAULT_CALIB_VALUE: &str = env!("DEFAULT_CALIB_VALUE");
const CAL_ADDR: u32 = 0x110000;
const CHK_ADDR: u32 = CAL_ADDR + 4;
const SECTOR_SIZE: u32 = 4096;

fn comp_checksum(bytes: &[u8]) -> [u8; 4] {
    let crc = Crc::<u32>::new(&CRC_32_ISCSI);
    crc.checksum(bytes).to_le_bytes()
}

pub struct CalibrationMem<'a> {
    flash: FlashStorage<'a>,
    pub calib: f32,
    checksum : u32,

}

impl<'a> CalibrationMem<'a> {
    pub fn new(flash: FlashStorage<'a>) -> Self {
        // Create initial CalibrationMem
        let mut new = Self {
            flash: flash,
            calib: DEFAULT_CALIB_VALUE.parse().unwrap(),
            checksum: 0u32,
        };
        let mut buf: Aligned<A32, [u8; 4]> = Aligned([0u8; 4]);
        // Read value in storage
        new.flash.read(CAL_ADDR, buf.as_mut()).unwrap();
        let cal = f32::from_le_bytes(*buf);
        // Compute checksum
        let computed_checksum = u32::from_le_bytes(comp_checksum(&*buf));
        // Read checksum from storage
        new.flash.read(CHK_ADDR, buf.as_mut()).unwrap();
        let checksum = u32::from_le_bytes(*buf);
        // If same, set values, else load default
        if computed_checksum == checksum {
            debug_info("Checksum match!");
            new.calib = cal;
            new.checksum = checksum;
        } else {
            debug_warn("Checksum does not match! Wrote default value");
            new.checksum = u32::from_le_bytes(comp_checksum(&new.calib.to_le_bytes()));
            new.set_in_memory();
        }
        new
    }

    fn set_in_memory(&mut self) {
        let checksum = self.checksum;
        let computed_checksum = u32::from_le_bytes(comp_checksum(&self.calib.to_le_bytes()));
        if checksum == computed_checksum {
            self.flash.erase(CAL_ADDR, CAL_ADDR + SECTOR_SIZE).unwrap();
            let cal_bytes: Aligned<A32, [u8; 4]> = Aligned(self.calib.to_le_bytes());
            let checksum_bytes: Aligned<A32, [u8; 4]> = Aligned(comp_checksum(&self.calib.to_le_bytes()));
            self.flash.write(CAL_ADDR, cal_bytes.as_ref()).unwrap();
            self.flash.write(CHK_ADDR, checksum_bytes.as_ref()).unwrap();
        }
    }

    pub fn set_calibration(&mut self, cal: f32) {
        let computed_checksum = u32::from_le_bytes(comp_checksum(&cal.to_le_bytes()));
        self.calib = cal;
        self.checksum = computed_checksum;
        self.set_in_memory();
    }
}
