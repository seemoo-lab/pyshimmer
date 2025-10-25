from ..channels import EChannelType, ChannelDataType, ESensorGroup
from ..revision import BaseRevision


class Shimmer3Revision(BaseRevision):

    # Device clock rate in ticks per second
    DEV_CLOCK_RATE: float = 32768.0
    ENABLED_SENSORS_LEN = 0x03
    SENSOR_DTYPE = ChannelDataType(size=ENABLED_SENSORS_LEN, signed=False, le=True)

    CH_DTYPE_ASSIGNMENT: dict[EChannelType, ChannelDataType] = {
        EChannelType.ACCEL_LN_X: ChannelDataType(2, signed=True, le=True),
        EChannelType.ACCEL_LN_Y: ChannelDataType(2, signed=True, le=True),
        EChannelType.ACCEL_LN_Z: ChannelDataType(2, signed=True, le=True),
        EChannelType.VBATT: ChannelDataType(2, signed=True, le=True),
        EChannelType.ACCEL_WR_X: ChannelDataType(2, signed=True, le=True),
        EChannelType.ACCEL_WR_Y: ChannelDataType(2, signed=True, le=True),
        EChannelType.ACCEL_WR_Z: ChannelDataType(2, signed=True, le=True),
        EChannelType.MAG_REG_X: ChannelDataType(2, signed=True, le=True),
        EChannelType.MAG_REG_Y: ChannelDataType(2, signed=True, le=True),
        EChannelType.MAG_REG_Z: ChannelDataType(2, signed=True, le=True),
        EChannelType.GYRO_X: ChannelDataType(2, signed=True, le=False),
        EChannelType.GYRO_Y: ChannelDataType(2, signed=True, le=False),
        EChannelType.GYRO_Z: ChannelDataType(2, signed=True, le=False),
        EChannelType.EXTERNAL_ADC_A0: ChannelDataType(2, signed=False, le=True),
        EChannelType.EXTERNAL_ADC_A1: ChannelDataType(2, signed=False, le=True),
        EChannelType.EXTERNAL_ADC_A2: ChannelDataType(2, signed=False, le=True),
        EChannelType.INTERNAL_ADC_A3: ChannelDataType(2, signed=False, le=True),
        EChannelType.INTERNAL_ADC_A0: ChannelDataType(2, signed=False, le=True),
        EChannelType.INTERNAL_ADC_A1: ChannelDataType(2, signed=False, le=True),
        EChannelType.INTERNAL_ADC_A2: ChannelDataType(2, signed=False, le=True),
        EChannelType.ACCEL_HG_X: None,
        EChannelType.ACCEL_HG_Y: None,
        EChannelType.ACCEL_HG_Z: None,
        EChannelType.MAG_WR_X: None,
        EChannelType.MAG_WR_Y: None,
        EChannelType.MAG_WR_Z: None,
        EChannelType.TEMPERATURE: ChannelDataType(2, signed=False, le=False),
        EChannelType.PRESSURE: ChannelDataType(3, signed=False, le=False),
        EChannelType.GSR_RAW: ChannelDataType(2, signed=False, le=True),
        EChannelType.EXG1_STATUS: ChannelDataType(1, signed=False, le=True),
        EChannelType.EXG1_CH1_24BIT: ChannelDataType(3, signed=True, le=False),
        EChannelType.EXG1_CH2_24BIT: ChannelDataType(3, signed=True, le=False),
        EChannelType.EXG2_STATUS: ChannelDataType(1, signed=False, le=True),
        EChannelType.EXG2_CH1_24BIT: ChannelDataType(3, signed=True, le=False),
        EChannelType.EXG2_CH2_24BIT: ChannelDataType(3, signed=True, le=False),
        EChannelType.EXG1_CH1_16BIT: ChannelDataType(2, signed=True, le=False),
        EChannelType.EXG1_CH2_16BIT: ChannelDataType(2, signed=True, le=False),
        EChannelType.EXG2_CH1_16BIT: ChannelDataType(2, signed=True, le=False),
        EChannelType.EXG2_CH2_16BIT: ChannelDataType(2, signed=True, le=False),
        EChannelType.STRAIN_HIGH: ChannelDataType(2, signed=False, le=True),
        EChannelType.STRAIN_LOW: ChannelDataType(2, signed=False, le=True),
        EChannelType.TIMESTAMP: ChannelDataType(3, signed=False, le=True),
    }

    SENSOR_CHANNEL_ASSIGNMENT: dict[ESensorGroup, list[EChannelType]] = {
        ESensorGroup.ACCEL_LN: [
            EChannelType.ACCEL_LN_X,
            EChannelType.ACCEL_LN_Y,
            EChannelType.ACCEL_LN_Z,
        ],
        ESensorGroup.BATTERY: [EChannelType.VBATT],
        ESensorGroup.EXT_CH_A0: [EChannelType.EXTERNAL_ADC_A0],
        ESensorGroup.EXT_CH_A1: [EChannelType.EXTERNAL_ADC_A1],
        ESensorGroup.EXT_CH_A2: [EChannelType.EXTERNAL_ADC_A2],
        ESensorGroup.INT_CH_A0: [EChannelType.INTERNAL_ADC_A0],
        ESensorGroup.INT_CH_A1: [EChannelType.INTERNAL_ADC_A1],
        ESensorGroup.INT_CH_A2: [EChannelType.INTERNAL_ADC_A2],
        ESensorGroup.STRAIN: [EChannelType.STRAIN_HIGH, EChannelType.STRAIN_LOW],
        ESensorGroup.INT_CH_A3: [EChannelType.INTERNAL_ADC_A3],
        ESensorGroup.GSR: [EChannelType.GSR_RAW],
        ESensorGroup.GYRO: [
            EChannelType.GYRO_X,
            EChannelType.GYRO_Y,
            EChannelType.GYRO_Z,
        ],
        ESensorGroup.ACCEL_WR: [
            EChannelType.ACCEL_WR_X,
            EChannelType.ACCEL_WR_Y,
            EChannelType.ACCEL_WR_Z,
        ],
        ESensorGroup.MAG_REG: [
            EChannelType.MAG_REG_X,
            EChannelType.MAG_REG_Y,
            EChannelType.MAG_REG_Z,
        ],
        ESensorGroup.ACCEL_HG: [
            EChannelType.ACCEL_HG_X,
            EChannelType.ACCEL_HG_Y,
            EChannelType.ACCEL_HG_Z,
        ],
        ESensorGroup.MAG_WR: [
            EChannelType.MAG_WR_X,
            EChannelType.MAG_WR_Y,
            EChannelType.MAG_WR_Z,
        ],
        ESensorGroup.PRESSURE: [EChannelType.TEMPERATURE, EChannelType.PRESSURE],
        ESensorGroup.EXG1_24BIT: [
            EChannelType.EXG1_STATUS,
            EChannelType.EXG1_CH1_24BIT,
            EChannelType.EXG1_CH2_24BIT,
        ],
        ESensorGroup.EXG1_16BIT: [
            EChannelType.EXG1_STATUS,
            EChannelType.EXG1_CH1_16BIT,
            EChannelType.EXG1_CH2_16BIT,
        ],
        ESensorGroup.EXG2_24BIT: [
            EChannelType.EXG2_STATUS,
            EChannelType.EXG2_CH1_24BIT,
            EChannelType.EXG2_CH2_24BIT,
        ],
        ESensorGroup.EXG2_16BIT: [
            EChannelType.EXG2_STATUS,
            EChannelType.EXG2_CH1_16BIT,
            EChannelType.EXG2_CH2_16BIT,
        ],
        # The MPU9150 Temp sensor is not yet available as a channel in the LogAndStream
        # firmware
        ESensorGroup.TEMP: [],
    }

    SENSOR_BIT_ASSIGNMENT: dict[ESensorGroup, int] = {
        ESensorGroup.EXT_CH_A1: 0,
        ESensorGroup.EXT_CH_A0: 1,
        ESensorGroup.GSR: 2,
        ESensorGroup.EXG2_24BIT: 3,
        ESensorGroup.EXG1_24BIT: 4,
        ESensorGroup.MAG_REG: 5,
        ESensorGroup.GYRO: 6,
        ESensorGroup.ACCEL_LN: 7,
        ESensorGroup.INT_CH_A1: 8,
        ESensorGroup.INT_CH_A0: 9,
        ESensorGroup.INT_CH_A3: 10,
        ESensorGroup.EXT_CH_A2: 11,
        ESensorGroup.ACCEL_WR: 12,
        ESensorGroup.BATTERY: 13,
        # No assignment 14
        ESensorGroup.STRAIN: 15,
        # No assignment 16
        ESensorGroup.TEMP: 17,
        ESensorGroup.PRESSURE: 18,
        ESensorGroup.EXG2_16BIT: 19,
        ESensorGroup.EXG1_16BIT: 20,
        ESensorGroup.MAG_WR: 21,
        ESensorGroup.ACCEL_HG: 22,
        ESensorGroup.INT_CH_A2: 23,
    }

    SENSOR_ORDER: dict[ESensorGroup, int] = {
        ESensorGroup.ACCEL_LN: 1,
        ESensorGroup.BATTERY: 2,
        ESensorGroup.EXT_CH_A0: 3,
        ESensorGroup.EXT_CH_A1: 4,
        ESensorGroup.EXT_CH_A2: 5,
        ESensorGroup.INT_CH_A0: 6,
        ESensorGroup.INT_CH_A1: 7,
        ESensorGroup.INT_CH_A2: 8,
        ESensorGroup.STRAIN: 9,
        ESensorGroup.INT_CH_A3: 10,
        ESensorGroup.GSR: 11,
        ESensorGroup.GYRO: 12,
        ESensorGroup.ACCEL_WR: 13,
        ESensorGroup.MAG_REG: 14,
        ESensorGroup.ACCEL_HG: 15,
        ESensorGroup.MAG_WR: 16,
        ESensorGroup.PRESSURE: 17,
        ESensorGroup.EXG1_24BIT: 18,
        ESensorGroup.EXG1_16BIT: 19,
        ESensorGroup.EXG2_24BIT: 20,
        ESensorGroup.EXG2_16BIT: 21,
        ESensorGroup.TEMP: 22,
    }

    def __init__(self):
        super().__init__(
            self.DEV_CLOCK_RATE,
            self.SENSOR_DTYPE,
            self.CH_DTYPE_ASSIGNMENT,
            self.SENSOR_CHANNEL_ASSIGNMENT,
            self.SENSOR_BIT_ASSIGNMENT,
            self.SENSOR_ORDER,
        )
