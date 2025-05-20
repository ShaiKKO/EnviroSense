"""
Spatial environment generators for EnviroSense testing.

This module provides generators for spatial distribution and propagation of environmental 
parameters in 3D space. These generators create realistic spatial patterns based on 
physical models for diffusion, advection, and other physical processes.
"""

import datetime
import math
import numpy as np
from typing import Any, Dict, List, Optional, Tuple, Union
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from mpl_toolkits.mplot3d import Axes3D
from scipy.ndimage import gaussian_filter

from envirosense.testing.framework import DataGenerator, TestScenario
from envirosense.testing.generators.environmental.parameter_generator import (
    PARAMETER_DEFINITIONS, EnvironmentalParameterGenerator
)


class SpatialEnvironmentGenerator(DataGenerator):
    """
    Generator for spatial distributions of environmental parameters.
    
    This generator creates realistic 3D spatial distributions of environmental parameters, 
    accounting for sources, barriers, diffusion, advection (airflow), and other physical 
    processes. It can be used to simulate how parameters like temperature, gas concentrations,
    or particulates spread through space over time.
    """
    
    def __init__(self):
        """Initialize the spatial environment generator with default parameters."""
        super().__init__()
        
        # Set default parameters
        self.parameters.update({
            'parameter_type': 'temperature',    # The environmental parameter to model
            'grid_size': (10, 10, 3),           # Size of the 3D grid (x, y, z) in meters
            'grid_resolution': 0.2,             # Resolution of the grid in meters
            'simulation_time': 3600,            # Simulation time in seconds
            'time_step': 10,                    # Time step in seconds
            'sources': [],                      # List of emission sources in the environment
            'barriers': [],                     # List of barriers/walls in the environment
            'initial_conditions': None,         # Initial conditions (uniform or spatially varying)
            'boundary_conditions': 'dirichlet', # Type of boundary conditions
            'diffusion_coefficient': None,      # Diffusion coefficient (parameter-specific if None)
            'advection_field': None,            # Vector field for advection/airflow
            'decay_rate': 0.0,                  # Decay rate for the parameter
            'random_seed': None,                # Seed for reproducibility
            'visualize': False,                 # Whether to visualize the results
            'visualization_slice': 'xy',        # Slice to visualize (xy, xz, yz)
            'visualization_slice_index': None,  # Index of the slice (middle if None)
            'output_full_grid': False           # Whether to output the full grid data
        })
        
        # Parameter-specific defaults
        self.parameter_defaults = {
            'temperature': {
                'diffusion_coefficient': 0.02,  # m²/s (thermal diffusivity in air)
                'decay_rate': 0.0,              # No natural decay for temperature
                'boundary_conditions': 'neumann' # No flow boundary at walls is often used
            },
            'co2': {
                'diffusion_coefficient': 0.16e-4, # m²/s
                'decay_rate': 0.0,               # CO2 is stable
                'boundary_conditions': 'neumann'  # No flow boundary at walls
            },
            'tvoc': {
                'diffusion_coefficient': 0.08e-4, # m²/s (depends on specific VOC)
                'decay_rate': 0.05,              # Some VOCs decay over time
                'boundary_conditions': 'neumann'  # No flow boundary at walls
            },
            'pm2_5': {
                'diffusion_coefficient': 0.05e-4, # m²/s
                'decay_rate': 0.02,              # Some particles settle out
                'boundary_conditions': 'neumann'  # No flow boundary at walls
            },
            'pm10': {
                'diffusion_coefficient': 0.1e-4,  # m²/s
                'decay_rate': 0.05,              # Larger particles settle faster
                'boundary_conditions': 'neumann'  # No flow boundary at walls
            },
            'ozone': {
                'diffusion_coefficient': 0.14e-4, # m²/s
                'decay_rate': 0.1,               # Ozone decays relatively quickly indoors
                'boundary_conditions': 'neumann'  # No flow boundary at walls
            },
            'no2': {
                'diffusion_coefficient': 0.14e-4, # m²/s
                'decay_rate': 0.05,              # NO2 decays indoors
                'boundary_conditions': 'neumann'  # No flow boundary at walls
            },
            'humidity': {
                'diffusion_coefficient': 0.24e-4, # m²/s (water vapor in air)
                'decay_rate': 0.0,               # Humidity doesn't decay
                'boundary_conditions': 'neumann'  # No flow boundary at walls
            }
        }
    
    def _setup_grid(self) -> Tuple[np.ndarray, Tuple[np.ndarray, np.ndarray, np.ndarray]]:
        """
        Set up the computational grid.
        
        Returns:
            Tuple of (grid, (x_coords, y_coords, z_coords))
        """
        # Get grid parameters
        grid_size = self.parameters['grid_size']
        resolution = self.parameters['grid_resolution']
        
        # Calculate number of cells in each dimension
        nx = int(grid_size[0] / resolution)
        ny = int(grid_size[1] / resolution)
        nz = int(grid_size[2] / resolution)
        
        # Create empty grid
        grid = np.zeros((nx, ny, nz))
        
        # Create coordinate arrays
        x_coords = np.linspace(0, grid_size[0], nx)
        y_coords = np.linspace(0, grid_size[1], ny)
        z_coords = np.linspace(0, grid_size[2], nz)
        
        return grid, (x_coords, y_coords, z_coords)
    
    def _initialize_grid(self, grid: np.ndarray, 
                        coords: Tuple[np.ndarray, np.ndarray, np.ndarray]) -> np.ndarray:
        """
        Initialize the grid with initial conditions.
        
        Args:
            grid: The grid to initialize
            coords: Tuple of coordinate arrays (x, y, z)
            
        Returns:
            Initialized grid
        """
        initial_conditions = self.parameters['initial_conditions']
        
        if initial_conditions is None:
            # Use ambient values for the parameter type from PARAMETER_DEFINITIONS
            param_type = self.parameters['parameter_type']
            if param_type in PARAMETER_DEFINITIONS:
                param_def = PARAMETER_DEFINITIONS[param_type]
                if 'typical_indoor_range' in param_def:
                    min_val, max_val = param_def['typical_indoor_range']
                    ambient_value = min_val + (max_val - min_val) * 0.5
                else:
                    min_val, max_val = param_def['default_range']
                    ambient_value = min_val + (max_val - min_val) * 0.5
            else:
                ambient_value = 20.0  # Default value if parameter not found
            
            # Set uniform initial condition
            grid.fill(ambient_value)
        
        elif isinstance(initial_conditions, (int, float)):
            # Uniform initial value
            grid.fill(initial_conditions)
        
        elif isinstance(initial_conditions, dict):
            # Spatial function or pattern
            if 'type' in initial_conditions:
                if initial_conditions['type'] == 'gaussian':
                    # Gaussian distribution centered at a point
                    center = initial_conditions.get('center', 
                                                  (grid.shape[0]//2, grid.shape[1]//2, grid.shape[2]//2))
                    sigma = initial_conditions.get('sigma', 
                                                 (grid.shape[0]//5, grid.shape[1]//5, grid.shape[2]//5))
                    amplitude = initial_conditions.get('amplitude', 1.0)
                    background = initial_conditions.get('background', 0.0)
                    
                    x_coords, y_coords, z_coords = coords
                    
                    for i in range(grid.shape[0]):
                        for j in range(grid.shape[1]):
                            for k in range(grid.shape[2]):
                                dx = (i - center[0]) / sigma[0]
                                dy = (j - center[1]) / sigma[1]
                                dz = (k - center[2]) / sigma[2]
                                r2 = dx*dx + dy*dy + dz*dz
                                grid[i, j, k] = background + amplitude * math.exp(-0.5 * r2)
                
                elif initial_conditions['type'] == 'gradient':
                    # Linear gradient along a direction
                    direction = initial_conditions.get('direction', 'x')
                    min_val = initial_conditions.get('min_value', 0.0)
                    max_val = initial_conditions.get('max_value', 1.0)
                    
                    if direction == 'x':
                        for i in range(grid.shape[0]):
                            val = min_val + (max_val - min_val) * i / (grid.shape[0] - 1)
                            grid[i, :, :] = val
                    elif direction == 'y':
                        for j in range(grid.shape[1]):
                            val = min_val + (max_val - min_val) * j / (grid.shape[1] - 1)
                            grid[:, j, :] = val
                    elif direction == 'z':
                        for k in range(grid.shape[2]):
                            val = min_val + (max_val - min_val) * k / (grid.shape[2] - 1)
                            grid[:, :, k] = val
                
                elif initial_conditions['type'] == 'layered':
                    # Stratified/layered distribution (common in air)
                    layer_values = initial_conditions.get('layer_values', [])
                    layer_heights = initial_conditions.get('layer_heights', [])
                    
                    if len(layer_values) != len(layer_heights) + 1:
                        raise ValueError("layer_values should have exactly one more element than layer_heights")
                    
                    # Convert relative heights to actual indices
                    height_indices = [int(h * grid.shape[2]) for h in layer_heights]
                    
                    # Fill each layer
                    for i, value in enumerate(layer_values):
                        if i == 0:
                            # First layer
                            grid[:, :, :height_indices[0]] = value
                        elif i == len(layer_values) - 1:
                            # Last layer
                            grid[:, :, height_indices[-1]:] = value
                        else:
                            # Middle layers
                            grid[:, :, height_indices[i-1]:height_indices[i]] = value
        
        elif isinstance(initial_conditions, np.ndarray):
            # Direct grid assignment
            if initial_conditions.shape == grid.shape:
                grid = initial_conditions.copy()
            else:
                raise ValueError("Initial conditions array shape must match grid shape")
        
        # Add random noise if specified
        noise_level = self.parameters.get('initial_noise_level', 0.0)
        if noise_level > 0:
            grid += self.rng.normal(0, noise_level, grid.shape)
        
        return grid
    
    def _apply_boundary_conditions(self, grid: np.ndarray) -> np.ndarray:
        """
        Apply boundary conditions to the grid.
        
        Args:
            grid: The current grid values
            
        Returns:
            Grid with boundary conditions applied
        """
        boundary_type = self.parameters['boundary_conditions']
        
        # Dirichlet boundary conditions (fixed value at boundary)
        if boundary_type == 'dirichlet':
            boundary_value = self.parameters.get('boundary_value', 0.0)
            
            # Set boundary values
            grid[0, :, :] = boundary_value
            grid[-1, :, :] = boundary_value
            grid[:, 0, :] = boundary_value
            grid[:, -1, :] = boundary_value
            grid[:, :, 0] = boundary_value
            grid[:, :, -1] = boundary_value
        
        # Neumann boundary conditions (zero gradient at boundary)
        elif boundary_type == 'neumann':
            # Implement using central differences with ghost cells
            grid[0, :, :] = grid[1, :, :]
            grid[-1, :, :] = grid[-2, :, :]
            grid[:, 0, :] = grid[:, 1, :]
            grid[:, -1, :] = grid[:, -2, :]
            grid[:, :, 0] = grid[:, :, 1]
            grid[:, :, -1] = grid[:, :, -2]
        
        # Periodic boundary conditions (wrap around)
        elif boundary_type == 'periodic':
            # Copy values from opposite boundaries
            grid[0, :, :] = grid[-2, :, :]
            grid[-1, :, :] = grid[1, :, :]
            grid[:, 0, :] = grid[:, -2, :]
            grid[:, -1, :] = grid[:, 1, :]
            grid[:, :, 0] = grid[:, :, -2]
            grid[:, :, -1] = grid[:, :, 1]
        
        return grid
    
    def _apply_sources(self, grid: np.ndarray, dt: float) -> np.ndarray:
        """
        Apply sources to the grid.
        
        Args:
            grid: The current grid values
            dt: Time step in seconds
            
        Returns:
            Grid with sources applied
        """
        sources = self.parameters['sources']
        
        for source in sources:
            if not source.get('active', True):
                continue
                
            source_type = source.get('type', 'point')
            strength = source.get('strength', 1.0)  # Units per second
            location = source.get('location', (0, 0, 0))
            
            # Convert physical location to grid indices
            resolution = self.parameters['grid_resolution']
            ix = int(location[0] / resolution)
            iy = int(location[1] / resolution)
            iz = int(location[2] / resolution)
            
            # Ensure indices are within grid
            ix = max(0, min(ix, grid.shape[0] - 1))
            iy = max(0, min(iy, grid.shape[1] - 1))
            iz = max(0, min(iz, grid.shape[2] - 1))
            
            # Apply source based on type
            if source_type == 'point':
                # Point source at a single grid cell
                grid[ix, iy, iz] += strength * dt
            
            elif source_type == 'gaussian':
                # Gaussian source spread over multiple cells
                sigma = source.get('sigma', (0.5, 0.5, 0.5))  # meters
                
                # Convert physical sigma to grid indices
                sigma_x = max(1, int(sigma[0] / resolution))
                sigma_y = max(1, int(sigma[1] / resolution))
                sigma_z = max(1, int(sigma[2] / resolution))
                
                # Define region to update
                x_min = max(0, ix - 3*sigma_x)
                x_max = min(grid.shape[0], ix + 3*sigma_x + 1)
                y_min = max(0, iy - 3*sigma_y)
                y_max = min(grid.shape[1], iy + 3*sigma_y + 1)
                z_min = max(0, iz - 3*sigma_z)
                z_max = min(grid.shape[2], iz + 3*sigma_z + 1)
                
                # Apply gaussian source
                for i in range(x_min, x_max):
                    for j in range(y_min, y_max):
                        for k in range(z_min, z_max):
                            dx = (i - ix) ** 2 / (2 * sigma_x ** 2)
                            dy = (j - iy) ** 2 / (2 * sigma_y ** 2)
                            dz = (k - iz) ** 2 / (2 * sigma_z ** 2)
                            value = strength * math.exp(-(dx + dy + dz)) * dt
                            grid[i, j, k] += value
            
            elif source_type == 'volume':
                # Volume source (constant emission in a rectangular volume)
                size = source.get('size', (1, 1, 1))  # meters
                
                # Convert physical size to grid indices
                nx = max(1, int(size[0] / resolution))
                ny = max(1, int(size[1] / resolution))
                nz = max(1, int(size[2] / resolution))
                
                # Define region to update
                x_min = max(0, ix - nx // 2)
                x_max = min(grid.shape[0], ix + nx // 2 + 1)
                y_min = max(0, iy - ny // 2)
                y_max = min(grid.shape[1], iy + ny // 2 + 1)
                z_min = max(0, iz - nz // 2)
                z_max = min(grid.shape[2], iz + nz // 2 + 1)
                
                # Volume is strength per unit volume
                volume_elements = (x_max - x_min) * (y_max - y_min) * (z_max - z_min)
                value_per_cell = strength * dt / volume_elements
                
                # Apply constant source throughout volume
                grid[x_min:x_max, y_min:y_max, z_min:z_max] += value_per_cell
        
        return grid
    
    def _apply_barriers(self, grid: np.ndarray) -> np.ndarray:
        """
        Apply barriers (walls, obstacles) to the grid.
        
        Args:
            grid: The current grid values
            
        Returns:
            Grid with barriers applied
        """
        barriers = self.parameters['barriers']
        
        # Create mask of barrier locations (1 for barrier, 0 for air)
        barrier_mask = np.zeros_like(grid, dtype=bool)
        
        for barrier in barriers:
            barrier_type = barrier.get('type', 'box')
            location = barrier.get('location', (0, 0, 0))
            
            # Convert physical location to grid indices
            resolution = self.parameters['grid_resolution']
            ix = int(location[0] / resolution)
            iy = int(location[1] / resolution)
            iz = int(location[2] / resolution)
            
            if barrier_type == 'box':
                # Box barrier
                size = barrier.get('size', (1, 1, 1))  # meters
                
                # Convert physical size to grid indices
                nx = max(1, int(size[0] / resolution))
                ny = max(1, int(size[1] / resolution))
                nz = max(1, int(size[2] / resolution))
                
                # Define region to update
                x_min = max(0, ix - nx // 2)
                x_max = min(grid.shape[0], ix + nx // 2 + 1)
                y_min = max(0, iy - ny // 2)
                y_max = min(grid.shape[1], iy + ny // 2 + 1)
                z_min = max(0, iz - nz // 2)
                z_max = min(grid.shape[2], iz + nz // 2 + 1)
                
                # Set barrier mask
                barrier_mask[x_min:x_max, y_min:y_max, z_min:z_max] = True
            
            elif barrier_type == 'wall':
                # Wall barrier (vertical plane)
                width = barrier.get('width', 5.0)  # meters
                height = barrier.get('height', 3.0)  # meters
                orientation = barrier.get('orientation', 'x')  # 'x' or 'y'
                
                # Convert physical dimensions to grid indices
                nw = max(1, int(width / resolution))
                nh = max(1, int(height / resolution))
                
                if orientation == 'x':
                    # Wall along x-axis
                    x_min = max(0, ix)
                    x_max = min(grid.shape[0], ix + 1)
                    y_min = max(0, iy - nw // 2)
                    y_max = min(grid.shape[1], iy + nw // 2 + 1)
                    z_min = max(0, iz)
                    z_max = min(grid.shape[2], iz + nh)
                    
                    # Set barrier mask
                    barrier_mask[x_min:x_max, y_min:y_max, z_min:z_max] = True
                    
                elif orientation == 'y':
                    # Wall along y-axis
                    x_min = max(0, ix - nw // 2)
                    x_max = min(grid.shape[0], ix + nw // 2 + 1)
                    y_min = max(0, iy)
                    y_max = min(grid.shape[1], iy + 1)
                    z_min = max(0, iz)
                    z_max = min(grid.shape[2], iz + nh)
                    
                    # Set barrier mask
                    barrier_mask[x_min:x_max, y_min:y_max, z_min:z_max] = True
        
        # Apply barrier effects to grid
        # For physical barriers, we typically use Dirichlet (fixed value) or 
        # Neumann (zero gradient) boundary conditions
        
        # For temperature, barriers often maintain their own temperature
        if self.parameters['parameter_type'] == 'temperature':
            barrier_value = self.parameters.get('barrier_temperature', 20.0)  # Default room temperature
            grid[barrier_mask] = barrier_value
        else:
            # For gases and particles, barriers are typically impermeable
            # We'll handle this in the diffusion step
            pass
        
        return grid, barrier_mask
    
    def _apply_advection(self, grid: np.ndarray, dt: float) -> np.ndarray:
        """
        Apply advection (e.g., from airflow) to the grid.
        
        Args:
            grid: The current grid values
            dt: Time step in seconds
            
        Returns:
            Grid with advection applied
        """
        advection_field = self.parameters['advection_field']
        
        if advection_field is None:
            return grid
        
        # Get grid dimensions
        nx, ny, nz = grid.shape
        
        # Create a copy of the grid for the updated values
        new_grid = grid.copy()
        
        # Check if advection field is constant or spatially varying
        if isinstance(advection_field, tuple) and len(advection_field) == 3:
            # Constant velocity field (vx, vy, vz)
            vx, vy, vz = advection_field
            
            # Convert physical velocities to grid velocities
            resolution = self.parameters['grid_resolution']
            vx_grid = vx * dt / resolution
            vy_grid = vy * dt / resolution
            vz_grid = vz * dt / resolution
            
            # Apply upwind scheme for advection
            for i in range(1, nx-1):
                for j in range(1, ny-1):
                    for k in range(1, nz-1):
                        # X-direction advection
                        if vx_grid > 0:
                            flux_x = vx_grid * (grid[i, j, k] - grid[i-1, j, k])
                        else:
                            flux_x = vx_grid * (grid[i+1, j, k] - grid[i, j, k])
                        
                        # Y-direction advection
                        if vy_grid > 0:
                            flux_y = vy_grid * (grid[i, j, k] - grid[i, j-1, k])
                        else:
                            flux_y = vy_grid * (grid[i, j+1, k] - grid[i, j, k])
                        
                        # Z-direction advection
                        if vz_grid > 0:
                            flux_z = vz_grid * (grid[i, j, k] - grid[i, j, k-1])
                        else:
                            flux_z = vz_grid * (grid[i, j, k+1] - grid[i, j, k])
                        
                        # Update grid with total flux
                        new_grid[i, j, k] = grid[i, j, k] - (flux_x + flux_y + flux_z)
        
        elif isinstance(advection_field, dict) and 'type' in advection_field:
            # Spatially varying velocity field
            if advection_field['type'] == 'hvac':
                # HVAC system with inlet and outlet
                inlet = advection_field.get('inlet', {'location': (0, 0, 0), 'velocity': (1, 0, 0)})
                outlet = advection_field.get('outlet', {'location': (nx-1, 0, 0), 'velocity': (1, 0, 0)})
                strength = advection_field.get('strength', 1.0)
                
                # Create velocity field based on inlet/outlet
                vx = np.zeros_like(grid)
                vy = np.zeros_like(grid)
                vz = np.zeros_like(grid)
                
                # Simple model: linear interpolation between inlet and outlet
                in_loc = inlet['location']
                out_loc = outlet['location']
                
                for i in range(nx):
                    for j in range(ny):
                        for k in range(nz):
                            # Distance from inlet and outlet
                            ri = np.sqrt((i - in_loc[0])**2 + (j - in_loc[1])**2 + (k - in_loc[2])**2)
                            ro = np.sqrt((i - out_loc[0])**2 + (j - out_loc[1])**2 + (k - out_loc[2])**2)
                            
                            # Direction vectors
                            if ri > 0:
                                dxi = (i - in_loc[0]) / ri
                                dyi = (j - in_loc[1]) / ri
                                dzi = (k - in_loc[2]) / ri
                            else:
                                dxi, dyi, dzi = inlet['velocity']
                            
                            if ro > 0:
                                dxo = (out_loc[0] - i) / ro
                                dyo = (out_loc[1] - j) / ro
                                dzo = (out_loc[2] - k) / ro
                            else:
                                dxo, dyo, dzo = outlet['velocity']
                            
                            # Weighting factors
                            wi = 1.0 / (1.0 + ri * ri)
                            wo = 1.0 / (1.0 + ro * ro)
                            
                            # Combined velocity
                            vx[i, j, k] = strength * (wi * dxi + wo * dxo) / (wi + wo)
                            vy[i, j, k] = strength * (wi * dyi + wo * dyo) / (wi + wo)
                            vz[i, j, k] = strength * (wi * dzi + wo * dzo) / (wi + wo)
                
                # Now apply advection with this velocity field
                for i in range(1, nx-1):
                    for j in range(1, ny-1):
                        for k in range(1, nz-1):
                            # Convert physical velocities to grid velocities
                            resolution = self.parameters['grid_resolution']
                            vx_grid = vx[i, j, k] * dt / resolution
                            vy_grid = vy[i, j, k] * dt / resolution
                            vz_grid = vz[i, j, k] * dt / resolution
                            
                            # X-direction advection
                            if vx_grid > 0:
                                flux_x = vx_grid * (grid[i, j, k] - grid[i-1, j, k])
                            else:
                                flux_x = vx_grid * (grid[i+1, j, k] - grid[i, j, k])
                            
                            # Y-direction advection
                            if vy_grid > 0:
                                flux_y = vy_grid * (grid[i, j, k] - grid[i, j-1, k])
                            else:
                                flux_y = vy_grid * (grid[i, j+1, k] - grid[i, j, k])
                            
                            # Z-direction advection
                            if vz_grid > 0:
                                flux_z = vz_grid * (grid[i, j, k] - grid[i, j, k-1])
                            else:
                                flux_z = vz_grid * (grid[i, j, k+1] - grid[i, j, k])
                            
                            # Update grid with total flux
                            new_grid[i, j, k] = grid[i, j, k] - (flux_x + flux_y + flux_z)
            
            elif advection_field['type'] == 'custom':
                # Custom velocity field provided as 3D arrays
                vx = advection_field.get('vx', np.zeros_like(grid))
                vy = advection_field.get('vy', np.zeros_like(grid))
                vz = advection_field.get('vz', np.zeros_like(grid))
                
                # Apply advection with this velocity field
                for i in range(1, nx-1):
                    for j in range(1, ny-1):
                        for k in range(1, nz-1):
                            # Convert physical velocities to grid velocities
                            resolution = self.parameters['grid_resolution']
                            vx_grid = vx[i, j, k] * dt / resolution
                            vy_grid = vy[i, j, k] * dt / resolution
                            vz_grid = vz[i, j, k] * dt / resolution
                            
                            # X-direction advection
                            if vx_grid > 0:
                                flux_x = vx_grid * (grid[i, j, k] - grid[i-1, j, k])
                            else:
                                flux_x = vx_grid * (grid[i+1, j, k] - grid[i, j, k])
                            
                            # Y-direction advection
                            if vy_grid > 0:
                                flux_y = vy_grid * (grid[i, j, k] - grid[i, j-1, k])
                            else:
                                flux_y = vy_grid * (grid[i, j+1, k] - grid[i, j, k])
                            
                            # Z-direction advection
                            if vz_grid > 0:
                                flux_z = vz_grid * (grid[i, j, k] - grid[i, j, k-1])
                            else:
                                flux_z = vz_grid * (grid[i, j, k+1] - grid[i, j, k])
                            
                            # Update grid with total flux
                            new_grid[i, j, k] = grid[i, j, k] - (flux_x + flux_y + flux_z)
        
        return new_grid
    
    def _apply_diffusion(self, grid: np.ndarray, barrier_mask: np.ndarray, dt: float) -> np.ndarray:
        """
        Apply diffusion to the grid.
        
        Args:
            grid: The current grid values
            barrier_mask: Mask indicating barrier locations
            dt: Time step in seconds
            
        Returns:
            Grid with diffusion applied
        """
        # Get diffusion coefficient
        parameter_type = self.parameters['parameter_type']
        diffusion_coefficient = self.parameters['diffusion_coefficient']
        
        # If not specified, use default for parameter type
        if diffusion_coefficient is None and parameter_type in self.parameter_defaults:
            diffusion_coefficient = self.parameter_defaults[parameter_type]['diffusion_coefficient']
        elif diffusion_coefficient is None:
            diffusion_coefficient = 0.01  # Default value if not specified
        
        # Get grid dimensions
        nx, ny, nz = grid.shape
        
        # Create a copy of the grid for the updated values
        new_grid = grid.copy()
        
        # Convert physical diffusion coefficient to grid units
        resolution = self.parameters['grid_resolution']
        D_grid = diffusion_coefficient * dt / (resolution * resolution)
        
        # Check stability condition (dt <= dx^2 / (2 * D * ndim))
        max_stable_dt = resolution * resolution / (6 * diffusion_coefficient)
        if dt > max_stable_dt:
            print(f"Warning: Time step {dt} exceeds stability limit {max_stable_dt} for diffusion.")
            # Reduce diffusion coefficient to maintain stability
            D_grid = 1.0 / 6.0
        
        # Apply explicit finite difference scheme for diffusion
        for i in range(1, nx-1):
            for j in range(1, ny-1):
                for k in range(1, nz-1):
                    # Skip barriers
                    if barrier_mask[i, j, k]:
                        continue
                    
                    # Calculate Laplacian
                    laplacian = (
                        grid[i+1, j, k] + grid[i-1, j, k] +
                        grid[i, j+1, k] + grid[i, j-1, k] +
                        grid[i, j, k+1] + grid[i, j, k-1] - 
                        6 * grid[i, j, k]
                    )
                    
                    # Update grid
                    new_grid[i, j, k] = grid[i, j, k] + D_grid * laplacian
        
        return new_grid
    
    def _apply_decay(self, grid: np.ndarray, dt: float) -> np.ndarray:
        """
        Apply decay to the parameter values.
        
        Args:
            grid: The current grid values
            dt: Time step in seconds
            
        Returns:
            Grid with decay applied
        """
        # Get decay rate
        parameter_type = self.parameters['parameter_type']
        decay_rate = self.parameters['decay_rate']
        
        # If not specified, use default for parameter type
        if decay_rate is None and parameter_type in self.parameter_defaults:
            decay_rate = self.parameter_defaults[parameter_type]['decay_rate']
        elif decay_rate is None:
            decay_rate = 0.0  # Default value if not specified
        
        # Apply first-order decay
        if decay_rate > 0:
            decay_factor = math.exp(-decay_rate * dt)
            grid = grid * decay_factor
        
        return grid
    
    def _simulate_step(self, grid: np.ndarray, barrier_mask: np.ndarray, dt: float) -> np.ndarray:
        """
        Simulate one time step.
        
        Args:
            grid: The current grid values
            barrier_mask: Mask indicating barrier locations
            dt: Time step in seconds
            
        Returns:
            Updated grid
        """
        # Apply sources
        grid = self._apply_sources(grid, dt)
        
        # Apply advection
        grid = self._apply_advection(grid, dt)
        
        # Apply diffusion
        grid = self._apply_diffusion(grid, barrier_mask, dt)
        
        # Apply decay
        grid = self._apply_decay(grid, dt)
        
        # Apply boundary conditions
        grid = self._apply_boundary_conditions(grid)
        
        return grid
    
    def _visualize_grid(self, grid: np.ndarray, barrier_mask: np.ndarray, 
                        coords: Tuple[np.ndarray, np.ndarray, np.ndarray], 
                        time_point: int) -> Optional[str]:
        """
        Visualize the current grid state.
        
        Args:
            grid: The current grid values
            barrier_mask: Mask indicating barrier locations
            coords: Tuple of coordinate arrays (x, y, z)
            time_point: Current time point
            
        Returns:
            Path to saved visualization if successful, None otherwise
        """
        if not self.parameters['visualize']:
            return None
        
        # Get visualization parameters
        slice_plane = self.parameters['visualization_slice']
        slice_index = self.parameters['visualization_slice_index']
        parameter_type = self.parameters['parameter_type']
        
        # Get parameter unit if available
        unit = ""
        if parameter_type in PARAMETER_DEFINITIONS:
            unit = PARAMETER_DEFINITIONS[parameter_type].get('unit', '')
        
        # Determine slice index if not specified
        if slice_index is None:
            if slice_plane == 'xy':
                slice_index = grid.shape[2] // 2
            elif slice_plane == 'xz':
                slice_index = grid.shape[1] // 2
            elif slice_plane == 'yz':
                slice_index = grid.shape[0] // 2
        
        # Create figure
        plt.figure(figsize=(10, 8))
        
        # Extract slice data
        if slice_plane == 'xy':
            slice_data = grid[:, :, slice_index]
            barrier_slice = barrier_mask[:, :, slice_index]
            x_coords, y_coords, _ = coords
            plt.pcolormesh(x_coords, y_coords, slice_data.T, cmap='viridis', shading='auto')
            plt.xlabel('X (m)')
            plt.ylabel('Y (m)')
            plt.title(f'{parameter_type.capitalize()} ({unit}) - XY Plane at Z={coords[2][slice_index]:.2f}m, t={time_point}s')
        
        elif slice_plane == 'xz':
            slice_data = grid[:, slice_index, :]
            barrier_slice = barrier_mask[:, slice_index, :]
            x_coords, _, z_coords = coords
            plt.pcolormesh(x_coords, z_coords, slice_data.T, cmap='viridis', shading='auto')
            plt.xlabel('X (m)')
            plt.ylabel('Z (m)')
            plt.title(f'{parameter_type.capitalize()} ({unit}) - XZ Plane at Y={coords[1][slice_index]:.2f}m, t={time_point}s')
        
        elif slice_plane == 'yz':
            slice_data = grid[slice_index, :, :]
            barrier_slice = barrier_mask[slice_index, :, :]
            _, y_coords, z_coords = coords
            plt.pcolormesh(y_coords, z_coords, slice_data.T, cmap='viridis', shading='auto')
            plt.xlabel('Y (m)')
            plt.ylabel('Z (m)')
            plt.title(f'{parameter_type.capitalize()} ({unit}) - YZ Plane at X={coords[0][slice_index]:.2f}m, t={time_point}s')
        
        # Add colorbar
        cbar = plt.colorbar()
        cbar.set_label(f'{parameter_type.capitalize()} ({unit})')
        
        # Overlay barriers if present
        if np.any(barrier_slice):
            if slice_plane == 'xy':
                plt.contour(x_coords, y_coords, barrier_slice.T, levels=[0.5], colors='red', linewidths=2)
            elif slice_plane == 'xz':
                plt.contour(x_coords, z_coords, barrier_slice.T, levels=[0.5], colors='red', linewidths=2)
            elif slice_plane == 'yz':
                plt.contour(y_coords, z_coords, barrier_slice.T, levels=[0.5], colors='red', linewidths=2)
        
        # Add sources
        sources = self.parameters['sources']
        for source in sources:
            if not source.get('active', True):
                continue
                
            location = source.get('location', (0, 0, 0))
            
            # Check if source is in current slice plane
            if slice_plane == 'xy' and abs(location[2] - coords[2][slice_index]) < self.parameters['grid_resolution']:
                plt.plot(location[0], location[1], 'ko', markersize=8)
                plt.plot(location[0], location[1], 'yo', markersize=5)
            elif slice_plane == 'xz' and abs(location[1] - coords[1][slice_index]) < self.parameters['grid_resolution']:
                plt.plot(location[0], location[2], 'ko', markersize=8)
                plt.plot(location[0], location[2], 'yo', markersize=5)
            elif slice_plane == 'yz' and abs(location[0] - coords[0][slice_index]) < self.parameters['grid_resolution']:
                plt.plot(location[1], location[2], 'ko', markersize=8)
                plt.plot(location[1], location[2], 'yo', markersize=5)
        
        # Save figure
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"spatial_{parameter_type}_{timestamp}.png"
        filepath = f"envirosense/plots/{filename}"
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        return filepath
    
    def generate(self, scenario: TestScenario, **kwargs) -> Dict[str, Any]:
        """
        Generate spatial environmental data based on scenario.
        
        Args:
            scenario: Test scenario to generate data for
            **kwargs: Additional parameters
            
        Returns:
            Generated spatial environmental data
        """
        # Update parameters from scenario
        for key, value in scenario.parameters.items():
            if key in self.parameters:
                self.parameters[key] = value
        
        # Override with any explicit kwargs
        for key, value in kwargs.items():
            if key in self.parameters:
                self.parameters[key] = value
        
        # Initialize random number generator if needed
        if self.parameters['random_seed'] is not None:
            self.rng = np.random.RandomState(self.parameters['random_seed'])
        else:
            self.rng = np.random.RandomState()
        
        # Set up the computational grid
        grid, coords = self._setup_grid()
        
        # Initialize the grid with initial conditions
        grid = self._initialize_grid(grid, coords)
        
        # Set up barriers
        grid, barrier_mask = self._apply_barriers(grid)
        
        # Apply boundary conditions
        grid = self._apply_boundary_conditions(grid)
        
        # Time stepping parameters
        simulation_time = self.parameters['simulation_time']
        dt = self.parameters['time_step']
        num_steps = int(simulation_time / dt)
        
        # Set up storage for results
        if self.parameters['output_full_grid']:
            grid_history = [grid.copy()]
        else:
            grid_history = []
        
        # Store source locations
        source_locations = []
        for source in self.parameters['sources']:
            if source.get('active', True):
                source_locations.append(source.get('location', (0, 0, 0)))
        
        # Store barrier positions
        barrier_positions = []
        for barrier in self.parameters['barriers']:
            barrier_positions.append({
                'type': barrier.get('type', 'box'),
                'location': barrier.get('location', (0, 0, 0)),
                'size': barrier.get('size', (1, 1, 1)) if 'size' in barrier else None,
                'width': barrier.get('width', None),
                'height': barrier.get('height', None),
                'orientation': barrier.get('orientation', None)
            })
        
        # Create time array
        times = [i * dt for i in range(num_steps + 1)]
        
        # Visualization paths
        visualization_paths = []
        
        # Run simulation
        for i in range(num_steps):
            # Simulate one step
            grid = self._simulate_step(grid, barrier_mask, dt)
            
            # Store results if needed
            if self.parameters['output_full_grid']:
                grid_history.append(grid.copy())
            
            # Visualize if needed
            if self.parameters['visualize'] and i % 10 == 0:  # Every 10 steps
                vis_path = self._visualize_grid(grid, barrier_mask, coords, i * dt)
                if vis_path:
                    visualization_paths.append(vis_path)
        
        # Final visualization
        if self.parameters['visualize']:
            vis_path = self._visualize_grid(grid, barrier_mask, coords, simulation_time)
            if vis_path:
                visualization_paths.append(vis_path)
        
        # Extract useful statistics
        if self.parameters['output_full_grid']:
            # Calculate time series at specific points
            point_time_series = {}
            
            # At source locations
            for i, loc in enumerate(source_locations):
                ix = int(loc[0] / self.parameters['grid_resolution'])
                iy = int(loc[1] / self.parameters['grid_resolution'])
                iz = int(loc[2] / self.parameters['grid_resolution'])
                
                # Ensure indices are within grid
                ix = max(0, min(ix, grid.shape[0] - 1))
                iy = max(0, min(iy, grid.shape[1] - 1))
                iz = max(0, min(iz, grid.shape[2] - 1))
                
                # Extract time series
                values = [g[ix, iy, iz] for g in grid_history]
                point_time_series[f'source_{i}'] = values
            
            # At corner points
            corner_points = [
                (0, 0, 0),
                (grid.shape[0]-1, 0, 0),
                (0, grid.shape[1]-1, 0),
                (0, 0, grid.shape[2]-1),
                (grid.shape[0]-1, grid.shape[1]-1, 0),
                (grid.shape[0]-1, 0, grid.shape[2]-1),
                (0, grid.shape[1]-1, grid.shape[2]-1),
                (grid.shape[0]-1, grid.shape[1]-1, grid.shape[2]-1)
            ]
            
            for i, point in enumerate(corner_points):
                ix, iy, iz = point
                
                # Extract time series if not in a barrier
                if not barrier_mask[ix, iy, iz]:
                    values = [g[ix, iy, iz] for g in grid_history]
                    point_time_series[f'corner_{i}'] = values
        
        # Create output dictionary
        parameter_type = self.parameters['parameter_type']
        unit = ""
        if parameter_type in PARAMETER_DEFINITIONS:
            unit = PARAMETER_DEFINITIONS[parameter_type].get('unit', '')
        
        result = {
            'parameter': parameter_type,
            'unit': unit,
            'grid_size': self.parameters['grid_size'],
            'grid_resolution': self.parameters['grid_resolution'],
            'simulation_time': simulation_time,
            'time_step': dt,
            'times': times,
            'source_locations': source_locations,
            'barrier_positions': barrier_positions,
            'final_grid': grid.tolist(),
            'min_value': float(np.min(grid)),
            'max_value': float(np.max(grid)),
            'mean_value': float(np.mean(grid)),
            'visualization_paths': visualization_paths,
            'timestamp': datetime.datetime.now().isoformat(),
            'scenario_id': getattr(scenario, 'id', None)
        }
        
        # Add full grid history if requested
        if self.parameters['output_full_grid']:
            result['grid_history'] = [g.tolist() for g in grid_history]
            result['point_time_series'] = point_time_series
        
        return result
