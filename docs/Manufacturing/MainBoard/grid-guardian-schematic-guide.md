# Grid Guardian Main PCB
# Schematic Design Guide

This document provides a structural representation of the Grid Guardian Main PCB schematic to guide the actual implementation in EDA software. The schematic is organized in functional blocks with key interconnections described.

## 1. Hierarchical Schematic Structure

The complete schematic should be organized in a hierarchical structure with the following pages:

1. **Top Level / Block Diagram**
2. **Power Supply**
3. **Main Processor (STM32H7)**
4. **Co-Processor (STM32L4+)**
5. **AI Accelerator**
6. **Memory & Security**
7. **Battery Management**
8. **Cellular Communications**
9. **LoRaWAN & Mesh Communications**
10. **Bluetooth Interface**
11. **Environmental Sensors**
12. **Infrastructure Monitoring Sensors**
13. **Interface & Expansion**
14. **Debug & Programming**

## 2. Power Supply Schematic Details

### 2.1 Input Power Section
```
Solar Panel Input (J10) --+-- TVS Diode (D35) --- PTC Fuse (F1) --+
                          |                                         |
                          +----------------------------------------+
                                                                    |
                                                                    V
                  +---------------+                             +--------+
Battery Input ----|               |                             |        |
(J9)             | Input Select   |--------------------------->| DC-DC  |
                  |  & Protections |     VIN_SYS               | Buck   |---> +5V System
USB-C Input ------|               |                             |  U36   |
(J1)              +---------------+                             +--------+
```

### 2.2 Power Management IC
```
                    +--------------------+
                    |                    |-----> +3.3V_MAIN
                    |                    |
+5V System -------->|     TPS65086      |-----> +1.8V_DIGITAL
                    |      (U9)         |
                    |                    |-----> +1.2V_CORE
ENABLE_MAIN ------->|                    |
                    |                    |-----> +3.3V_ANALOG
I²C_PMIC ---------->|                    |
                    +--------------------+
```

### 2.3 LDO Regulators
```
                    +--------------------+
+5V System -------->|     LT1963AES8     |-----> +3.3V_SENSORS
                    |      (U37)         |
                    +--------------------+

                    +--------------------+
+5V System -------->|     LT1963AES8     |-----> +3.3V_RF
                    |      (U38)         |
                    +--------------------+
```

### 2.4 Battery Management
```
                   +---------------------+
Solar Input ------>|                     |
                   |      BQ25798        |
Battery + -------->|       (U7)          |------> Battery Output
                   |                     |
SMBUS_BAT -------->|                     |
                   +---------------------+

                   +---------------------+
Battery Pack ----->|                     |
                   |      BQ40Z80        |
                   |       (U8)          |------> Battery Status
                   |                     |
SMBUS_BAT -------->|                     |
                   +---------------------+

                   +---------------------+
Battery Pack ----->|                     |
                   |      LTC4162        |
                   |       (U35)         |------> Charge Control
                   |                     |
SMBUS_BAT -------->|                     |
                   +---------------------+
```

## 3. Main Processor Section (STM32H7)

### 3.1 STM32H7 Core
```
                   +---------------------+
                   |                     |
XTAL_26MHz <------>|      STM32H753      |
                   |        (U1)         |
Reset ------------->|                     |
                   |                     |
+3.3V_MAIN ------->| VDD                 |
+1.2V_CORE ------->| VCORE               |
                   |                     |------> JTAG/SWD
                   |                     |
                   |                     |------> UART_DBG
                   |                     |
                   |                     |------> SPI_FLASH
                   |                     |
                   |                     |------> I²C_MAIN
                   |                     |
                   |                     |------> SDMMC
                   |                     |
                   |                     |------> SPI_COPROCESSOR
                   |                     |
                   |                     |------> QSPI_AI
                   |                     |
                   +---------------------+
```

### 3.2 Crystal Configuration
```
       +-------+
       |       |
       |  Y1   |
       | 26MHz |
       |       |
       +---+---+
           |
      C83 === === C84
           |
          GND
```

### 3.3 Reset Circuit
```
          R21
+3.3V_MAIN---/\/\/\---+-----> NRST (STM32H7)
                      |
                      |
                 C41 ===
                      |
                      |
                     GND
```

## 4. Co-Processor Section (STM32L4+)

### 4.1 STM32L4+ Core
```
                   +---------------------+
                   |                     |
XTAL_8MHz <------->|      STM32L4S9      |
                   |        (U2)         |
Reset ------------->|                     |
                   |                     |
+3.3V_MAIN ------->| VDD                 |
                   |                     |------> JTAG/SWD
                   |                     |
                   |                     |------> UART_SENSOR
                   |                     |
                   |                     |------> SPI_MAIN
                   |                     |
                   |                     |------> I²C_SENSOR
                   |                     |
                   |                     |------> ADC_INPUTS
                   |                     |
                   +---------------------+
```

### 4.2 SPI Connection between Processors

```
STM32H7 (U1)                 STM32L4+ (U2)
    SPI1_SCK -------------> SPI1_SCK
    SPI1_MISO <------------- SPI1_MISO
    SPI1_MOSI -------------> SPI1_MOSI
    SPI1_NSS --------------> SPI1_NSS
    GPIO_IRQ <-------------- GPIO_IRQ
```

## 5. AI Accelerator Section

### 5.1 ECM3532 Connections
```
                   +---------------------+
                   |                     |
XTAL_12MHz <------>|      ECM3532        |
                   |        (U3)         |
Reset ------------->|                     |
                   |                     |
+3.3V_MAIN ------->| VDD                 |
+1.8V_DIGITAL ----->| VDDIO               |
                   |                     |------> QSPI (to STM32H7)
                   |                     |
                   |                     |------> I²C_AI
                   |                     |
                   |                     |------> GPIO_CONTROL
                   |                     |
                   +---------------------+
```

## 6. Memory & Security

### 6.1 External Flash
```
                   +---------------------+
                   |                     |
SPI_FLASH_CS1 ---->|    MT25QU512ABB     |
SPI_FLASH_CLK ---->|        (U4)         |
SPI_FLASH_DI ----->|                     |
SPI_FLASH_DO <-----|                     |
                   |                     |
+3.3V_MAIN ------->| VCC                 |
                   +---------------------+

                   +---------------------+
                   |                     |
SPI_FLASH_CS2 ---->|    MT25QU512ABB     |
SPI_FLASH_CLK ---->|        (U5)         |
SPI_FLASH_DI ----->|                     |
SPI_FLASH_DO <-----|                     |
                   |                     |
+3.3V_MAIN ------->| VCC                 |
                   +---------------------+
```

### 6.2 Secure Element
```
                   +---------------------+
                   |                     |
I²C_SEC_SCL ------>|      A71CH          |
I²C_SEC_SDA <----->|       (U6)          |
                   |                     |
+3.3V_MAIN ------->| VDD                 |
                   +---------------------+
```

### 6.3 MicroSD Card
```
                   +---------------------+
                   |                     |
SDMMC_CMD -------->|                     |
SDMMC_CLK -------->|      MicroSD        |
SDMMC_D0 <-------->|       (J2)          |
SDMMC_D1 <-------->|                     |
SDMMC_D2 <-------->|                     |
SDMMC_D3 <-------->|                     |
                   |                     |
CD_DETECT <--------|                     |
                   +---------------------+
```

## 7. Cellular Communications

### 7.1 u-blox LTE Module
```
                   +---------------------+
                   |                     |
UART_CELL_TX ----->|                     |
UART_CELL_RX <-----|                     |
UART_CELL_RTS ---->|     SARA-R510S      |
UART_CELL_CTS <----|        (U14)        |
                   |                     |
CELL_PWR_EN ------>|                     |
CELL_RST ---------->|                     |
                   |                     |
+3.8V_CELL ------->| VCC                 |
                   |                     |------> RF (to U.FL J14)
                   +---------------------+
```

## 8. LoRaWAN Communications

### 8.1 SX1262 LoRaWAN Transceiver
```
                   +---------------------+
                   |                     |
SPI_LORA_CS ------>|                     |
SPI_LORA_CLK ----->|                     |
SPI_LORA_MOSI ---->|      SX1262         |
SPI_LORA_MISO <----|       (U15)         |
                   |                     |
LORA_RESET ------->|                     |
LORA_BUSY <--------|                     |
LORA_DIO1 <--------|                     |
                   |                     |
XTA_40MHz <------->|                     |
                   |                     |
+3.3V_RF ---------->| VCC                 |
                   |                     |-----> RF_LORA (to RF Frontend)
                   +---------------------+
```

### 8.2 RF Front End
```
                   +---------------------+
                   |                     |
RF_LORA ---------->|     SKY66423        |
                   |       (U17)         |
LORA_PA_CTRL ----->|                     |-----> RF (to SMA J7)
                   |                     |
+3.3V_RF ---------->| VCC                 |
                   +---------------------+
```

## 9. Bluetooth Interface

### 9.1 nRF52840 Bluetooth Module
```
                   +---------------------+
                   |                     |
UART_BT_TX ------->|                     |
UART_BT_RX <-------|                     |
UART_BT_RTS ------>|     nRF52840        |
UART_BT_CTS <------|       (U16)         |
                   |                     |
BT_RESET ---------->|                     |
                   |                     |
+3.3V_RF ---------->| VCC                 |
                   |                     |-----> RF (to U.FL J15)
                   +---------------------+
```

## 10. Environmental Sensor Integration

### 10.1 VOC Sensor Array
```
                   +---------------------+
                   |                     |
I²C_SENSOR_SCL --->|   TFSGS-MULTI2-ENV  |
I²C_SENSOR_SDA <-->|        (U19)        |
                   |                     |
VOC_HEAT_EN ------>|                     |
VOC_INT <----------|                     |
                   |                     |
+3.3V_SENSORS ----->| VCC                 |
                   +---------------------+
```

### 10.2 Particulate Matter Sensor
```
                   +---------------------+
                   |                     |
I²C_SENSOR_SCL --->|       SPS30         |
I²C_SENSOR_SDA <-->|        (U20)        |
                   |                     |
PM_RESET ---------->|                     |
                   |                     |
+5V System -------->| VCC                 |
                   +---------------------+
```

### 10.3 Temperature/Humidity Sensors
```
                   +---------------------+
                   |                     |
I²C_SENSOR_SCL --->|       SHT85         |
I²C_SENSOR_SDA <-->|        (U21)        |
                   |                     |
+3.3V_SENSORS ----->| VCC                 |
                   +---------------------+

                   +---------------------+
                   |                     |
I²C_SENSOR_SCL --->|       SHT85         |
I²C_SENSOR_SDA <-->|        (U22)        |
                   |                     |
+3.3V_SENSORS ----->| VCC                 |
                   +---------------------+
```

### 10.4 Barometric Pressure Sensor
```
                   +---------------------+
                   |                     |
I²C_SENSOR_SCL --->|       BMP388        |
I²C_SENSOR_SDA <-->|        (U23)        |
                   |                     |
BARO_INT <---------|                     |
                   |                     |
+3.3V_SENSORS ----->| VCC                 |
                   +---------------------+
```

### 10.5 Lightning Detector
```
                   +---------------------+
                   |                     |
SPI_SENSOR_CS1 --->|                     |
SPI_SENSOR_CLK --->|       AS3935        |
SPI_SENSOR_MOSI -->|        (U25)        |
SPI_SENSOR_MISO <--|                     |
                   |                     |
LIGHTNING_INT <----|                     |
                   |                     |
+3.3V_SENSORS ----->| VCC                 |
                   +---------------------+
```

## 11. Infrastructure Monitoring Sensors

### 11.1 Thermal Camera
```
                   +---------------------+
                   |                     |
SPI_SENSOR_CS2 --->|                     |
SPI_SENSOR_CLK --->|  FLIR Lepton 3.5    |
SPI_SENSOR_MOSI -->|        (U26)        |
SPI_SENSOR_MISO <--|                     |
                   |                     |
I²C_SENSOR_SCL --->|                     |
I²C_SENSOR_SDA <-->|                     |
                   |                     |
+3.3V_SENSORS ----->| VCC                 |
+1.2V_CORE -------->| VDDC                |
                   +---------------------+
```

### 11.2 Acoustic Sensors
```
                   +---------------------+
                   |                     |
                   |    SPU0410HR5H      |
                   |       (U27)         |
                   |                     |-----> ADC_AUDIO1
+3.3V_SENSORS ----->| VCC                 |
                   +---------------------+

                   +---------------------+
                   |                     |
                   |    SPU0410HR5H      |
                   |       (U28)         |
                   |                     |-----> ADC_AUDIO2
+3.3V_SENSORS ----->| VCC                 |
                   +---------------------+
```

### 11.3 EMF Sensor
```
                   +---------------------+
                   |                     |
I²C_SENSOR_SCL --->|     TF-EMF-PWR1     |
I²C_SENSOR_SDA <-->|        (U29)        |
                   |                     |
EMF_INT <----------|                     |
                   |                     |
+3.3V_SENSORS ----->| VCC                 |
                   +---------------------+
```

### 11.4 Accelerometer/Gyroscope
```
                   +---------------------+
                   |                     |
I²C_SENSOR_SCL --->|       BMI270        |
I²C_SENSOR_SDA <-->|        (U30)        |
                   |                     |
IMU_INT1 <---------|                     |
IMU_INT2 <---------|                     |
                   |                     |
+3.3V_SENSORS ----->| VCC                 |
                   +---------------------+
```

## 12. Interface & Expansion

### 12.1 USB Type-C Interface
```
                   +---------------------+
                   |                     |
USB_D+ <----------->|                     |
USB_D- <----------->|       USB-C         |
                   |        (J1)         |
                   |                     |
VBUS -------------->|                     |
                   +---------------------+
                          |
                          v
                   +---------------------+
                   |                     |
VBUS -------------->|     STUSB4500       |
                   |       (U40)         |
I²C_MAIN_SCL ----->|                     |
I²C_MAIN_SDA <---->|                     |
                   |                     |
+3.3V_MAIN -------->| VCC                 |
                   +---------------------+
```

### 12.2 External I²C Expansion
```
                   +---------------------+
                   |                     |
I²C_EXP_SCL ------>|                     |
I²C_EXP_SDA <----->|     Picoblade       |
                   |        (J11)        |
+3.3V_MAIN -------->|                     |
GND ---------------->|                     |
                   +---------------------+
```

### 12.3 UART/Debug Port
```
                   +---------------------+
                   |                     |
UART_DBG_TX ------>|                     |
UART_DBG_RX <------|                     |
UART_DBG_RTS ----->|     Picoblade       |
UART_DBG_CTS <-----|       (J12)         |
                   |                     |
+3.3V_MAIN -------->|                     |
GND ---------------->|                     |
                   +---------------------+
```

### 12.4 M12 Expansion Port
```
                   +---------------------+
                   |                     |
RS485_A <---------->|                     |
RS485_B <---------->|                     |
CAN_H <------------->|                     |
CAN_L <------------->|     M12 8-Pin       |
                   |       (J13)         |
I²C_EXP_SCL ------>|                     |
I²C_EXP_SDA <----->|                     |
                   |                     |
+12V ---------------->|                     |
GND ---------------->|                     |
                   +---------------------+
                      |     |
                      v     v
        +--------------+   +--------------+
        |              |   |              |
RS485_A/B|    MAX3485    |   |    TCAN1042   |CAN_H/L
<------->|     (U31)     |   |     (U32)     |<------>
        |              |   |              |
        +--------------+   +--------------+
```

## 13. Debug & Programming

### 13.1 JTAG/SWD Interface
```
                   +---------------------+
                   |                     |
SWDIO_MAIN <------>|                     |
SWCLK_MAIN ------->|     Spring          |
NRST_MAIN -------->|     Contacts        |
                   |      (J16)          |
+3.3V_MAIN -------->|                     |
GND ---------------->|                     |
                   +---------------------+
```

## 14. Key Component Interconnections Summary

1. **Main CPU to Co-Processor**
   - SPI interface for high-speed data exchange
   - Interrupt lines for event signaling
   - Shared power domain

2. **Main CPU to AI Accelerator**
   - QSPI interface for high-speed data exchange
   - I²C for configuration
   - GPIO control lines

3. **Main CPU to External Memory**
   - SPI interface to flash memory
   - SDMMC interface to microSD card

4. **Co-Processor to Sensor Systems**
   - I²C bus for most environmental sensors
   - SPI for high-speed sensors (thermal camera, lightning)
   - ADC inputs for analog sensors
   - Direct GPIO for interrupts

5. **Main CPU to Communication Systems**
   - UART to cellular module
   - SPI to LoRaWAN transceiver
   - UART to Bluetooth module

6. **Interface Buses**
   - I²C_MAIN: Main CPU to PMIC, RTC, USB-PD controller
   - I²C_SENSOR: Co-processor to environmental sensors
   - I²C_EXP: Expansion port for external sensors
   - SPI_FLASH: Main CPU to external flash
   - SPI_SENSOR: Co-processor to specialized sensors
   - SPI_MAIN: Inter-processor communication
   - UART_CELL: Main CPU to cellular module
   - UART_BT: Main CPU to Bluetooth module
   - UART_DBG: Main CPU to debug port

## 15. Special Layout Considerations

1. **RF Section**
   - Keep LoRaWAN, cellular, and Bluetooth circuits isolated
   - Control trace impedance for RF signal paths (50Ω)
   - Consider ground plane segmentation
   - RF components should have dedicated power supplies

2. **Sensitive Analog Section**
   - Isolate analog sensors from digital noise
   - Separate analog and digital ground planes with controlled connection points
   - Route analog signals away from high-speed digital

3. **Power Supply Distribution**
   - Star topology for power distribution
   - Sufficient bulk and decoupling capacitors at all ICs
   - Power planes for main supplies
   - Adequate copper for high-current paths

4. **Thermal Considerations**
   - Thermal relief for high-power components
   - Thermal vias under STM32H7, AI accelerator, and cellular module
   - Consider heat spreading for power management ICs

5. **Environmental Sensors**
   - Positioning to allow proper airflow
   - Thermal isolation from heat-generating components
   - Protection from light exposure for sensitive components
