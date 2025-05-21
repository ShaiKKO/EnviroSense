"""
Vibration profile implementation.

This module provides classes for creating, storing, and analyzing vibration profiles,
which represent the characteristic vibration signatures of equipment or conditions.
"""

import numpy as np
from typing import Tuple, List, Dict, Optional, Any, Union
import matplotlib.pyplot as plt
import json
import os
from datetime import datetime
import uuid


class VibrationProfile:
    """
    Represents a vibration profile with frequency and time domain data.
    
    A vibration profile stores characteristic vibration signatures that can be used
    for analysis, comparison, and classification of equipment conditions.
    """
    
    def __init__(self, 
                 name: str,
                 frequencies: Optional[np.ndarray] = None,
                 spectrum: Optional[np.ndarray] = None,
                 time_points: Optional[np.ndarray] = None,
                 time_signal: Optional[np.ndarray] = None,
                 profile_id: Optional[str] = None):
        """
        Initialize a vibration profile.
        
        Args:
            name: Profile name
            frequencies: Array of frequency points (Hz)
            spectrum: Array of amplitude values corresponding to frequencies
            time_points: Array of time points (seconds)
            time_signal: Array of amplitude values corresponding to time_points
            profile_id: Unique identifier for the profile, auto-generated if not provided
        """
        self.name = name
        self.profile_id = profile_id or str(uuid.uuid4())
        self.created_at = datetime.now().isoformat()
        
        # Initialize frequency domain data
        self.frequencies = frequencies
        self.spectrum = spectrum
        
        # Initialize time domain data
        self.time_points = time_points
        self.time_signal = time_signal
        
        # Additional metadata
        self.metadata = {}
        
        # Analysis results cache
        self._analysis_cache = {}
    
    def add_frequency_data(self, frequencies: np.ndarray, spectrum: np.ndarray) -> None:
        """
        Add or update frequency domain data.
        
        Args:
            frequencies: Array of frequency points (Hz)
            spectrum: Array of amplitude values corresponding to frequencies
        """
        self.frequencies = np.array(frequencies)
        self.spectrum = np.array(spectrum)
        
        # Clear cached analysis results that depend on frequency data
        keys_to_clear = ['peak_frequencies', 'rms_amplitude', 'spectral_moments']
        for key in keys_to_clear:
            if key in self._analysis_cache:
                del self._analysis_cache[key]
    
    def add_time_data(self, time_points: np.ndarray, time_signal: np.ndarray) -> None:
        """
        Add or update time domain data.
        
        Args:
            time_points: Array of time points (seconds)
            time_signal: Array of amplitude values corresponding to time_points
        """
        self.time_points = np.array(time_points)
        self.time_signal = np.array(time_signal)
        
        # Clear cached analysis results that depend on time data
        keys_to_clear = ['peak_to_peak', 'rms_value', 'crest_factor']
        for key in keys_to_clear:
            if key in self._analysis_cache:
                del self._analysis_cache[key]
    
    def get_peak_frequencies(self, num_peaks: int = 5) -> List[Tuple[float, float]]:
        """
        Get the most dominant frequencies in the spectrum.
        
        Args:
            num_peaks: Number of peak frequencies to return
            
        Returns:
            List of (frequency, amplitude) tuples sorted by amplitude
        """
        cache_key = f'peak_frequencies_{num_peaks}'
        if cache_key in self._analysis_cache:
            return self._analysis_cache[cache_key]
        
        if self.frequencies is None or self.spectrum is None:
            return []
        
        # Find indices of peaks
        # Using a simple algorithm: a point is a peak if it's greater than its neighbors
        peak_indices = []
        for i in range(1, len(self.spectrum) - 1):
            if (self.spectrum[i] > self.spectrum[i-1] and 
                self.spectrum[i] > self.spectrum[i+1]):
                peak_indices.append(i)
        
        # Sort peaks by amplitude
        peak_indices.sort(key=lambda i: self.spectrum[i], reverse=True)
        
        # Return top peaks
        result = []
        for i in peak_indices[:num_peaks]:
            result.append((self.frequencies[i], self.spectrum[i]))
        
        self._analysis_cache[cache_key] = result
        return result
    
    def get_rms_amplitude(self) -> float:
        """
        Calculate the RMS amplitude of the frequency spectrum.
        
        Returns:
            RMS amplitude value
        """
        if 'rms_amplitude' in self._analysis_cache:
            return self._analysis_cache['rms_amplitude']
        
        if self.spectrum is None:
            return 0.0
        
        rms = np.sqrt(np.mean(np.square(self.spectrum)))
        self._analysis_cache['rms_amplitude'] = rms
        return rms
    
    def get_time_domain_stats(self) -> Dict[str, float]:
        """
        Calculate time domain statistics.
        
        Returns:
            Dictionary of time domain statistics
        """
        if 'time_domain_stats' in self._analysis_cache:
            return self._analysis_cache['time_domain_stats']
        
        if self.time_signal is None:
            return {
                'peak_to_peak': 0.0,
                'rms': 0.0,
                'crest_factor': 0.0,
                'kurtosis': 0.0
            }
        
        # Calculate peak-to-peak amplitude
        peak_to_peak = np.max(self.time_signal) - np.min(self.time_signal)
        
        # Calculate RMS value
        rms = np.sqrt(np.mean(np.square(self.time_signal)))
        
        # Calculate crest factor (peak/RMS)
        crest_factor = np.max(np.abs(self.time_signal)) / rms if rms > 0 else 0.0
        
        # Calculate kurtosis (4th moment, measure of "peakedness")
        # Normalized signal
        if rms > 0:
            norm_signal = self.time_signal / rms
            kurtosis = np.mean(norm_signal**4) / (np.mean(norm_signal**2)**2)
        else:
            kurtosis = 0.0
        
        stats = {
            'peak_to_peak': peak_to_peak,
            'rms': rms,
            'crest_factor': crest_factor,
            'kurtosis': kurtosis
        }
        
        self._analysis_cache['time_domain_stats'] = stats
        return stats
    
    def plot_spectrum(self, title: Optional[str] = None, show: bool = True) -> plt.Figure:
        """
        Plot the frequency spectrum.
        
        Args:
            title: Plot title
            show: Whether to show the plot
            
        Returns:
            Matplotlib figure
        """
        if self.frequencies is None or self.spectrum is None:
            # Create empty figure if no data
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.set_title("No Frequency Data Available" if title is None else title)
            ax.set_xlabel("Frequency (Hz)")
            ax.set_ylabel("Amplitude")
            if show:
                plt.show()
            return fig
        
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(self.frequencies, self.spectrum)
        ax.set_xlabel("Frequency (Hz)")
        ax.set_ylabel("Amplitude")
        ax.set_title(self.name + " - Frequency Spectrum" if title is None else title)
        ax.grid(True)
        
        # Add log scale if frequency range is large enough
        if np.max(self.frequencies) / np.min(self.frequencies) > 10:
            ax.set_xscale('log')
        
        if show:
            plt.show()
            
        return fig
    
    def plot_time_signal(self, title: Optional[str] = None, show: bool = True) -> plt.Figure:
        """
        Plot the time domain signal.
        
        Args:
            title: Plot title
            show: Whether to show the plot
            
        Returns:
            Matplotlib figure
        """
        if self.time_points is None or self.time_signal is None:
            # Create empty figure if no data
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.set_title("No Time Domain Data Available" if title is None else title)
            ax.set_xlabel("Time (s)")
            ax.set_ylabel("Amplitude")
            if show:
                plt.show()
            return fig
        
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(self.time_points, self.time_signal)
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Amplitude")
        ax.set_title(self.name + " - Time Domain Signal" if title is None else title)
        ax.grid(True)
        
        if show:
            plt.show()
            
        return fig
    
    def compute_spectrogram(self, window_size: int = 256, overlap: float = 0.5) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Compute the spectrogram of the time domain signal.
        
        Args:
            window_size: Size of the window for STFT
            overlap: Overlap between windows (0.0 to 1.0)
            
        Returns:
            Tuple of (time points, frequencies, spectrogram values)
        """
        if 'spectrogram' in self._analysis_cache:
            return self._analysis_cache['spectrogram']
        
        if self.time_points is None or self.time_signal is None:
            return np.array([]), np.array([]), np.array([[]])
        
        # Calculate sample rate
        sample_rate = 1.0 / (self.time_points[1] - self.time_points[0])
        
        # Calculate hop length based on overlap
        hop_length = int(window_size * (1 - overlap))
        
        # Compute spectrogram
        frequencies, times, spectrogram = plt.mlab.specgram(
            self.time_signal, 
            NFFT=window_size, 
            Fs=sample_rate, 
            noverlap=int(window_size * overlap)
        )
        
        result = (times, frequencies, spectrogram)
        self._analysis_cache['spectrogram'] = result
        return result
    
    def plot_spectrogram(self, title: Optional[str] = None, show: bool = True) -> plt.Figure:
        """
        Plot the spectrogram of the time domain signal.
        
        Args:
            title: Plot title
            show: Whether to show the plot
            
        Returns:
            Matplotlib figure
        """
        if self.time_points is None or self.time_signal is None:
            # Create empty figure if no data
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.set_title("No Time Domain Data Available for Spectrogram" if title is None else title)
            ax.set_xlabel("Time (s)")
            ax.set_ylabel("Frequency (Hz)")
            if show:
                plt.show()
            return fig
        
        times, frequencies, spectrogram = self.compute_spectrogram()
        
        fig, ax = plt.subplots(figsize=(10, 6))
        pcm = ax.pcolormesh(times, frequencies, 10 * np.log10(spectrogram), shading='gouraud')
        fig.colorbar(pcm, ax=ax, label='Power/Frequency (dB/Hz)')
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Frequency (Hz)")
        ax.set_title(self.name + " - Spectrogram" if title is None else title)
        
        if show:
            plt.show()
            
        return fig
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert profile to dictionary for serialization.
        
        Returns:
            Dictionary representation of the profile
        """
        data = {
            'name': self.name,
            'profile_id': self.profile_id,
            'created_at': self.created_at,
            'metadata': self.metadata
        }
        
        # Include frequency data if available
        if self.frequencies is not None and self.spectrum is not None:
            data['frequency_data'] = {
                'frequencies': self.frequencies.tolist(),
                'spectrum': self.spectrum.tolist()
            }
        
        # Include time data if available
        if self.time_points is not None and self.time_signal is not None:
            data['time_data'] = {
                'time_points': self.time_points.tolist(),
                'time_signal': self.time_signal.tolist()
            }
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VibrationProfile':
        """
        Create profile from dictionary.
        
        Args:
            data: Dictionary representation of the profile
            
        Returns:
            New VibrationProfile instance
        """
        # Extract frequency data if available
        frequencies = None
        spectrum = None
        if 'frequency_data' in data:
            frequencies = np.array(data['frequency_data']['frequencies'])
            spectrum = np.array(data['frequency_data']['spectrum'])
        
        # Extract time data if available
        time_points = None
        time_signal = None
        if 'time_data' in data:
            time_points = np.array(data['time_data']['time_points'])
            time_signal = np.array(data['time_data']['time_signal'])
        
        # Create profile instance
        profile = cls(
            name=data['name'],
            frequencies=frequencies,
            spectrum=spectrum,
            time_points=time_points,
            time_signal=time_signal,
            profile_id=data.get('profile_id')
        )
        
        # Set created_at if available
        if 'created_at' in data:
            profile.created_at = data['created_at']
        
        # Set metadata if available
        if 'metadata' in data:
            profile.metadata = data['metadata']
        
        return profile
    
    def save_to_file(self, directory: str, filename: Optional[str] = None) -> str:
        """
        Save profile to a JSON file.
        
        Args:
            directory: Directory to save the file in
            filename: Filename to use, defaults to profile_id.json
            
        Returns:
            Path to the saved file
        """
        # Create directory if it doesn't exist
        os.makedirs(directory, exist_ok=True)
        
        # Use default filename if none provided
        if filename is None:
            filename = f"{self.profile_id}.json"
        
        # Full path to the file
        filepath = os.path.join(directory, filename)
        
        # Convert to dictionary
        data = self.to_dict()
        
        # Save as JSON
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        return filepath
    
    @classmethod
    def load_from_file(cls, filepath: str) -> 'VibrationProfile':
        """
        Load profile from a JSON file.
        
        Args:
            filepath: Path to the JSON file
            
        Returns:
            Loaded VibrationProfile instance
        """
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        return cls.from_dict(data)
    
    def compare_with(self, other: 'VibrationProfile') -> Dict[str, float]:
        """
        Compare this profile with another.
        
        Args:
            other: VibrationProfile to compare with
            
        Returns:
            Dictionary of comparison metrics
        """
        results = {}
        
        # Compare frequency spectra if available
        if (self.frequencies is not None and self.spectrum is not None and
            other.frequencies is not None and other.spectrum is not None):
            
            # Ensure frequencies match
            if np.array_equal(self.frequencies, other.frequencies):
                # Calculate correlation coefficient
                correlation = np.corrcoef(self.spectrum, other.spectrum)[0, 1]
                
                # Calculate mean squared error
                mse = np.mean((self.spectrum - other.spectrum) ** 2)
                
                # Calculate difference in peak frequencies
                self_peaks = self.get_peak_frequencies(3)
                other_peaks = other.get_peak_frequencies(3)
                
                peak_freq_diff = 0.0
                if self_peaks and other_peaks:
                    self_peak_freqs = [p[0] for p in self_peaks]
                    other_peak_freqs = [p[0] for p in other_peaks]
                    
                    for i, freq in enumerate(self_peak_freqs):
                        if i < len(other_peak_freqs):
                            peak_freq_diff += abs(freq - other_peak_freqs[i])
                
                results['spectrum_correlation'] = correlation
                results['spectrum_mse'] = mse
                results['peak_frequency_difference'] = peak_freq_diff
                
            else:
                # Frequencies don't match, need to interpolate
                # This is a simplified approach
                min_freq = max(np.min(self.frequencies), np.min(other.frequencies))
                max_freq = min(np.max(self.frequencies), np.max(other.frequencies))
                
                # Create a common frequency array
                common_freqs = np.linspace(min_freq, max_freq, 1000)
                
                # Interpolate both spectra to the common frequency array
                from scipy.interpolate import interp1d
                
                self_interp = interp1d(self.frequencies, self.spectrum, 
                                      bounds_error=False, fill_value=0.0)
                other_interp = interp1d(other.frequencies, other.spectrum,
                                        bounds_error=False, fill_value=0.0)
                
                self_spectrum_common = self_interp(common_freqs)
                other_spectrum_common = other_interp(common_freqs)
                
                # Calculate correlation coefficient
                correlation = np.corrcoef(self_spectrum_common, other_spectrum_common)[0, 1]
                
                # Calculate mean squared error
                mse = np.mean((self_spectrum_common - other_spectrum_common) ** 2)
                
                results['spectrum_correlation'] = correlation
                results['spectrum_mse'] = mse
        
        # Compare time domain signals if available
        if (self.time_signal is not None and other.time_signal is not None):
            # Get statistics
            self_stats = self.get_time_domain_stats()
            other_stats = other.get_time_domain_stats()
            
            # Calculate differences in statistics
            for stat in ['rms', 'peak_to_peak', 'crest_factor', 'kurtosis']:
                diff = abs(self_stats[stat] - other_stats[stat])
                results[f'time_{stat}_diff'] = diff
        
        return results
    
    def add_metadata(self, key: str, value: Any) -> None:
        """
        Add metadata to the profile.
        
        Args:
            key: Metadata key
            value: Metadata value
        """
        self.metadata[key] = value


class VibrationProfileCollection:
    """
    Collection of vibration profiles for comparison and classification.
    
    This class provides functionality for managing multiple vibration profiles,
    including loading/saving collections, comparing profiles, and classification.
    """
    
    def __init__(self, name: str):
        """
        Initialize a vibration profile collection.
        
        Args:
            name: Collection name
        """
        self.name = name
        self.profiles = {}  # Dictionary of profile_id -> VibrationProfile
        self.metadata = {}
    
    def add_profile(self, profile: VibrationProfile) -> None:
        """
        Add a profile to the collection.
        
        Args:
            profile: VibrationProfile to add
        """
        self.profiles[profile.profile_id] = profile
    
    def remove_profile(self, profile_id: str) -> bool:
        """
        Remove a profile from the collection.
        
        Args:
            profile_id: ID of the profile to remove
            
        Returns:
            True if profile was removed, False if not found
        """
        if profile_id in self.profiles:
            del self.profiles[profile_id]
            return True
        return False
    
    def get_profile(self, profile_id: str) -> Optional[VibrationProfile]:
        """
        Get a profile by ID.
        
        Args:
            profile_id: ID of the profile to get
            
        Returns:
            VibrationProfile or None if not found
        """
        return self.profiles.get(profile_id)
    
    def get_profiles_by_name(self, name: str) -> List[VibrationProfile]:
        """
        Get profiles by name.
        
        Args:
            name: Name to search for
            
        Returns:
            List of VibrationProfile objects with matching name
        """
        return [p for p in self.profiles.values() if p.name == name]
    
    def compare_profiles(self, profile_id1: str, profile_id2: str) -> Dict[str, float]:
        """
        Compare two profiles in the collection.
        
        Args:
            profile_id1: ID of the first profile
            profile_id2: ID of the second profile
            
        Returns:
            Dictionary of comparison metrics
        """
        profile1 = self.get_profile(profile_id1)
        profile2 = self.get_profile(profile_id2)
        
        if profile1 is None or profile2 is None:
            return {}
        
        return profile1.compare_with(profile2)
    
    def find_similar_profiles(self, profile: VibrationProfile, 
                             threshold: float = 0.8, 
                             metric: str = 'spectrum_correlation',
                             max_results: int = 5) -> List[Tuple[VibrationProfile, float]]:
        """
        Find profiles similar to the given profile.
        
        Args:
            profile: Profile to compare with collection
            threshold: Similarity threshold
            metric: Metric to use for comparison
            max_results: Maximum number of results to return
            
        Returns:
            List of (profile, similarity) tuples sorted by similarity
        """
        results = []
        
        for coll_profile in self.profiles.values():
            # Skip comparing to self
            if coll_profile.profile_id == profile.profile_id:
                continue
            
            # Compare profiles
            comparison = profile.compare_with(coll_profile)
            
            # Skip if metric not available
            if metric not in comparison:
                continue
            
            similarity = comparison[metric]
            
            # Add to results if above threshold
            if metric == 'spectrum_correlation' and similarity >= threshold:
                results.append((coll_profile, similarity))
            elif metric == 'spectrum_mse' and similarity <= threshold:
                # For MSE, lower is better
                results.append((coll_profile, 1.0 / similarity))
            elif 'diff' in metric and similarity <= threshold:
                # For differences, lower is better
                results.append((coll_profile, 1.0 / similarity))
        
        # Sort by similarity (descending)
        results.sort(key=lambda x: x[1], reverse=True)
        
        # Return top results
        return results[:max_results]
    
    def save_to_directory(self, directory: str, save_profiles: bool = True) -> str:
        """
        Save the collection to a directory.
        
        Args:
            directory: Directory to save the collection to
            save_profiles: Whether to save individual profiles
            
        Returns:
            Path to the saved collection file
        """
        # Create directory if it doesn't exist
        os.makedirs(directory, exist_ok=True)
        
        # Create collection data
        collection_data = {
            'name': self.name,
            'metadata': self.metadata,
            'profiles': {}
        }
        
        # Add profile references
        for profile_id, profile in self.profiles.items():
            collection_data['profiles'][profile_id] = {
                'name': profile.name,
                'filename': f"{profile_id}.json" if save_profiles else None
            }
            
            # Save profile if requested
            if save_profiles:
                profile.save_to_file(directory)
        
        # Save collection file
        collection_file = os.path.join(directory, f"{self.name}_collection.json")
        with open(collection_file, 'w') as f:
            json.dump(collection_data, f, indent=2)
            
        return collection_file
    
    @classmethod
    def load_from_directory(cls, directory: str, collection_filename: Optional[str] = None,
                           load_profiles: bool = True) -> 'VibrationProfileCollection':
        """
        Load a collection from a directory.
        
        Args:
            directory: Directory to load from
            collection_filename: Collection file name, if None will try to find by extension
            load_profiles: Whether to load individual profiles
            
        Returns:
            Loaded VibrationProfileCollection
        """
        # Find collection file if not specified
        if collection_filename is None:
            # Find first file with _collection.json suffix
            for filename in os.listdir(directory):
                if filename.endswith('_collection.json'):
                    collection_filename = filename
                    break
            
            if collection_filename is None:
                raise FileNotFoundError("No collection file found in directory")
        
        # Load collection data
        collection_file = os.path.join(directory, collection_filename)
        with open(collection_file, 'r') as f:
            collection_data = json.load(f)
        
        # Create collection
        collection = cls(collection_data['name'])
        
        # Set metadata
        if 'metadata' in collection_data:
            collection.metadata = collection_data['metadata']
        
        # Load profiles if requested
        if load_profiles and 'profiles' in collection_data:
            for profile_id, profile_info in collection_data['profiles'].items():
                # Skip if no filename
                if not profile_info.get('filename'):
                    continue
                
                # Load profile
                profile_file = os.path.join(directory, profile_info['filename'])
                try:
                    profile = VibrationProfile.load_from_file(profile_file)
                    collection.add_profile(profile)
                except FileNotFoundError:
                    print(f"Warning: Profile file {profile_file} not found")
        
        return collection
