"""
This module will contain implementations for fire-related simulation scenarios,
all inheriting from BaseScenario. These scenarios are designed to generate
data for testing fire precursor detection algorithms and for ML training.
"""

from typing import Dict, Any, Optional, List

from pydantic import BaseModel, Field, validator

from .base import BaseScenario, ScenarioComplexity
# from envirosense.simulation_engine.physics_orchestrator import Environment3DOrchestrator # Example import

class CellulosePyrolysisParams(BaseModel):
    """
    Parameters for configuring the CellulosePyrolysisScenario.
    """
    location: List[float] = Field(
        default_factory=lambda: [0.0, 0.0, 0.5],
        min_items=3,
        max_items=3,
        description="Location [x, y, z] of the pyrolysis event."
    )
    base_emission_rates_g_s: Dict[str, float] = Field(
        default_factory=lambda: {"CO": 0.001, "CH2O": 0.0005},
        description="Base emission rates in grams per second for key VOCs at peak_intensity (intensity=1.0)."
    )
    initial_intensity: float = Field(
        default=0.1,
        ge=0,
        le=1.0,
        description="Initial intensity factor of emissions (0.0 to 1.0)."
    )
    peak_intensity: float = Field(
        default=1.0,
        ge=0,
        le=1.0,
        description="Peak intensity factor of emissions (0.0 to 1.0)."
    )
    peak_time_factor: float = Field(
        default=0.6,
        ge=0,
        le=1.0,
        description="Fraction of total scenario duration at which peak emission intensity occurs."
    )

    @validator('peak_intensity')
    def check_peak_intensity_ge_initial(cls, v, values):
        if 'initial_intensity' in values and v < values['initial_intensity']:
            raise ValueError("peak_intensity must be greater than or equal to initial_intensity.")
        return v

    class Config:
        extra = "forbid"


class CellulosePyrolysisScenario(BaseScenario):
    def __init__(self, scenario_id: str, name: Optional[str] = "Cellulose Pyrolysis",
                 description: Optional[str] = "Simulates the slow pyrolysis of cellulosic materials, a common fire precursor, releasing CO, Formaldehyde, Acetic Acid, etc.",
                 expected_duration_seconds: Optional[float] = 3600.0, # 1 hour
                 difficulty_level: ScenarioComplexity = ScenarioComplexity.MEDIUM,
                 location: List[float] = [0.0, 0.0, 0.5],
                 base_emission_rates_g_s: Dict[str, float] = {"CO": 0.001, "CH2O": 0.0005},
                 initial_intensity: float = 0.1,
                 peak_intensity: float = 1.0,
                 peak_time_factor: float = 0.6,
                 **kwargs):
        super().__init__(scenario_id=scenario_id, name=name, description=description,
                         category="fire_precursor",
                         difficulty_level=difficulty_level,
                         expected_duration_seconds=expected_duration_seconds,
                         **kwargs)
        
        param_dict = {
            "location": location,
            "base_emission_rates_g_s": base_emission_rates_g_s,
            "initial_intensity": initial_intensity,
            "peak_intensity": peak_intensity,
            "peak_time_factor": peak_time_factor
        }
        self.params = CellulosePyrolysisParams(**param_dict)

        self.active_source_id: Optional[str] = f"cellulose_pyro_{self.scenario_id}"
        self.pyrolysis_active = False
        self.current_intensity_factor = 0.0 # Will be set in setup_environment

    def _get_specific_params(self) -> Dict[str, Any]:
        """Returns the scenario-specific parameters as a dictionary."""
        return self.params.model_dump(mode='python')

    def _calculate_current_intensity(self) -> float:
        """Calculates current emission intensity based on scenario parameters and time."""
        if not self.expected_duration_seconds or self.expected_duration_seconds == 0:
            return self.params.initial_intensity
        
        progress = self.current_time_seconds / self.expected_duration_seconds
        
        intensity = 0.0
        if progress < self.params.peak_time_factor:
            # Ramp up from initial to peak
            # Ensure peak_time_factor is not zero to avoid division by zero
            denominator = self.params.peak_time_factor if self.params.peak_time_factor > 0 else 1.0
            intensity = self.params.initial_intensity + \
                        (self.params.peak_intensity - self.params.initial_intensity) * (progress / denominator)
        else:
            # Ramp down from peak to a lower value (e.g., initial_intensity or 0)
            ramp_down_duration_factor = 1.0 - self.params.peak_time_factor
            if ramp_down_duration_factor > 0:
                progress_in_ramp_down = (progress - self.params.peak_time_factor) / ramp_down_duration_factor
                intensity = self.params.peak_intensity - \
                            (self.params.peak_intensity - self.params.initial_intensity) * progress_in_ramp_down # Ramp down to initial
            else: # At peak or beyond if peak_time_factor is 1
                intensity = self.params.peak_intensity
        
        return max(0.0, min(intensity, self.params.peak_intensity)) # Clamp between 0 and peak_intensity

    def setup_environment(self, environment_3d_orchestrator: Any) -> None:
        self.reset()
        self.pyrolysis_active = True
        self.current_intensity_factor = self.params.initial_intensity # Use param
        
        current_emission_rates = {k: v * self.current_intensity_factor for k, v in self.params.base_emission_rates_g_s.items()}

        if hasattr(environment_3d_orchestrator, 'add_chemical_source') and self.active_source_id:
            environment_3d_orchestrator.add_chemical_source(
                source_id=self.active_source_id,
                position=self.params.location,
                emission_rates_g_s=current_emission_rates,
                source_type="cellulose_pyrolysis"
            )
        print(f"Scenario {self.scenario_id}: Cellulose pyrolysis source activated at {self.params.location} with initial intensity {self.current_intensity_factor}.")

    def get_ground_truth_labels(self, environment_3d_state: Any) -> Dict[str, Any]:
        return {
            "event_type": "cellulose_pyrolysis",
            "is_anomaly": self.pyrolysis_active,
            "fire_precursor_stage": 1,
            "current_intensity_factor": round(self.current_intensity_factor, 3),
            "location": self.params.location,
            "active_source_id": self.active_source_id if self.pyrolysis_active else None
        }

    def update(self, time_step_seconds: float, environment_3d_orchestrator: Any) -> None:
        super().update(time_step_seconds, environment_3d_orchestrator)

        if not self.pyrolysis_active:
            return
            
        self.current_intensity_factor = self._calculate_current_intensity()
        current_emission_rates = {k: v * self.current_intensity_factor for k, v in self.params.base_emission_rates_g_s.items()}

        if hasattr(environment_3d_orchestrator, 'update_chemical_source_emissions') and self.active_source_id:
            environment_3d_orchestrator.update_chemical_source_emissions(self.active_source_id, current_emission_rates)
        
        if self.is_completed(None):
            self.pyrolysis_active = False
            if hasattr(environment_3d_orchestrator, 'remove_source') and self.active_source_id:
                environment_3d_orchestrator.remove_source(self.active_source_id)
            print(f"Scenario {self.scenario_id}: Cellulose pyrolysis completed and source deactivated.")

    def is_completed(self, environment_3d_state: Any) -> bool:
        if self.expected_duration_seconds is not None and \
           self.current_time_seconds >= self.expected_duration_seconds:
            # Placeholder: orchestrator.remove_chemical_source(self.active_source_id)
            return True
        return False

class LigninDecompositionParams(BaseModel):
    """
    Parameters for configuring the LigninDecompositionScenario.
    """
    location: List[float] = Field(
        default_factory=lambda: [0.0, 0.0, 0.5],
        min_items=3,
        max_items=3,
        description="Location [x, y, z] of the lignin decomposition event."
    )
    base_emission_rates_g_s: Dict[str, float] = Field(
        default_factory=lambda: {"Phenol": 0.0008, "Guaiacol": 0.0006},
        description="Base emission rates in grams per second for key VOCs at peak_intensity (intensity=1.0)."
    )
    initial_intensity: float = Field(
        default=0.1,
        ge=0,
        le=1.0,
        description="Initial intensity factor of emissions (0.0 to 1.0)."
    )
    peak_intensity: float = Field(
        default=1.0,
        ge=0,
        le=1.0,
        description="Peak intensity factor of emissions (0.0 to 1.0)."
    )
    peak_time_factor: float = Field(
        default=0.7,
        ge=0,
        le=1.0,
        description="Fraction of total scenario duration at which peak emission intensity occurs."
    )

    @validator('peak_intensity')
    def check_peak_intensity_ge_initial(cls, v, values):
        if 'initial_intensity' in values and v < values['initial_intensity']:
            raise ValueError("peak_intensity must be greater than or equal to initial_intensity.")
        return v

    class Config:
        extra = "forbid"


class LigninDecompositionScenario(BaseScenario):
    def __init__(self, scenario_id: str, name: Optional[str] = "Lignin Decomposition",
                 description: Optional[str] = "Simulates the decomposition of lignin, producing different VOC signatures (e.g., phenols, guaiacols).",
                 expected_duration_seconds: Optional[float] = 2700.0, # 45 minutes
                 difficulty_level: ScenarioComplexity = ScenarioComplexity.MEDIUM,
                 location: List[float] = [0.0, 0.0, 0.5],
                 base_emission_rates_g_s: Dict[str, float] = {"Phenol": 0.0008, "Guaiacol": 0.0006},
                 initial_intensity: float = 0.1,
                 peak_intensity: float = 1.0,
                 peak_time_factor: float = 0.7,
                 **kwargs):
        super().__init__(scenario_id=scenario_id, name=name, description=description,
                         category="fire_precursor",
                         difficulty_level=difficulty_level,
                         expected_duration_seconds=expected_duration_seconds,
                         **kwargs)
        
        param_dict = {
            "location": location,
            "base_emission_rates_g_s": base_emission_rates_g_s,
            "initial_intensity": initial_intensity,
            "peak_intensity": peak_intensity,
            "peak_time_factor": peak_time_factor
        }
        self.params = LigninDecompositionParams(**param_dict)

        self.active_source_id: Optional[str] = f"lignin_decomp_{self.scenario_id}"
        self.decomposition_active = False
        self.current_intensity_factor = 0.0 # Will be set in setup_environment

    def _get_specific_params(self) -> Dict[str, Any]:
        """Returns the scenario-specific parameters as a dictionary."""
        return self.params.model_dump(mode='python')

    def _calculate_current_intensity(self) -> float:
        """Calculates current emission intensity based on scenario parameters and time."""
        if not self.expected_duration_seconds or self.expected_duration_seconds == 0:
            return self.params.initial_intensity
        
        progress = self.current_time_seconds / self.expected_duration_seconds
        
        intensity = 0.0
        if progress < self.params.peak_time_factor:
            # Ramp up from initial to peak
            denominator = self.params.peak_time_factor if self.params.peak_time_factor > 0 else 1.0
            intensity = self.params.initial_intensity + \
                        (self.params.peak_intensity - self.params.initial_intensity) * (progress / denominator)
        else:
            # Ramp down from peak
            ramp_down_duration_factor = 1.0 - self.params.peak_time_factor
            if ramp_down_duration_factor > 0:
                progress_in_ramp_down = (progress - self.params.peak_time_factor) / ramp_down_duration_factor
                intensity = self.params.peak_intensity - \
                            (self.params.peak_intensity - self.params.initial_intensity) * progress_in_ramp_down # Ramp down to initial
            else: # At peak or beyond if peak_time_factor is 1
                intensity = self.params.peak_intensity
        
        return max(0.0, min(intensity, self.params.peak_intensity))

    def setup_environment(self, environment_3d_orchestrator: Any) -> None:
        self.reset()
        self.decomposition_active = True
        self.current_intensity_factor = self.params.initial_intensity # Use param
        
        current_emission_rates = {k: v * self.current_intensity_factor for k, v in self.params.base_emission_rates_g_s.items()}

        if hasattr(environment_3d_orchestrator, 'add_chemical_source') and self.active_source_id:
            environment_3d_orchestrator.add_chemical_source(
                source_id=self.active_source_id,
                position=self.params.location,
                emission_rates_g_s=current_emission_rates,
                source_type="lignin_decomposition"
            )
        print(f"Scenario {self.scenario_id}: Lignin decomposition source activated at {self.params.location} with initial intensity {self.current_intensity_factor}.")

    def get_ground_truth_labels(self, environment_3d_state: Any) -> Dict[str, Any]:
        return {
            "event_type": "lignin_decomposition",
            "is_anomaly": self.decomposition_active,
            "fire_precursor_stage": 2,
            "current_intensity_factor": round(self.current_intensity_factor, 3),
            "location": self.params.location,
            "active_source_id": self.active_source_id if self.decomposition_active else None
        }

    def update(self, time_step_seconds: float, environment_3d_orchestrator: Any) -> None:
        super().update(time_step_seconds, environment_3d_orchestrator)

        if not self.decomposition_active:
            return
            
        self.current_intensity_factor = self._calculate_current_intensity()
        current_emission_rates = {k: v * self.current_intensity_factor for k, v in self.params.base_emission_rates_g_s.items()}

        if hasattr(environment_3d_orchestrator, 'update_chemical_source_emissions') and self.active_source_id:
            environment_3d_orchestrator.update_chemical_source_emissions(self.active_source_id, current_emission_rates)
        
        if self.is_completed(None):
            self.decomposition_active = False
            if hasattr(environment_3d_orchestrator, 'remove_source') and self.active_source_id:
                environment_3d_orchestrator.remove_source(self.active_source_id)
            print(f"Scenario {self.scenario_id}: Lignin decomposition completed and source deactivated.")

    def is_completed(self, environment_3d_state: Any) -> bool:
        if self.expected_duration_seconds is not None and \
           self.current_time_seconds >= self.expected_duration_seconds:
            return True
        return False

class EarlyCombustionParams(BaseModel):
    """
    Parameters for configuring an EarlyCombustionScenario.
    """
    location: List[float] = Field(
        default_factory=lambda: [0.0, 0.0, 0.0],
        min_items=3,
        max_items=3,
        description="Location [x, y, z] of the combustion event."
    )
    initial_heat_w: float = Field(
        default=500.0,
        ge=0,
        description="Initial heat output in Watts at the start of the scenario."
    )
    max_heat_w: float = Field(
        default=5000.0,
        ge=0,
        description="Maximum heat output in Watts, typically reached towards the end of the scenario duration."
    )
    chemical_emission_rates_g_s: Dict[str, float] = Field(
        default_factory=lambda: {"CO": 0.01, "PM2.5": 0.005},
        description="Dictionary of chemical species to their constant emission rates in grams per second during the event."
    )

    @validator('max_heat_w')
    def check_max_heat_w_greater_than_initial(cls, v, values):
        if 'initial_heat_w' in values and v < values['initial_heat_w']:
            raise ValueError("max_heat_w must be greater than or equal to initial_heat_w")
        return v

    class Config:
        extra = "forbid"


class EarlyCombustionScenario(BaseScenario):
    def __init__(self, scenario_id: str, name: Optional[str] = "Early Combustion",
                 description: Optional[str] = "Simulates the initial phase of smoldering or flaming combustion.",
                 expected_duration_seconds: Optional[float] = 1800.0,
                 difficulty_level: ScenarioComplexity = ScenarioComplexity.HIGH,
                 location: List[float] = [0.0,0.0,0.0], # Matched default_factory
                 initial_heat_w: float = 500.0,
                 max_heat_w: float = 5000.0,
                 chemical_emission_rates_g_s: Dict[str, float] = {"CO": 0.01, "PM2.5": 0.005}, # Matched default_factory
                 **kwargs):
        super().__init__(scenario_id=scenario_id, name=name, description=description,
                         category="fire_event",
                         difficulty_level=difficulty_level,
                         expected_duration_seconds=expected_duration_seconds,
                         **kwargs)
        
        param_dict = {
            "location": location,
            "initial_heat_w": initial_heat_w,
            "max_heat_w": max_heat_w,
            "chemical_emission_rates_g_s": chemical_emission_rates_g_s
        }
        self.params = EarlyCombustionParams(**param_dict)
        
        self.combustion_location = self.params.location # Keep for direct access if needed, sourced from params

        self.active_source_ids: Dict[str, Optional[str]] = {
            "heat": f"comb_heat_{self.scenario_id}",
            "chemical": f"comb_chem_{self.scenario_id}"
        }
        self.combustion_active = False
        self.current_heat_w = 0.0 # Will be set in setup_environment

    def _get_specific_params(self) -> Dict[str, Any]:
        """Returns the scenario-specific parameters as a dictionary."""
        return self.params.model_dump(mode='python')

    def setup_environment(self, environment_3d_orchestrator: Any) -> None:
        self.reset()
        self.combustion_active = True
        self.current_heat_w = self.params.initial_heat_w # Use param for initial value

        heat_source_id = self.active_source_ids.get("heat")
        if hasattr(environment_3d_orchestrator, 'add_heat_source') and heat_source_id:
            environment_3d_orchestrator.add_heat_source(
                source_id=heat_source_id,
                position=self.params.location,
                heat_output_watts=self.current_heat_w,
                source_type="early_combustion"
            )
        
        chem_source_id = self.active_source_ids.get("chemical")
        if hasattr(environment_3d_orchestrator, 'add_chemical_source') and chem_source_id:
            environment_3d_orchestrator.add_chemical_source(
                source_id=chem_source_id,
                position=self.params.location,
                emission_rates_g_s=self.params.chemical_emission_rates_g_s,
                source_type="early_combustion_smoke_gases"
            )
        print(f"Scenario {self.scenario_id}: Early combustion sources activated at {self.params.location}.")

    def get_ground_truth_labels(self, environment_3d_state: Any) -> Dict[str, Any]:
        stage = "smoldering"
        if self.current_heat_w > (self.params.initial_heat_w + self.params.max_heat_w) / 2:
            stage = "flaming_initial"

        active_ids_for_label = {}
        if self.combustion_active:
            if self.active_source_ids.get("heat"): active_ids_for_label["heat"] = self.active_source_ids["heat"]
            if self.active_source_ids.get("chemical"): active_ids_for_label["chemical"] = self.active_source_ids["chemical"]
            
        return {
            "event_type": "early_combustion",
            "is_anomaly": self.combustion_active,
            "fire_event_stage": stage,
            "current_heat_output_watts": round(self.current_heat_w,1),
            "combustion_location": self.params.location,
            "active_source_ids": active_ids_for_label
        }

    def update(self, time_step_seconds: float, environment_3d_orchestrator: Any) -> None:
        super().update(time_step_seconds, environment_3d_orchestrator)

        if not self.combustion_active:
            return

        # Gradually increase heat output
        if self.current_heat_w < self.params.max_heat_w and self.expected_duration_seconds and self.expected_duration_seconds > 0:
            progression_factor = self.current_time_seconds / self.expected_duration_seconds
            self.current_heat_w = self.params.initial_heat_w + (self.params.max_heat_w - self.params.initial_heat_w) * min(progression_factor, 1.0)
            
            heat_source_id = self.active_source_ids.get("heat")
            if hasattr(environment_3d_orchestrator, 'update_source_intensity') and heat_source_id:
                 environment_3d_orchestrator.update_source_intensity(heat_source_id, self.current_heat_w)
            # Chemical emission rates are constant as per current Pydantic model, no update needed here for them.

        if self.is_completed(None):
            self.combustion_active = False
            if hasattr(environment_3d_orchestrator, 'remove_source'):
                if self.active_source_ids["heat"]:
                    environment_3d_orchestrator.remove_source(self.active_source_ids["heat"])
                if self.active_source_ids["chemical"]:
                    environment_3d_orchestrator.remove_source(self.active_source_ids["chemical"])
            print(f"Scenario {self.scenario_id}: Early combustion completed and sources deactivated.")


    def is_completed(self, environment_3d_state: Any) -> bool:
        if self.expected_duration_seconds is not None and \
           self.current_time_seconds >= self.expected_duration_seconds:
            return True
        # Could also complete if a certain temperature is reached in environment_3d_state
        return False

class ComboHeatSourceParams(BaseModel):
    """Parameters for the heat source component of a combo scenario."""
    location: List[float] = Field(min_items=3, max_items=3, description="Location [x,y,z] of the heat source.")
    start_heat_w: float = Field(ge=0, description="Initial heat output in Watts when the source activates.")
    max_heat_w: float = Field(ge=0, description="Maximum heat output in Watts.")
    start_delay_factor: float = Field(
        default=0.0, ge=0, le=1.0,
        description="Delay before heat source activation, as a fraction of total scenario duration."
    )
    duration_factor: float = Field(
        gt=0, le=1.0,
        description="Duration of heat source activity, as a fraction of total scenario duration."
    )
    peak_time_factor: float = Field(
        default=0.5, ge=0, le=1.0,
        description="Time to reach max_heat_w, as a fraction of this heat source's own active duration."
    )

    @validator('max_heat_w')
    def check_max_heat_ge_start(cls, v, values):
        if 'start_heat_w' in values and v < values['start_heat_w']:
            raise ValueError("max_heat_w must be greater than or equal to start_heat_w.")
        return v

    class Config:
        extra = "forbid"

class ComboChemicalSourceParams(BaseModel):
    """Parameters for the chemical source component of a combo scenario."""
    location: List[float] = Field(min_items=3, max_items=3, description="Location [x,y,z] of the chemical source.")
    base_emission_rates_g_s: Dict[str, float] = Field(description="Base emission rates (at intensity 1.0) in g/s.")
    start_delay_factor: float = Field(
        default=0.0, ge=0, le=1.0,
        description="Delay before chemical source activation, as a fraction of total scenario duration."
    )
    duration_factor: float = Field(
        gt=0, le=1.0,
        description="Duration of chemical source activity, as a fraction of total scenario duration."
    )
    initial_intensity: float = Field(default=0.1, ge=0, le=1.0, description="Initial emission intensity factor.")
    peak_intensity: float = Field(default=1.0, ge=0, le=1.0, description="Peak emission intensity factor.")
    peak_time_factor: float = Field(
        default=0.5, ge=0, le=1.0,
        description="Time to reach peak_intensity, as a fraction of this chemical source's own active duration."
    )

    @validator('peak_intensity')
    def check_peak_intensity_ge_initial(cls, v, values):
        if 'initial_intensity' in values and v < values['initial_intensity']:
            raise ValueError("peak_intensity must be greater than or equal to initial_intensity.")
        return v
        
    class Config:
        extra = "forbid"

class FirePrecursorComboParams(BaseModel):
    """
    Parameters for configuring the FirePrecursorComboScenario.
    At least one source (heat or chemical) must be configured.
    """
    heat_source_config: Optional[ComboHeatSourceParams] = None
    chemical_source_config: Optional[ComboChemicalSourceParams] = None

    # Pydantic v2 style model validator
    @validator('*', pre=True, always=True) # Generic validator, specific logic below
    def check_at_least_one_source(cls, values):
        # This is a placeholder for a root_validator (Pydantic v1) or model_validator (Pydantic v2)
        # The actual implementation would depend on the Pydantic version.
        # For now, this check will be enforced in the __init__ of the scenario.
        # if not values.get('heat_source_config') and not values.get('chemical_source_config'):
        #     raise ValueError("At least one of heat_source_config or chemical_source_config must be provided.")
        return values

    class Config:
        extra = "forbid"


class FirePrecursorComboScenario(BaseScenario):
    def __init__(self, scenario_id: str, name: Optional[str] = "Fire Precursor Combination",
                 description: Optional[str] = "Simulates multiple fire precursor conditions interacting.",
                 expected_duration_seconds: Optional[float] = 3600.0,
                 difficulty_level: ScenarioComplexity = ScenarioComplexity.VERY_HIGH,
                 heat_source_config: Optional[Dict[str, Any]] = None,
                 chemical_source_config: Optional[Dict[str, Any]] = None,
                 **kwargs):
        super().__init__(scenario_id=scenario_id, name=name, description=description,
                         category="fire_precursor_complex",
                         difficulty_level=difficulty_level,
                         expected_duration_seconds=expected_duration_seconds,
                         **kwargs)

        parsed_heat_config = ComboHeatSourceParams(**heat_source_config) if heat_source_config else None
        parsed_chem_config = ComboChemicalSourceParams(**chemical_source_config) if chemical_source_config else None

        if parsed_heat_config is None and parsed_chem_config is None:
            raise ValueError("FirePrecursorComboScenario requires at least one of heat_source_config or chemical_source_config.")

        self.params = FirePrecursorComboParams(
            heat_source_config=parsed_heat_config,
            chemical_source_config=parsed_chem_config
        )
        
        self.active_source_ids: Dict[str, Optional[str]] = {
            "combo_heat": f"combo_h_{self.scenario_id}" if self.params.heat_source_config else None,
            "combo_chemical": f"combo_c_{self.scenario_id}" if self.params.chemical_source_config else None
        }
        self.sources_active: Dict[str, bool] = {"heat": False, "chemical": False}
        
        self.current_heat_w: float = 0.0
        self.current_chem_intensity_factor: float = 0.0
        self.scenario_active = False

    def _get_specific_params(self) -> Dict[str, Any]:
        return self.params.model_dump(mode='python', exclude_none=True)

    def setup_environment(self, environment_3d_orchestrator: Any) -> None:
        self.reset()
        self.sources_active = {"heat": False, "chemical": False} # Reset activity state
        self.current_heat_w = 0.0
        self.current_chem_intensity_factor = 0.0
        self.scenario_active = True

        # Initial setup for heat source (if defined and starts immediately based on its delay_factor = 0)
        if self.params.heat_source_config and self.params.heat_source_config.start_delay_factor == 0.0:
            h_cfg = self.params.heat_source_config
            self.current_heat_w = h_cfg.start_heat_w
            if self.current_heat_w > 0 and self.active_source_ids.get("combo_heat"):
                 if hasattr(environment_3d_orchestrator, 'add_heat_source'): # Assuming add_heat_source for consistency
                    environment_3d_orchestrator.add_heat_source(
                        source_id=self.active_source_ids["combo_heat"],
                        position=h_cfg.location,
                        heat_output_watts=self.current_heat_w,
                        source_type="combo_heat_component"
                    )
                    self.sources_active["heat"] = True
                    print(f"Scenario {self.scenario_id}: Combo heat source initially active with {self.current_heat_w}W.")
        
        # Chemical source activation is handled in update based on its start_delay_factor
        print(f"Scenario {self.scenario_id}: Combination precursor scenario initialized.")

    def get_ground_truth_labels(self, environment_3d_state: Any) -> Dict[str, Any]:
        active_sids_for_label = {}
        if self.sources_active.get("heat") and self.active_source_ids.get("combo_heat"):
            active_sids_for_label["heat"] = self.active_source_ids["combo_heat"]
        if self.sources_active.get("chemical") and self.active_source_ids.get("combo_chemical"):
            active_sids_for_label["chemical"] = self.active_source_ids["combo_chemical"]
        
        factors = []
        if self.sources_active.get("heat"): factors.append("overheating_component")
        if self.sources_active.get("chemical"): factors.append("flammable_offgassing")

        return {
            "event_type": "multi_fire_precursor",
            "is_anomaly": any(self.sources_active.values()),
            "contributing_factors": factors,
            "current_heat_output_watts": round(self.current_heat_w, 1) if self.sources_active.get("heat") else 0,
            "current_chemical_intensity_factor": round(self.current_chem_intensity_factor, 3) if self.sources_active.get("chemical") else 0,
            "active_source_ids": active_sids_for_label
        }

    def update(self, time_step_seconds: float, environment_3d_orchestrator: Any) -> None:
        super().update(time_step_seconds, environment_3d_orchestrator)

        if not self.scenario_active:
            return
        
        total_duration = self.expected_duration_seconds or 1.0 # Avoid division by zero if duration is None/0

        # --- Update Heat Source ---
        if self.params.heat_source_config and self.active_source_ids.get("combo_heat"):
            h_cfg = self.params.heat_source_config
            heat_start_delay_abs = total_duration * h_cfg.start_delay_factor
            heat_duration_abs = total_duration * h_cfg.duration_factor
            heat_peak_time_in_own_duration_abs = heat_duration_abs * h_cfg.peak_time_factor
            heat_peak_time_scenario_abs = heat_start_delay_abs + heat_peak_time_in_own_duration_abs
            heat_end_time_abs = heat_start_delay_abs + heat_duration_abs

            if not self.sources_active["heat"] and self.current_time_seconds >= heat_start_delay_abs and self.current_time_seconds < heat_end_time_abs:
                self.current_heat_w = h_cfg.start_heat_w
                if hasattr(environment_3d_orchestrator, 'add_heat_source') and self.active_source_ids.get("combo_heat"):
                    environment_3d_orchestrator.add_heat_source(
                        source_id=self.active_source_ids["combo_heat"], position=h_cfg.location,
                        heat_output_watts=self.current_heat_w, source_type="combo_heat_component")
                    self.sources_active["heat"] = True
                    print(f"Scenario {self.scenario_id}: Combo heat source activated at {self.current_time_seconds:.0f}s.")
            
            if self.sources_active["heat"] and self.current_time_seconds < heat_end_time_abs:
                effective_time_in_heat = self.current_time_seconds - heat_start_delay_abs
                if effective_time_in_heat < heat_peak_time_in_own_duration_abs and heat_peak_time_in_own_duration_abs > 0:
                    prog = effective_time_in_heat / heat_peak_time_in_own_duration_abs
                    self.current_heat_w = h_cfg.start_heat_w + (h_cfg.max_heat_w - h_cfg.start_heat_w) * prog
                elif (heat_duration_abs - heat_peak_time_in_own_duration_abs) > 0:
                    prog = (effective_time_in_heat - heat_peak_time_in_own_duration_abs) / (heat_duration_abs - heat_peak_time_in_own_duration_abs)
                    self.current_heat_w = h_cfg.max_heat_w - (h_cfg.max_heat_w - h_cfg.start_heat_w) * prog
                else:
                    self.current_heat_w = h_cfg.max_heat_w
                self.current_heat_w = max(0, min(self.current_heat_w, h_cfg.max_heat_w))

                if hasattr(environment_3d_orchestrator, 'update_source_intensity') and self.active_source_ids.get("combo_heat"):
                    environment_3d_orchestrator.update_source_intensity(self.active_source_ids["combo_heat"], self.current_heat_w)

            elif self.sources_active["heat"] and self.current_time_seconds >= heat_end_time_abs:
                if hasattr(environment_3d_orchestrator, 'remove_source') and self.active_source_ids.get("combo_heat"):
                    environment_3d_orchestrator.remove_source(self.active_source_ids["combo_heat"])
                self.sources_active["heat"] = False
                self.current_heat_w = 0.0
                print(f"Scenario {self.scenario_id}: Combo heat source deactivated at {self.current_time_seconds:.0f}s.")

        # --- Update Chemical Source ---
        if self.params.chemical_source_config and self.active_source_ids.get("combo_chemical"):
            c_cfg = self.params.chemical_source_config
            chem_start_delay_abs = total_duration * c_cfg.start_delay_factor
            chem_duration_abs = total_duration * c_cfg.duration_factor
            chem_peak_time_in_own_duration_abs = chem_duration_abs * c_cfg.peak_time_factor
            chem_peak_time_scenario_abs = chem_start_delay_abs + chem_peak_time_in_own_duration_abs
            chem_end_time_abs = chem_start_delay_abs + chem_duration_abs
            
            if not self.sources_active["chemical"] and self.current_time_seconds >= chem_start_delay_abs and self.current_time_seconds < chem_end_time_abs:
                self.current_chem_intensity_factor = c_cfg.initial_intensity
                current_emissions = {k: v * self.current_chem_intensity_factor for k,v in c_cfg.base_emission_rates_g_s.items()}
                if hasattr(environment_3d_orchestrator, 'add_chemical_source') and self.active_source_ids.get("combo_chemical"):
                    environment_3d_orchestrator.add_chemical_source(
                        source_id=self.active_source_ids["combo_chemical"], position=c_cfg.location,
                        emission_rates_g_s=current_emissions, source_type="combo_chemical_offgassing")
                    self.sources_active["chemical"] = True
                    print(f"Scenario {self.scenario_id}: Combo chemical source activated at {self.current_time_seconds:.0f}s.")

            if self.sources_active["chemical"] and self.current_time_seconds < chem_end_time_abs:
                effective_time_in_chem = self.current_time_seconds - chem_start_delay_abs
                if effective_time_in_chem < chem_peak_time_in_own_duration_abs and chem_peak_time_in_own_duration_abs > 0:
                    prog = effective_time_in_chem / chem_peak_time_in_own_duration_abs
                    self.current_chem_intensity_factor = c_cfg.initial_intensity + (c_cfg.peak_intensity - c_cfg.initial_intensity) * prog
                elif (chem_duration_abs - chem_peak_time_in_own_duration_abs) > 0:
                    prog = (effective_time_in_chem - chem_peak_time_in_own_duration_abs) / (chem_duration_abs - chem_peak_time_in_own_duration_abs)
                    self.current_chem_intensity_factor = c_cfg.peak_intensity - (c_cfg.peak_intensity - c_cfg.initial_intensity) * prog
                else:
                    self.current_chem_intensity_factor = c_cfg.peak_intensity
                self.current_chem_intensity_factor = max(0, min(self.current_chem_intensity_factor, c_cfg.peak_intensity))
                
                current_emissions = {k: v * self.current_chem_intensity_factor for k,v in c_cfg.base_emission_rates_g_s.items()}
                if hasattr(environment_3d_orchestrator, 'update_chemical_source_emissions') and self.active_source_ids.get("combo_chemical"):
                     environment_3d_orchestrator.update_chemical_source_emissions(self.active_source_ids["combo_chemical"], current_emissions)

            elif self.sources_active["chemical"] and self.current_time_seconds >= chem_end_time_abs:
                if hasattr(environment_3d_orchestrator, 'remove_source') and self.active_source_ids.get("combo_chemical"):
                    environment_3d_orchestrator.remove_source(self.active_source_ids["combo_chemical"])
                self.sources_active["chemical"] = False
                self.current_chem_intensity_factor = 0.0
                print(f"Scenario {self.scenario_id}: Combo chemical source deactivated at {self.current_time_seconds:.0f}s.")

        if self.is_completed(None):
            self.scenario_active = False
            # Ensure all sources are cleaned up if not already by their individual durations
            if self.sources_active["heat"] and hasattr(environment_3d_orchestrator, 'remove_source') and self.active_source_ids["combo_heat"]:
                 environment_3d_orchestrator.remove_source(self.active_source_ids["combo_heat"])
            if self.sources_active["chemical"] and hasattr(environment_3d_orchestrator, 'remove_source') and self.active_source_ids["combo_chemical"]:
                 environment_3d_orchestrator.remove_source(self.active_source_ids["combo_chemical"])
            print(f"Scenario {self.scenario_id}: Fire Precursor Combo Scenario completed.")


    def is_completed(self, environment_3d_state: Any) -> bool:
        if self.expected_duration_seconds is not None and \
           self.current_time_seconds >= self.expected_duration_seconds:
            return True
        return False

__all__ = [
    "CellulosePyrolysisScenario",
    "LigninDecompositionScenario",
    "EarlyCombustionScenario",
    "FirePrecursorComboScenario"
]