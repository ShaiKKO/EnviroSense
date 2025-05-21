# Grid Guardian Main PCB
# Bill of Materials (BOM)

**Project:** EnviroSense™ Grid Guardian  
**PCB:** Main Board  
**Version:** 1.0  
**Date:** May 20, 2025  
**Part Count:** 269  

## Integrated Circuits

| Item | Qty | Reference Designator | Manufacturer | Part Number | Description | Package | Value/Rating | Substitution Allowed | Notes |
|------|-----|----------------------|--------------|-------------|-------------|---------|--------------|----------------------|-------|
| 1 | 1 | U1 | STMicroelectronics | STM32H753ZIT6 | Microcontroller, ARM Cortex-M7F, 550MHz | LQFP-144 | 2MB Flash, 1MB RAM | No | Main processor |
| 2 | 1 | U2 | STMicroelectronics | STM32L4S9ZIT6 | Microcontroller, ARM Cortex-M4F | LQFP-144 | 2MB Flash, 640KB RAM | No | Co-processor |
| 3 | 1 | U3 | Eta Compute | ECM3532 | AI Accelerator | QFN-48 | 2.0 TOPS | No | Edge AI processor, TeraFlux supplied |
| 4 | 2 | U4, U5 | Micron | MT25QU512ABB1EW9 | NOR Flash | 8-WSON | 512Mb, 133MHz | No | External flash memory |
| 5 | 1 | U6 | NXP | A71CH-TLLHT-0GB | Secure Element | HVQFN-14 | ECC P-256, SHA-256 | No | Hardware security |
| 6 | 1 | U7 | Texas Instruments | BQ25798RTWT | Battery Charge Controller | WQFN-32 | 5A, 1.8-24V | No | Solar charge controller |
| 7 | 1 | U8 | Texas Instruments | BQ40Z80RSMT | Battery Management System | VQFN-32 | 4S, 5A | No | Battery protection and fuel gauge |
| 8 | 1 | U9 | Texas Instruments | TPS65086RWHR | Power Management IC | VQFN-40 | 6 outputs | No | System power management |
| 9 | 4 | U10-U13 | Texas Instruments | TPS62840DLCR | DC-DC Buck Converter | WSON-8 | 1.8-6.5V, 750mA | No | Ultra-low-power regulators |
| 10 | 1 | U14 | u-blox | SARA-R510S-01B | Cellular LTE Cat-M1/NB-IoT | LGA-96 | Global bands | No | Primary communication module |
| 11 | 1 | U15 | Semtech | SX1262IMLTRT | LoRaWAN Transceiver | QFN-24 | 915/868MHz | No | Long-range communication |
| 12 | 1 | U16 | Nordic | nRF52840-QIAA | Bluetooth Module | QFN-73 | BLE 5.2 | No | Bluetooth interface |
| 13 | 2 | U17, U18 | Skyworks | SKY66423-11 | RF Front End | QFN-16 | 860-930MHz | No | RF power amplifier and LNA |
| 14 | 1 | U19 | TeraFlux/Sensirion | TFSGS-MULTI2-ENV | Gas Sensor Array | Custom | 8-channel | No | TeraFlux supplied VOC sensor array |
| 15 | 1 | U20 | Sensirion | SPS30 | Particulate Matter Sensor | LGA | PM1.0, 2.5, 10 | No | Smoke/particle detection |
| 16 | 2 | U21, U22 | Sensirion | SHT85 | Temperature/Humidity Sensor | DFN-8 | ±0.1°C, ±1.5%RH | No | Environmental sensing |
| 17 | 1 | U23 | Bosch | BMP388 | Barometric Pressure Sensor | LGA-10 | 300-1200 hPa | No | Atmospheric pressure |
| 18 | 1 | U24 | FT Technologies | FT205 | Ultrasonic Anemometer | Custom | 0-75 m/s | No | TeraFlux supplied wind sensor |
| 19 | 1 | U25 | AMS | AS3935 | Lightning Detector | MLPQ-20 | 40km range | No | Lightning detection |
| 20 | 1 | U26 | FLIR | 500-0771-01 | Lepton 3.5 Thermal Camera | Custom | 160x120 VOx | No | TeraFlux supplied thermal camera |
| 21 | 2 | U27, U28 | Knowles | SPU0410HR5H | Acoustic Sensor | Bottom Port | 20Hz-80kHz | No | Acoustic monitoring |
| 22 | 1 | U29 | TeraFlux Custom | TF-EMF-PWR1 | EMF Sensor | Custom | AC field detection | No | TeraFlux supplied EMF sensor |
| 23 | 1 | U30 | Bosch | BMI270 | Accelerometer/Gyroscope | LGA-14 | ±16g, ±2000°/s | Yes | Vibration monitoring |
| 24 | 1 | U31 | Maxim | MAX3485EESA+ | RS-485 Transceiver | SOIC-8 | 3.3V, 12Mbps | Yes | Industrial interface |
| 25 | 1 | U32 | Texas Instruments | TCAN1042GVDR | CAN Transceiver | SOIC-8 | 3.3V | Yes | Industrial interface |
| 26 | 1 | U33 | Analog Devices | ADM3053BRWZ | Isolated CAN Transceiver | SOIC-16W | 2.5kV isolation | No | Isolated CAN interface |
| 27 | 1 | U34 | Silicon Labs | Si5351A-B-GT | Clock Generator | QFN-20 | 8kHz-200MHz | Yes | Clock generation |
| 28 | 1 | U35 | Linear Technology | LTC4162-LAD | Battery Charger | QFN-28 | 35V, 3.2A | No | Advanced charge management |
| 29 | 1 | U36 | Texas Instruments | TPS61099-Q1 | Boost Converter | WSON-6 | 5V, 400mA | Yes | Solar input management |
| 30 | 2 | U37, U38 | Linear Technology | LT1963AES8 | LDO Regulator | SOIC-8 | 3.3V, 1.5A | Yes | Low-noise regulation |
| 31 | 1 | U39 | Maxim | DS3231MZ+ | Real-Time Clock | SOIC-8 | ±2ppm | No | Precision timekeeping |
| 32 | 1 | U40 | ST Microelectronics | STUSB4500QTR | USB-C PD Controller | QFN-24 | 5-20V | Yes | USB power delivery |

## Discrete Semiconductors

| Item | Qty | Reference Designator | Manufacturer | Part Number | Description | Package | Value/Rating | Substitution Allowed | Notes |
|------|-----|----------------------|--------------|-------------|-------------|---------|--------------|----------------------|-------|
| 33 | 8 | D1-D8 | Vishay | TMMBAT54FILM | Schottky Diode | SOD-523 | 30V, 200mA | Yes | Signal protection |
| 34 | 4 | D9-D12 | ON Semiconductor | MBR0540T1G | Schottky Diode | SOD-123 | 40V, 0.5A | Yes | Power path control |
| 35 | 2 | D13, D14 | Littelfuse | SP0524NUTG | TVS Diode Array | SOT-23-6 | 5V, 4-channel | Yes | USB protection |
| 36 | 6 | D15-D20 | Nexperia | PESD5V0L1BA,115 | TVS Diode | SOD-323 | 5V unidirectional | Yes | Signal line protection |
| 37 | 2 | D21, D22 | Vishay | VEMD5080X01 | Photodiode | SMD | 850nm | Yes | Optical sensing |
| 38 | 4 | D23-D26 | Luxeon | LXML-PR01-0500 | LED | 3.5x3.5mm | Red, 500mcd | Yes | Status indication |
| 39 | 4 | D27-D30 | Luxeon | LXML-PB01-0040 | LED | 3.5x3.5mm | Blue, 40lm | Yes | Status indication |
| 40 | 4 | D31-D34 | Luxeon | LXML-PM01-0100 | LED | 3.5x3.5mm | Green, 100lm | Yes | Status indication |
| 41 | 4 | D35-D38 | Littelfuse | SMAJ16A | TVS Diode | SMA | 16V, 400W | Yes | Input protection |
| 42 | 4 | Q1-Q4 | Infineon | BSS138N | MOSFET N-Channel | SOT-23 | 60V, 360mA | Yes | Level shifting |
| 43 | 4 | Q5-Q8 | Infineon | BSS84P | MOSFET P-Channel | SOT-23 | -50V, -130mA | Yes | Load switching |
| 44 | 2 | Q9, Q10 | Infineon | IPD50N06S4L-12 | MOSFET N-Channel | DPAK | 60V, 50A | Yes | Power switching |
| 45 | 4 | Q11-Q14 | ON Semiconductor | MMBT3904LT1G | BJT NPN | SOT-23 | 40V, 200mA | Yes | Signal switching |
| 46 | 4 | Q15-Q18 | ON Semiconductor | MMBT3906LT1G | BJT PNP | SOT-23 | -40V, -200mA | Yes | Signal switching |

## Passive Components - Resistors

| Item | Qty | Reference Designator | Manufacturer | Part Number | Description | Package | Value/Rating | Substitution Allowed | Notes |
|------|-----|----------------------|--------------|-------------|-------------|---------|--------------|----------------------|-------|
| 47 | 20 | R1-R20 | Yageo | RC0603FR-071KL | Resistor | 0603 | 1kΩ ±1% | Yes | General purpose |
| 48 | 20 | R21-R40 | Yageo | RC0603FR-074K7L | Resistor | 0603 | 4.7kΩ ±1% | Yes | Pull-up |
| 49 | 10 | R41-R50 | Yageo | RC0603FR-0710KL | Resistor | 0603 | 10kΩ ±1% | Yes | Pull-up |
| 50 | 10 | R51-R60 | Yageo | RC0603FR-07100KL | Resistor | 0603 | 100kΩ ±1% | Yes | Bias |
| 51 | 10 | R61-R70 | Yageo | RC0603FR-07330RL | Resistor | 0603 | 330Ω ±1% | Yes | LED current limiting |
| 52 | 5 | R71-R75 | Yageo | RC0603FR-0749R9L | Resistor | 0603 | 49.9Ω ±1% | Yes | Termination |
| 53 | 5 | R76-R80 | Susumu | RG2012P-2211-W-T1 | Resistor | 0805 | 2.21kΩ ±0.1% | No | Precision voltage divider |
| 54 | 5 | R81-R85 | Susumu | RG2012P-1001-W-T1 | Resistor | 0805 | 1.00kΩ ±0.1% | No | Precision voltage divider |
| 55 | 4 | R86-R89 | Vishay | CRCW20100000Z0EF | Resistor | 2010 | 0Ω | Yes | Jumper/bridge |
| 56 | 4 | R90-R93 | Bourns | CR0603-FX-1002ELF | Resistor | 0603 | 10kΩ ±1% | Yes | Thermal NTC |
| 57 | 8 | R94-R101 | Yageo | RC0603FR-072K2L | Resistor | 0603 | 2.2kΩ ±1% | Yes | I²C pull-up |
| 58 | 8 | R102-R109 | Yageo | RC2010FK-0710ML | Resistor | 2010 | 10mΩ ±1% | No | Current sensing |

## Passive Components - Capacitors

| Item | Qty | Reference Designator | Manufacturer | Part Number | Description | Package | Value/Rating | Substitution Allowed | Notes |
|------|-----|----------------------|--------------|-------------|-------------|---------|--------------|----------------------|-------|
| 59 | 25 | C1-C25 | Murata | GRM188R71C104KA01D | Ceramic Capacitor, X7R | 0603 | 0.1μF, 16V | Yes | Decoupling |
| 60 | 15 | C26-C40 | Murata | GRM188R71C105KA12D | Ceramic Capacitor, X7R | 0603 | 1μF, 16V | Yes | Decoupling |
| 61 | 10 | C41-C50 | Murata | GRM21BR71C106KE15L | Ceramic Capacitor, X7R | 0805 | 10μF, 16V | Yes | Bulk decoupling |
| 62 | 6 | C51-C56 | Murata | GRM32ER71K226KE15L | Ceramic Capacitor, X7R | 1210 | 22μF, 25V | Yes | Bulk capacitance |
| 63 | 4 | C57-C60 | Murata | GRM32ER71K476ME15L | Ceramic Capacitor, X7R | 1210 | 47μF, 25V | Yes | Input filtering |
| 64 | 2 | C61, C62 | Panasonic | EEE-FT1V221AP | Aluminum Electrolytic | 8x10mm | 220μF, 35V | Yes | Bulk capacitance |
| 65 | 2 | C63, C64 | Nichicon | UUD1H221MNL1GS | Aluminum Electrolytic | 8x12mm | 220μF, 50V | Yes | Input filtering |
| 66 | 4 | C65-C68 | Taiyo Yuden | TMK212BJ104KG-T | Ceramic Capacitor, X5R | 0805 | 0.1μF, 50V | Yes | RF decoupling |
| 67 | 4 | C69-C72 | AVX | TPSD226K016R0150 | Tantalum Capacitor | 7343 | 22μF, 16V | Yes | SMPS output |
| 68 | 10 | C73-C82 | Murata | GRM1885C1H101JA01D | Ceramic Capacitor, NP0 | 0603 | 100pF, 50V | Yes | RF tuning |
| 69 | 6 | C83-C88 | Murata | GCM1555C1H270JA16D | Ceramic Capacitor, NP0 | 0402 | 27pF, 50V | Yes | Crystal load |
| 70 | 4 | C89-C92 | Murata | GJM1555C1H150JB01D | Ceramic Capacitor, NP0 | 0402 | 15pF, 50V | Yes | RF tuning |

## Passive Components - Inductors/Magnetics

| Item | Qty | Reference Designator | Manufacturer | Part Number | Description | Package | Value/Rating | Substitution Allowed | Notes |
|------|-----|----------------------|--------------|-------------|-------------|---------|--------------|----------------------|-------|
| 71 | 4 | L1-L4 | Murata | LQH43PN4R7M03L | Power Inductor | 4.3x3.0mm | 4.7μH, 1.5A | Yes | SMPS |
| 72 | 2 | L5, L6 | Murata | LQM21FN100M70L | Power Inductor | 0805 | 10μH, 200mA | Yes | RF filter |
| 73 | 4 | L7-L10 | TDK | MLZ2012M100WT000 | Power Inductor | 0805 | 10μH, 300mA | Yes | Power filtering |
| 74 | 4 | L11-L14 | Coilcraft | XAL5030-102MEB | Power Inductor | 5.2x5.4mm | 1μH, 3.6A | No | High-current SMPS |
| 75 | 8 | L15-L22 | Murata | BLM18AG102SN1D | Ferrite Bead | 0603 | 1kΩ @ 100MHz | Yes | EMI suppression |
| 76 | 4 | L23-L26 | Taiyo Yuden | NR3015T4R7M | Power Inductor | 3.0x3.0mm | 4.7μH, 1.3A | Yes | SMPS |
| 77 | 2 | T1, T2 | Würth Elektronik | 750315839 | Common Mode Choke | 7.3x7.3mm | 39μH, 1.85A | No | EMI filtering |

## Crystals/Oscillators

| Item | Qty | Reference Designator | Manufacturer | Part Number | Description | Package | Value/Rating | Substitution Allowed | Notes |
|------|-----|----------------------|--------------|-------------|-------------|---------|--------------|----------------------|-------|
| 78 | 1 | Y1 | Epson | TSX-3225 | Crystal | 3.2x2.5mm | 26MHz, 10ppm | No | Main processor clock |
| 79 | 1 | Y2 | Epson | FC-135 | Crystal | 3.2x1.5mm | 32.768kHz, 20ppm | No | RTC clock |
| 80 | 1 | Y3 | Abracon | ABMM-8.000MHZ-B2-T | Crystal | 3.2x2.5mm | 8MHz, 10ppm | Yes | Co-processor clock |
| 81 | 1 | Y4 | Epson | TSX-3225 | Crystal | 3.2x2.5mm | 40MHz, 10ppm | No | LoRaWAN reference |
| 82 | 1 | Y5 | SiTime | SIT8208AC-23-18S-16.369MHZ | MEMS Oscillator | 2.0x1.6mm | 16.369MHz, 10ppm | No | Cellular reference |

## Connectors

| Item | Qty | Reference Designator | Manufacturer | Part Number | Description | Package | Value/Rating | Substitution Allowed | Notes |
|------|-----|----------------------|--------------|-------------|-------------|---------|--------------|----------------------|-------|
| 83 | 1 | J1 | Amphenol | 12401598E4#2A | USB Type-C Receptacle | SMT | 5A, USB 2.0 | No | Maintenance port |
| 84 | 1 | J2 | Würth | 636104151421 | Micro SD Card Holder | SMT | Push-pull | Yes | Data storage |
| 85 | 1 | J3 | KYOCERA | 046288 | M.2 Card Edge Connector | SMT | Key E | No | Expansion slot |
| 86 | 3 | J4, J5, J6 | Samtec | QSE-020-01-F-D-A | Board-to-Board | 2x10, 1.27mm | 2A per pin | No | Expansion |
| 87 | 2 | J7, J8 | Amphenol | 132291-10 | SMA Jack | Edge Mount | 50Ω | No | RF antenna |
| 88 | 1 | J9 | JST | SM08B-SRSS-TB | JST-SH | 1.0mm, 8-pos | 1A per pin | Yes | Battery connection |
| 89 | 1 | J10 | Phoenix Contact | 1778887 | Terminal Block | 3-position | 8A, 150V | Yes | Solar panel |
| 90 | 1 | J11 | Molex | 0532610571 | Picoblade | 1.25mm, 5-pos | 1A per pin | Yes | I²C expansion |
| 91 | 1 | J12 | Molex | 0532610871 | Picoblade | 1.25mm, 8-pos | 1A per pin | Yes | UART/debug |
| 92 | 1 | J13 | TE Connectivity | 5-1634503-1 | M12 Panel Mount | 8-position | IP67 | No | Expansion port |
| 93 | 1 | J14 | Hirose | U.FL-R-SMT-1 | U.FL Receptacle | SMT | 6GHz, 50Ω | No | Cellular antenna |
| 94 | 1 | J15 | Hirose | U.FL-R-SMT-1 | U.FL Receptacle | SMT | 6GHz, 50Ω | No | Bluetooth antenna |
| 95 | 1 | J16 | TE Connectivity | 1-1612528-1 | Spring Contact | 2mm | 2A | Yes | Debug contact |
| 96 | 2 | J17, J18 | Molex | 1050170001 | Battery Contacts | SMT | 2A | No | Coin cell holder |

## Miscellaneous Components

| Item | Qty | Reference Designator | Manufacturer | Part Number | Description | Package | Value/Rating | Substitution Allowed | Notes |
|------|-----|----------------------|--------------|-------------|-------------|---------|--------------|----------------------|-------|
| 97 | 1 | BZ1 | Soberton | GT-0950RP3 | Piezo Buzzer | SMT | 1-3kHz, 70dB | Yes | Audible alert |
| 98 | 1 | SW1 | C&K | PTS645SM43SMTR92 | Tactile Switch | 6.0x6.0mm | 1.6N, 0.05A | Yes | Reset button |
| 99 | 2 | SW2, SW3 | C&K | PTS645SM43SMTR92 | Tactile Switch | 6.0x6.0mm | 1.6N, 0.05A | Yes | User buttons |
| 100 | 1 | F1 | Littelfuse | 2920L075DR | PTC Fuse | 2920 | 750mA, 16V | Yes | Input protection |
| 101 | 1 | F2 | Littelfuse | 0603L050YR | PTC Fuse | 0603 | 500mA, 6V | Yes | USB protection |
| 102 | 1 | ANT1 | Antenova | SR42I010-R | Chip Antenna | 12.0x3.0mm | 860-930MHz | No | LoRaWAN antenna |
| 103 | 1 | BAT1 | Panasonic | BR1225 | Coin Cell Battery | 12.5mm | 3V, 48mAh | Yes | RTC backup |
| 104 | 1 | B1 | Würth | 61300311121 | Ferrite Core | SMT | 300Ω, 2A | Yes | Common mode filter |
| 105 | 1 | TP1 | Keystone | 5019 | Test Point | SMT | Red | Yes | VBAT test |
| 106 | 1 | TP2 | Keystone | 5021 | Test Point | SMT | Black | Yes | GND test |
| 107 | 1 | TP3 | Keystone | 5020 | Test Point | SMT | White | Yes | 3.3V test |
| 108 | 1 | TP4 | Keystone | 5022 | Test Point | SMT | Green | Yes | 1.8V test |
| 109 | 4 | MP1-MP4 | Würth | 9774025151R | Mounting Hole | 2.5mm | M2.5 | Yes | PCB mounting |

## Total Component Count: 269 items
