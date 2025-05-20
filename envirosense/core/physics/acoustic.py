"""
EnviroSense Physics Engine - Acoustic Signature Modeling

This module provides classes and functions for modeling acoustic signatures
produced by utility infrastructure components such as transformers, switches,
and other electrical equipment. It implements frequency spectrum generation,
sound propagation, and analysis tools for acoustic signature detection.

Classes:
    AcousticSource: Base class for acoustic sources
    AcousticProfile: Represents sound propagation in space
    TransformerSound: Models acoustic signature of transformers
    SwitchSound: Models acoustic signature of switches and circuit breakers
    DischargeSound: Models sound of electrical discharges (corona, arcing)
    AcousticVisualizer: Provides visualization tools for acoustic signatures
"""

import numpy as np
from scipy import signal
import matplotlib.pyplot as plt
from matplotlib import cm
import time
from typing import Tuple, List, Dict, Optional, Union, Any
from abc import ABC, abstractmethod

from envirosense.core.physics.coordinates import Vector3D

# Constants
SPEED_OF_SOUND = 343.0  # Speed of sound in air at 20°C (m/s)


class AcousticSource(ABC):
    """
    Abstract base class for all acoustic sources.
    
    Attributes:
        name (str): Unique identifier for the source
        position (Vector3D): 3D position of the source
        enabled (bool): Whether the source is currently active
        sound_power (float): Sound power in watts
        sample_rate (int): Sample rate for audio generation in Hz
    """
    
    def __init__(self, name: str,
                position: Tuple[float, float, float],
                sound_power: float,
                sample_rate: int = 44100):
        """
        Initialize an acoustic source.
        
        Args:
            name: Unique identifier for the source
            position: 3D coordinates (x, y, z) of the source in meters
            sound_power: Sound power in watts
            sample_rate: Sample rate for audio generation in Hz (default: 44100)
        """
        self.name = name
        self.position = Vector3D(*position)
        self.enabled = True
        self.sound_power = max(0.0, sound_power)
        self.sample_rate = sample_rate
    
    @abstractmethod
    def generate_spectrum(self, freq_range: Tuple[float, float, int]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate the frequency spectrum for this acoustic source.
        
        Args:
            freq_range: Tuple of (min_freq, max_freq, num_points) in Hz
            
        Returns:
            Tuple of (frequencies, amplitudes)
        """
        pass
    
    @abstractmethod
    def generate_time_signal(self, duration: float) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate a time-domain signal of the acoustic source.
        
        Args:
            duration: Signal duration in seconds
            
        Returns:
            Tuple of (time_points, amplitude_values)
        """
        pass
    
    def calculate_spl_at(self, position: Tuple[float, float, float]) -> float:
        """
        Calculate sound pressure level (SPL) at a specified position.
        
        Args:
            position: 3D coordinates (x, y, z) to calculate SPL at
            
        Returns:
            Sound pressure level in dB
        """
        if not self.enabled or self.sound_power <= 0:
            return 0.0
        
        # Calculate distance from source to position
        pos = Vector3D(*position)
        distance = (pos - self.position).magnitude()
        
        # Avoid division by zero
        if distance < 0.1:
            distance = 0.1
            
        # Calculate sound pressure level using the inverse square law
        # SPL = SWL - 20*log10(r) - 11
        # where SWL is sound power level, r is distance
        
        # Convert power to sound power level
        reference_power = 1e-12  # Reference sound power (1 pW)
        swl = 10 * np.log10(self.sound_power / reference_power)
        
        # Calculate SPL at the given position
        spl = swl - 20 * np.log10(distance) - 11
        
        return max(0, spl)  # Ensure non-negative SPL
    
    @property
    @abstractmethod
    def source_type(self) -> str:
        """Return the type of acoustic source."""
        pass
    
    def enable(self):
        """Enable this acoustic source."""
        self.enabled = True
        
    def disable(self):
        """Disable this acoustic source."""
        self.enabled = False


class TransformerSound(AcousticSource):
    """
    Models acoustic signature of transformers.
    
    Attributes:
        name (str): Unique identifier for the source
        position (Vector3D): 3D position of the transformer
        power_rating (float): Power rating in VA
        fundamental_freq (float): Fundamental frequency in Hz (typically 100 or 120 Hz)
        load_factor (float): Current load factor (0-1)
        condition (str): Condition of the transformer (NORMAL, OVERLOADED, etc.)
    """
    
    # Condition constants
    CONDITION_NORMAL = "normal"
    CONDITION_OVERLOADED = "overloaded"
    CONDITION_COOLING_ISSUE = "cooling_issue"
    CONDITION_LOOSE_WINDING = "loose_winding"
    CONDITION_AGING = "aging"
    
    def __init__(self, name: str,
                position: Tuple[float, float, float],
                power_rating: float,
                fundamental_freq: float = 120.0,  # 60Hz power -> 120Hz hum
                load_factor: float = 0.7,
                condition: str = CONDITION_NORMAL):
        """
        Initialize a transformer sound source.
        
        Args:
            name: Unique identifier for the source
            position: 3D coordinates (x, y, z) of the transformer in meters
            power_rating: Power rating in VA
            fundamental_freq: Fundamental frequency in Hz (default: 120.0)
            load_factor: Current load factor 0-1 (default: 0.7)
            condition: Transformer condition (default: CONDITION_NORMAL)
        """
        # Calculate sound power based on power rating and empirical formula
        # Typical transformer sound levels depend on size and design
        # NEMA std: sound level (dB) = 55 + 11.7*log10(MVA) for large transformers
        
        # Convert to MVA
        mva = power_rating / 1e6
        if mva < 0.001:  # Small transformer
            sound_level_db = 25 + 15 * np.log10(1000 * mva)
        else:  # Large transformer
            sound_level_db = 55 + 11.7 * np.log10(mva)
        
        # Convert to sound power (watts)
        reference_power = 1e-12  # 1 pW
        sound_power = reference_power * (10 ** (sound_level_db / 10))
        
        super().__init__(name, position, sound_power, 44100)
        
        self.power_rating = power_rating
        self.fundamental_freq = fundamental_freq
        self.load_factor = min(1.0, max(0.0, load_factor))  # Clamp to valid range
        
        if condition not in [self.CONDITION_NORMAL, self.CONDITION_OVERLOADED,
                          self.CONDITION_COOLING_ISSUE, self.CONDITION_LOOSE_WINDING,
                          self.CONDITION_AGING]:
            condition = self.CONDITION_NORMAL
        self.condition = condition
        
        # Pre-compute the harmonic profile based on condition
        self._harmonic_profile = self._create_harmonic_profile()
    
    @property
    def source_type(self) -> str:
        return "transformer_sound"
    
    def set_load_factor(self, load_factor: float):
        """
        Update the transformer's load factor.
        
        Args:
            load_factor: New load factor (0-1)
        """
        self.load_factor = min(1.0, max(0.0, load_factor))
        
        # Adjust sound power based on load factor
        # Sound level increases with load, approximately logarithmically
        if self.load_factor > 0.01:
            # Base level at 70% load (reference level)
            adjustment = 10 * np.log10(self.load_factor / 0.7)
            
            # Update sound power
            reference_power = 1e-12  # 1 pW
            mva = self.power_rating / 1e6
            if mva < 0.001:  # Small transformer
                base_sound_level_db = 25 + 15 * np.log10(1000 * mva)
            else:  # Large transformer
                base_sound_level_db = 55 + 11.7 * np.log10(mva)
            
            adjusted_level = base_sound_level_db + adjustment
            self.sound_power = reference_power * (10 ** (adjusted_level / 10))
    
    def set_condition(self, condition: str):
        """
        Update the transformer's condition.
        
        Args:
            condition: New condition
        """
        if condition not in [self.CONDITION_NORMAL, self.CONDITION_OVERLOADED,
                          self.CONDITION_COOLING_ISSUE, self.CONDITION_LOOSE_WINDING,
                          self.CONDITION_AGING]:
            return
            
        self.condition = condition
        
        # Update harmonic profile based on new condition
        self._harmonic_profile = self._create_harmonic_profile()
    
    def _create_harmonic_profile(self) -> Dict[int, float]:
        """
        Create a harmonic profile based on transformer condition.
        
        Returns:
            Dictionary mapping harmonic number to relative amplitude
        """
        # Initialize with default harmonics
        # Transformer hum is typically dominated by even harmonics of line frequency
        # (especially 2nd harmonic)
        harmonics = {
            1: 1.0,    # Fundamental (typically 120 Hz)
            2: 0.6,    # 240 Hz
            3: 0.1,    # 360 Hz
            4: 0.3,    # 480 Hz
            5: 0.05,   # 600 Hz
            6: 0.15,   # 720 Hz
            8: 0.08,   # 960 Hz
            10: 0.04   # 1200 Hz
        }
        
        # Modify harmonic profile based on condition
        if self.condition == self.CONDITION_OVERLOADED:
            # Overloaded transformers have stronger higher harmonics
            harmonics[2] *= 1.4
            harmonics[4] *= 1.8
            harmonics[6] *= 2.0
            harmonics[8] *= 2.5
            harmonics[10] *= 3.0
            harmonics[12] = 0.1  # Add harmonic
            harmonics[14] = 0.07  # Add harmonic
            
        elif self.condition == self.CONDITION_COOLING_ISSUE:
            # Cooling issues cause increased overall noise with fan noise components
            harmonics[1] *= 1.5
            harmonics[2] *= 1.3
            # Add fan blade passing harmonics (assuming 7-blade fan at 1800 RPM)
            # 1800/60 * 7 = 210 Hz
            harmonics[1.75] = 0.4  # ~210 Hz (fan fundamental)
            harmonics[3.5] = 0.25  # ~420 Hz (fan harmonic)
            harmonics[5.25] = 0.15  # ~630 Hz (fan harmonic)
            
        elif self.condition == self.CONDITION_LOOSE_WINDING:
            # Loose windings create characteristic vibrations
            harmonics[1] *= 1.2
            harmonics[2] *= 1.5
            # Add sidebands around main harmonics
            harmonics[1.9] = 0.3
            harmonics[2.1] = 0.3
            harmonics[3.9] = 0.2
            harmonics[4.1] = 0.2
            # Add mid-frequency resonances
            harmonics[15] = 0.15  # ~1800 Hz
            harmonics[16] = 0.12  # ~1920 Hz
            
        elif self.condition == self.CONDITION_AGING:
            # Aging transformers have broader spectrum
            harmonics[1] *= 0.9  # Slight decrease in fundamental
            # Increased mid-high frequency noise due to material degradation
            for i in range(5, 30):
                harmonics[i] = 0.1 * (0.9 ** (i-5))
            # Add specific resonance peaks
            harmonics[7] = 0.15
            harmonics[13] = 0.18
            harmonics[21] = 0.12
        
        return harmonics
    
    def generate_spectrum(self, freq_range: Tuple[float, float, int]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate the frequency spectrum for this transformer.
        
        Args:
            freq_range: Tuple of (min_freq, max_freq, num_points) in Hz
            
        Returns:
            Tuple of (frequencies, amplitudes)
        """
        if not self.enabled:
            return np.linspace(freq_range[0], freq_range[1], freq_range[2]), np.zeros(freq_range[2])
        
        # Create frequency array
        frequencies = np.linspace(freq_range[0], freq_range[1], freq_range[2])
        
        # Initialize amplitudes to small background level
        amplitudes = np.ones_like(frequencies) * 0.0001
        
        # Add harmonics based on the source's properties
        for harmonic, amplitude in self._harmonic_profile.items():
            harmonic_freq = harmonic * self.fundamental_freq
            
            if harmonic_freq < freq_range[0] or harmonic_freq > freq_range[1]:
                continue
                
            # Use a narrow Gaussian peak for each harmonic
            peak_width = 2.0  # Hz
            gauss = amplitude * np.exp(-0.5 * ((frequencies - harmonic_freq) / peak_width) ** 2)
            amplitudes += gauss
        
        # Scale by load factor (sound increases with load)
        amplitudes *= (0.4 + 0.6 * self.load_factor)
        
        # Normalize to keep peak amplitude at 1.0
        if np.max(amplitudes) > 0:
            amplitudes /= np.max(amplitudes)
        
        return frequencies, amplitudes
    
    def generate_time_signal(self, duration: float) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate a time-domain signal of the transformer sound.
        
        Args:
            duration: Signal duration in seconds
            
        Returns:
            Tuple of (time_points, amplitude_values)
        """
        if not self.enabled:
            # Return silence
            time_points = np.linspace(0, duration, int(duration * self.sample_rate))
            return time_points, np.zeros_like(time_points)
        
        # Create time array
        time_points = np.linspace(0, duration, int(duration * self.sample_rate))
        signal_values = np.zeros_like(time_points)
        
        # Add harmonics
        for harmonic, amplitude in self._harmonic_profile.items():
            harmonic_freq = harmonic * self.fundamental_freq
            # Add sine wave for each harmonic
            signal_values += amplitude * np.sin(2 * np.pi * harmonic_freq * time_points)
        
        # Add some noise based on condition
        noise_level = 0.01
        if self.condition == self.CONDITION_OVERLOADED:
            noise_level = 0.05
        elif self.condition == self.CONDITION_COOLING_ISSUE:
            noise_level = 0.08
        elif self.condition == self.CONDITION_LOOSE_WINDING:
            noise_level = 0.12
        elif self.condition == self.CONDITION_AGING:
            noise_level = 0.15
            
        noise = np.random.normal(0, noise_level, len(time_points))
        signal_values += noise
        
        # Add amplitude modulation for certain conditions
        if self.condition in [self.CONDITION_LOOSE_WINDING, self.CONDITION_AGING]:
            # Add slow amplitude modulation to represent mechanical oscillations
            mod_freq = 5.0  # 5 Hz modulation
            mod_depth = 0.15
            modulation = 1.0 + mod_depth * np.sin(2 * np.pi * mod_freq * time_points)
            signal_values *= modulation
        
        # Scale by load factor
        signal_values *= (0.4 + 0.6 * self.load_factor)
        
        # Normalize
        if np.max(np.abs(signal_values)) > 0:
            signal_values /= np.max(np.abs(signal_values))
        
        return time_points, signal_values


class SwitchSound(AcousticSource):
    """
    Models acoustic signature of switches and circuit breakers.
    
    Attributes:
        name (str): Unique identifier for the source
        position (Vector3D): 3D position of the switch
        voltage_rating (float): Voltage rating in volts
        current_rating (float): Current rating in amperes
        switch_state (str): State of the switch (OPEN, CLOSED, TRANSITIONING)
    """
    
    # Switch state constants
    STATE_OPEN = "open"
    STATE_CLOSED = "closed"
    STATE_TRANSITIONING = "transitioning"
    
    def __init__(self, name: str,
                position: Tuple[float, float, float],
                voltage_rating: float,
                current_rating: float,
                switch_type: str = "circuit_breaker",
                switch_state: str = STATE_CLOSED):
        """
        Initialize a switch sound source.
        
        Args:
            name: Unique identifier for the source
            position: 3D coordinates (x, y, z) of the switch in meters
            voltage_rating: Voltage rating in volts
            current_rating: Current rating in amperes
            switch_type: Type of switch (circuit_breaker, disconnect, etc.)
            switch_state: Initial state of the switch
        """
        # For steady-state operation (open/closed), sound power is low
        # During transition, sound power depends on rating
        base_sound_power = 1e-10  # Very low for steady state
        
        super().__init__(name, position, base_sound_power)
        
        self.voltage_rating = voltage_rating
        self.current_rating = current_rating
        self.switch_type = switch_type
        
        if switch_state not in [self.STATE_OPEN, self.STATE_CLOSED, self.STATE_TRANSITIONING]:
            switch_state = self.STATE_CLOSED
        
        self.switch_state = switch_state
        self._update_sound_power()
        
        # Transition sound characteristics
        self.transition_duration = 0.15  # seconds
        self.transition_start_time = 0.0
    
    @property
    def source_type(self) -> str:
        return "switch_sound"
    
    def set_state(self, state: str, transition_time: float = None):
        """
        Update the switch state.
        
        Args:
            state: New state
            transition_time: Time at which the transition started (None for instantaneous)
        """
        if state not in [self.STATE_OPEN, self.STATE_CLOSED, self.STATE_TRANSITIONING]:
            return
            
        self.switch_state = state
        
        if transition_time is not None:
            self.transition_start_time = transition_time
            
        self._update_sound_power()
    
    def _update_sound_power(self):
        """Update sound power based on current state and ratings."""
        if self.switch_state == self.STATE_TRANSITIONING:
            # Sound power during transition is much higher
            # Base level depends on voltage and current ratings
            # Use empirical formula based on power
            apparent_power = self.voltage_rating * self.current_rating
            kva = apparent_power / 1000
            
            # Logarithmic relationship with kVA rating
            if kva > 0:
                sound_level_db = 60 + 10 * np.log10(kva)
                
                # Convert to sound power (watts)
                reference_power = 1e-12  # 1 pW
                self.sound_power = reference_power * (10 ** (sound_level_db / 10))
            else:
                self.sound_power = 1e-6  # Minimal sound
        else:
            # Minimal sound during steady state (open/closed)
            if self.switch_state == self.STATE_CLOSED:
                # Slight hum when closed (current flowing)
                self.sound_power = 1e-10
            else:
                # Silent when open
                self.sound_power = 1e-12
    
    def generate_spectrum(self, freq_range: Tuple[float, float, int]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate the frequency spectrum for this switch.
        
        Args:
            freq_range: Tuple of (min_freq, max_freq, num_points) in Hz
            
        Returns:
            Tuple of (frequencies, amplitudes)
        """
        if not self.enabled:
            return np.linspace(freq_range[0], freq_range[1], freq_range[2]), np.zeros(freq_range[2])
        
        # Create frequency array
        frequencies = np.linspace(freq_range[0], freq_range[1], freq_range[2])
        
        # Generate different spectra based on state
        if self.switch_state == self.STATE_TRANSITIONING:
            # Transition sound - wideband with resonance peaks
            
            # Low background
            amplitudes = np.ones_like(frequencies) * 0.01
            
            # Add resonance peaks based on switch type
            if self.switch_type == "circuit_breaker":
                # Circuit breaker - metallic impact sound
                resonances = [
                    (500, 0.7),  # Metal case resonance
                    (1200, 0.9),  # Main impact frequency
                    (1800, 0.5),  # Secondary resonance
                    (2400, 0.3),  # Higher harmonic
                    (3000, 0.2)   # Highest audible resonance
                ]
            elif self.switch_type == "disconnect":
                # Disconnect switch - more mechanical sound
                resonances = [
                    (300, 0.6),   # Lower frequency mechanical movement
                    (800, 0.8),   # Primary resonance
                    (1500, 0.4),  # Secondary resonance
                    (2200, 0.25)  # Higher resonance
                ]
            else:
                # Generic switch
                resonances = [
                    (600, 0.7),  # Primary resonance
                    (1500, 0.5)  # Secondary resonance
                ]
                
            # Add resonance peaks to the spectrum
            for freq, amp in resonances:
                # Use a Gaussian shape for each resonance
                width = freq * 0.1  # 10% of center frequency
                peak = amp * np.exp(-0.5 * ((frequencies - freq) / width) ** 2)
                amplitudes += peak
                
            # Add broadband noise component (impact noise)
            noise_shape = np.exp(-frequencies / 3000)  # Exponential decay with frequency
            amplitudes += noise_shape * 0.3
            
        elif self.switch_state == self.STATE_CLOSED:
            # Closed state - slight hum at power frequency (60 Hz) and harmonics
            amplitudes = np.ones_like(frequencies) * 0.001  # Very low background
            
            # Add power frequency components (60 Hz and harmonics)
            power_freq = 60  # Hz
            for n in range(1, 6):  # Fundamental and 5 harmonics
                harm_freq = power_freq * n
                if harm_freq >= freq_range[0] and harm_freq <= freq_range[1]:
                    # Find nearest index
                    idx = int(np.round((harm_freq - freq_range[0]) / 
                                     (freq_range[1] - freq_range[0]) * (len(frequencies) - 1)))
                    if 0 <= idx < len(amplitudes):
                        # Add harmonic with decreasing amplitude
                        amplitudes[idx] = 0.05 / n
            
            # Smooth the spectrum
            amplitudes = np.convolve(amplitudes, np.ones(5)/5, mode='same')
            
        else:  # STATE_OPEN
            # Open state - essentially silent
            amplitudes = np.ones_like(frequencies) * 0.0001
        
        # Normalize
        if np.max(amplitudes) > 0:
            amplitudes /= np.max(amplitudes)
        
        return frequencies, amplitudes
    
    def generate_time_signal(self, duration: float) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate a time-domain signal of the switch sound.
        
        Args:
            duration: Signal duration in seconds
            
        Returns:
            Tuple of (time_points, amplitude_values)
        """
        if not self.enabled:
            # Return silence
            time_points = np.linspace(0, duration, int(duration * self.sample_rate))
            return time_points, np.zeros_like(time_points)
        
        # Create time array
        time_points = np.linspace(0, duration, int(duration * self.sample_rate))
        signal_values = np.zeros_like(time_points)
        
        if self.switch_state == self.STATE_TRANSITIONING:
            # Create a brief impact sound followed by decay
            
            # Determine the position of the impact in the signal
            impact_time = 0.02  # Impact at 20ms
            impact_pos = int(impact_time * self.sample_rate)
            
            # Ensure impact_pos is within the signal duration
            if impact_pos >= len(time_points):
                impact_pos = 0
            
            # Create exponential decay envelope
            decay_const = 15.0  # Decay constant
            t_env = np.arange(len(time_points) - impact_pos) / self.sample_rate
            envelope = np.exp(-decay_const * t_env)
            
            # Generate white noise for the impact
            noise = np.random.normal(0, 1, len(time_points) - impact_pos)
            
            # Apply envelope to noise
            impact_signal = noise * envelope
            
            # Add to signal at impact position
            signal_values[impact_pos:] += impact_signal
            
            # Add resonances based on switch type
            if self.switch_type == "circuit_breaker":
                resonance_freqs = [500, 1200, 1800, 2400, 3000]
                resonance_amps = [0.7, 0.9, 0.5, 0.3, 0.2]
            else:
                resonance_freqs = [300, 800, 1500, 2200]
                resonance_amps = [0.6, 0.8, 0.4, 0.25]
                
            # Add damped sinusoids for each resonance
            for freq, amp in zip(resonance_freqs, resonance_amps):
                # Different decay rates for different frequencies
                decay = 8.0 + freq / 500.0  # Higher frequencies decay faster
                damped_sin = amp * np.exp(-decay * t_env) * np.sin(2 * np.pi * freq * t_env)
                signal_values[impact_pos:] += damped_sin
                
        elif self.switch_state == self.STATE_CLOSED:
            # Add very quiet 60Hz hum and harmonics
            power_freq = 60  # Hz
            for n in range(1, 6):  # Fundamental and 5 harmonics
                amplitude = 0.05 / n  # Decreasing amplitude with harmonic number
                signal_values += amplitude * np.sin(2 * np.pi * power_freq * n * time_points)
            
            # Add very low level noise
            noise = np.random.normal(0, 0.01, len(time_points))
            signal_values += noise
            
        # Normalize
        if np.max(np.abs(signal_values)) > 0:
            signal_values /= np.max(np.abs(signal_values))
        
        return time_points, signal_values


class DischargeSound(AcousticSource):
    """
    Models sound of electrical discharges such as corona, arcing, and partial discharge.
    
    Attributes:
        name (str): Unique identifier for the source
        position (Vector3D): 3D position of the discharge
        discharge_type (str): Type of discharge (CORONA, ARCING, PARTIAL)
        voltage (float): Voltage in volts
        intensity (float): Relative intensity of the discharge (0-1)
    """
    
    # Discharge type constants
    TYPE_CORONA = "corona"
    TYPE_ARCING = "arcing"
    TYPE_PARTIAL = "partial"
    
    def __init__(self, name: str,
                position: Tuple[float, float, float],
                discharge_type: str,
                voltage: float,
                intensity: float = 0.7):
        """
        Initialize a discharge sound source.
        
        Args:
            name: Unique identifier for the source
            position: 3D coordinates (x, y, z) of the discharge in meters
            discharge_type: Type of discharge (corona, arcing, partial)
            voltage: Voltage in volts
            intensity: Relative intensity of the discharge 0-1 (default: 0.7)
        """
        # Calculate sound power based on discharge type and voltage
        # Base values from empirical data
        if discharge_type == self.TYPE_CORONA:
            # Corona discharge is usually quieter
            base_sound_level = 30 + 10 * np.log10(voltage / 1000)
        elif discharge_type == self.TYPE_ARCING:
            # Arcing is usually louder
            base_sound_level = 40 + 15 * np.log10(voltage / 1000)
        elif discharge_type == self.TYPE_PARTIAL:
            # Partial discharge sound level
            base_sound_level = 25 + 12 * np.log10(voltage / 1000)
        else:
            # Default to corona type
            discharge_type = self.TYPE_CORONA
            base_sound_level = 30 + 10 * np.log10(voltage / 1000)
        
        # Apply intensity scaling
        sound_level_db = base_sound_level + 10 * np.log10(max(0.01, intensity))
        
        # Convert to sound power (watts)
        reference_power = 1e-12  # 1 pW
        sound_power = reference_power * (10 ** (sound_level_db / 10))
        
        super().__init__(name, position, sound_power)
        
        self.discharge_type = discharge_type
        self.voltage = voltage
        self.intensity = min(1.0, max(0.0, intensity))  # Clamp to valid range
        
        # Update sound power based on new intensity
        self._update_sound_power()
    
    @property
    def source_type(self) -> str:
        return "discharge_sound"
    
    def set_intensity(self, intensity: float):
        """
        Update the discharge intensity.
        
        Args:
            intensity: New intensity value (0-1)
        """
        self.intensity = min(1.0, max(0.0, intensity))
        self._update_sound_power()
    
    def _update_sound_power(self):
        """Update sound power based on current parameters."""
        # Recalculate sound level based on voltage and type
        if self.discharge_type == self.TYPE_CORONA:
            base_sound_level = 30 + 10 * np.log10(self.voltage / 1000)
        elif self.discharge_type == self.TYPE_ARCING:
            base_sound_level = 40 + 15 * np.log10(self.voltage / 1000)
        elif self.discharge_type == self.TYPE_PARTIAL:
            base_sound_level = 25 + 12 * np.log10(self.voltage / 1000)
        else:
            base_sound_level = 30 + 10 * np.log10(self.voltage / 1000)
        
        # Apply intensity scaling
        sound_level_db = base_sound_level + 10 * np.log10(max(0.01, self.intensity))
        
        # Convert to sound power (watts)
        reference_power = 1e-12  # 1 pW
        self.sound_power = reference_power * (10 ** (sound_level_db / 10))
    
    def generate_spectrum(self, freq_range: Tuple[float, float, int]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate the frequency spectrum for this discharge.
        
        Args:
            freq_range: Tuple of (min_freq, max_freq, num_points) in Hz
            
        Returns:
            Tuple of (frequencies, amplitudes)
        """
        if not self.enabled:
            return np.linspace(freq_range[0], freq_range[1], freq_range[2]), np.zeros(freq_range[2])
        
        # Create frequency array
        frequencies = np.linspace(freq_range[0], freq_range[1], freq_range[2])
        
        # Generate spectrum based on discharge type
        if self.discharge_type == self.TYPE_CORONA:
            # Corona has distinctive spectrum with broadband noise and specific peaks
            # Initialize with low background noise
            amplitudes = np.random.normal(0, 0.05, len(frequencies))
            
            # Add characteristic peaks for corona
            for peak_freq in [800, 1600, 2400, 3200, 4800]:
                if freq_range[0] <= peak_freq <= freq_range[1]:
                    # Find nearest index
                    idx = int(np.round((peak_freq - freq_range[0]) / 
                                      (freq_range[1] - freq_range[0]) * (len(frequencies) - 1)))
                    
                    # Add Gaussian peak
                    width = peak_freq * 0.1  # 10% of center frequency
                    peak = 0.6 * np.exp(-0.5 * ((frequencies - peak_freq) / width) ** 2)
                    amplitudes += peak
                    
            # Apply high-pass filter characteristic
            high_pass = 1.0 - np.exp(-frequencies / 500)
            amplitudes *= high_pass
            
        elif self.discharge_type == self.TYPE_ARCING:
            # Arcing has more chaotic spectrum with broader peaks
            # Start with higher noise level
            amplitudes = np.random.normal(0, 0.1, len(frequencies))
            
            # Add broader frequency distribution
            for i in range(10):
                peak_freq = 500 + 800 * i
                if freq_range[0] <= peak_freq <= freq_range[1]:
                    width = peak_freq * 0.2  # 20% of center frequency
                    amp = 0.8 * (0.9 ** i)  # Decreasing amplitude for higher harmonics
                    peak = amp * np.exp(-0.5 * ((frequencies - peak_freq) / width) ** 2)
                    amplitudes += peak
            
            # Add random crackle components
            for _ in range(5):
                crackle_freq = np.random.uniform(freq_range[0], freq_range[1])
                width = crackle_freq * 0.05
                amp = np.random.uniform(0.3, 0.7)
                peak = amp * np.exp(-0.5 * ((frequencies - crackle_freq) / width) ** 2)
                amplitudes += peak
                
            # Apply characteristic coloration
            amplitudes *= np.exp(-frequencies / 5000)
            
        elif self.discharge_type == self.TYPE_PARTIAL:
            # Partial discharge has periodic pulses
            # Start with low noise
            amplitudes = np.random.normal(0, 0.03, len(frequencies))
            
            # Add regular harmonic structure
            base_freq = 120  # Hz
            for i in range(1, 30):
                harm_freq = base_freq * i
                if freq_range[0] <= harm_freq <= freq_range[1]:
                    width = 10  # Hz
                    amp = 0.9 * (0.9 ** (i-1))  # Decreasing amplitude
                    peak = amp * np.exp(-0.5 * ((frequencies - harm_freq) / width) ** 2)
                    amplitudes += peak
            
            # Add some randomization
            amplitudes += np.random.normal(0, 0.02 * amplitudes, len(frequencies))
        
        else:
            # Generic electrical noise
            amplitudes = np.random.normal(0, 0.05, len(frequencies))
            # Add 1/f noise characteristic
            pink_noise = np.sqrt(1.0 / np.maximum(frequencies, 1.0))
            amplitudes += 0.5 * pink_noise / np.max(pink_noise)
        
        # Apply intensity scaling
        amplitudes *= self.intensity
        
        # Ensure positive values
        amplitudes = np.abs(amplitudes)
        
        # Normalize
        if np.max(amplitudes) > 0:
            amplitudes /= np.max(amplitudes)
        
        return frequencies, amplitudes
    
    def generate_time_signal(self, duration: float) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate a time-domain signal of the discharge sound.
        
        Args:
            duration: Signal duration in seconds
            
        Returns:
            Tuple of (time_points, amplitude_values)
        """
        if not self.enabled:
            # Return silence
            time_points = np.linspace(0, duration, int(duration * self.sample_rate))
            return time_points, np.zeros_like(time_points)
        
        # Create time array
        time_points = np.linspace(0, duration, int(duration * self.sample_rate))
        signal_values = np.zeros_like(time_points)
        
        if self.discharge_type == self.TYPE_CORONA:
            # Corona has characteristic hissing sound
            
            # Generate base noise
            base_noise = np.random.normal(0, 1, len(time_points))
            
            # Apply bandpass filtering to shape spectrum
            sos = signal.butter(6, [800, 5000], 'bandpass', fs=self.sample_rate, output='sos')
            filtered_noise = signal.sosfilt(sos, base_noise)
            
            # Add amplitude modulation
            mod_freq = 120  # Hz
            mod_depth = 0.3
            modulation = 1.0 + mod_depth * np.sin(2 * np.pi * mod_freq * time_points)
            signal_values = filtered_noise * modulation
            
        elif self.discharge_type == self.TYPE_ARCING:
            # Arcing has irregular crackling
            
            # Generate base noise with higher amplitude
            base_noise = np.random.normal(0, 1.5, len(time_points))
            
            # Apply filter to shape spectrum
            sos = signal.butter(4, [200, 8000], 'bandpass', fs=self.sample_rate, output='sos')
            filtered_noise = signal.sosfilt(sos, base_noise)
            
            # Add crackle events
            num_crackles = int(duration * 20)  # 20 crackles per second average
            for _ in range(num_crackles):
                # Random position
                pos = np.random.randint(0, len(time_points))
                
                # Generate pulse
                pulse_width = int(0.005 * self.sample_rate)  # 5ms pulse
                if pos + pulse_width < len(time_points):
                    pulse = np.random.normal(0, 3, pulse_width) * \
                            np.exp(-np.arange(pulse_width) / (0.001 * self.sample_rate))
                    signal_values[pos:pos+pulse_width] += pulse
            
            # Add base filtered noise
            signal_values += filtered_noise * 0.3
            
        elif self.discharge_type == self.TYPE_PARTIAL:
            # Partial discharge has periodic pulses
            
            # Generate base noise
            base_noise = np.random.normal(0, 0.2, len(time_points))
            
            # Add periodic pulses (120 Hz rate for 60 Hz power)
            pulse_rate = 120  # Hz
            pulse_interval = self.sample_rate / pulse_rate
            
            for i in range(int(duration * pulse_rate)):
                pos = int(i * pulse_interval)
                if pos < len(time_points):
                    # Generate pulse
                    pulse_width = int(0.001 * self.sample_rate)  # 1ms pulse
                    if pos + pulse_width < len(time_points):
                        # Exponential decay pulse
                        pulse = 2.0 * np.exp(-np.arange(pulse_width) / (0.0002 * self.sample_rate))
                        signal_values[pos:pos+pulse_width] += pulse
            
            # Add some randomization to pulse amplitudes
            signal_values *= (1.0 + 0.3 * np.random.normal(0, 1, len(time_points)))
            
            # Add base noise
            signal_values += base_noise
            
        else:
            # Generic electrical noise
            base_noise = np.random.normal(0, 1, len(time_points))
            
            # Apply filter for electrical noise character
            sos = signal.butter(3, [300, 3000], 'bandpass', fs=self.sample_rate, output='sos')
            signal_values = signal.sosfilt(sos, base_noise)
        
        # Apply intensity scaling
        signal_values *= self.intensity
        
        # Normalize
        if np.max(np.abs(signal_values)) > 0:
            signal_values /= np.max(np.abs(signal_values))
        
        return time_points, signal_values


class AcousticProfile:
    """
    Represents acoustic properties and sound propagation in space.
    
    Attributes:
        sources (List[AcousticSource]): Collection of sound sources
        boundaries (Dict): Information about acoustic boundaries
        ambient_noise (float): Ambient noise level in dB
    """
    
    def __init__(self, ambient_noise: float = 35.0):
        """
        Initialize an acoustic profile.
        
        Args:
            ambient_noise: Ambient noise level in dB (default: 35.0)
        """
        self.sources = []
        self.boundaries = {}
        self.ambient_noise = ambient_noise
    
    def add_source(self, source: AcousticSource):
        """
        Add a sound source to the profile.
        
        Args:
            source: The acoustic source to add
        """
        self.sources.append(source)
    
    def remove_source(self, source_name: str) -> bool:
        """
        Remove a sound source from the profile by name.
        
        Args:
            source_name: Name of the source to remove
            
        Returns:
            True if source was found and removed, False otherwise
        """
        for i, source in enumerate(self.sources):
            if source.name == source_name:
                del self.sources[i]
                return True
        return False
    
    def get_source_by_name(self, source_name: str) -> Optional[AcousticSource]:
        """
        Get a source by its name.
        
        Args:
            source_name: Name of the source to retrieve
            
        Returns:
            The source if found, None otherwise
        """
        for source in self.sources:
            if source.name == source_name:
                return source
        return None
    
    def calculate_combined_spl(self, position: Tuple[float, float, float]) -> float:
        """
        Calculate combined sound pressure level at a specified position.
        
        Args:
            position: 3D coordinates (x, y, z) to calculate SPL at
            
        Returns:
            Combined sound pressure level in dB
        """
        # If no sources, return ambient noise
        if not self.sources:
            return self.ambient_noise
        
        # Calculate SPL for each source
        source_spls = [source.calculate_spl_at(position) for source in self.sources]
        
        # Convert dB values to linear power
        linear_powers = [10 ** (spl / 10) for spl in source_spls]
        
        # Add ambient noise in linear domain
        linear_ambient = 10 ** (self.ambient_noise / 10)
        total_linear = sum(linear_powers) + linear_ambient
        
        # Convert back to dB
        combined_spl = 10 * np.log10(total_linear)
        
        return combined_spl
    
    def generate_combined_spectrum(self, 
                                position: Tuple[float, float, float],
                                freq_range: Tuple[float, float, int]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate combined frequency spectrum at a specified position.
        
        Args:
            position: 3D coordinates (x, y, z) to calculate spectrum at
            freq_range: Tuple of (min_freq, max_freq, num_points) in Hz
            
        Returns:
            Tuple of (frequencies, amplitudes)
        """
        # Create frequency array
        frequencies = np.linspace(freq_range[0], freq_range[1], freq_range[2])
        
        # Initialize combined spectrum with ambient noise
        # Ambient noise is typically modeled as pink noise (1/f spectrum)
        ambient_amplitudes = np.sqrt(1.0 / np.maximum(frequencies, 1.0))
        ambient_amplitudes *= (10 ** (self.ambient_noise / 20)) / np.max(ambient_amplitudes)
        
        combined_amplitudes = np.copy(ambient_amplitudes)
        
        # Add spectra from all sources
        for source in self.sources:
            if not source.enabled:
                continue
                
            # Get source spectrum
            _, source_amplitudes = source.generate_spectrum(freq_range)
            
            # Calculate attenuation factor based on distance
            pos = Vector3D(*position)
            distance = (pos - source.position).magnitude()
            if distance < 0.1:
                distance = 0.1
                
            # Inverse square law attenuation
            attenuation = 1.0 / (distance ** 2)
            
            # Scale source spectrum by attenuation
            scaled_amplitudes = source_amplitudes * attenuation
            
            # Add to combined spectrum (in linear domain)
            combined_amplitudes = np.sqrt(combined_amplitudes**2 + scaled_amplitudes**2)
        
        return frequencies, combined_amplitudes


class AcousticVisualizer:
    """
    Provides visualization tools for acoustic signatures.
    
    This class helps visualize audio signals, frequency spectra, and spatial 
    distributions of sound pressure levels.
    """
    
    @staticmethod
    def plot_spectrum(frequencies: np.ndarray, 
                      amplitudes: np.ndarray, 
                      title: str = "Frequency Spectrum",
                      log_scale: bool = True) -> plt.Figure:
        """
        Plot a frequency spectrum.
        
        Args:
            frequencies: Array of frequency points
            amplitudes: Array of amplitude values
            title: Plot title
            log_scale: Whether to use logarithmic scale for frequency axis
            
        Returns:
            Matplotlib figure object
        """
        fig, ax = plt.subplots(figsize=(10, 6))
        
        ax.plot(frequencies, amplitudes)
        
        if log_scale and np.min(frequencies) > 0:
            ax.set_xscale('log')
            
        ax.set_xlabel('Frequency (Hz)')
        ax.set_ylabel('Amplitude')
        ax.set_title(title)
        ax.grid(True, which='both', linestyle='--', alpha=0.7)
        
        # Add minor grid lines for log scale
        if log_scale:
            ax.grid(True, which='minor', linestyle=':', alpha=0.4)
        
        return fig
    
    @staticmethod
    def plot_time_signal(time_points: np.ndarray, 
                         amplitudes: np.ndarray, 
                         title: str = "Time Domain Signal") -> plt.Figure:
        """
        Plot a time domain signal.
        
        Args:
            time_points: Array of time points
            amplitudes: Array of amplitude values
            title: Plot title
            
        Returns:
            Matplotlib figure object
        """
        fig, ax = plt.subplots(figsize=(10, 6))
        
        ax.plot(time_points, amplitudes)
        
        ax.set_xlabel('Time (s)')
        ax.set_ylabel('Amplitude')
        ax.set_title(title)
        ax.grid(True, linestyle='--', alpha=0.7)
        
        return fig
    
    @staticmethod
    def plot_spectrogram(time_points: np.ndarray, 
                         amplitudes: np.ndarray, 
                         sample_rate: int = 44100,
                         title: str = "Spectrogram") -> plt.Figure:
        """
        Plot a spectrogram from time domain data.
        
        Args:
            time_points: Array of time points
            amplitudes: Array of amplitude values
            sample_rate: Sample rate in Hz
            title: Plot title
            
        Returns:
            Matplotlib figure object
        """
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Calculate spectrogram
        f, t, Sxx = signal.spectrogram(amplitudes, fs=sample_rate, nperseg=1024, noverlap=512)
        
        # Plot spectrogram
        pcm = ax.pcolormesh(t, f, 10 * np.log10(Sxx + 1e-10), shading='gouraud', cmap='viridis')
        fig.colorbar(pcm, ax=ax, label='Power (dB)')
        
        ax.set_xlabel('Time (s)')
        ax.set_ylabel('Frequency (Hz)')
        ax.set_title(title)
        ax.set_ylim(0, sample_rate // 2)  # Limit to Nyquist frequency
        
        return fig
    
    @staticmethod
    def plot_spatial_distribution(profile: AcousticProfile, 
                                z_level: float,
                                x_range: Tuple[float, float, int],
                                y_range: Tuple[float, float, int],
                                title: str = "Sound Pressure Level Distribution") -> plt.Figure:
        """
        Plot spatial distribution of sound pressure levels on a 2D plane.
        
        Args:
            profile: Acoustic profile containing sources
            z_level: Z-coordinate for the 2D plane
            x_range: Tuple of (min_x, max_x, num_points)
            y_range: Tuple of (min_y, max_y, num_points)
            title: Plot title
            
        Returns:
            Matplotlib figure object
        """
        # Create coordinate grids
        x = np.linspace(x_range[0], x_range[1], x_range[2])
        y = np.linspace(y_range[0], y_range[1], y_range[2])
        X, Y = np.meshgrid(x, y)
        
        # Calculate SPL at each point
        Z = np.zeros_like(X)
        for i in range(X.shape[0]):
            for j in range(X.shape[1]):
                Z[i, j] = profile.calculate_combined_spl((X[i, j], Y[i, j], z_level))
        
        # Create plot
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Plot contour
        levels = np.linspace(np.min(Z), np.max(Z), 20)
        contour = ax.contourf(X, Y, Z, levels=levels, cmap='inferno')
        fig.colorbar(contour, ax=ax, label='Sound Pressure Level (dB)')
        
        # Add source positions to plot
        for source in profile.sources:
            if source.enabled:
                ax.plot(source.position.x, source.position.y, 'o', 
                       markersize=8, markeredgecolor='white', markerfacecolor='blue',
                       label=f"{source.name} ({source.source_type})")
        
        # Show only one instance of each label in the legend
        handles, labels = ax.get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        ax.legend(by_label.values(), by_label.keys(), loc='upper right')
        
        ax.set_xlabel('X (m)')
        ax.set_ylabel('Y (m)')
        ax.set_title(title)
        
        return fig
    
    @staticmethod
    def plot_comparative_spectra(sources: List[AcousticSource],
                               freq_range: Tuple[float, float, int],
                               title: str = "Comparative Frequency Spectra") -> plt.Figure:
        """
        Plot comparative frequency spectra for multiple sources.
        
        Args:
            sources: List of acoustic sources to compare
            freq_range: Tuple of (min_freq, max_freq, num_points) in Hz
            title: Plot title
            
        Returns:
            Matplotlib figure object
        """
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # Create color cycle
        colors = plt.cm.tab10(np.linspace(0, 1, len(sources)))
        
        # Plot spectrum for each source
        for i, source in enumerate(sources):
            frequencies, amplitudes = source.generate_spectrum(freq_range)
            ax.plot(frequencies, amplitudes, color=colors[i], 
                   label=f"{source.name} ({source.source_type})")
        
        ax.set_xlabel('Frequency (Hz)')
        ax.set_ylabel('Amplitude')
        ax.set_title(title)
        
        if np.min(frequencies) > 0:
            ax.set_xscale('log')
            
        ax.grid(True, which='both', linestyle='--', alpha=0.7)
        ax.legend()
        
        return fig
