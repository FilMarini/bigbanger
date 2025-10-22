use crate::datapoint::DATA_PAYLOAD_SIZE;
use trouble_host::prelude::*;

#[gatt_server]
pub struct Server {
    pub progressor_service: ProgressorService,
}

#[gatt_service(uuid = "7e4e1701-1ea6-40c9-9dcc-13d34ffead57")]
pub struct ProgressorService {
    #[characteristic(
        uuid = "7e4e1702-1ea6-40c9-9dcc-13d34ffead57",
        notify,
        value = [0; DATA_PAYLOAD_SIZE + 2]
    )]
    pub data_point: [u8; DATA_PAYLOAD_SIZE + 2],

    #[characteristic(
        uuid = "7e4e1703-1ea6-40c9-9dcc-13d34ffead57",
        write,
        write_without_response,
        read,
        value = [0]
    )]
    pub control_point: [u8; 1],
}

