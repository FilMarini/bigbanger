use embassy_futures::{join::join, select::select};
use static_cell::StaticCell;
use trouble_host::prelude::*;
use alloc::format;

use esp_radio::ble::controller::BleConnector;
use crate::measurement::{MEASUREMENT_CMD, MEASUREMENT_DATA, MeasurementCommand};
use crate::datapoint::{ControlOpcode, DataOpcode};
use super::gatt::Server;
use crate::utils::{debug_info, debug_warn};
use super::BLE_CONNECTED;
use super::{PROGRESSOR_NAME, APP_VERSION, DEVICE_ID};

/// Max number of connections and channels
const CONNECTIONS_MAX: usize = 1;
const L2CAP_CHANNELS_MAX: usize = 2;

/// Entry point for BLE operation
pub async fn run_ble(bt_peripheral: esp_hal::peripherals::BT<'_>) {
    static RADIO: StaticCell<esp_radio::Controller<'static>> = StaticCell::new();
    let radio = RADIO.init(esp_radio::init().unwrap());
    let connector = BleConnector::new(radio, bt_peripheral, Default::default()).unwrap();
    let controller: ExternalController<_, 20> = ExternalController::new(connector);
    let mut resources: HostResources<DefaultPacketPool, CONNECTIONS_MAX, L2CAP_CHANNELS_MAX> =
        HostResources::new();
    let stack = trouble_host::new(controller, &mut resources);
    let Host { mut peripheral, runner, .. } = stack.build();

    let server = Server::new_with_config(GapConfig::Peripheral(PeripheralConfig {
        name: PROGRESSOR_NAME,
        appearance: &appearance::power_device::GENERIC_POWER_DEVICE,
    }))
        .unwrap();

    debug_info("[ble] starting advertising and GATT service");

    let _ = join(ble_task(runner), async {
        loop {
            match advertise(PROGRESSOR_NAME, &mut peripheral, &server).await {
                Ok(conn) => {
                    BLE_CONNECTED.signal(true);
                    debug_info("[BLE] Connected");
                    let a = gatt_events_task(&server, &conn);
                    let b = data_notify_task(&server, &conn);
                    select(a, b).await;
                    BLE_CONNECTED.signal(false);
                    debug_info("[BLE] Disconnected");
                }
                Err(e) => {
                    debug_warn(&format!("[BLE] advertising error: {:?}", e));
                }
            }
        }
    })
    .await;
}

/// Runs the main BLE host loop forever.
async fn ble_task<C: Controller, P: PacketPool>(mut runner: Runner<'_, C, P>) {
    loop {
        if let Err(e) = runner.run().await {
            debug_warn(&format!("[ble_task] error: {:?}", e));
        }
    }
}

/// Create an advertiser to use to connect to a BLE Central, and wait for it to connect.
async fn advertise<'values, 'server, C: Controller>(
    name: &'values str,
    peripheral: &mut Peripheral<'values, C, DefaultPacketPool>,
    server: &'server Server<'values>,
) -> Result<GattConnection<'values, 'server, DefaultPacketPool>, BleHostError<C::Error>> {
    let mut advertiser_data = [0; 31];
    let len = AdStructure::encode_slice(
        &[
            AdStructure::Flags(LE_GENERAL_DISCOVERABLE | BR_EDR_NOT_SUPPORTED),
            AdStructure::ServiceUuids16(&[[0x0f, 0x18]]),
            AdStructure::CompleteLocalName(name.as_bytes()),
        ],
        &mut advertiser_data[..],
    )?;
    let advertiser = peripheral
        .advertise(
            &Default::default(),
            Advertisement::ConnectableScannableUndirected {
                adv_data: &advertiser_data[..len],
                scan_data: &[],
            },
        )
        .await?;
    debug_info("[adv] advertising");
    let conn = advertiser.accept().await?.with_attribute_server(server)?;
    Ok(conn)
}

/// Handles GATT read/write events for control and data characteristics.
async fn gatt_events_task<P: PacketPool>(
    server: &Server<'_>,
    conn: &GattConnection<'_, '_, P>,
) -> Result<(), Error> {
    let data_point = server.progressor_service.data_point;
    let control_point = server.progressor_service.control_point;

    let reason = loop {
        match conn.next().await {
            GattConnectionEvent::Disconnected { reason } => break reason,
            GattConnectionEvent::Gatt { event } => match &event {
                GattEvent::Write(e) if e.handle() == control_point.handle => {
                    let data = e.data();
                    debug_info(&format!("[gatt] Control Write: {:?}", ControlOpcode::from_bytes(data).name()));
                    match ControlOpcode::from_bytes(data) {
                        ControlOpcode::GetProgressorID => {
                            let response = DataOpcode::ProgressorId(DEVICE_ID.parse().unwrap());
                            if data_point.notify(conn, &response.to_bytes()).await.is_err() {
                                debug_warn("[gatt] Failed to notify data point");
                            }
                        }
                        ControlOpcode::GetAppVersion => {
                            let response = DataOpcode::AppVersion(APP_VERSION.as_bytes());
                            if data_point.notify(conn, &response.to_bytes()).await.is_err(){
                                debug_warn("[gatt] Failed to notify data point");
                            }
                        }
                        ControlOpcode::SampleBattery => {  // Not working, not even with the placeholder value, why??
                            let response = DataOpcode::BatteryVoltage(env!("FAKE_BATTERY_VOLTAGE").parse().unwrap());
                            if data_point.notify(conn, &response.to_bytes()).await.is_err(){
                                debug_warn("[gatt] Failed to notify data point");
                            }
                        }
                        ControlOpcode::StartMeasurement => {
                            MEASUREMENT_CMD.signal(MeasurementCommand::Start);
                        }
                        ControlOpcode::StopMeasurement => {
                            MEASUREMENT_CMD.signal(MeasurementCommand::Stop);
                        }
                        ControlOpcode::Tare => {
                            MEASUREMENT_CMD.signal(MeasurementCommand::Tare);
                        }
                        ControlOpcode::Unknown(code) => {
                            debug_warn(&format!("Unknown with code {:?}", code));
                        }
                        _ => {}
                    }
                }
                _ => {}
            },
            _ => {}
        }
    };

    debug_info(&format!("[gatt] disconnected: {:?}", reason));
    Ok(())
}

/// Forwards measurement packets to the BLE client using notifications.
async fn data_notify_task<P: PacketPool>(
    server: &Server<'_>,
    conn: &GattConnection<'_, '_, P>,
) {
    let data_point = server.progressor_service.data_point;
    loop {
        let packet = MEASUREMENT_DATA.receive().await;
        if data_point.notify(conn, &packet.to_bytes()).await.is_err() {
            debug_warn("[notify] connection closed");
            break;
        }
    }
}
