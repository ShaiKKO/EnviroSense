"""
This module will contain implementations for electrical fault simulation scenarios,
all inheriting from BaseScenario. These scenarios are designed to generate
data for testing electrical anomaly detection algorithms and for ML training.
"""

from typing import Dict, Any, Optional, List
import random # For potential randomness in arcing

from pydantic import BaseModel, Field, validator

from .base import BaseScenario, ScenarioComplexity
# from envirosense.simulation_engine.physics_orchestrator import Environment3DOrchestrator # Example import

class CoronaDischargeParams(BaseModel):
    """
    Parameters for configuring a CoronaDischargeScenario.
    """
    location: List[float] = Field(
        default_factory=lambda: [0.0, 0.0, 2.0],
        min_items=3,
        max_items=3,
        description="Location [x, y, z] of the corona discharge."
    )
    emf_strength_v_m: float = Field(
        default=50.0,
        ge=0,
        description="EMF strength in Volts per meter."
    )
    acoustic_level_db: float = Field(
        default=40.0,
        description="Acoustic level in dB."
    )
    ozone_emission_g_s: float = Field(
        default=0.0001,
        ge=0,
        description="Ozone (O3) emission rate in grams per second."
    )
    nox_emission_g_s: float = Field(
        default=0.00005,
        ge=0,
        description="Nitrogen Oxides (NOx) emission rate in grams per second."
    )

    class Config:
        extra = "forbid"


class CoronaDischargeScenario(BaseScenario):
    def __init__(self, scenario_id: str, name: Optional[str] = "Corona Discharge",
                 description: Optional[str] = "Simulates corona discharge on high-voltage components, producing ozone, NOx, specific EMF and acoustic signatures.",
                 expected_duration_seconds: Optional[float] = 1200.0, # 20 minutes
                 difficulty_level: ScenarioComplexity = ScenarioComplexity.MEDIUM,
                 location: List[float] = [0.0, 0.0, 2.0],
                 emf_strength_v_m: float = 50.0,
                 acoustic_level_db: float = 40.0,
                 ozone_emission_g_s: float = 0.0001,
                 nox_emission_g_s: float = 0.00005,
                 **kwargs):
        super().__init__(scenario_id=scenario_id, name=name, description=description,
                         category="electrical_fault",
                         difficulty_level=difficulty_level,
                         expected_duration_seconds=expected_duration_seconds,
                         **kwargs)
        
        param_dict = {
            "location": location,
            "emf_strength_v_m": emf_strength_v_m,
            "acoustic_level_db": acoustic_level_db,
            "ozone_emission_g_s": ozone_emission_g_s,
            "nox_emission_g_s": nox_emission_g_s
        }
        self.params = CoronaDischargeParams(**param_dict)

        self.active_source_ids: Dict[str, Optional[str]] = {
            "emf": f"corona_emf_{self.scenario_id}",
            "acoustic": f"corona_acoustic_{self.scenario_id}",
            "chemical_ozone": f"corona_ozone_{self.scenario_id}",
            "chemical_nox": f"corona_nox_{self.scenario_id}"
        }
        self.corona_active = False

    def _get_specific_params(self) -> Dict[str, Any]:
        """Returns the scenario-specific parameters as a dictionary."""
        return self.params.model_dump(mode='python')

    def setup_environment(self, environment_3d_orchestrator: Any) -> None:
        self.reset()
        self.corona_active = True

        if hasattr(environment_3d_orchestrator, 'add_emf_source'):
            environment_3d_orchestrator.add_emf_source(
                source_id=self.active_source_ids["emf"],
                position=self.params.location,
                strength=self.params.emf_strength_v_m,
                source_type="corona_discharge_emf"
            )
        if hasattr(environment_3d_orchestrator, 'add_acoustic_source'):
            environment_3d_orchestrator.add_acoustic_source(
                source_id=self.active_source_ids["acoustic"],
                position=self.params.location,
                sound_level_db=self.params.acoustic_level_db,
                sound_type="corona_hiss_crackle"
            )
        if hasattr(environment_3d_orchestrator, 'add_chemical_source'):
            environment_3d_orchestrator.add_chemical_source(
                source_id=self.active_source_ids["chemical_ozone"],
                position=self.params.location,
                emission_rates_g_s={"O3": self.params.ozone_emission_g_s},
                source_type="corona_ozone_production"
            )
            environment_3d_orchestrator.add_chemical_source(
                source_id=self.active_source_ids["chemical_nox"],
                position=self.params.location,
                emission_rates_g_s={"NOx": self.params.nox_emission_g_s}, # Assuming NOx is a single species for simplicity here
                source_type="corona_nox_production"
            )
        print(f"Scenario {self.scenario_id}: Corona discharge sources activated at {self.params.location}.")

    def get_ground_truth_labels(self, environment_3d_state: Any) -> Dict[str, Any]:
        severity = "low" # Default severity
        # Example: Severity could be tied to EMF strength if it were variable, or duration
        if self.params.emf_strength_v_m > 100: # Arbitrary example
             severity = "medium"
        if self.current_time_seconds > (self.expected_duration_seconds or 0) * 0.75 : # If late in scenario
            severity = "high" if severity == "medium" else "medium"


        return {
            "event_type": "corona_discharge",
            "is_anomaly": self.corona_active,
            "fault_severity": severity,
            "location": self.params.location,
            "active_source_ids": self.active_source_ids if self.corona_active else {}
        }

    def update(self, time_step_seconds: float, environment_3d_orchestrator: Any) -> None:
        super().update(time_step_seconds, environment_3d_orchestrator)
        
        if not self.corona_active:
            return

        # Placeholder: Intensity of corona might vary with humidity, contamination, or voltage fluctuations
        # For now, assume constant emission/strength once started.
        # Example: if self.current_time_seconds > X and hasattr(orchestrator, 'update_source_intensity'):
        #    orchestrator.update_source_intensity(self.active_source_ids["emf"], new_strength)

        if self.is_completed(None):
            self.corona_active = False
            if hasattr(environment_3d_orchestrator, 'remove_source'):
                for source_id_key in self.active_source_ids:
                    source_id_val = self.active_source_ids[source_id_key]
                    if source_id_val:
                        environment_3d_orchestrator.remove_source(source_id_val)
            print(f"Scenario {self.scenario_id}: Corona discharge completed and sources deactivated.")

    def is_completed(self, environment_3d_state: Any) -> bool:
        if self.expected_duration_seconds is not None and \
           self.current_time_seconds >= self.expected_duration_seconds:
            return True
        return False

class ArcingEventParams(BaseModel):
    """
    Parameters for configuring an ArcingEventScenario.
    """
    location: List[float] = Field(
        default_factory=lambda: [0.0, 0.0, 1.0],
        min_items=3,
        max_items=3,
        description="Location [x, y, z] of the arcing event."
    )
    base_intensity_emf_v_m: float = Field(
        default=1000.0,
        ge=0,
        description="Base intensity of the EMF signal in Volts per meter."
    )
    emf_frequency_hz: float = Field(
        default=60.0,
        gt=0,
        description="Frequency of the EMF signal in Hertz."
    )
    base_intensity_acoustic_db: float = Field(
        default=90.0,
        description="Base intensity of the acoustic signal in dB."
    )
    base_intensity_thermal_w: float = Field(
        default=5000.0,
        ge=0,
        description="Base thermal intensity (heat output) in Watts."
    )
    fluctuation_min_factor: float = Field(
        default=0.8,
        ge=0,
        description="Minimum factor for random intensity fluctuation (e.g., 0.8 for 80% of base)."
    )
    fluctuation_max_factor: float = Field(
        default=1.2,
        ge=0,
        description="Maximum factor for random intensity fluctuation (e.g., 1.2 for 120% of base)."
    )

    @validator('fluctuation_max_factor')
    def check_max_fluctuation_greater_than_min(cls, v, values):
        if 'fluctuation_min_factor' in values and v < values['fluctuation_min_factor']:
            raise ValueError("fluctuation_max_factor must be greater than or equal to fluctuation_min_factor")
        return v

    class Config:
        extra = "forbid"


class ArcingEventScenario(BaseScenario):
    def __init__(self, scenario_id: str, name: Optional[str] = "Arcing Event",
                 description: Optional[str] = "Simulates an electrical arcing event, characterized by strong EMF, acoustic, thermal, and light signatures.",
                 expected_duration_seconds: Optional[float] = 60.0, # Arcing might be shorter, more intense
                 difficulty_level: ScenarioComplexity = ScenarioComplexity.VERY_HIGH,
                 location: List[float] = [0.0, 0.0, 1.0], # Matched default_factory
                 base_intensity_emf_v_m: float = 1000.0,
                 emf_frequency_hz: float = 60.0,
                 base_intensity_acoustic_db: float = 90.0,
                 base_intensity_thermal_w: float = 5000.0,
                 fluctuation_min_factor: float = 0.8,
                 fluctuation_max_factor: float = 1.2,
                 **kwargs):
        super().__init__(scenario_id=scenario_id, name=name, description=description,
                         category="electrical_fault_critical",
                         difficulty_level=difficulty_level,
                         expected_duration_seconds=expected_duration_seconds,
                         **kwargs)
        
        param_dict = {
            "location": location,
            "base_intensity_emf_v_m": base_intensity_emf_v_m,
            "emf_frequency_hz": emf_frequency_hz,
            "base_intensity_acoustic_db": base_intensity_acoustic_db,
            "base_intensity_thermal_w": base_intensity_thermal_w,
            "fluctuation_min_factor": fluctuation_min_factor,
            "fluctuation_max_factor": fluctuation_max_factor
        }
        self.params = ArcingEventParams(**param_dict)
        
        # Keep arc_location for direct access if preferred, but it's sourced from params
        self.arc_location = self.params.location

        self.active_source_ids: Dict[str, Optional[str]] = {
            "emf": f"arc_emf_{self.scenario_id}",
            "acoustic": f"arc_acoustic_{self.scenario_id}",
            "thermal": f"arc_thermal_{self.scenario_id}"
        }
        self.arc_active = False

    def _get_specific_params(self) -> Dict[str, Any]:
        """Returns the scenario-specific parameters as a dictionary."""
        return self.params.model_dump(mode='python')

    def setup_environment(self, environment_3d_orchestrator: Any) -> None:
        self.reset()
        self.arc_active = True # Arc starts immediately in this simple model

        if hasattr(environment_3d_orchestrator, 'add_emf_source'):
            environment_3d_orchestrator.add_emf_source(
                source_id=self.active_source_ids["emf"],
                position=self.params.location,
                strength=self.params.base_intensity_emf_v_m,
                frequency_hz=self.params.emf_frequency_hz,
                source_type="arcing_event"
            )
        if hasattr(environment_3d_orchestrator, 'add_acoustic_source'):
            environment_3d_orchestrator.add_acoustic_source(
                source_id=self.active_source_ids["acoustic"],
                position=self.params.location,
                sound_level_db=self.params.base_intensity_acoustic_db,
                sound_type="arcing_crackle_buzz"
            )
        if hasattr(environment_3d_orchestrator, 'add_thermal_source'):
            environment_3d_orchestrator.add_thermal_source(
                source_id=self.active_source_ids["thermal"],
                position=self.params.location,
                heat_output_watts=self.params.base_intensity_thermal_w,
                source_type="arcing_heat"
            )
        print(f"Scenario {self.scenario_id}: Arcing event sources activated at {self.params.location}.")

    def get_ground_truth_labels(self, environment_3d_state: Any) -> Dict[str, Any]:
        severity = "high" if self.arc_active else "none"
        return {
            "event_type": "arcing_event",
            "is_anomaly": self.arc_active,
            "fault_severity": severity,
            "arc_location": self.params.location, # Use params directly
            "active_source_ids": self.active_source_ids if self.arc_active else {}
        }

    def update(self, time_step_seconds: float, environment_3d_orchestrator: Any) -> None:
        super().update(time_step_seconds, environment_3d_orchestrator)
        
        if not self.arc_active:
            return

        if hasattr(environment_3d_orchestrator, 'update_source_intensity'):
            fluctuation = random.uniform(self.params.fluctuation_min_factor, self.params.fluctuation_max_factor)
            if self.active_source_ids.get("emf"): # Check if source_id exists
                environment_3d_orchestrator.update_source_intensity(
                    self.active_source_ids["emf"],
                    self.params.base_intensity_emf_v_m * fluctuation
                )
            # Similar checks and updates for acoustic and thermal if their intensity can be updated
            # For example, for thermal:
            if self.active_source_ids.get("thermal"):
                 environment_3d_orchestrator.update_source_intensity(
                    self.active_source_ids["thermal"],
                    self.params.base_intensity_thermal_w * fluctuation # Assuming thermal source intensity can be updated
                )


        if self.is_completed(None):
            self.arc_active = False
            # Clean up sources
            if hasattr(environment_3d_orchestrator, 'remove_source'):
                for source_type, source_id in self.active_source_ids.items():
                    if source_id:
                        environment_3d_orchestrator.remove_source(source_id)
            print(f"Scenario {self.scenario_id}: Arcing event completed and sources deactivated.")


    def is_completed(self, environment_3d_state: Any) -> bool:
        if self.expected_duration_seconds is not None and \
           self.current_time_seconds >= self.expected_duration_seconds:
            return True
        return False

class StageSignatureParams(BaseModel):
    """
    Defines the physical signatures for a single stage of insulation breakdown.
    All parameters are optional, allowing stages to only define relevant signatures.
    """
    emf_v_m: Optional[float] = Field(default=None, ge=0, description="EMF strength in V/m for this stage.")
    acoustic_db: Optional[float] = Field(default=None, description="Acoustic level in dB for this stage.")
    thermal_w: Optional[float] = Field(default=None, ge=0, description="Thermal heat output in Watts for this stage.")
    voc_g_s: Optional[Dict[str, float]] = Field(
        default=None,
        description="VOC emission rates in grams per second (e.g., {'voc_a': 0.001}) for this stage."
    )

    class Config:
        extra = "forbid"

class InsulationBreakdownParams(BaseModel):
    """
    Parameters for configuring an InsulationBreakdownScenario.
    """
    location: List[float] = Field(
        default_factory=lambda: [0.0, 1.0, 0.0],
        min_items=3,
        max_items=3,
        description="Location [x, y, z] of the insulation breakdown event."
    )
    stage_durations_s: List[float] = Field(
        default_factory=lambda: [3600.0, 3000.0, 600.0],
        min_length=1,
        description="List of durations in seconds for each stage of the breakdown."
    )
    stage_signatures: List[StageSignatureParams] = Field(
        default_factory=lambda: [
            StageSignatureParams(emf_v_m=10, voc_g_s={"insulation_voc_a": 0.00001}),
            StageSignatureParams(emf_v_m=100, acoustic_db=35, voc_g_s={"insulation_voc_a": 0.00005, "insulation_voc_b": 0.00002}),
            StageSignatureParams(emf_v_m=800, acoustic_db=75, thermal_w=2000, voc_g_s={"insulation_voc_b": 0.0001, "combustion_voc": 0.00003})
        ],
        description="List of signature parameters for each corresponding stage."
    )

    @validator('stage_durations_s')
    def check_stage_durations_positive(cls, v):
        if not all(duration > 0 for duration in v):
            raise ValueError("All stage durations must be positive.")
        return v

    @validator('stage_signatures')
    def check_signatures_match_durations_length(cls, v, values):
        if 'stage_durations_s' in values and len(v) != len(values['stage_durations_s']):
            raise ValueError("The number of stage_signatures must match the number of stage_durations_s.")
        return v
    
    class Config:
        extra = "forbid"


class InsulationBreakdownScenario(BaseScenario):
    def __init__(self, scenario_id: str, name: Optional[str] = "Insulation Breakdown",
                 description: Optional[str] = "Simulates progressive breakdown of electrical insulation, leading to partial discharges, increased EMF, and eventual arcing.",
                 expected_duration_seconds: Optional[float] = None, # Calculated from stages if not provided
                 difficulty_level: ScenarioComplexity = ScenarioComplexity.HIGH,
                 location: List[float] = [0.0, 1.0, 0.0],
                 stage_durations_s: List[float] = [3600.0, 3000.0, 600.0],
                 stage_signatures: Optional[List[Dict[str, Any]]] = None, # Allow dicts for easier JSON init
                 **kwargs):
        
        # Default expected_duration_seconds if not provided
        calculated_expected_duration = sum(stage_durations_s) if stage_durations_s else 0
        if expected_duration_seconds is None:
            expected_duration_seconds = calculated_expected_duration
        elif expected_duration_seconds < calculated_expected_duration:
            # Or raise warning/error if explicit duration is less than sum of stages
            print(f"Warning: Explicit expected_duration_seconds ({expected_duration_seconds}) is less than sum of stage_durations_s ({calculated_expected_duration}). Using sum of stages.")
            expected_duration_seconds = calculated_expected_duration


        super().__init__(scenario_id=scenario_id, name=name, description=description,
                         category="electrical_fault_progressive",
                         difficulty_level=difficulty_level,
                         expected_duration_seconds=expected_duration_seconds,
                         **kwargs)
        
        # Handle stage_signatures: convert list of dicts to list of StageSignatureParams if needed
        parsed_stage_signatures: List[StageSignatureParams]
        if stage_signatures is None: # Use default from Pydantic model
            # This will trigger the default_factory in InsulationBreakdownParams
            # To do this cleanly, we might need to pass a sentinel or handle it inside Pydantic
            # For now, let's assume if None, the Pydantic default_factory is used.
            # Or, explicitly create the default here if stage_signatures is None
             parsed_stage_signatures = [
                StageSignatureParams(emf_v_m=10, voc_g_s={"insulation_voc_a": 0.00001}),
                StageSignatureParams(emf_v_m=100, acoustic_db=35, voc_g_s={"insulation_voc_a": 0.00005, "insulation_voc_b": 0.00002}),
                StageSignatureParams(emf_v_m=800, acoustic_db=75, thermal_w=2000, voc_g_s={"insulation_voc_b": 0.0001, "combustion_voc": 0.00003})
            ]
        else:
            parsed_stage_signatures = [StageSignatureParams(**sig) for sig in stage_signatures]


        param_dict = {
            "location": location,
            "stage_durations_s": stage_durations_s,
            "stage_signatures": parsed_stage_signatures
        }
        self.params = InsulationBreakdownParams(**param_dict)
        
        self.stage_thresholds_s: List[float] = []
        current_threshold = 0.0
        for duration in self.params.stage_durations_s:
            current_threshold += duration
            self.stage_thresholds_s.append(current_threshold)
        
        self.current_stage: int = 0
        self._active_stage_source_map: Dict[int, Dict[str, str]] = {}
        self.breakdown_active = False

    def _get_specific_params(self) -> Dict[str, Any]:
        """Returns the scenario-specific parameters as a dictionary."""
        # Pydantic's model_dump will handle nested models correctly.
        return self.params.model_dump(mode='python')

    def _get_source_id(self, source_type: str, stage: int) -> str:
        """Generates a unique source ID for a given type and stage."""
        return f"ins_brk_{source_type}_s{stage}_{self.scenario_id}"

    def _deactivate_stage_sources(self, stage: int, orchestrator: Any):
        """Deactivates all sources associated with a given stage."""
        if stage in self._active_stage_source_map and hasattr(orchestrator, 'remove_source'):
            for source_id in self._active_stage_source_map[stage].values(): # Iterate over source_ids directly
                orchestrator.remove_source(source_id)
                print(f"Scenario {self.scenario_id}: Deactivated source {source_id} from stage {stage}.")
            del self._active_stage_source_map[stage]

    def _activate_stage_sources(self, stage: int, orchestrator: Any):
        """Activates sources for the given stage."""
        if stage >= len(self.params.stage_signatures):
            print(f"Warning: Stage {stage} requested but only {len(self.params.stage_signatures)} signatures defined.")
            return

        sig = self.params.stage_signatures[stage] # Now a StageSignatureParams object
        current_stage_active_ids: Dict[str, str] = {}

        if sig.emf_v_m is not None and hasattr(orchestrator, 'add_emf_source'):
            sid = self._get_source_id("emf", stage)
            orchestrator.add_emf_source(source_id=sid, position=self.params.location, strength=sig.emf_v_m, source_type=f"insulation_s{stage}_emf")
            current_stage_active_ids["emf"] = sid
        
        if sig.acoustic_db is not None and hasattr(orchestrator, 'add_acoustic_source'):
            sid = self._get_source_id("acoustic", stage)
            orchestrator.add_acoustic_source(source_id=sid, position=self.params.location, sound_level_db=sig.acoustic_db, sound_type=f"insulation_s{stage}_acoustic")
            current_stage_active_ids["acoustic"] = sid

        if sig.thermal_w is not None and hasattr(orchestrator, 'add_thermal_source'):
            sid = self._get_source_id("thermal", stage)
            orchestrator.add_thermal_source(source_id=sid, position=self.params.location, heat_output_watts=sig.thermal_w, source_type=f"insulation_s{stage}_thermal")
            current_stage_active_ids["thermal"] = sid
            
        if sig.voc_g_s is not None and hasattr(orchestrator, 'add_chemical_source'):
            sid = self._get_source_id("chemical", stage)
            orchestrator.add_chemical_source(source_id=sid, position=self.params.location, emission_rates_g_s=sig.voc_g_s, source_type=f"insulation_s{stage}_voc")
            current_stage_active_ids["chemical"] = sid
        
        if current_stage_active_ids: # Only add to map if there are active sources for this stage
            self._active_stage_source_map[stage] = current_stage_active_ids
        print(f"Scenario {self.scenario_id}: Insulation breakdown activated sources for stage {stage}: {current_stage_active_ids}.")


    def setup_environment(self, environment_3d_orchestrator: Any) -> None:
        self.reset()
        self.current_stage = 0
        self.breakdown_active = True
        self._active_stage_source_map.clear() # Clear any previous run's map
        if self.params.stage_signatures: # Ensure there are stages to activate
            self._activate_stage_sources(self.current_stage, environment_3d_orchestrator)

    def get_ground_truth_labels(self, environment_3d_state: Any) -> Dict[str, Any]:
        severity_map = {0: "low", 1: "medium", 2: "high"} # Adjust if more stages
        # Extend severity map if more stages are defined than this map covers
        for i in range(len(self.params.stage_durations_s)):
            if i not in severity_map:
                severity_map[i] = "very_high" if i > 2 else "custom_stage"


        current_severity = severity_map.get(self.current_stage, "unknown")
        stage_descriptions = ["initial_degradation", "partial_discharges", "arcing_imminent", "full_failure_stage4", "full_failure_stage5"] # Extend as needed
        stage_desc = stage_descriptions[self.current_stage] if self.current_stage < len(stage_descriptions) else f"stage_{self.current_stage}"


        return {
            "event_type": "insulation_breakdown",
            "is_anomaly": self.breakdown_active,
            "fault_severity": current_severity,
            "breakdown_stage": self.current_stage,
            "stage_description": stage_desc,
            "location": self.params.location,
            "active_source_ids_current_stage": list(self._active_stage_source_map.get(self.current_stage, {}).values()) if self.breakdown_active else []
        }

    def update(self, time_step_seconds: float, environment_3d_orchestrator: Any) -> None:
        super().update(time_step_seconds, environment_3d_orchestrator)

        if not self.breakdown_active:
            return

        new_stage_candidate = 0
        # Determine current stage based on time and stage thresholds
        for i, threshold_s in enumerate(self.stage_thresholds_s):
            if self.current_time_seconds < threshold_s:
                new_stage_candidate = i
                break
            # If current_time_seconds is >= last threshold, it means we are in the last stage
            # or beyond its defined duration start
            if i == len(self.stage_thresholds_s) - 1 and self.current_time_seconds >= threshold_s:
                 new_stage_candidate = len(self.params.stage_durations_s) -1 # Stay in the last defined stage
        
        # Ensure candidate is within bounds of defined signatures
        if new_stage_candidate >= len(self.params.stage_signatures):
            # This case should ideally not be hit if validator for lengths works,
            # but as a safeguard, cap it to the last available signature index.
            new_stage_candidate = len(self.params.stage_signatures) - 1


        if new_stage_candidate != self.current_stage:
            print(f"Scenario {self.scenario_id}: Time {self.current_time_seconds:.0f}s. Transitioning from stage {self.current_stage} to {new_stage_candidate}.")
            self._deactivate_stage_sources(self.current_stage, environment_3d_orchestrator)
            
            self.current_stage = new_stage_candidate
            if self.current_stage < len(self.params.stage_signatures): # Ensure we don't try to activate a non-existent stage
                self._activate_stage_sources(self.current_stage, environment_3d_orchestrator)
            else:
                print(f"Warning: Reached stage {self.current_stage} but no signatures defined. Scenario might effectively end.")


        if self.is_completed(None):
            self.breakdown_active = False
            # Deactivate sources of the final active stage
            self._deactivate_stage_sources(self.current_stage, environment_3d_orchestrator)
            print(f"Scenario {self.scenario_id}: Insulation breakdown scenario marked completed. Final sources for stage {self.current_stage} deactivated.")


    def is_completed(self, environment_3d_state: Any) -> bool:
        if self.expected_duration_seconds is not None and \
           self.current_time_seconds >= self.expected_duration_seconds:
            return True
        return False

class EquipmentOverheatParams(BaseModel):
    """
    Parameters for configuring an EquipmentOverheatScenario.
    """
    location: List[float] = Field(
        default_factory=lambda: [1.0, 1.0, 1.0],
        min_items=3,
        max_items=3,
        description="Location [x, y, z] of the overheating equipment."
    )
    start_heat_w: float = Field(
        default=100.0,
        ge=0,
        description="Initial heat output in Watts at the start of the scenario."
    )
    max_heat_w: float = Field(
        default=1000.0,
        ge=0,
        description="Maximum heat output in Watts, typically reached towards the end of the scenario duration."
    )
    offgas_profile_g_s: Optional[Dict[str, float]] = Field(
        default=None,
        description="Optional chemical off-gassing profile as a dictionary of {chemical_species: rate_g_s}."
    )
    offgas_start_time_s: Optional[float] = Field(
        default=None,
        ge=0,
        description="Time in seconds into the scenario when off-gassing begins, if a profile is provided. If None, defaults relative to expected_duration_seconds."
    )

    @validator('max_heat_w')
    def check_max_heat_w_greater_than_start(cls, v, values):
        if 'start_heat_w' in values and v < values['start_heat_w']:
            raise ValueError("max_heat_w must be greater than or equal to start_heat_w")
        return v

    class Config:
        extra = "forbid"


class EquipmentOverheatScenario(BaseScenario):
    def __init__(self, scenario_id: str, name: Optional[str] = "Equipment Overheat",
                 description: Optional[str] = "Simulates overheating of an electrical component, leading to increased thermal signature and potentially off-gassing.",
                 expected_duration_seconds: Optional[float] = 3600.0, # 1 hour
                 difficulty_level: ScenarioComplexity = ScenarioComplexity.MEDIUM,
                 location: List[float] = [1.0, 1.0, 1.0],
                 start_heat_w: float = 100.0,
                 max_heat_w: float = 1000.0,
                 offgas_profile_g_s: Optional[Dict[str, float]] = None,
                 offgas_start_time_s: Optional[float] = None,
                 **kwargs):
        super().__init__(scenario_id=scenario_id, name=name, description=description,
                         category="electrical_thermal_fault",
                         difficulty_level=difficulty_level,
                         expected_duration_seconds=expected_duration_seconds,
                         **kwargs)
        
        param_dict = {
            "location": location,
            "start_heat_w": start_heat_w,
            "max_heat_w": max_heat_w,
            "offgas_profile_g_s": offgas_profile_g_s,
            "offgas_start_time_s": offgas_start_time_s
        }
        self.params = EquipmentOverheatParams(**param_dict)

        # Handle default for offgas_start_time_s if it was None and depends on expected_duration_seconds
        if self.params.offgas_start_time_s is None and self.params.offgas_profile_g_s:
            self.params.offgas_start_time_s = (self.expected_duration_seconds / 3.0) if self.expected_duration_seconds and self.expected_duration_seconds > 0 else 600.0
        elif self.params.offgas_profile_g_s is None: # Ensure no start time if no profile
             self.params.offgas_start_time_s = None
        
        self.active_source_ids: Dict[str, Optional[str]] = {
            "thermal": f"overheat_thermal_{self.scenario_id}",
            "chemical": f"overheat_chem_{self.scenario_id}" if self.params.offgas_profile_g_s else None
        }
        self.overheating_active = False
        self.current_heat_w = 0.0 # Will be set in setup_environment
        self.offgassing_active = False

    def _get_specific_params(self) -> Dict[str, Any]:
        """Returns the scenario-specific parameters as a dictionary."""
        return self.params.model_dump(mode='python')

    def setup_environment(self, environment_3d_orchestrator: Any) -> None:
        self.reset()
        self.overheating_active = True
        self.offgassing_active = False # Reset offgassing state
        self.current_heat_w = self.params.start_heat_w

        thermal_source_id = self.active_source_ids.get("thermal")
        if hasattr(environment_3d_orchestrator, 'add_thermal_source') and thermal_source_id:
            environment_3d_orchestrator.add_thermal_source( # Consistent with ArcingEvent
                source_id=thermal_source_id,
                position=self.params.location,
                heat_output_watts=self.current_heat_w,
                source_type="equipment_overheat"
            )
        print(f"Scenario {self.scenario_id}: Equipment overheat thermal source activated at {self.params.location} with {self.current_heat_w}W.")

    def get_ground_truth_labels(self, environment_3d_state: Any) -> Dict[str, Any]:
        severity = "low"
        if self.current_heat_w > (self.params.start_heat_w + self.params.max_heat_w) * 0.33: severity = "medium"
        if self.current_heat_w > (self.params.start_heat_w + self.params.max_heat_w) * 0.66: severity = "high"
        
        active_ids_for_label = {}
        if self.overheating_active and self.active_source_ids.get("thermal"):
            active_ids_for_label["thermal"] = self.active_source_ids["thermal"]
        if self.offgassing_active and self.active_source_ids.get("chemical"):
            active_ids_for_label["chemical"] = self.active_source_ids["chemical"]

        return {
            "event_type": "equipment_overheat",
            "is_anomaly": self.overheating_active,
            "fault_severity": severity,
            "current_heat_output_watts": round(self.current_heat_w, 1),
            "offgassing_active": self.offgassing_active,
            "location": self.params.location,
            "active_source_ids": active_ids_for_label
        }

    def update(self, time_step_seconds: float, environment_3d_orchestrator: Any) -> None:
        super().update(time_step_seconds, environment_3d_orchestrator)

        if not self.overheating_active:
            return

        # Progress heat
        if self.current_heat_w < self.params.max_heat_w and self.expected_duration_seconds and self.expected_duration_seconds > 0:
            progression_factor = self.current_time_seconds / self.expected_duration_seconds
            self.current_heat_w = self.params.start_heat_w + (self.params.max_heat_w - self.params.start_heat_w) * min(progression_factor, 1.0)
            
            thermal_source_id = self.active_source_ids.get("thermal")
            if hasattr(environment_3d_orchestrator, 'update_source_intensity') and thermal_source_id:
                environment_3d_orchestrator.update_source_intensity(thermal_source_id, self.current_heat_w)
        
        # Check for off-gassing start
        chemical_source_id = self.active_source_ids.get("chemical")
        if not self.offgassing_active and self.params.offgas_profile_g_s and chemical_source_id and \
           self.params.offgas_start_time_s is not None and self.current_time_seconds >= self.params.offgas_start_time_s:
            self.offgassing_active = True
            if hasattr(environment_3d_orchestrator, 'add_chemical_source'):
                environment_3d_orchestrator.add_chemical_source(
                    source_id=chemical_source_id,
                    position=self.params.location,
                    emission_rates_g_s=self.params.offgas_profile_g_s,
                    source_type="overheat_offgassing"
                )
                print(f"Scenario {self.scenario_id}: Off-gassing started.")

        if self.is_completed(None):
            self.overheating_active = False
            self.offgassing_active = False # Ensure this is reset
            if hasattr(environment_3d_orchestrator, 'remove_source'):
                thermal_source_id_to_remove = self.active_source_ids.get("thermal")
                if thermal_source_id_to_remove:
                    # Simple removal, assuming orchestrator handles existence check or it's safe
                    environment_3d_orchestrator.remove_source(thermal_source_id_to_remove)

                chemical_source_id_to_remove = self.active_source_ids.get("chemical")
                if chemical_source_id_to_remove:
                    environment_3d_orchestrator.remove_source(chemical_source_id_to_remove)
            print(f"Scenario {self.scenario_id}: Equipment overheat completed and sources deactivated.")

    def is_completed(self, environment_3d_state: Any) -> bool:
        if self.expected_duration_seconds is not None and \
           self.current_time_seconds >= self.expected_duration_seconds:
            return True
        return False

__all__ = [
    "CoronaDischargeScenario",
    "ArcingEventScenario",
    "InsulationBreakdownScenario",
    "EquipmentOverheatScenario"
]