"""
Vibration visualization module.

This module provides specialized visualization tools for vibration data,
including interactive plots, 3D visualizations, and report-ready graphics.
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from mpl_toolkits.mplot3d import Axes3D
from typing import Tuple, List, Dict, Optional, Any, Union
import os
from datetime import datetime
import math

from envirosense.core.physics.coordinates import Vector3D
from envirosense.core.physics.vibration.base import VibrationSource
from envirosense.core.physics.vibration.profile import VibrationProfile
from envirosense.core.physics.vibration.propagation import SpatialPropagationModel


class VibrationVisualizer:
    """
    Create visualizations of vibration data for analysis and reporting.
    """
    
    def __init__(self, style: str = 'seaborn-v0_8-whitegrid'):
        """Initialize a vibration visualizer."""
        self.style = style
        self.configure()
        
        # Default output directory
        self.output_dir = os.path.join("envirosense", "output", "vibration_viz")
        os.makedirs(self.output_dir, exist_ok=True)
    
    def configure(self) -> None:
        """Configure matplotlib for better visualizations."""
        plt.style.use(self.style)
        plt.rcParams['figure.figsize'] = [12, 8]
        plt.rcParams['figure.dpi'] = 100
        plt.rcParams['axes.grid'] = True
        plt.rcParams['grid.alpha'] = 0.3
        plt.rcParams['font.size'] = 12
    
    def plot_spectrum(self, 
                     frequencies: np.ndarray,
                     spectrum: np.ndarray,
                     title: str = "Frequency Spectrum",
                     log_scale: bool = True,
                     show: bool = True,
                     save_path: Optional[str] = None) -> plt.Figure:
        """
        Plot a frequency spectrum.
        
        Args:
            frequencies: Array of frequency points (Hz)
            spectrum: Array of amplitude values
            title: Plot title
            log_scale: Whether to use logarithmic x-axis scale
            show: Whether to display the plot
            save_path: Optional path to save the plot image
            
        Returns:
            Matplotlib figure
        """
        fig, ax = plt.subplots(figsize=(10, 6))
        
        ax.plot(frequencies, spectrum)
        ax.set_xlabel("Frequency (Hz)")
        ax.set_ylabel("Amplitude")
        ax.set_title(title)
        
        if log_scale:
            ax.set_xscale('log')
            
        ax.grid(True)
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            
        if show:
            plt.show()
            
        return fig
        
    def plot_time_signal(self,
                        time_points: np.ndarray,
                        signal: np.ndarray,
                        title: str = "Time Domain Signal",
                        show: bool = True,
                        save_path: Optional[str] = None) -> plt.Figure:
        """
        Plot a time domain signal.
        
        Args:
            time_points: Array of time points (seconds)
            signal: Array of amplitude values
            title: Plot title
            show: Whether to display the plot
            save_path: Optional path to save the plot image
            
        Returns:
            Matplotlib figure
        """
        fig, ax = plt.subplots(figsize=(10, 6))
        
        ax.plot(time_points, signal)
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Amplitude")
        ax.set_title(title)
        ax.grid(True)
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            
        if show:
            plt.show()
            
        return fig
    
    def plot_source_comparison(self, 
                             sources: List[VibrationSource],
                             freq_range: Tuple[float, float, int],
                             title: str = "Source Comparison",
                             show: bool = True,
                             save_path: Optional[str] = None) -> plt.Figure:
        """
        Plot frequency spectra of multiple sources for comparison.
        
        Args:
            sources: List of VibrationSource objects
            freq_range: Tuple of (min_freq, max_freq, num_points)
            title: Plot title
            show: Whether to display the plot
            save_path: Optional path to save the plot image
            
        Returns:
            Matplotlib figure
        """
        fig, ax = plt.subplots(figsize=(12, 8))
        
        for source in sources:
            frequencies, spectrum = source.generate_spectrum(freq_range)
            ax.plot(frequencies, spectrum, label=source.name)
        
        ax.set_xlabel("Frequency (Hz)")
        ax.set_ylabel("Amplitude")
        ax.set_title(title)
        ax.set_xscale('log')
        ax.grid(True)
        ax.legend()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            
        if show:
            plt.show()
            
        return fig
    
    def plot_profile_comparison(self,
                              profiles: List[VibrationProfile],
                              title: str = "Profile Comparison",
                              show: bool = True,
                              save_path: Optional[str] = None) -> plt.Figure:
        """
        Plot comparison of multiple vibration profiles.
        
        Args:
            profiles: List of VibrationProfile objects
            title: Plot title
            show: Whether to display the plot
            save_path: Optional path to save the plot image
            
        Returns:
            Matplotlib figure
        """
        if not profiles:
            return None
            
        fig = plt.figure(figsize=(15, 10))
        gs = gridspec.GridSpec(2, 1, height_ratios=[2, 1])
        
        # Frequency domain plot
        ax1 = fig.add_subplot(gs[0])
        
        for profile in profiles:
            if profile.frequencies is not None and profile.spectrum is not None:
                ax1.plot(profile.frequencies, profile.spectrum, label=profile.name)
                
        ax1.set_xlabel("Frequency (Hz)")
        ax1.set_ylabel("Amplitude")
        ax1.set_title(f"{title} - Frequency Domain")
        ax1.set_xscale('log')
        ax1.grid(True)
        ax1.legend()
        
        # Time domain plot
        ax2 = fig.add_subplot(gs[1])
        
        for profile in profiles:
            if profile.time_points is not None and profile.time_signal is not None:
                ax2.plot(profile.time_points, profile.time_signal, label=profile.name)
                
        ax2.set_xlabel("Time (s)")
        ax2.set_ylabel("Amplitude")
        ax2.set_title(f"{title} - Time Domain")
        ax2.grid(True)
        ax2.legend()
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            
        if show:
            plt.show()
            
        return fig
    
    def plot_propagation_model(self,
                             model: SpatialPropagationModel,
                             source_pos: Tuple[float, float, float],
                             receivers: List[Tuple[float, float, float]],
                             title: str = "Spatial Propagation Model",
                             show: bool = True,
                             save_path: Optional[str] = None) -> plt.Figure:
        """
        Create a 3D visualization of a spatial propagation model.
        
        Args:
            model: SpatialPropagationModel object
            source_pos: Source position (x, y, z)
            receivers: List of receiver positions (x, y, z)
            title: Plot title
            show: Whether to display the plot
            save_path: Optional path to save the plot image
            
        Returns:
            Matplotlib figure
        """
        fig = plt.figure(figsize=(12, 10))
        ax = fig.add_subplot(111, projection='3d')
        
        # Plot regions
        for region_id, (bounding_box, material) in model.regions.items():
            min_point, max_point = bounding_box
            
            # Create wireframe for region
            x = [min_point[0], max_point[0], max_point[0], min_point[0], min_point[0],
                 min_point[0], max_point[0], max_point[0], min_point[0]]
            y = [min_point[1], min_point[1], max_point[1], max_point[1], min_point[1],
                 min_point[1], min_point[1], max_point[1], max_point[1]]
            z = [min_point[2], min_point[2], min_point[2], min_point[2], min_point[2],
                 max_point[2], max_point[2], max_point[2], max_point[2]]
            
            # Plot region with some transparency
            ax.plot_surface(
                np.array([
                    [min_point[0], max_point[0]],
                    [min_point[0], max_point[0]]
                ]),
                np.array([
                    [min_point[1], min_point[1]],
                    [max_point[1], max_point[1]]
                ]),
                np.array([
                    [min_point[2], min_point[2]],
                    [min_point[2], min_point[2]]
                ]),
                alpha=0.2
            )
            
            # Add a label
            center_x = (min_point[0] + max_point[0]) / 2
            center_y = (min_point[1] + max_point[1]) / 2
            center_z = (min_point[2] + max_point[2]) / 2
            ax.text(center_x, center_y, center_z, region_id, fontsize=8)
        
        # Plot source
        ax.scatter([source_pos[0]], [source_pos[1]], [source_pos[2]], 
                  color='red', s=100, marker='*', label='Source')
        
        # Plot receivers
        for i, pos in enumerate(receivers):
            ax.scatter([pos[0]], [pos[1]], [pos[2]], 
                      color='blue', s=50, marker='o', 
                      label=f'Receiver {i+1}' if i == 0 else "")
            
            # Add text label
            ax.text(pos[0] + 0.1, pos[1] + 0.1, pos[2] + 0.1, f"R{i+1}", fontsize=8)
            
        ax.set_xlabel('X (m)')
        ax.set_ylabel('Y (m)')
        ax.set_zlabel('Z (m)')
        ax.set_title(title)
        ax.legend()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            
        if show:
            plt.show()
            
        return fig
    
    def create_vibration_report(self,
                               profile: VibrationProfile,
                               output_dir: Optional[str] = None,
                               filename_prefix: str = "vibration_report") -> str:
        """
        Create a comprehensive report for a vibration profile.
        
        Args:
            profile: VibrationProfile to create report for
            output_dir: Directory to save report files
            filename_prefix: Prefix for output filenames
            
        Returns:
            Path to the main report file
        """
        if output_dir is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = os.path.join(self.output_dir, f"{filename_prefix}_{timestamp}")
            
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate plots
        spectrum_path = os.path.join(output_dir, f"{filename_prefix}_spectrum.png")
        time_path = os.path.join(output_dir, f"{filename_prefix}_time.png")
        spectrogram_path = os.path.join(output_dir, f"{filename_prefix}_spectrogram.png")
        
        # Create and save plots
        if profile.frequencies is not None and profile.spectrum is not None:
            self.plot_spectrum(
                profile.frequencies, 
                profile.spectrum,
                title=f"{profile.name} - Frequency Spectrum",
                show=False,
                save_path=spectrum_path
            )
            
        if profile.time_points is not None and profile.time_signal is not None:
            self.plot_time_signal(
                profile.time_points,
                profile.time_signal,
                title=f"{profile.name} - Time Signal",
                show=False,
                save_path=time_path
            )
            
            # Create spectrogram
            fig = plt.figure(figsize=(10, 6))
            times, frequencies, spectrogram = profile.compute_spectrogram()
            plt.pcolormesh(times, frequencies, 10 * np.log10(spectrogram), shading='gouraud')
            plt.colorbar(label='Power/Frequency (dB/Hz)')
            plt.title(f"{profile.name} - Spectrogram")
            plt.xlabel("Time (s)")
            plt.ylabel("Frequency (Hz)")
            plt.savefig(spectrogram_path, dpi=150, bbox_inches='tight')
            plt.close(fig)
        
        # Calculate statistics
        stats = profile.get_time_domain_stats()
        peak_freqs = profile.get_peak_frequencies(5)
        
        # Create a markdown report
        report_path = os.path.join(output_dir, f"{filename_prefix}.md")
        
        with open(report_path, 'w') as f:
            f.write(f"# Vibration Analysis Report: {profile.name}\n\n")
            f.write(f"**Profile ID:** {profile.profile_id}\n")
            f.write(f"**Created:** {profile.created_at}\n\n")
            
            f.write("## Profile Metadata\n\n")
            for key, value in profile.metadata.items():
                f.write(f"- **{key}:** {value}\n")
            f.write("\n")
            
            f.write("## Dominant Frequencies\n\n")
            f.write("| Frequency (Hz) | Amplitude |\n")
            f.write("|---------------|----------|\n")
            for freq, amp in peak_freqs:
                f.write(f"| {freq:.2f} | {amp:.6f} |\n")
            f.write("\n")
            
            f.write("## Time Domain Statistics\n\n")
            f.write(f"- **RMS Amplitude:** {stats['rms']:.6f}\n")
            f.write(f"- **Peak-to-Peak Amplitude:** {stats['peak_to_peak']:.6f}\n")
            f.write(f"- **Crest Factor:** {stats['crest_factor']:.6f}\n")
            f.write(f"- **Kurtosis:** {stats['kurtosis']:.6f}\n\n")
            
            f.write("## Visualizations\n\n")
            
            if profile.frequencies is not None and profile.spectrum is not None:
                f.write("### Frequency Spectrum\n\n")
                f.write(f"![Frequency Spectrum](./{os.path.basename(spectrum_path)})\n\n")
                
            if profile.time_points is not None and profile.time_signal is not None:
                f.write("### Time Domain Signal\n\n")
                f.write(f"![Time Domain Signal](./{os.path.basename(time_path)})\n\n")
                
                f.write("### Spectrogram\n\n")
                f.write(f"![Spectrogram](./{os.path.basename(spectrogram_path)})\n\n")
                
            f.write("## Analysis Summary\n\n")
            f.write("Based on the vibration profile analysis:\n\n")
            
            # Add some basic analysis based on the profile
            if 'condition' in profile.metadata:
                f.write(f"- Equipment condition is recorded as: **{profile.metadata['condition']}**\n")
                
            if peak_freqs:
                f.write(f"- The dominant vibration frequency is {peak_freqs[0][0]:.2f} Hz\n")
                
            # Add crest factor analysis
            if 'crest_factor' in stats:
                cf = stats['crest_factor']
                if cf < 1.5:
                    f.write("- Low crest factor suggests predominantly sinusoidal vibration\n")
                elif cf < 3.0:
                    f.write("- Moderate crest factor indicates some impulsive content\n")
                else:
                    f.write("- High crest factor indicates significant impulsive content\n")
                    
            # Add kurtosis analysis
            if 'kurtosis' in stats:
                k = stats['kurtosis']
                if k < 2.5:
                    f.write("- Low kurtosis indicates uniform vibration amplitude\n")
                elif k < 4.0:
                    f.write("- Normal kurtosis suggests expected vibration patterns\n")
                else:
                    f.write("- High kurtosis may indicate intermittent impacts or faults\n")
                    
        return report_path
