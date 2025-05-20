# Exposure Tracking System

This module provides a comprehensive system for tracking, assessing, and managing exposure to various chemicals and environmental parameters. It integrates with sensitivity profiles to provide personalized risk assessments based on individual health factors.

## Status Update (May 19, 2025 - 10:30 PM)
- ✓ Checkpoint 1.3.2A: Exposure tracking system successfully records and manages exposure events
- ✓ Checkpoint 1.3.2B: Exposure aggregation correctly calculates total exposure burden
- ✓ Checkpoint 1.3.2C: Time-weighted average calculations validated against expected results
- ✓ Checkpoint 1.3.2D: Persistence mechanisms successfully maintain exposure history
- ✓ Task 1.3.2 Completed

## Core Components

The exposure tracking system consists of four main components:

### 1. Records (`records.py`)

Manages individual exposure records and exposure histories.

- `ExposureRecord`: Represents a single exposure event with attributes like chemical ID, concentration, duration, and location.
- `ExposureHistory`: Collects and organizes multiple ExposureRecords, providing methods for filtering and calculating metrics like time-weighted averages.

### 2. Assessment (`assessment.py`)

Evaluates exposure data against health thresholds and sensitivity profiles.

- `ExposureAssessment`: Assesses exposure against standard regulatory thresholds.
- `PersonalizedExposureAssessment`: Extends assessment by incorporating individual sensitivity factors based on physiological profiles.

### 3. Storage (`storage.py`)

Handles persistence for exposure records and histories.

- `ExposureStorage`: Manages saving and loading exposure data in various formats (JSON, CSV), including backup and restore functionality.

### 4. Demos and Tests

- `profile_integrated_demo.py`: Demonstrates the integration between exposure tracking and sensitivity profiles.
- `test_exposure_tracking.py`: Unit tests ensuring accurate implementation of core functionality.

## Key Features

- **Standardized Risk Levels**: Categorization of exposure risk from NEGLIGIBLE to SEVERE.
- **Time-Weighted Averages**: Calculation of exposure metrics like 8-hour TWA based on industry standards, using the trapezoid rule for time-series integration to accurately represent exposure patterns over time.
- **Health Threshold Comparison**: Evaluation against established regulatory limits (OSHA PEL, NIOSH REL, etc.).
- **Personalization**: Integration with sensitivity profiles to adjust assessments based on age, conditions, and individual sensitivities.
- **Storage & Visualization**: Tools for saving, loading, and visualizing exposure data with persistence mechanisms.

## Usage Examples

### Creating Exposure Records

```python
from envirosense.core.exposure.records import ExposureRecord, ExposureHistory

# Create individual exposure record
record = ExposureRecord(
    chemical_id="formaldehyde",
    concentration=0.05,  # ppm
    duration=1800,       # seconds
    location_id="kitchen",
    coordinates=(3.5, 2.0, 1.2)  # x, y, z in meters
)

# Create exposure history
history = ExposureHistory()
history.add_record(record)
```

### Performing Standard Assessment

```python
from envirosense.core.exposure.assessment import ExposureAssessment

# Create assessment
assessment = ExposureAssessment(history)

# Assess a specific chemical
result = assessment.assess_chemical("formaldehyde")
print(f"Risk level: {result['risk_level']}")

# Get metrics
twa = result["metrics"]["8hr_twa"]
peak = result["metrics"]["peak_concentration"]
```

### Performing Personalized Assessment

```python
from envirosense.core.exposure.assessment import PersonalizedExposureAssessment

# Load a sensitivity profile
with open("profile.json", "r") as f:
    profile = json.load(f)

# Create personalized assessment
personalized = PersonalizedExposureAssessment(history, profile)

# Assess exposure with personalization
result = personalized.assess_chemical("formaldehyde")

# Get personalization factor and metrics
factor = result["sensitivity_factor"]
adjusted_twa = result["metrics"]["adjusted_8hr_twa"]
```

### Storing Exposure Data

```python
from envirosense.core.exposure.storage import ExposureStorage

# Create storage manager
storage = ExposureStorage()

# Save exposure history
filepath = storage.save_history(history, format="json")

# Load exposure history
loaded_history = storage.load_history(filepath)

# Save visualization
visualization_path = storage.save_history_visualization(
    history,
    chemicals=["formaldehyde", "co"],
    include_thresholds=True
)
```

### Running the Demo

The `profile_integrated_demo.py` script demonstrates the full integration:

```bash
python -m envirosense.core.exposure.profile_integrated_demo
```

This will:
1. Generate sample exposure data for multiple chemicals
2. Create standard and personalized assessments
3. Create visualizations comparing assessment results
4. Save all data to the output directory

### Running the Tests

Unit tests validate all core functionality:

```bash
python -m envirosense.core.exposure.test_exposure_tracking
```

This validates:
- Record creation and management
- Time-weighted average calculations using trapezoid rule
- Exposure assessment against standard thresholds
- Personalized assessment with sensitivity profiles
- Storage and serialization functionality

## Integration with Other Components

The exposure tracking system integrates with:

- **Chemical Properties**: Uses chemical health data from `chemical_properties.py` for threshold evaluations.
- **Sensitivity Profiles**: Incorporates individual sensitivity data for personalized assessments.
- **Physics & Simulation**: Can use data from physics simulations as input for exposure records.

## Development Guidelines

When extending the exposure system:

1. Ensure all records have proper timestamps and chemical IDs
2. Use consistent units (ppm for concentration, seconds for duration)
3. Add unit tests for new functionality
4. Update visualizations when adding new assessment metrics
5. Document sensitivity factors and personalization logic

## Future Enhancements

Planned enhancements for this system include:

- Integration with real-time sensor data
- Expanded health effects prediction using machine learning models
- Support for complex exposure scenarios with multiple interacting chemicals
- Mobile notification system for real-time exposure alerts
