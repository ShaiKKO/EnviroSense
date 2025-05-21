"""
Vibration physics demonstration.

This module provides demonstration functions that showcase the capabilities
of the vibration physics system, including sources, propagation, and analysis.
"""

import numpy as np
import matplotlib.pyplot as plt
from typing import Tuple, List, Dict, Optional, Any, Union
import os
from datetime import datetime
import matplotlib.gridspec as gridspec
from mpl_toolkits.mplot3d import Axes3D
import math

from envirosense.core.physics.coordinates import Vector3D
from envirosense.core.physics.vibration.base import VibrationSource
from envirosense.core.physics.vibration.sources.transformer import TransformerVibration
from envirosense.core.physics.vibration.sources.motor import MotorVibration
from envirosense.core.physics.vibration.sources.generator import GeneratorVibration
from envirosense.core.physics.vibration.sources.compressor import CompressorVibration
from envirosense.core.physics.vibration.profile import VibrationProfile, VibrationProfileCollection
from envirosense.core.physics.vibration.propagation import (
    Material, COMMON_MATERIALS, VibrationPath, PropagationModel, SpatialPropagationModel
)


def configure_plotting():
    """Configure matplotlib for better visualizations."""
    plt.style.use('seaborn-v0_8-whitegrid')
    plt.rcParams['figure.figsize'] = [12, 8]
    plt.rcParams['figure.dpi'] = 100
    plt.rcParams['axes.grid'] = True
    plt.rcParams['grid.alpha'] = 0.3
    plt.rcParams['font.size'] = 12


def create_sample_source_collection() -> List[VibrationSource]:
    """
    Create a collection of sample vibration sources.
    
    Returns:
        List of various vibration sources
    """
    sources = []
    
    # Add transformer sources
    transformer_normal = TransformerVibration(
        name="Transformer 1MVA Normal",
        position=(0, 0, 0),
        power_rating=1e6,  # 1 MVA
        fundamental_freq=120.0,
        condition=TransformerVibration.CONDITION_NORMAL
    )
    
    transformer_overloaded = TransformerVibration(
        name="Transformer 1MVA Overloaded",
        position=(2, 0, 0),
        power_rating=1e6,  # 1 MVA
        fundamental_freq=120.0,
        condition=TransformerVibration.CONDITION_OVERLOADED
    )
    
    transformer_winding_issue = TransformerVibration(
        name="Transformer 1MVA Winding Issue",
        position=(4, 0, 0),
        power_rating=1e6,  # 1 MVA
        fundamental_freq=120.0,
        condition=TransformerVibration.CONDITION_WINDING_ISSUE
    )
    
    # Add motor sources
    motor_normal = MotorVibration(
        name="Motor 50kW Normal",
        position=(0, 2, 0),
        power_rating=50e3,  # 50 kW
        rpm=1800.0,
        condition=MotorVibration.CONDITION_NORMAL
    )
    
    motor_unbalanced = MotorVibration(
        name="Motor 50kW Unbalanced",
        position=(2, 2, 0),
        power_rating=50e3,  # 50 kW
        rpm=1800.0,
        condition=MotorVibration.CONDITION_UNBALANCED
    )
    
    motor_bearing = MotorVibration(
        name="Motor 50kW Bearing Wear",
        position=(4, 2, 0),
        power_rating=50e3,  # 50 kW
        rpm=1800.0,
        condition=MotorVibration.CONDITION_BEARING_WEAR
    )
    
    # Add generator sources
    generator_normal = GeneratorVibration(
        name="Diesel Generator Normal",
        position=(0, 4, 0),
        power_rating=200e3,  # 200 kVA
        rpm=1800.0,
        fuel_type=GeneratorVibration.FUEL_DIESEL,
        condition=GeneratorVibration.CONDITION_NORMAL
    )
    
    generator_misaligned = GeneratorVibration(
        name="Diesel Generator Misaligned",
        position=(2, 4, 0),
        power_rating=200e3,  # 200 kVA
        rpm=1800.0,
        fuel_type=GeneratorVibration.FUEL_DIESEL,
        condition=GeneratorVibration.CONDITION_MISALIGNED
    )
    
    generator_fuel_issue = GeneratorVibration(
        name="Diesel Generator Fuel System Issue",
        position=(4, 4, 0),
        power_rating=200e3,  # 200 kVA
        rpm=1800.0,
        fuel_type=GeneratorVibration.FUEL_DIESEL,
        condition=GeneratorVibration.CONDITION_FUEL_SYSTEM
    )
    
    # Add compressor sources
    compressor_normal = CompressorVibration(
        name="Rotary Screw Compressor Normal",
        position=(0, 6, 0),
        power_rating=75e3,  # 75 kW
        rotation_speed=3600.0,
        comp_type=CompressorVibration.TYPE_ROTARY_SCREW,
        condition=CompressorVibration.CONDITION_NORMAL
    )
    
    compressor_bearing = CompressorVibration(
        name="Rotary Screw Compressor Bearing Fault",
        position=(2, 6, 0),
        power_rating=75e3,  # 75 kW
        rotation_speed=3600.0,
        comp_type=CompressorVibration.TYPE_ROTARY_SCREW,
        condition=CompressorVibration.CONDITION_BEARING_FAULT
    )
    
    # Add all sources to the list
    sources.extend([
        transformer_normal, transformer_overloaded, transformer_winding_issue,
        motor_normal, motor_unbalanced, motor_bearing,
        generator_normal, generator_misaligned, generator_fuel_issue,
        compressor_normal, compressor_bearing
    ])
    
    return sources


def demonstrate_source_spectra(save_dir: Optional[str] = None) -> None:
    """
    Demonstrate vibration spectra for different sources.
    
    Args:
        save_dir: Optional directory to save plots
    """
    configure_plotting()
    sources = create_sample_source_collection()
    
    # Define frequency range for analysis
    freq_range = (1.0, 1000.0, 1000)  # min_freq, max_freq, num_points
    
    # Create figure for comparison
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    axes = axes.flatten()
    
    # Plot spectra for different source types
    source_types = {
        "Transformer": [s for s in sources if isinstance(s, TransformerVibration)],
        "Motor": [s for s in sources if isinstance(s, MotorVibration)],
        "Generator": [s for s in sources if isinstance(s, GeneratorVibration)],
        "Compressor": [s for s in sources if isinstance(s, CompressorVibration)]
    }
    
    for i, (source_type, type_sources) in enumerate(source_types.items()):
        ax = axes[i]
        
        for source in type_sources:
            frequencies, spectrum = source.generate_spectrum(freq_range)
            ax.plot(frequencies, spectrum, label=source.name)
        
        ax.set_title(f"{source_type} Vibration Spectra")
        ax.set_xlabel("Frequency (Hz)")
        ax.set_ylabel("Amplitude")
        ax.set_xscale('log')
        ax.legend()
    
    plt.tight_layout()
    
    if save_dir:
        os.makedirs(save_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(save_dir, f"source_spectra_comparison_{timestamp}.png")
        plt.savefig(filename, dpi=150)
        print(f"Saved source spectra comparison to {filename}")
    else:
        plt.show()
    
    # Create detailed individual plots
    for source in sources[:4]:  # Just show first 4 to avoid too many plots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # Generate and plot frequency spectrum
        frequencies, spectrum = source.generate_spectrum(freq_range)
        ax1.plot(frequencies, spectrum)
        ax1.set_title(f"{source.name} - Frequency Spectrum")
        ax1.set_xlabel("Frequency (Hz)")
        ax1.set_ylabel("Amplitude")
        ax1.set_xscale('log')
        
        # Generate and plot time domain signal
        time_points, signal = source.generate_time_signal(duration=0.5, sample_rate=5000)
        ax2.plot(time_points, signal)
        ax2.set_title(f"{source.name} - Time Domain Signal")
        ax2.set_xlabel("Time (s)")
        ax2.set_ylabel("Amplitude")
        
        plt.tight_layout()
        
        if save_dir:
            filename = os.path.join(save_dir, f"source_detail_{source.name.replace(' ', '_')}_{timestamp}.png")
            plt.savefig(filename, dpi=150)
            print(f"Saved source detail to {filename}")
        else:
            plt.show()


def demonstrate_vibration_profiles(save_dir: Optional[str] = None) -> None:
    """
    Demonstrate vibration profiles for different sources.
    
    Args:
        save_dir: Optional directory to save plots
    """
    configure_plotting()
    sources = create_sample_source_collection()
    
    # Define frequency range for analysis
    freq_range = (1.0, 1000.0, 1000)  # min_freq, max_freq, num_points
    
    # Create profiles from sources
    profiles = []
    for source in sources[:6]:  # Use a subset of sources
        # Generate spectrum
        frequencies, spectrum = source.generate_spectrum(freq_range)
        
        # Generate time signal
        time_points, signal = source.generate_time_signal(duration=1.0, sample_rate=5000)
        
        # Create profile
        profile = VibrationProfile(
            name=source.name,
            frequencies=frequencies,
            spectrum=spectrum,
            time_points=time_points,
            time_signal=signal
        )
        
        # Add source metadata
        for key, value in source.metadata.items():
            profile.add_metadata(key, value)
        
        profiles.append(profile)
    
    # Create a profile collection
    collection = VibrationProfileCollection("Demo Equipment Profiles")
    for profile in profiles:
        collection.add_profile(profile)
    
    # Save collection if directory provided
    if save_dir:
        os.makedirs(save_dir, exist_ok=True)
        collection_dir = os.path.join(save_dir, "vibration_profiles")
        collection.save_to_directory(collection_dir)
        print(f"Saved profile collection to {collection_dir}")
    
    # Demonstrate profile analysis and visualization
    # Pick a couple of profiles for detailed analysis
    normal_transformer = profiles[0]  # Should be the normal transformer
    faulty_transformer = profiles[1]  # Should be the overloaded transformer
    
    # Compare the profiles
    comparison = normal_transformer.compare_with(faulty_transformer)
    
    # Create visualization
    fig = plt.figure(figsize=(15, 10))
    gs = gridspec.GridSpec(2, 2)
    
    # Plot frequency spectra
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.plot(normal_transformer.frequencies, normal_transformer.spectrum, 
             label=normal_transformer.name)
    ax1.plot(faulty_transformer.frequencies, faulty_transformer.spectrum, 
             label=faulty_transformer.name)
    ax1.set_title("Frequency Spectra Comparison")
    ax1.set_xlabel("Frequency (Hz)")
    ax1.set_ylabel("Amplitude")
    ax1.set_xscale('log')
    ax1.legend()
    
    # Plot time signals
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.plot(normal_transformer.time_points, normal_transformer.time_signal, 
             label=normal_transformer.name)
    ax2.plot(faulty_transformer.time_points, faulty_transformer.time_signal, 
             label=faulty_transformer.name)
    ax2.set_title("Time Domain Signal Comparison")
    ax2.set_xlabel("Time (s)")
    ax2.set_ylabel("Amplitude")
    ax2.legend()
    
    # Plot spectrograms side by side
    ax3 = fig.add_subplot(gs[1, 0])
    times, frequencies, spectrogram = normal_transformer.compute_spectrogram()
    pcm = ax3.pcolormesh(times, frequencies, 10 * np.log10(spectrogram), shading='gouraud')
    fig.colorbar(pcm, ax=ax3, label='Power/Frequency (dB/Hz)')
    ax3.set_title(f"{normal_transformer.name} - Spectrogram")
    ax3.set_xlabel("Time (s)")
    ax3.set_ylabel("Frequency (Hz)")
    
    ax4 = fig.add_subplot(gs[1, 1])
    times, frequencies, spectrogram = faulty_transformer.compute_spectrogram()
    pcm = ax4.pcolormesh(times, frequencies, 10 * np.log10(spectrogram), shading='gouraud')
    fig.colorbar(pcm, ax=ax4, label='Power/Frequency (dB/Hz)')
    ax4.set_title(f"{faulty_transformer.name} - Spectrogram")
    ax4.set_xlabel("Time (s)")
    ax4.set_ylabel("Frequency (Hz)")
    
    plt.tight_layout()
    
    if save_dir:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(save_dir, f"profile_analysis_{timestamp}.png")
        plt.savefig(filename, dpi=150)
        print(f"Saved profile analysis to {filename}")
    else:
        plt.show()
    
    # Display comparison metrics
    print("\nProfile Comparison Metrics:")
    for metric, value in comparison.items():
        print(f"  {metric}: {value:.6f}")


def demonstrate_vibration_propagation(save_dir: Optional[str] = None) -> None:
    """
    Demonstrate vibration propagation through different materials.
    
    Args:
        save_dir: Optional directory to save plots
    """
    configure_plotting()
    
    # Create a simple propagation model
    model = PropagationModel("Demo Propagation Model")
    
    # Create source (transformer)
    transformer = TransformerVibration(
        name="Transformer 5MVA",
        position=(0, 0, 0),
        power_rating=5e6,  # 5 MVA
        fundamental_freq=120.0,
        condition=TransformerVibration.CONDITION_NORMAL
    )
    
    # Create paths through different materials
    materials = {
        "concrete": COMMON_MATERIALS["concrete"],
        "steel": COMMON_MATERIALS["steel"],
        "soil": COMMON_MATERIALS["soil"],
        "rubber": COMMON_MATERIALS["rubber"]
    }
    
    paths = {}
    for material_name, material in materials.items():
        # Create a 10m path through this material
        path = model.create_simple_path(
            path_id=material_name,
            distance=10.0,
            material=material,
            name=f"10m {material_name} path"
        )
        paths[material_name] = path
    
    # Generate source spectrum
    freq_range = (1.0, 1000.0, 1000)
    frequencies, source_spectrum = transformer.generate_spectrum(freq_range)
    
    # Apply propagation for each path
    propagation_results = model.apply_propagation(frequencies, source_spectrum)
    
    # Plot the results
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    axes = axes.flatten()
    
    # Plot frequency response for each material
    for i, (material_name, (freq, spectrum)) in enumerate(propagation_results.items()):
        ax = axes[i]
        
        # Plot source spectrum
        ax.plot(frequencies, source_spectrum, label="Source", alpha=0.7)
        
        # Plot propagated spectrum
        ax.plot(freq, spectrum, label=f"After 10m in {material_name}", linewidth=2)
        
        ax.set_title(f"Vibration Propagation Through {material_name.capitalize()}")
        ax.set_xlabel("Frequency (Hz)")
        ax.set_ylabel("Amplitude")
        ax.set_xscale('log')
        ax.legend()
    
    plt.tight_layout()
    
    if save_dir:
        os.makedirs(save_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(save_dir, f"vibration_propagation_{timestamp}.png")
        plt.savefig(filename, dpi=150)
        print(f"Saved vibration propagation to {filename}")
    else:
        plt.show()
    
    # Demonstrate more complex propagation through multiple materials
    # Create a path with multiple segments
    model.create_multi_segment_path(
        path_id="complex_path",
        segments=[
            (5.0, COMMON_MATERIALS["concrete"]),  # 5m of concrete
            (10.0, COMMON_MATERIALS["soil"]),     # 10m of soil
            (3.0, COMMON_MATERIALS["steel"])      # 3m of steel
        ],
        name="Complex propagation path"
    )
    
    # Compare frequency response of different paths
    path_ids = ["concrete", "complex_path"]
    frequencies, combined_response = model.calculate_combined_response(path_ids, freq_range)
    
    plt.figure(figsize=(10, 6))
    plt.plot(frequencies, source_spectrum, label="Source", alpha=0.7)
    
    for path_id in path_ids:
        freq, response = propagation_results.get(path_id, (None, None))
        if freq is not None:
            plt.plot(freq, response, label=f"Path: {path_id}", linewidth=2)
    
    plt.title("Comparison of Vibration Paths")
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("Amplitude")
    plt.xscale('log')
    plt.legend()
    plt.grid(True)
    
    if save_dir:
        filename = os.path.join(save_dir, f"complex_propagation_{timestamp}.png")
        plt.savefig(filename, dpi=150)
        print(f"Saved complex propagation to {filename}")
    else:
        plt.show()


def demonstrate_spatial_propagation(save_dir: Optional[str] = None) -> None:
    """
    Demonstrate spatial vibration propagation in a room-like environment.
    
    Args:
        save_dir: Optional directory to save plots
    """
    configure_plotting()
    
    # Create a spatial propagation model
    model = SpatialPropagationModel("Room Environment")
    
    # Define room dimensions
    room_width = 10.0
    room_length = 15.0
    room_height = 3.0
    
    # Add regions (walls, floor, ceiling, objects)
    # Floor (concrete)
    model.add_region(
        "floor",
        ((0, 0, -0.2), (room_width, room_length, 0)),
        COMMON_MATERIALS["concrete"]
    )
    
    # Ceiling (concrete)
    model.add_region(
        "ceiling",
        ((0, 0, room_height), (room_width, room_length, room_height + 0.2)),
        COMMON_MATERIALS["concrete"]
    )
    
    # Walls (concrete)
    model.add_region(
        "wall_x1",
        ((-0.2, 0, 0), (0, room_length, room_height)),
        COMMON_MATERIALS["concrete"]
    )
    model.add_region(
        "wall_x2",
        ((room_width, 0, 0), (room_width + 0.2, room_length, room_height)),
        COMMON_MATERIALS["concrete"]
    )
    model.add_region(
        "wall_y1",
        ((0, -0.2, 0), (room_width, 0, room_height)),
        COMMON_MATERIALS["concrete"]
    )
    model.add_region(
        "wall_y2",
        ((0, room_length, 0), (room_width, room_length + 0.2, room_height)),
        COMMON_MATERIALS["concrete"]
    )
    
    # Add a steel machine base in the room
    model.add_region(
        "machine_base",
        ((3, 5, 0), (6, 7, 0.5)),
        COMMON_MATERIALS["steel"]
    )
    
    # Add a vibration isolation pad (rubber)
    model.add_region(
        "isolation_pad",
        ((3.2, 5.2, 0.5), (5.8, 6.8, 0.6)),
        COMMON_MATERIALS["rubber"]
    )
    
    # Create a source (motor) on the isolation pad
    motor_position = (4.5, 6.0, 0.6)
    motor = MotorVibration(
        name="Motor 100kW",
        position=motor_position,
        power_rating=100e3,  # 100 kW
        rpm=1800.0,
        condition=MotorVibration.CONDITION_NORMAL
    )
    
    # Define receiver positions throughout the room
    receiver_positions = [
        (4.5, 6.0, 1.5),   # Directly above motor, 0.9m up
        (8.0, 6.0, 1.5),   # 3.5m to the right of motor
        (4.5, 12.0, 1.5),  # 6m to the front of motor
        (1.0, 1.0, 1.5)    # Far corner of room
    ]
    
    # Generate source spectrum
    freq_range = (1.0, 1000.0, 500)
    frequencies, source_spectrum = motor.generate_spectrum(freq_range)
    
    # Calculate spatial response
    responses = model.calculate_spatial_response(
        source_pos=motor_position,
        receiver_positions=receiver_positions,
        freq_range=freq_range,
        num_segments=20
    )
    
    # Create a 3D plot of the room and source/receivers
    fig = plt.figure(figsize=(15, 10))
    gs = gridspec.GridSpec(2, 2, height_ratios=[2, 1])
    
    # 3D plot of room
    ax1 = fig.add_subplot(gs[0, :], projection='3d')
    
    # Plot room boundaries as a wireframe
    x = np.array([0, room_width, room_width, 0, 0, room_width, room_width, 0])
    y = np.array([0, 0, room_length, room_length, 0, 0, room_length, room_length])
    z = np.array([0, 0, 0, 0, room_height, room_height, room_height, room_height])
    
    # Plot the room edges
    for i, j in [(0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4), (0, 4), (1, 5), (2, 6), (3, 7)]:
        ax1.plot([x[i], x[j]], [y[i], y[j]], [z[i], z[j]], 'k-', alpha=0.5)
    
    # Plot machine base and isolation pad
    x_base = np.array([3, 6, 6, 3, 3])
    y_base = np.array([5, 5, 7, 7, 5])
    z_base = np.array([0.5, 0.5, 0.5, 0.5, 0.5])
    ax1.plot(x_base, y_base, z_base, 'b-', linewidth=2, label="Machine Base")
    
    x_pad = np.array([3.2, 5.8, 5.8, 3.2, 3.2])
    y_pad = np.array([5.2, 5.2, 6.8, 6.8, 5.2])
    z_pad = np.array([0.6, 0.6, 0.6, 0.6, 0.6])
    ax1.plot(x_pad, y_pad, z_pad, 'g-', linewidth=2, label="Isolation Pad")
    
    # Plot source and receivers
    ax1.scatter([motor_position[0]], [motor_position[1]], [motor_position[2]], 
                color='red', s=100, marker='*', label="Vibration Source (Motor)")
    
    for i, pos in enumerate(receiver_positions):
        ax1.scatter([pos[0]], [pos[1]], [pos[2]], 
                   color='blue', s=80, marker='o', label=f"Receiver {i+1}" if i == 0 else "")
        
        # Add text label
        ax1.text(pos[0], pos[1], pos[2] + 0.2, f"R{i+1}", fontsize=12)
    
    ax1.set_xlabel('X (m)')
    ax1.set_ylabel('Y (m)')
    ax1.set_zlabel('Z (m)')
    ax1.set_title('3D Room Environment with Vibration Source and Receivers')
    ax1.legend()
    
    # Plot frequency responses
    ax2 = fig.add_subplot(gs[1, 0])
    ax2.plot(frequencies, source_spectrum, 'k-', label="Source", alpha=0.7)
    
    for i, (freq, resp) in responses.items():
        ax2.plot(freq, resp, label=f"Receiver {i+1}")
    
    ax2.set_title("Vibration Amplitude vs. Frequency")
    ax2.set_xlabel("Frequency (Hz)")
    ax2.set_ylabel("Amplitude")
    ax2.set_xscale('log')
    ax2.legend()
    
    # Plot attenuation vs distance
    ax3 = fig.add_subplot(gs[1, 1])
    
    # Calculate distance from source to each receiver
    source_vec = Vector3D(*motor_position)
    distances = [source_vec.distance_to(Vector3D(*pos)) for pos in receiver_positions]
    
    # Calculate total attenuation at 120 Hz (example frequency)
    freq_idx = np.argmin(np.abs(frequencies - 120))
    attenuations = [resp[freq_idx] / source_spectrum[freq_idx] for _, resp in responses.items()]
    
    # Plot distance vs attenuation
    ax3.scatter(distances, attenuations, s=80)
    ax3.plot(distances, attenuations, 'b--')
    
    for i, (dist, atten) in enumerate(zip(distances, attenuations)):
        ax3.annotate(f"R{i+1}", (dist, atten), fontsize=12)
    
    ax3.set_title("Attenuation vs. Distance (at 120 Hz)")
    ax3.set_xlabel("Distance from Source (m)")
    ax3.set_ylabel("Amplitude Ratio")
    ax3.grid(True)
    
    plt.tight_layout()
    
    if save_dir:
        os.makedirs(save_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(save_dir, f"spatial_propagation_{timestamp}.png")
        plt.savefig(filename, dpi=150)
        print(f"Saved spatial propagation to {filename}")
    else:
        plt.show()


def run_complete_demo(save_dir: Optional[str] = None) -> None:
    """
    Run all demonstration functions.
    
    Args:
        save_dir: Optional directory to save output files
    """
    if save_dir:
        os.makedirs(save_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        demo_dir = os.path.join(save_dir, f"vibration_demo_{timestamp}")
        os.makedirs(demo_dir, exist_ok=True)
    else:
        demo_dir = None
    
    print("\n=== Demonstrating Source Spectra ===")
    demonstrate_source_spectra(demo_dir)
    
    print("\n=== Demonstrating Vibration Profiles ===")
    demonstrate_vibration_profiles(demo_dir)
    
    print("\n=== Demonstrating Vibration Propagation ===")
    demonstrate_vibration_propagation(demo_dir)
    
    print("\n=== Demonstrating Spatial Propagation ===")
    demonstrate_spatial_propagation(demo_dir)
    
    if demo_dir:
        print(f"\nAll demonstration outputs have been saved to: {demo_dir}")


if __name__ == "__main__":
    output_dir = os.path.join("envirosense", "output", "vibration_demo")
    run_complete_demo(output_dir)
