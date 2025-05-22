"""
Utilities for creating mock Environment3DState objects for testing purposes.
"""
import time
from typing import Dict, Any, Tuple, Optional, List

from .state import Environment3DState

def create_mock_environment_state(
    timestamp: Optional[float] = None,
    simulation_time_seconds: float = 0.0,
    default_temp_c: float = 22.0,
    default_humidity_percent: float = 45.0,
    default_pressure_hpa: float = 1012.0,
    chemical_concentrations: Optional[Dict[str, float]] = None, # chemical_id -> concentration_ppb
    pm_concentrations: Optional[Dict[str, float]] = None, # pm_size -> concentration_ug_m3
    emf_details: Optional[Dict[str, float]] = None, # e.g., {"v_per_m": 0.05, "dominant_freq_hz": 60.0}
    thermal_image_pattern: str = "uniform", # "uniform", "gradient_horizontal", "hotspot"
    thermal_image_base_temp_c: float = 22.0,
    thermal_image_hotspot_temp_c: float = 50.0,
    thermal_image_resolution: Tuple[int, int] = (80, 60)
) -> Environment3DState:
    """
    Creates a mock Environment3DState object with configurable default values
    and simple patterns for testing sensors.

    Args:
        timestamp: Absolute timestamp for the state. Defaults to current time.
        simulation_time_seconds: Simulation time in seconds.
        default_temp_c: Default ambient temperature.
        default_humidity_percent: Default relative humidity.
        default_pressure_hpa: Default barometric pressure.
        chemical_concentrations: Dict of chemical_id to its uniform concentration (ppb).
        pm_concentrations: Dict of PM size (e.g., "pm2.5") to its uniform concentration (ug/m3).
        emf_details: Dict defining EMF characteristics.
        thermal_image_pattern: Pattern for the mock thermal image.
        thermal_image_base_temp_c: Base temperature for the thermal image.
        thermal_image_hotspot_temp_c: Temperature for hotspots in thermal image.
        thermal_image_resolution: Resolution (width, height) for the mock thermal image.

    Returns:
        An Environment3DState instance populated with mock data.
    """
    if timestamp is None:
        timestamp = time.time()
    
    mock_state = Environment3DState(timestamp=timestamp, simulation_time_seconds=simulation_time_seconds)

    # Override query methods to return controlled mock data
    
    def mock_get_chemical_concentration(chemical_id: str, position, sampling_volume) -> float:
        return (chemical_concentrations or {}).get(chemical_id, 0.0)
    mock_state.get_chemical_concentration = mock_get_chemical_concentration

    def mock_get_temperature_celsius(position, sampling_volume) -> float:
        return default_temp_c
    mock_state.get_temperature_celsius = mock_get_temperature_celsius

    def mock_get_thermal_field_view(camera_position, camera_orientation, fov_degrees, resolution, **kwargs) -> List[List[float]]:
        # Parameters camera_position, camera_orientation, fov_degrees are now named to match the caller
        # **kwargs is added to accept any other potential arguments without erroring.
        img = [[thermal_image_base_temp_c for _ in range(resolution[0])] for _ in range(resolution[1])]
        if thermal_image_pattern == "gradient_horizontal":
            for r_idx in range(resolution[1]):
                for c_idx in range(resolution[0]):
                    img[r_idx][c_idx] = thermal_image_base_temp_c + (c_idx / resolution[0]) * 10.0 # 10C gradient
        elif thermal_image_pattern == "hotspot" and resolution[0] >= 5 and resolution[1] >= 5: # Relaxed condition for 5x5 hotspot
            hs_r, hs_c = resolution[1] // 2, resolution[0] // 2
            for r_offset in range(-2, 3): # 5x5 hotspot
                for c_offset in range(-2, 3): # 5x5 hotspot
                    if 0 <= hs_r + r_offset < resolution[1] and 0 <= hs_c + c_offset < resolution[0]:
                        img[hs_r + r_offset][hs_c + c_offset] = thermal_image_hotspot_temp_c
        return img
    mock_state.get_thermal_field_view = mock_get_thermal_field_view

    def mock_get_emf_field_strength(position, frequency_range_hz) -> Dict[str, float]:
        return emf_details or {"v_per_m": 0.0, "dominant_freq_hz": 0.0}
    mock_state.get_emf_field_strength = mock_get_emf_field_strength

    def mock_get_particulate_matter_concentration(pm_size: str, position, sampling_volume) -> float:
        return (pm_concentrations or {}).get(pm_size, 0.0)
    mock_state.get_particulate_matter_concentration = mock_get_particulate_matter_concentration

    def mock_get_relative_humidity_percent(position, sampling_volume) -> float:
        return default_humidity_percent
    mock_state.get_relative_humidity_percent = mock_get_relative_humidity_percent

    def mock_get_barometric_pressure_hpa(position) -> float:
        return default_pressure_hpa
    mock_state.get_barometric_pressure_hpa = mock_get_barometric_pressure_hpa
    
    # Add mocks for other query methods as needed for sensor testing...
    # e.g., get_acoustic_signature, get_vibration_levels, get_wind_vector, etc.
    # For now, they will use the default placeholders in Environment3DState.

    return mock_state


if __name__ == '__main__':
    # Example of using the mock state generator
    mock_env = create_mock_environment_state(
        simulation_time_seconds=120.0,
        default_temp_c=28.5,
        chemical_concentrations={"CO": 10.5, "NO2": 2.1}, # ppb
        pm_concentrations={"pm2.5": 15.2, "pm10": 25.0}, # ug/m3
        emf_details={"v_per_m": 1.5, "dominant_freq_hz": 50.0},
        thermal_image_pattern="hotspot",
        thermal_image_base_temp_c=20.0,
        thermal_image_hotspot_temp_c=75.0
    )

    print(f"Mock Environment State created: {mock_env}")
    print(f"  Query CO: {mock_env.get_chemical_concentration('CO', (0,0,0), None)} ppb")
    print(f"  Query O3 (not set): {mock_env.get_chemical_concentration('O3', (0,0,0), None)} ppb")
    print(f"  Query Temp: {mock_env.get_temperature_celsius((0,0,0), None)} C")
    print(f"  Query PM2.5: {mock_env.get_particulate_matter_concentration('pm2.5', (0,0,0), None)} ug/m3")
    print(f"  Query EMF: {mock_env.get_emf_field_strength((0,0,0), None)}")
    
    # Test thermal image
    thermal_img = mock_env.get_thermal_field_view((0,0,0), {}, (90,60), (10,8)) # Smaller res for printing
    print("  Mock Thermal Image (10x8, hotspot pattern):")
    # for row in thermal_img:
    #     print(f"    {[f'{val:.1f}' for val in row]}")
    # Check a hotspot pixel
    if len(thermal_img) > 4 and len(thermal_img[0]) > 4:
         print(f"    Center pixel (hotspot area): {thermal_img[4][4]}") # Should be hotspot temp
         print(f"    Corner pixel (base area): {thermal_img[0][0]}") # Should be base temp