#![allow(unused)]

pub const DATA_PAYLOAD_SIZE: usize = 12;

/// DataOpCode: Data to send in response to ControlOpcode
#[derive(Copy, Clone)]
pub enum DataOpcode {
    BatteryVoltage(u32), // Not currently supported
    Weight(f32, u32),
    LowPowerWarning, // Not currently supported
    AppVersion(&'static [u8]),
    ProgressorId(u8),
}

impl DataOpcode {
    fn opcode(&self) -> u8 {
        match self {
            DataOpcode::BatteryVoltage(..)
                | DataOpcode::AppVersion(..)
                | DataOpcode::ProgressorId(..) => 0x00,
            DataOpcode::Weight(..) => 0x01,
            DataOpcode::LowPowerWarning => 0x04,
        }
    }

    fn length(&self) -> u8 {
        match self {
            DataOpcode::BatteryVoltage(..) => 4,
            DataOpcode::Weight(..) => 8,
            DataOpcode::ProgressorId(..) => 1,
            DataOpcode::LowPowerWarning => 0,
            DataOpcode::AppVersion(version) => version.len() as u8,
        }
    }

    fn value(&self) -> [u8; DATA_PAYLOAD_SIZE] {
        let mut value = [0; DATA_PAYLOAD_SIZE];
        match self {
            DataOpcode::BatteryVoltage(voltage) => {
                value[0..4].copy_from_slice(&voltage.to_le_bytes());
            }
            DataOpcode::Weight(weight, timestamp) => {
                value[0..4].copy_from_slice(&weight.to_le_bytes());
                value[4..8].copy_from_slice(&timestamp.to_le_bytes());
            }
            DataOpcode::LowPowerWarning => (),
            DataOpcode::ProgressorId(id) => {
                value[0..1].copy_from_slice(&id.to_le_bytes());
            }
            DataOpcode::AppVersion(version) => {
                value[0..version.len()].copy_from_slice(version);
            }
        };
        value
    }

    pub fn to_bytes(&self) -> [u8; DATA_PAYLOAD_SIZE + 2] {
        let mut buf = [0u8; DATA_PAYLOAD_SIZE + 2];
        buf[0] = self.opcode();
        buf[1] = self.length();
        buf[2..].copy_from_slice(&self.value());
        buf
    }

}

/// ControlOpcode: command received
#[derive(Copy, Clone)]
pub enum ControlOpcode {
    Tare,
    StartMeasurement,
    StopMeasurement,
    StartPeakRfdMeasurement,
    StartPeakRfdMeasurementSeries,
    GetAppVersion,
    GetErrorInfo,
    ClearErrorInfo,
    SampleBattery,
    GetProgressorID,
    Unknown(u8),
    Invalid,
}

impl ControlOpcode {
    pub fn is_known_opcode(&self) -> bool {
        !matches!(self, Self::Unknown(_) | Self::Invalid)
    }

    pub fn from_bytes(data: &[u8]) -> Self {
        if data.is_empty() {
            return ControlOpcode::Invalid;
        }
        match data[0] {
            0x64 => ControlOpcode::Tare,
            0x65 => ControlOpcode::StartMeasurement,
            0x66 => ControlOpcode::StopMeasurement,
            0x67 => ControlOpcode::StartPeakRfdMeasurement,
            0x68 => ControlOpcode::StartPeakRfdMeasurementSeries,
            0x6B => ControlOpcode::GetAppVersion,
            0x6C => ControlOpcode::GetErrorInfo,
            0x6D => ControlOpcode::ClearErrorInfo,
            0x6F => ControlOpcode::SampleBattery,
            0x70 => ControlOpcode::GetProgressorID,
            other => ControlOpcode::Unknown(other),
        }
    }

    pub fn name(&self) -> &'static str {
        match self {
            ControlOpcode::Tare                          => "Tare",
            ControlOpcode::StartMeasurement              => "StartMeasurement",
            ControlOpcode::StopMeasurement               => "StopMeasurement",
            ControlOpcode::StartPeakRfdMeasurement       => "StartPeakRfdMeasurement",
            ControlOpcode::StartPeakRfdMeasurementSeries => "StartPeakRfdMeasurementSeries",
            ControlOpcode::GetAppVersion                 => "GetAppVersion",
            ControlOpcode::GetErrorInfo                  => "GetErrorInfo",
            ControlOpcode::ClearErrorInfo                => "ClearErrorInfo",
            ControlOpcode::SampleBattery                 => "SampleBattery",
            ControlOpcode::GetProgressorID               => "Get ProgressorId",
            ControlOpcode::Unknown(_)                    => "Unknown",
            ControlOpcode::Invalid                       => "Invalid",
        }
    }
}
