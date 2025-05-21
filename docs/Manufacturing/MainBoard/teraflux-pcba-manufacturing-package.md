# TeraFlux Studios
# PCBA Manufacturing Partner Requirements Package

## Document Control

| Document ID | TF-MFG-2025-001 |
|-------------|-----------------|
| Version | 1.0 |
| Date | May 20, 2025 |
| Confidentiality | Confidential - Subject to NDA |
| Owner | TeraFlux Studios Manufacturing Operations |

## Table of Contents

1. [Introduction and Purpose](#1-introduction-and-purpose)
2. [Project Overview](#2-project-overview)
3. [PCB Specifications](#3-pcb-specifications)
4. [Component Requirements](#4-component-requirements)
5. [Assembly Requirements](#5-assembly-requirements)
6. [Testing Requirements](#6-testing-requirements)
7. [Quality Standards](#7-quality-standards)
8. [Documentation Requirements](#8-documentation-requirements)
9. [Manufacturing Partner Qualifications](#9-manufacturing-partner-qualifications)
10. [Intellectual Property Protection](#10-intellectual-property-protection)
11. [Engagement Process](#11-engagement-process)
12. [Appendices](#12-appendices)

## 1. Introduction and Purpose

This document provides comprehensive information for PCBA (Printed Circuit Board Assembly) manufacturing partners who will be producing circuit boards for TeraFlux Studios' EnviroSense™ product line. It outlines technical specifications, quality requirements, and operational processes needed to establish a successful manufacturing partnership.

All information contained in this document is considered confidential and requires an executed Non-Disclosure Agreement (NDA) prior to review.

## 2. Project Overview

### 2.1 Product Line Summary

TeraFlux Studios is developing a suite of environmental monitoring products for industrial and outdoor applications. The product line consists of three main devices:

1. **EnviroSense™ Grid Guardian**: Utility infrastructure monitoring system for wildfire prevention
2. **EnviroSense™ Wildland Sentinel**: Remote environmental monitoring for wilderness areas
3. **EnviroSense™ Zone Monitor**: Fixed environmental monitoring station for comprehensive coverage

### 2.2 PCBA Requirements Summary

| Product | PCB Types | Annual Volume Estimate | Complexity Level |
|---------|-----------|------------------------|------------------|
| Grid Guardian | Main Board, Sensor Board, Power Board | 5,000 - 10,000 units | High |
| Wildland Sentinel | Main Board, Sensor Board | 3,000 - 8,000 units | Medium-High |
| Zone Monitor | Main Board, Sensor Board, Power Board, RF Board | 2,000 - 5,000 units | Very High |

### 2.3 Environmental Requirements Overview

All PCBAs must meet the following environmental requirements:

- Operating temperature range: -40°C to +85°C
- Storage temperature range: -50°C to +95°C
- Humidity: 0-100% RH, condensing
- IP rating of final products: IP66 to IP68
- Expected 5+ year field lifetime in harsh outdoor conditions

## 3. PCB Specifications

### 3.1 Grid Guardian Main PCB

#### Physical Specifications
- Dimensions: 160mm × 100mm (±0.2mm)
- Layers: 8-layer, high-density
- Material: FR-4, Tg 170°C minimum
- Copper Weight: 1oz outer, 0.5oz inner
- Min Trace/Space: 4mil/4mil
- Min Hole Size: 0.2mm
- Surface Finish: ENIG (IPC-4552 Class A)
- Solder Mask: Green LPI (IPC-SM-840 Class T)
- Board Thickness: 1.6mm (±10%)
- Controlled Impedance: Yes, 50Ω ±10% for critical traces
- PCB Outline Tolerance: ±0.1mm

#### Design Data Provided
- Gerber files (RS-274X)
- NC Drill files (Excellon)
- ODB++ data (optional)
- IPC-D-356A netlist
- Assembly drawings
- Pick and place files
- Bill of Materials (BOM)
- PCB stack-up requirements

#### Special Requirements
- Heavy copper pour areas for thermal management
- Blind and buried vias for high-density sections
- Impedance control required for RF sections
- RF section requires Rogers RO4350B material
- Black pad mitigation processes required
- Micro-via in pad allowed for BGA components

### 3.2 Grid Guardian Power Management PCB

#### Physical Specifications
- Dimensions: 100mm × 60mm (±0.2mm)
- Layers: 4-layer
- Material: FR-4, Tg 170°C minimum
- Copper Weight: 2oz outer, 1oz inner
- Min Trace/Space: 5mil/5mil
- Min Hole Size: 0.25mm
- Surface Finish: ENIG (IPC-4552 Class A)
- Solder Mask: Green LPI (IPC-SM-840 Class T)
- Board Thickness: 1.6mm (±10%)
- Controlled Impedance: Not required
- PCB Outline Tolerance: ±0.1mm

#### Design Data Provided
- Gerber files (RS-274X)
- NC Drill files (Excellon)
- ODB++ data (optional)
- IPC-D-356A netlist
- Assembly drawings
- Pick and place files
- Bill of Materials (BOM)
- PCB stack-up requirements

#### Special Requirements
- High current traces require 2oz min copper
- Thermal relief on high-power component pads
- Reinforced isolation between high/low voltage sections
- High-pot test capability required for verification
- Designated copper pours for heat dissipation

### 3.3 Wildland Sentinel Main PCB

#### Physical Specifications
- Dimensions: 100mm × 80mm (±0.2mm)
- Layers: 6-layer
- Material: FR-4, Tg 170°C minimum
- Copper Weight: 1oz all layers
- Min Trace/Space: 5mil/5mil
- Min Hole Size: 0.25mm
- Surface Finish: ENIG (IPC-4552 Class A)
- Solder Mask: Green LPI (IPC-SM-840 Class T)
- Board Thickness: 1.6mm (±10%)
- Controlled Impedance: Yes, 50Ω ±10% for antenna feeds
- PCB Outline Tolerance: ±0.1mm

#### Design Data Provided
- Gerber files (RS-274X)
- NC Drill files (Excellon)
- ODB++ data (optional)
- IPC-D-356A netlist
- Assembly drawings
- Pick and place files
- Bill of Materials (BOM)
- PCB stack-up requirements

#### Special Requirements
- Ultra-low power design requiring clean manufacturing
- Through-hole vias with tenting
- Controlled impedance for antenna feeds
- Component keep-out zones around RF sections
- Special handling for moisture-sensitive components

### 3.4 Zone Monitor Carrier Board

#### Physical Specifications
- Dimensions: 200mm × 160mm (±0.2mm)
- Layers: 12-layer, high-density interconnect
- Material: FR-4, Tg 170°C minimum
- Copper Weight: 1oz outer, 0.5oz inner
- Min Trace/Space: 3mil/3mil
- Min Hole Size: 0.15mm
- Surface Finish: ENIG (IPC-4552 Class A)
- Solder Mask: Green LPI (IPC-SM-840 Class T)
- Board Thickness: 1.6mm (±10%)
- Controlled Impedance: Yes, multiple requirements by net class
- PCB Outline Tolerance: ±0.1mm

#### Design Data Provided
- Gerber files (RS-274X)
- NC Drill files (Excellon)
- ODB++ data (optional)
- IPC-D-356A netlist
- Assembly drawings
- Pick and place files
- Bill of Materials (BOM)
- PCB stack-up requirements

#### Special Requirements
- Sequentially laminated HDI construction
- Staggered vias and laser-drilled microvias
- Controlled impedance on differential pairs and RF paths
- Multiple ground and power planes
- Multiple keep-out zones for RF and sensitive analog sections

## 4. Component Requirements

### 4.1 Component Sourcing Responsibility

The following component sourcing responsibilities apply:

- **CM-Sourced Components**: Standard components, including passives, common ICs, connectors, and hardware
- **TeraFlux-Supplied Components**: Custom components, proprietary sensors, and long-lead items

### 4.2 Component Categories and Requirements

#### 4.2.1 Standard Components

| Component Type | Specification | Notes |
|----------------|---------------|-------|
| Passive Components | Tolerance: ±1% for resistors, ±5% for capacitors | Automotive-grade preferred |
| | Temperature Range: -40°C to +125°C | Must meet operating temperature range |
| | Moisture Sensitivity Level (MSL): Level 3 or better | For standard operating environment |
| | Package Size: 0402 minimum, 0201 where specified | No smaller than 0201 for manufacturability |
| ICs and Semiconductors | Temperature Range: -40°C to +85°C or +125°C | Industrial or automotive grade required |
| | MSL: Level 3 or better | For standard operating environment |
| | Lead-free compatible | Must withstand lead-free reflow process |
| Connectors | Temperature Range: -40°C to +85°C | Industrial or automotive grade required |
| | Mating Cycles: 100 minimum | For field serviceability |
| | Locking Features: Required where specified | For vibration resistance |
| | Moisture/Dust Protection: IP rated where specified | For environmental protection |

#### 4.2.2 Special Handling Components

The following components require special handling during assembly:

| Component | Special Requirements | Handling Instructions |
|-----------|----------------------|----------------------|
| FLIR Lepton Thermal Camera | MSL: Level 3 | Factory calibration must be preserved |
| | Anti-static precautions | Avoid direct contact with lens element |
| | No-clean flux only | Protect lens during assembly |
| Environmental Sensors | MSL: Level 3 | Protection from contamination |
| | Low-temperature soldering where specified | Some sensors have max temp rating |
| | No-wash chemicals near sensing elements | Protect sensing elements during cleaning |
| RF Components | Controlled impedance matching | Follow reference design layout exactly |
| | Minimal hand-rework | Automated placement preferred |
| | Special grounding requirements | Per component datasheet |

#### 4.2.3 TeraFlux-Supplied Components

The following components will be supplied by TeraFlux:

| Component | Product | Lead Time Requirement | Special Instructions |
|-----------|---------|----------------------|----------------------|
| Custom Gas Sensor Arrays | All Products | 8 weeks | MSL 3, ESD sensitive, temperature sensitive |
| FLIR Thermal Cameras | Grid Guardian, Wildland Sentinel | 12 weeks | Factory calibration must be preserved |
| Ultrasonic Wind Sensors | Grid Guardian, Wildland Sentinel | 10 weeks | Protection from mechanical stress |
| Custom RF Modules | All Products | 8 weeks | No rework permitted, ESD sensitive |
| Specialty Microcontrollers | All Products | 10 weeks | Secure boot configuration preserved |

### 4.3 Component Management Requirements

- **Inventory Management**: Just-in-time (JIT) manufacturing for standard components
- **Consignment Management**: Tracking and handling of TeraFlux-supplied components
- **Traceability**: Component lot traceability required for all PCBAs
- **MRB Process**: Material Review Board process for component issues
- **Obsolescence Management**: Component lifecycle tracking and notification

## 5. Assembly Requirements

### 5.1 Assembly Standards

All PCBAs shall be assembled in accordance with the following standards:

- IPC-A-610 Class 3 (Acceptability of Electronic Assemblies)
- J-STD-001 Class 3 (Requirements for Soldered Electrical and Electronic Assemblies)
- IPC-7711/7721 (Rework, Modification and Repair of Electronic Assemblies)
- ANSI/ESD S20.20 (ESD Control Program)

### 5.2 General Assembly Requirements

- Lead-free assembly process (SAC305 or equivalent)
- Nitrogen atmosphere reflow for all critical components
- Clean-room environment for sensor assembly (ISO Class 7 or better)
- ESD protection throughout assembly process
- Component placement accuracy: ±0.075mm (3 mils)
- Automated optical inspection (AOI) after placement and reflow
- X-ray inspection for BGA, QFN, and bottom-terminated components
- Selective conformal coating application post-assembly

### 5.3 Product-Specific Assembly Requirements

#### 5.3.1 Grid Guardian

- **Critical Components**:
  - U12 (STM32H753ZI): Requires precise orientation and X-ray verification
  - U8 (AI Accelerator): Thermal management critical, requires precise solder paste stencil
  - J5-J8 (RF Connectors): Require specialized alignment and soldering
  - Thermal Camera Module: Factory calibration must be preserved

- **Special Processes**:
  - Selective conformal coating (acrylic, MIL-I-46058C)
  - Must mask all connectors, switches, and test points
  - Thermal interface material application for U8, U12
  - Strain relief for all cable assemblies

#### 5.3.2 Wildland Sentinel

- **Critical Components**:
  - U5 (STM32L4+): Requires precise orientation and solder paste stencil
  - U21-U28 (Sensor Array): Anti-contamination measures during assembly
  - Y1-Y2 (Crystals): Mechanical stress minimization during assembly
  - BT1 (Battery Connector): Specific soldering profile to prevent damage

- **Special Processes**:
  - Conformal coating (acrylic, MIL-I-46058C)
  - Must mask all sensors, connectors, and test points
  - Special handling for moisture-sensitive components
  - No-clean flux required for all processes

#### 5.3.3 Zone Monitor

- **Critical Components**:
  - U1 (SOM Module): Requires specialized handling and placement
  - U15 (High-speed Memory): Signal integrity critical, controlled placement
  - J1-J12 (Interconnect): Alignment critical for system operation
  - RF Section Components: Controlled impedance and placement critical

- **Special Processes**:
  - Selective conformal coating with precision masking
  - Sequential assembly process for multi-board stack
  - System-level alignment verification
  - Special thermal profile for high-component-density areas

### 5.4 Process Control Requirements

- SPC (Statistical Process Control) monitoring for critical parameters
- Process capability index Cpk ≥ 1.33 for all critical parameters
- First Article Inspection (FAI) for first production run
- Process validation for all specialized processes
- MSA (Measurement System Analysis) for all testing equipment
- PFMEA (Process Failure Mode Effects Analysis) documentation
- Control plans for all critical processes

## 6. Testing Requirements

### 6.1 In-Process Testing

The following in-process tests are required:

- Automated Optical Inspection (AOI) post-placement
- Automated Optical Inspection (AOI) post-reflow
- X-ray inspection for BGA, QFN, and bottom-terminated components
- In-Circuit Testing (ICT) where test points are provided
- Flying Probe Testing for prototype/low-volume runs

### 6.2 Functional Testing

Functional testing requirements include:

- Boundary Scan Testing (JTAG) where supported
- Power-on validation test
- Communication interface testing
- Sensor basic functionality testing
- Peripheral device testing
- TeraFlux will provide functional test specifications and procedures
- CM must develop appropriate test fixtures and equipment

### 6.3 Environmental Testing

The following environmental tests are required for qualification and periodic verification:

- Thermal cycling (-40°C to +85°C, 10 cycles min)
- Temperature and humidity exposure (85°C/85% RH for 168 hours)
- Highly Accelerated Stress Test (HAST) for qualification builds
- Mechanical shock and vibration testing
- PCBA level IP testing for conformally coated assemblies

### 6.4 Test Equipment Requirements

- Automated test equipment compatible with TeraFlux test protocols
- Environmental chambers capable of -40°C to +85°C testing
- X-ray inspection system capable of detecting voids down to 2%
- Flying probe or bed-of-nails testing capability
- Data logging system for test results with statistical analysis
- Calibration system meeting ISO 17025 requirements

### 6.5 Test Data Requirements

- 100% test data capture and storage
- Statistical analysis of test results
- Correlation between serial number and test data
- Historical trend analysis capability
- Test data made available to TeraFlux via secure portal
- Minimum 5-year retention of test data

## 7. Quality Standards

### 7.1 Required Certifications and Standards

The PCBA manufacturing partner must maintain the following certifications:

- ISO 9001:2015 Quality Management System
- IPC-A-610 Class 3 Certified Operators
- J-STD-001 Certified Operators
- ISO 14001:2015 Environmental Management System
- IPC/WHMA-A-620 (Cable and Wire Harness Assemblies) if applicable
- ISO/IEC 17025 (Test Laboratory Accreditation) for in-house lab
- ISO 13485 (Medical Devices Quality Management) preferred

### 7.2 Quality Management System Requirements

- Documented quality management system
- Process validation and verification procedures
- Nonconforming material control system
- Corrective and Preventive Action (CAPA) system
- Statistical process control for critical parameters
- Change management system
- Document control system
- Component traceability system
- Calibration management system
- Internal audit program

### 7.3 Acceptable Quality Limits (AQLs)

| Inspection Type | AQL | Critical Defect | Major Defect | Minor Defect |
|----------------|-----|----------------|--------------|--------------|
| Incoming Components | 0.065% | 0% | 0.1% | 0.65% |
| In-Process Inspection | 0.1% | 0% | 0.15% | 1.0% |
| Final PCBA Inspection | 0.065% | 0% | 0.1% | 0.65% |

### 7.4 PCBA Acceptance Criteria

- Visual inspection per IPC-A-610 Class 3
- Solder joint quality per IPC-A-610 Class 3
- Component placement per IPC-A-610 Class 3
- Conformal coating per IPC-CC-830B
- Cleanliness per IPC-TM-650 method 2.3.25
- Ionic contamination: <1.56 μg/cm² NaCl equivalent
- Functional test: 100% pass rate
- Environmental test: 100% pass rate per criteria
- No physical damage, scratches, or cosmetic defects

### 7.5 Quality Improvement Process

- Monthly quality performance reviews
- Continuous improvement program
- Root cause analysis for any quality issues
- Process improvement projects
- Six Sigma or Lean Manufacturing methodologies
- Best practice sharing
- Supplier quality management program

## 8. Documentation Requirements

### 8.1 Manufacturing Documentation

The following documentation must be maintained for each production lot:

- Production work order
- Process routing
- Build records
- Material traceability records
- Process control charts
- Inspection and test records
- Nonconformance reports
- Rework and repair records
- Final acceptance documentation
- Certificate of Conformance (CoC)

### 8.2 Process Documentation

The following process documentation must be developed and maintained:

- Standard Operating Procedures (SOPs)
- Work Instructions
- Process Flow Diagrams
- Control Plans
- Process FMEA
- Equipment maintenance records
- Calibration records
- Process validation reports
- Process capability studies
- Training records

### 8.3 Reporting Requirements

The following reports must be submitted to TeraFlux:

- **Weekly**: Production status, yield data, defect summaries
- **Monthly**: Quality metrics, improvement initiatives, capacity utilization
- **Quarterly**: Process capability trends, technology roadmap updates
- **As Needed**: Non-conformance reports, corrective action status, engineering change impacts

### 8.4 Record Retention

Records must be retained for the following timeframes:

- Production records: Minimum 5 years
- Quality records: Minimum 5 years
- Traceability data: Minimum 7 years
- Test data: Minimum 5 years
- Calibration records: Minimum 3 years
- Training records: Duration of employment plus 2 years

## 9. Manufacturing Partner Qualifications

### 9.1 Required Technical Capabilities

The PCBA manufacturing partner must have the following capabilities:

- High-mix, medium-volume manufacturing capability
- Lead-free assembly capability
- Fine-pitch component placement (0.4mm pitch minimum)
- BGA and QFN assembly capabilities
- Conformal coating application
- X-ray inspection capability
- AOI systems
- Environmental testing capabilities
- In-circuit and functional testing capability
- Design for Manufacturability (DFM) review capability
- Process engineering support
- New Product Introduction (NPI) process

### 9.2 Required Experience

The PCBA manufacturing partner should have:

- Minimum 5 years experience in industrial electronics manufacturing
- Experience with outdoor/environmental monitoring product assembly
- Experience with IoT devices
- Experience with high-reliability electronics
- Experience with products requiring environmental durability
- Experience with sensor integration

### 9.3 Capacity Requirements

The manufacturing partner should have:

- Minimum capacity for 5,000 PCBAs per month at full production
- Ability to scale to 15,000 PCBAs per month within 12 months
- Quick-turn prototype capability (10-15 business days)
- Component sourcing capability for 90% of BOM
- Sufficient floor space for dedicated production line
- Sufficient equipment for all required processes
- Engineering support capacity for NPI and sustaining activities

### 9.4 Location Preferences

Preferred manufacturing partner locations are:

- United States (for IP protection and logistics)
- Mexico (for cost optimization with NAFTA benefits)
- Eastern Europe (for EU market support)
- East Asia (for high-volume, cost-sensitive production)

### 9.5 Business Requirements

The manufacturing partner should meet the following business requirements:

- Financial stability (minimum 3 years profitable operation)
- Appropriate business insurance coverage
- Willingness to sign comprehensive NDA
- Flexibility in business terms
- Customer-focused culture
- Transparent costing model
- Willingness to invest in dedicated equipment if needed
- Openness to on-site customer quality representatives

## 10. Intellectual Property Protection

### 10.1 Confidentiality Requirements

- Comprehensive NDA required prior to receiving design files
- Documented IP protection procedures
- Controlled access to TeraFlux design files
- Secure data storage and transmission
- Employee confidentiality agreements
- Clean desk policy in production areas
- Visitor control procedures
- No photography policy in production areas

### 10.2 Critical IP Components

The following elements are considered critical IP and require special protection:

- Proprietary sensor designs and integration methods
- Custom firmware and software (though CM will not receive source code)
- Circuit designs for specialized sensing functions
- Manufacturing processes developed specifically for TeraFlux products

### 10.3 Protection Measures

The following protection measures will be implemented:

- Limited access to complete design documentation
- Need-to-know information sharing
- No subcontracting without TeraFlux approval
- Return of all documentation upon project completion
- No reverse engineering clause in agreements
- Black-box approach for critical components supplied by TeraFlux
- Documentation watermarking and tracking
- Regular IP protection audits

## 11. Engagement Process

### 11.1 Initial Qualification Process

1. NDA execution
2. Manufacturer capability assessment
3. Quality system audit
4. Process capability assessment
5. Financial and business evaluation
6. Reference checks
7. Production process evaluation
8. Quote and terms negotiation
9. Prototype order placement
10. Prototype evaluation and acceptance
11. Manufacturing agreement execution

### 11.2 New Product Introduction Process

1. Design for manufacturability (DFM) review
2. Bill of Materials (BOM) review
3. Approved Vendor List (AVL) development
4. Component sourcing strategy
5. Test strategy development
6. Process development
7. Fixture and tooling development
8. First article build
9. First article inspection and testing
10. Process validation
11. Production readiness review
12. Production release

### 11.3 Ongoing Relationship Management

1. Regular business reviews (quarterly)
2. Quality performance reviews (monthly)
3. Capacity planning meetings (quarterly)
4. Technology roadmap discussions (semi-annually)
5. Continuous improvement projects (ongoing)
6. Cost reduction initiatives (quarterly)
7. Engineering change management (as needed)
8. Escalation process for issues
9. Contract renewals and amendments

## 12. Appendices

### Appendix A: Document Checklist for PCBA Manufacturing

| Document Type | Format | Required for Quote | Required for Production |
|---------------|--------|--------------------|-----------------------|
| Gerber Files | RS-274X | ✅ | ✅ |
| NC Drill Files | Excellon | ✅ | ✅ |
| Bill of Materials | Excel/CSV | ✅ | ✅ |
| Approved Vendor List | Excel/CSV | ❌ | ✅ |
| Assembly Drawings | PDF | ✅ | ✅ |
| Pick and Place Files | CSV/TXT | ✅ | ✅ |
| Schematic Diagrams | PDF | ❌ | ✅ |
| 3D Models | STEP | ❌ | ✅ |
| Test Specifications | PDF | ❌ | ✅ |
| Design Reviews | PDF | ❌ | ✅ |
| Component Datasheets | PDF | ❌ | ✅ |
| Functional Test Procedures | PDF | ❌ | ✅ |
| Special Instructions | PDF | ✅ | ✅ |

### Appendix B: Typical DFM Issues and Requirements

| Category | Requirement | Description |
|----------|-------------|-------------|
| Component Spacing | Minimum 0.5mm between components | Ensures reliable assembly and rework capability |
| Edge Clearance | Minimum 3mm from PCB edge | Prevents damage during depanelization |
| Test Point Access | 0.035" minimum test point size | Ensures reliable test contact |
| Thermal Relief | Required for high-power components | Prevents soldering issues |
| Via-in-Pad | Filled and plated where used | Prevents solder wicking |
| Fiducial Marks | Minimum 3 per PCB | Ensures accurate component placement |
| Panel Design | 4-up for small boards, max 18" x 24" | Optimizes manufacturing efficiency |
| Panel Tooling | 3mm tooling holes at corners | Required for manufacturing equipment |
| Reference Designators | Clear marking on silkscreen | Ensures assembly and test traceability |
| Component Orientation | Consistent orientation for same components | Minimizes assembly errors |

### Appendix C: Request for Quote (RFQ) Template

```
TeraFlux Studios - PCBA Manufacturing RFQ

COMPANY INFORMATION:
Company Name: TeraFlux Studios
Contact Person: [Name]
Email: [Email Address]
Phone: [Phone Number]
Date: [Date]

PROJECT OVERVIEW:
Product: [Product Name]
Description: [Brief Description]
Expected Annual Volume: [Volume Range]
Target Production Start: [Date]

QUOTE REQUIREMENTS:

1. PCB FABRICATION
   PCB Name: [PCB Name]
   Dimensions: [Dimensions]
   Layers: [Layer Count]
   Material: [Material Specification]
   Quantity: [Quantity]
   Special Requirements: [List Any Special Requirements]

2. PCBA MANUFACTURING
   Assembly Type: [SMT/Thru-hole/Mixed]
   Component Count: [Total Components] ([SMT Count] SMT, [THT Count] THT)
   BGA Component Count: [Count]
   Fine-Pitch Component Count: [Count]
   Special Processes Required: [List Processes]
   Testing Requirements: [List Testing Needs]
   
3. PRICING REQUEST
   □ Prototype Quantities (10, 25, 50 units)
   □ Production Quantities (100, 500, 1000, 5000 units)
   □ Turnkey (CM sources all components)
   □ Partial Turnkey (Customer supplies specific components)
   □ Labor Only (Customer supplies all components)
   
4. LEAD TIME REQUEST
   □ Standard Lead Time
   □ Expedited Service (if available)
   
5. ADDITIONAL SERVICES REQUIRED
   □ DFM Review
   □ Component Sourcing
   □ Test Development
   □ Conformal Coating
   □ Custom Packaging
   □ Drop Shipping
   □ Other: [Specify]
   
6. QUALITY REQUIREMENTS
   Required Certifications: [List Required Certifications]
   Quality Standards: [List Required Standards]
   
7. ATTACHMENTS
   □ Gerber Files
   □ BOM
   □ Pick and Place File
   □ Assembly Drawing
   □ Test Requirements
   □ Special Instructions
   
8. ADDITIONAL INFORMATION
   [Any Other Relevant Information]

QUOTE DUE DATE: [Date]

Please provide quote in writing by the due date above. Questions can be directed to [Contact Information].
```

### Appendix D: Abbreviations and Definitions

| Abbreviation | Definition |
|--------------|------------|
| PCBA | Printed Circuit Board Assembly |
| BGA | Ball Grid Array |
| QFN | Quad Flat No-leads |
| AOI | Automated Optical Inspection |
| ICT | In-Circuit Test |
| ENIG | Electroless Nickel Immersion Gold |
| BOM | Bill of Materials |
| DFM | Design for Manufacturability |
| AQL | Acceptable Quality Limit |
| SMT | Surface Mount Technology |
| THT | Through-Hole Technology |
| NPI | New Product Introduction |
| MSL | Moisture Sensitivity Level |
| PFMEA | Process Failure Mode Effects Analysis |
| SPC | Statistical Process Control |
| CoC | Certificate of Conformance |
| FAI | First Article Inspection |
| CM | Contract Manufacturer |

### Appendix E: Revision History

| Version | Date | Description | Author | Approver |
|---------|------|-------------|--------|----------|
| 0.1 | 2025-04-10 | Initial draft | J. Smith | |
| 0.2 | 2025-04-25 | Technical review updates | T. Johnson | |
| 0.3 | 2025-05-10 | Manufacturing review updates | S. Lee | |
| 1.0 | 2025-05-20 | Released version | J. Smith | A. Director |
