"""
Profile management system for EnviroSense physiological sensitivity profiles.

This module provides a comprehensive management system for handling sensitivity profiles,
including storage, retrieval, versioning, search, and documentation generation.
"""

import os
import json
import uuid
import datetime
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple, Union

from envirosense.testing.generators.physiological.sensitivity_profiles import SensitivityProfile


class ValidationResult:
    """
    Represents the result of a profile validation operation.
    
    Attributes:
        is_valid: Whether the profile is valid
        errors: List of validation errors
        warnings: List of validation warnings
    """
    
    def __init__(self, is_valid: bool = True, errors: List[str] = None, warnings: List[str] = None):
        self.is_valid = is_valid
        self.errors = errors or []
        self.warnings = warnings or []
    
    def __bool__(self):
        return self.is_valid


class ValidationError(Exception):
    """Exception raised for profile validation errors."""
    pass


class ProfileStorageBackend:
    """
    Abstract base class for profile storage backends.
    
    This class defines the interface that all storage backends must implement
    to be used with the ProfileManager.
    """
    
    def save(self, profile: SensitivityProfile) -> bool:
        """
        Save a profile to storage.
        
        Args:
            profile: The profile to save
            
        Returns:
            True if successful, False otherwise
        """
        raise NotImplementedError("Subclasses must implement save()")
    
    def load(self, profile_id: str) -> Optional[SensitivityProfile]:
        """
        Load a profile from storage.
        
        Args:
            profile_id: The ID of the profile to load
            
        Returns:
            The loaded profile, or None if not found
        """
        raise NotImplementedError("Subclasses must implement load()")
    
    def delete(self, profile_id: str) -> bool:
        """
        Delete a profile from storage.
        
        Args:
            profile_id: The ID of the profile to delete
            
        Returns:
            True if successful, False otherwise
        """
        raise NotImplementedError("Subclasses must implement delete()")
    
    def list(self, filters: Dict = None) -> List[str]:
        """
        List profile IDs matching filters.
        
        Args:
            filters: Optional filtering criteria
            
        Returns:
            List of profile IDs
        """
        raise NotImplementedError("Subclasses must implement list()")


class FileSystemStorage(ProfileStorageBackend):
    """
    File system-based profile storage.
    
    This class provides a simple implementation of profile storage using the file system,
    with profiles stored as JSON files.
    """
    
    def __init__(self, base_path: str, use_compression: bool = False):
        """
        Initialize the file system storage.
        
        Args:
            base_path: Base directory for profile storage
            use_compression: Whether to compress stored files (not yet implemented)
        """
        self.base_path = Path(base_path)
        self.use_compression = use_compression
        self.base_path.mkdir(exist_ok=True, parents=True)
    
    def _get_path_for_profile(self, profile_id: str) -> Path:
        """
        Get the file path for a profile.
        
        Args:
            profile_id: The profile ID
            
        Returns:
            Path object for the profile file
        """
        return self.base_path / f"{profile_id}.json"
    
    def save(self, profile: SensitivityProfile) -> bool:
        """
        Save profile to a JSON file.
        
        Args:
            profile: The profile to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            file_path = self._get_path_for_profile(profile.profile_id)
            with open(file_path, 'w') as f:
                json.dump(profile.to_dict(), f, indent=2)
            return True
        except (IOError, OSError, TypeError) as e:
            print(f"Error saving profile {profile.profile_id}: {str(e)}")
            return False
    
    def load(self, profile_id: str) -> Optional[SensitivityProfile]:
        """
        Load a profile from a JSON file.
        
        Args:
            profile_id: The ID of the profile to load
            
        Returns:
            The loaded profile, or None if not found
        """
        file_path = self._get_path_for_profile(profile_id)
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            profile = SensitivityProfile()
            profile.from_dict(data)
            return profile
        except (IOError, json.JSONDecodeError, KeyError) as e:
            print(f"Error loading profile {profile_id}: {str(e)}")
            return None
    
    def delete(self, profile_id: str) -> bool:
        """
        Delete a profile file.
        
        Args:
            profile_id: The ID of the profile to delete
            
        Returns:
            True if successful, False otherwise
        """
        file_path = self._get_path_for_profile(profile_id)
        if not file_path.exists():
            return False
        
        try:
            file_path.unlink()
            return True
        except OSError as e:
            print(f"Error deleting profile {profile_id}: {str(e)}")
            return False
    
    def list(self, filters: Dict = None) -> List[str]:
        """
        List profile IDs in the storage directory.
        
        Args:
            filters: Optional filtering criteria (not used in this implementation)
            
        Returns:
            List of profile IDs
        """
        profile_ids = []
        
        for file_path in self.base_path.glob("*.json"):
            profile_id = file_path.stem
            profile_ids.append(profile_id)
        
        return profile_ids


class ProfileIndex:
    """
    Indexing system for fast profile lookup and search.
    
    This class maintains an in-memory index of profile attributes to enable
    efficient searching without loading all profiles.
    """
    
    def __init__(self, storage_backend: ProfileStorageBackend):
        """
        Initialize the profile index.
        
        Args:
            storage_backend: The storage backend to index
        """
        self.storage = storage_backend
        self.index = {}
        self.rebuild_index()
    
    def rebuild_index(self):
        """Rebuild the entire index from storage."""
        self.index = {
            'demographics': {},
            'conditions': {},
            'sensitivity_scores': {},
            'created_at': {},
            'updated_at': {},
            'version': {}
        }
        
        # Populate index from storage
        for profile_id in self.storage.list():
            profile = self.storage.load(profile_id)
            if profile:
                self.add_to_index(profile)
    
    def add_to_index(self, profile: SensitivityProfile):
        """
        Add a single profile to the index.
        
        Args:
            profile: The profile to index
        """
        profile_id = profile.profile_id
        
        # Index by demographics
        for key, value in profile.demographics.items():
            if value is not None:
                if key not in self.index['demographics']:
                    self.index['demographics'][key] = {}
                if value not in self.index['demographics'][key]:
                    self.index['demographics'][key][value] = set()
                self.index['demographics'][key][value].add(profile_id)
        
        # Index by conditions
        for condition in profile.conditions:
            if condition not in self.index['conditions']:
                self.index['conditions'][condition] = set()
            self.index['conditions'][condition].add(profile_id)
        
        # Index by sensitivity scores
        for sens_type, score in profile.sensitivity_scores.items():
            if sens_type not in self.index['sensitivity_scores']:
                self.index['sensitivity_scores'][sens_type] = {}
            
            # Discretize scores for indexing (0.5 increments)
            discrete_score = round(score * 2) / 2
            if discrete_score not in self.index['sensitivity_scores'][sens_type]:
                self.index['sensitivity_scores'][sens_type][discrete_score] = set()
            self.index['sensitivity_scores'][sens_type][discrete_score].add(profile_id)
        
        # Index by version
        if profile.version not in self.index['version']:
            self.index['version'][profile.version] = set()
        self.index['version'][profile.version].add(profile_id)
        
        # Index by creation and update timestamps (by year-month)
        for timestamp_type, timestamp in [('created_at', profile.created_at), ('updated_at', profile.updated_at)]:
            try:
                dt = datetime.datetime.fromisoformat(timestamp)
                period = dt.strftime("%Y-%m")
                
                if period not in self.index[timestamp_type]:
                    self.index[timestamp_type][period] = set()
                self.index[timestamp_type][period].add(profile_id)
            except (ValueError, TypeError):
                # Skip invalid timestamps
                pass
    
    def remove_from_index(self, profile_id: str):
        """
        Remove a profile from the index.
        
        Args:
            profile_id: The ID of the profile to remove
        """
        # For simplicity, just rebuild the index
        # A more efficient implementation would selectively remove entries
        self.rebuild_index()
    
    def search(self, criteria: Dict) -> Set[str]:
        """
        Search for profiles matching criteria.
        
        Args:
            criteria: Dictionary of search criteria
            
        Returns:
            Set of profile IDs matching the criteria
        """
        if not criteria:
            return set(self.storage.list())
        
        # Start with all profiles or None
        result_set = None
        
        # Process demographic criteria
        if 'demographics' in criteria:
            for key, value in criteria['demographics'].items():
                matching_ids = set()
                
                if key in self.index['demographics'] and value in self.index['demographics'][key]:
                    matching_ids = self.index['demographics'][key][value]
                
                if result_set is None:
                    result_set = matching_ids
                else:
                    result_set &= matching_ids
                
                if not result_set:
                    return set()  # Empty intersection, no need to continue
        
        # Process condition criteria
        if 'conditions' in criteria:
            conditions = criteria['conditions']
            if isinstance(conditions, str):
                conditions = [conditions]  # Convert single condition to list
                
            for condition in conditions:
                matching_ids = set()
                
                if condition in self.index['conditions']:
                    matching_ids = self.index['conditions'][condition]
                
                if result_set is None:
                    result_set = matching_ids
                else:
                    result_set &= matching_ids
                
                if not result_set:
                    return set()  # Empty intersection, no need to continue
        
        # Process sensitivity score criteria
        if 'sensitivity_scores' in criteria:
            for sens_type, score_range in criteria['sensitivity_scores'].items():
                matching_ids = set()
                
                if isinstance(score_range, (int, float)):
                    # Single value - use as minimum
                    min_score = score_range
                    max_score = 2.0  # Maximum possible score
                elif isinstance(score_range, (list, tuple)) and len(score_range) == 2:
                    # Range [min, max]
                    min_score, max_score = score_range
                else:
                    continue  # Invalid format
                
                if sens_type in self.index['sensitivity_scores']:
                    for score, ids in self.index['sensitivity_scores'][sens_type].items():
                        if min_score <= score <= max_score:
                            matching_ids.update(ids)
                
                if result_set is None:
                    result_set = matching_ids
                else:
                    result_set &= matching_ids
                
                if not result_set:
                    return set()  # Empty intersection, no need to continue
        
        # Process version criteria
        if 'version' in criteria:
            version = criteria['version']
            matching_ids = set()
            
            if version in self.index['version']:
                matching_ids = self.index['version'][version]
            
            if result_set is None:
                result_set = matching_ids
            else:
                result_set &= matching_ids
            
            if not result_set:
                return set()  # Empty intersection, no need to continue
        
        # Process date range criteria
        for date_field in ['created_at', 'updated_at']:
            if date_field in criteria:
                date_range = criteria[date_field]
                if not isinstance(date_range, (list, tuple)) or len(date_range) != 2:
                    continue  # Invalid format
                
                start_date, end_date = date_range
                try:
                    # Convert to datetime objects if strings
                    if isinstance(start_date, str):
                        start_date = datetime.datetime.fromisoformat(start_date)
                    if isinstance(end_date, str):
                        end_date = datetime.datetime.fromisoformat(end_date)
                    
                    matching_ids = set()
                    
                    # Find matching time periods in the index
                    for period, ids in self.index[date_field].items():
                        period_start = datetime.datetime.strptime(period + "-01", "%Y-%m-%d")
                        
                        # Add one month to get period end
                        if period_start.month == 12:
                            period_end = datetime.datetime(period_start.year + 1, 1, 1)
                        else:
                            period_end = datetime.datetime(period_start.year, period_start.month + 1, 1)
                        
                        # Check for overlap with requested range
                        if (start_date is None or period_end > start_date) and \
                           (end_date is None or period_start < end_date):
                            matching_ids.update(ids)
                    
                    if result_set is None:
                        result_set = matching_ids
                    else:
                        result_set &= matching_ids
                    
                    if not result_set:
                        return set()  # Empty intersection, no need to continue
                
                except (ValueError, TypeError):
                    # Skip invalid date ranges
                    pass
        
        # Return empty set if no criteria matched
        return set() if result_set is None else result_set


class ProfileVersionManager:
    """
    Manages profile versioning and migration.
    
    This class handles the migration of profiles between different schema versions,
    ensuring backward compatibility.
    """
    
    def __init__(self):
        """Initialize the version manager with migration paths."""
        self.current_version = "1.0.0"  # Current schema version
        
        # Define version migration paths
        self.version_migrations = {
            # Future version migrations will be added here
            # "1.0.0": {
            #     "1.1.0": self._migrate_1_0_to_1_1
            # },
        }
    
    def get_current_version(self) -> str:
        """
        Get the current schema version.
        
        Returns:
            The current version string
        """
        return self.current_version
    
    def migrate_to_version(self, profile: SensitivityProfile, target_version: str) -> SensitivityProfile:
        """
        Migrate a profile to the target version.
        
        Args:
            profile: The profile to migrate
            target_version: The target version
            
        Returns:
            The migrated profile
            
        Raises:
            ValueError: If no migration path exists
        """
        current_version = profile.version
        
        if current_version == target_version:
            return profile
        
        # Find migration path
        path = self._find_migration_path(current_version, target_version)
        if not path:
            raise ValueError(f"No migration path from {current_version} to {target_version}")
        
        # Apply migrations in sequence
        migrated_profile = profile
        for i in range(len(path) - 1):
            from_ver = path[i]
            to_ver = path[i + 1]
            migration_func = self.version_migrations[from_ver][to_ver]
            migrated_profile = migration_func(migrated_profile)
        
        # Update version
        migrated_profile.version = target_version
        migrated_profile.updated_at = datetime.datetime.now().isoformat()
        
        return migrated_profile
    
    def _find_migration_path(self, start: str, end: str) -> List[str]:
        """
        Find a path of version migrations from start to end.
        
        Args:
            start: Starting version
            end: Target version
            
        Returns:
            List of versions forming a path, or empty list if no path exists
        """
        # Simple BFS to find a path through the version graph
        queue = [(start, [start])]
        visited = {start}
        
        while queue:
            (node, path) = queue.pop(0)
            
            if node == end:
                return path
            
            if node in self.version_migrations:
                for next_ver in self.version_migrations[node]:
                    if next_ver not in visited:
                        queue.append((next_ver, path + [next_ver]))
                        visited.add(next_ver)
        
        return []  # No path found
    
    # Example migration function, will be used when new versions are defined
    def _migrate_1_0_to_1_1(self, profile: SensitivityProfile) -> SensitivityProfile:
        """
        Migrate a profile from version 1.0.0 to 1.1.0.
        
        Args:
            profile: The profile to migrate
            
        Returns:
            The migrated profile
        """
        # Clone the profile
        data = profile.to_dict()
        
        # Example migration changes
        # Add a change_history field if it doesn't exist
        if 'change_history' not in data:
            data['change_history'] = []
        
        # Record the migration
        data['change_history'].append({
            'timestamp': datetime.datetime.now().isoformat(),
            'type': 'version_migration',
            'from': '1.0.0',
            'to': '1.1.0'
        })
        
        # Update version
        data['version'] = '1.1.0'
        
        # Create new profile
        migrated_profile = SensitivityProfile()
        migrated_profile.from_dict(data)
        
        return migrated_profile


class ProfileValidator:
    """
    Validates sensitivity profiles against schema and consistency rules.
    
    This class contains validation logic to ensure that profiles are well-formed
    and internally consistent.
    """
    
    def validate(self, profile: SensitivityProfile) -> ValidationResult:
        """
        Validate a profile.
        
        Args:
            profile: The profile to validate
            
        Returns:
            ValidationResult containing validation status and any errors/warnings
        """
        errors = []
        warnings = []
        
        # Check for required fields
        if not profile.profile_id:
            errors.append("Missing profile_id")
        
        if not profile.created_at:
            errors.append("Missing created_at timestamp")
        
        if not profile.updated_at:
            errors.append("Missing updated_at timestamp")
        
        if not profile.version:
            errors.append("Missing version")
        
        # Validate demographics
        if not hasattr(profile, 'demographics') or not profile.demographics:
            warnings.append("No demographic information provided")
        else:
            demographics = profile.demographics
            
            # Age validation
            if 'age' in demographics and demographics['age'] is not None:
                age = demographics['age']
                if not isinstance(age, (int, float)) or age < 0 or age > 120:
                    errors.append(f"Invalid age: {age}. Must be between 0 and 120.")
                
                # Check consistency between age and age_group
                if 'age_group' in demographics and demographics['age_group']:
                    age_group = demographics['age_group']
                    
                    # Define age range for each age_group
                    age_ranges = {
                        'child': (0, 12),
                        'adolescent': (13, 19),
                        'young_adult': (20, 39),
                        'middle_aged': (40, 59),
                        'older_adult': (60, 79),
                        'elderly': (80, 120)
                    }
                    
                    if age_group in age_ranges:
                        min_age, max_age = age_ranges[age_group]
                        if age < min_age or age > max_age:
                            warnings.append(
                                f"Age {age} is inconsistent with age_group '{age_group}' "
                                f"(expected range: {min_age}-{max_age})"
                            )
                    else:
                        warnings.append(f"Unknown age_group: {age_group}")
            
            # Height and weight validation for BMI
            if 'height' in demographics and 'weight' in demographics:
                height = demographics.get('height')
                weight = demographics.get('weight')
                
                if height is not None and weight is not None:
                    if height <= 0:
                        errors.append(f"Invalid height: {height}. Must be positive.")
                    if weight <= 0:
                        errors.append(f"Invalid weight: {weight}. Must be positive.")
                    
                    # Check BMI consistency if provided
                    if 'bmi' in demographics and demographics['bmi'] is not None:
                        bmi = demographics['bmi']
                        calculated_bmi = round(weight / ((height / 100) ** 2), 1)
                        
                        if abs(bmi - calculated_bmi) > 0.5:
                            warnings.append(
                                f"BMI value {bmi} is inconsistent with height and weight. "
                                f"Calculated BMI: {calculated_bmi}"
                            )
        
        # Validate sensitivity scores
        for sens_type, score in profile.sensitivity_scores.items():
            if not isinstance(score, (int, float)) or score < 0 or score > 2.0:
                errors.append(
                    f"Invalid sensitivity score for {sens_type}: {score}. "
                    f"Must be between 0 and 2.0."
                )
        
        # Validate conditions and sensitivity scores consistency
        for condition in profile.conditions:
            # Check for corresponding sensitivity scores based on condition
            # This is a very basic check - a real implementation would have more complex rules
            if condition == 'asthma' and 'respiratory' not in profile.sensitivity_scores:
                warnings.append(
                    f"Condition '{condition}' usually affects respiratory sensitivity, "
                    f"but no respiratory sensitivity score is defined."
                )
            elif condition == 'eczema' and 'dermal' not in profile.sensitivity_scores:
                warnings.append(
                    f"Condition '{condition}' usually affects dermal sensitivity, "
                    f"but no dermal sensitivity score is defined."
                )
        
        # Check result
        is_valid = len(errors) == 0
        
        return ValidationResult(is_valid, errors, warnings)


class ProfileDocumentationGenerator:
    """
    Generates human-readable documentation for sensitivity profiles.
    
    This class provides methods to create various documentation formats
    for sensitivity profiles.
    """
    
    def generate(self, profile: SensitivityProfile, format: str = 'text') -> str:
        """
        Generate documentation for a profile.
        
        Args:
            profile: The profile to document
            format: The output format (text, markdown, html)
            
        Returns:
            Documentation string in the requested format
        """
        if format == 'markdown':
            return self._generate_markdown(profile)
        elif format == 'html':
            return self._generate_html(profile)
        else:
            return self._generate_text(profile)
    
    def _generate_text(self, profile: SensitivityProfile) -> str:
        """
        Generate plain text documentation.
        
        Args:
            profile: The profile to document
            
        Returns:
            Text documentation
        """
        lines = [
            f"SENSITIVITY PROFILE: {profile.profile_id}",
            f"==========================================================",
            f"",
            f"Created: {profile.created_at}",
            f"Updated: {profile.updated_at}",
            f"Version: {profile.version}",
            f"",
            f"DEMOGRAPHICS",
            f"----------------------------------------------------------",
        ]
        
        # Add demographics
        for key, value in profile.demographics.items():
            if value is not None:
                lines.append(f"{key.replace('_', ' ').title()}: {value}")
        
        lines.append("")
        
        # Add conditions
        if profile.conditions:
            lines.append("PRE-EXISTING CONDITIONS")
            lines.append("----------------------------------------------------------")
            for condition in profile.conditions:
                lines.append(f"- {condition.replace('_', ' ').title()}")
            lines.append("")
        
        # Add sensitivity scores
        if profile.sensitivity_scores:
            lines.append("SENSITIVITY SCORES")
            lines.append("----------------------------------------------------------")
            lines.append("Sensitivity scores range from 0.0 to 2.0, where:")
            lines.append("  < 0.5: Low sensitivity")
            lines.append("  0.5-0.9: Below average sensitivity")
            lines.append("  1.0: Average sensitivity")
            lines.append("  1.1-1.5: Above average sensitivity")
            lines.append("  > 1.5: High sensitivity")
            lines.append("")
            
            for sens_type, score in profile.sensitivity_scores.items():
                lines.append(f"{sens_type.replace('_', ' ').title()}: {score:.1f}")
            
            lines.append("")
        
        # Add notes about empty fields
        empty_sections = []
        if not profile.subtype_modifiers:
            empty_sections.append("Subtype Modifiers")
        if not profile.parameter_modifiers:
            empty_sections.append("Parameter Modifiers")
        if not profile.response_curves:
            empty_sections.append("Response Curves")
        if not profile.symptom_thresholds:
            empty_sections.append("Symptom Thresholds")
        
        if empty_sections:
            lines.append("NOTES")
            lines.append("----------------------------------------------------------")
            lines.append("The following sections are not defined in this profile:")
            for section in empty_sections:
                lines.append(f"- {section}")
        
        return "\n".join(lines)
    
    def _generate_markdown(self, profile: SensitivityProfile) -> str:
        """
        Generate Markdown documentation.
        
        Args:
            profile: The profile to document
            
        Returns:
            Markdown documentation
        """
        lines = [
            f"# Sensitivity Profile: {profile.profile_id}",
            f"",
            f"**Created:** {profile.created_at}  ",
            f"**Updated:** {profile.updated_at}  ",
            f"**Version:** {profile.version}",
            f"",
            f"## Demographics",
            f"",
        ]
        
        # Add demographics
        for key, value in profile.demographics.items():
            if value is not None:
                lines.append(f"**{key.replace('_', ' ').title()}:** {value}  ")
        
        lines.append("")
        
        # Add conditions
        if profile.conditions:
            lines.append("## Pre-existing Conditions")
            lines.append("")
            for condition in profile.conditions:
                lines.append(f"- {condition.replace('_', ' ').title()}")
            lines.append("")
        
        # Add sensitivity scores
        if profile.sensitivity_scores:
            lines.append("## Sensitivity Scores")
            lines.append("")
            lines.append("Sensitivity scores range from 0.0 to 2.0, where:")
            lines.append("- **< 0.5:** Low sensitivity")
            lines.append("- **0.5-0.9:** Below average sensitivity")
            lines.append("- **1.0:** Average sensitivity")
            lines.append("- **1.1-1.5:** Above average sensitivity")
            lines.append("- **> 1.5:** High sensitivity")
            lines.append("")
            
            for sens_type, score in profile.sensitivity_scores.items():
                lines.append(f"**{sens_type.replace('_', ' ').title()}:** {score:.1f}  ")
            
            lines.append("")
        
        # Add notes about empty fields
        empty_sections = []
        if not profile.subtype_modifiers:
            empty_sections.append("Subtype Modifiers")
        if not profile.parameter_modifiers:
            empty_sections.append("Parameter Modifiers")
        if not profile.response_curves:
            empty_sections.append("Response Curves")
        if not profile.symptom_thresholds:
            empty_sections.append("Symptom Thresholds")
        
        if empty_sections:
            lines.append("## Notes")
            lines.append("")
            lines.append("The following sections are not defined in this profile:")
            for section in empty_sections:
                lines.append(f"- {section}")
        
        return "\n".join(lines)
    
    def _generate_html(self, profile: SensitivityProfile) -> str:
        """
        Generate HTML documentation.
        
        Args:
            profile: The profile to document
            
        Returns:
            HTML documentation
        """
        # Convert markdown to simple HTML
        md = self._generate_markdown(profile)
        
        # Very basic markdown to HTML conversion
        html = md.replace("\n\n", "</p><p>")
        html = html.replace("# ", "<h1>").replace("\n## ", "</p><h2>")
        html = html.replace("**", "<strong>").replace("**", "</strong>")
        html = html.replace("- ", "<li>").replace("\n- ", "</li><li>")
        
        # Wrap in basic HTML structure
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Sensitivity Profile: {profile.profile_id}</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 20px; }}
        h1 {{ color: #2c3e50; }}
        h2 {{ color: #3498db; border-bottom: 1px solid #eee; padding-bottom: 5px; }}
        strong {{ color: #2c3e50; }}
    </style>
</head>
<body>
    <p>{html}</p>
</body>
</html>
"""
        
        return html


class ProfileManager:
    """
    Central management system for sensitivity profiles.
    
    This class brings together all the components of the profile management system
    to provide a unified interface for working with sensitivity profiles.
    """
    
    def __init__(self, storage_path: str):
        """
        Initialize the profile manager.
        
        Args:
            storage_path: Path to the profile storage directory
        """
        self.storage = FileSystemStorage(storage_path)
        self.index = ProfileIndex(self.storage)
        self.version_manager = ProfileVersionManager()
        self.validator = ProfileValidator()
        self.doc_generator = ProfileDocumentationGenerator()
        self.cache = {}  # Simple in-memory cache
    
    def get_profile(self, profile_id: str) -> Optional[SensitivityProfile]:
        """
        Get a profile by ID, with caching.
        
        Args:
            profile_id: The ID of the profile to retrieve
            
        Returns:
            The profile, or None if not found
        """
        # Check cache first
        if profile_id in self.cache:
            return self.cache[profile_id]
        
        # Load from storage
        profile = self.storage.load(profile_id)
        if profile:
            # Add to cache
            self.cache[profile_id] = profile
        return profile
    
    def save_profile(self, profile: SensitivityProfile, validate: bool = True) -> bool:
        """
        Save a profile, with optional validation.
        
        Args:
            profile: The profile to save
            validate: Whether to validate the profile before saving
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            ValidationError: If validation fails and validate is True
        """
        # Validate if requested
        if validate:
            validation_result = self.validator.validate(profile)
            if not validation_result.is_valid:
                raise ValidationError(f"Profile validation failed: {validation_result.errors}")
        
        # Update timestamp
        profile.updated_at = datetime.datetime.now().isoformat()
        
        # Save to storage
        success = self.storage.save(profile)
        
        if success:
            # Update cache and index
            self.cache[profile.profile_id] = profile
            self.index.add_to_index(profile)
        
        return success
    
    def search_profiles(self, criteria: Dict) -> List[SensitivityProfile]:
        """
        Search for profiles matching criteria.
        
        Args:
            criteria: Dictionary of search criteria
            
        Returns:
            List of matching profiles
        """
        # Use index for efficient searching
        profile_ids = self.index.search(criteria)
        return [self.get_profile(pid) for pid in profile_ids]
    
    def delete_profile(self, profile_id: str) -> bool:
        """
        Delete a profile.
        
        Args:
            profile_id: The ID of the profile to delete
            
        Returns:
            True if successful, False otherwise
        """
        # Delete from storage
        success = self.storage.delete(profile_id)
        
        if success:
            # Remove from cache and index
            if profile_id in self.cache:
                del self.cache[profile_id]
            self.index.remove_from_index(profile_id)
        
        return success
    
    def create_profile(self, data: Dict = None) -> SensitivityProfile:
        """
        Create a new profile, optionally with initial data.
        
        Args:
            data: Optional initial data for the profile
            
        Returns:
            The newly created profile
        """
        profile = SensitivityProfile()
        
        # Set defaults
        profile.profile_id = str(uuid.uuid4())
        profile.created_at = datetime.datetime.now().isoformat()
        profile.updated_at = profile.created_at
        profile.version = self.version_manager.get_current_version()
        
        # Apply provided data
        if data:
            # Don't overwrite our defaults unless explicitly provided
            temp_data = profile.to_dict()
            temp_data.update(data)
            profile.from_dict(temp_data)
        
        return profile
    
    def clone_profile(self, source_id: str, include_history: bool = False) -> Optional[SensitivityProfile]:
        """
        Create a copy of an existing profile.
        
        Args:
            source_id: The ID of the profile to clone
            include_history: Whether to include change history
            
        Returns:
            The cloned profile, or None if the source wasn't found
        """
        source = self.get_profile(source_id)
        if not source:
            return None
        
        # Create copy
        data = source.to_dict()
        
        # Generate new ID and reset timestamps
        data['profile_id'] = str(uuid.uuid4())
        data['created_at'] = datetime.datetime.now().isoformat()
        data['updated_at'] = data['created_at']
        
        # Optionally exclude history
        if not include_history and 'change_history' in data:
            data['change_history'] = []
            # Add a reference to the source profile
            data['change_history'].append({
                'timestamp': data['created_at'],
                'type': 'cloned_from',
                'source_id': source_id
            })
        
        # Create new profile
        profile = SensitivityProfile()
        profile.from_dict(data)
        return profile
    
    def derive_profile(self, parent_id: str, modifications: Dict = None) -> Optional[SensitivityProfile]:
        """
        Create a derived profile with inheritance from parent.
        
        Args:
            parent_id: The ID of the parent profile
            modifications: Optional modifications to apply
            
        Returns:
            The derived profile, or None if the parent wasn't found
        """
        parent = self.get_profile(parent_id)
        if not parent:
            return None
        
        # Create base derived profile
        child = self.clone_profile(parent_id, include_history=False)
        
        # Record parentage
        if not hasattr(child, 'metadata'):
            child.metadata = {}
        child.metadata['derived_from'] = parent_id
        
        # Apply modifications if provided
        if modifications:
            # Demographics modifications
            if 'demographics' in modifications:
                for key, value in modifications['demographics'].items():
                    if not hasattr(child, 'demographics'):
                        child.demographics = {}
                    child.demographics[key] = value
            
            # Conditions modifications
            if 'conditions' in modifications:
                for condition in modifications['conditions']:
                    if condition not in child.conditions:
                        child.conditions.append(condition)
            
            # Sensitivity scores modifications
            if 'sensitivity_scores' in modifications:
                for sens_type, score in modifications['sensitivity_scores'].items():
                    child.sensitivity_scores[sens_type] = score
            
            # Subtype modifiers modifications
            if 'subtype_modifiers' in modifications:
                for subtype, modifiers in modifications['subtype_modifiers'].items():
                    child.subtype_modifiers[subtype] = modifiers
            
            # Parameter modifiers modifications
            if 'parameter_modifiers' in modifications:
                for param, modifier in modifications['parameter_modifiers'].items():
                    child.parameter_modifiers[param] = modifier
            
            # Response curves modifications
            if 'response_curves' in modifications:
                for curve_type, curve in modifications['response_curves'].items():
                    child.response_curves[curve_type] = curve
            
            # Symptom thresholds modifications
            if 'symptom_thresholds' in modifications:
                for symptom, threshold in modifications['symptom_thresholds'].items():
                    child.symptom_thresholds[symptom] = threshold
        
        return child
    
    def generate_documentation(self, profile_id: str, format: str = 'text') -> Optional[str]:
        """
        Generate documentation for a profile.
        
        Args:
            profile_id: The ID of the profile
            format: The output format (text, markdown, html)
            
        Returns:
            Documentation string, or None if the profile wasn't found
        """
        profile = self.get_profile(profile_id)
        if not profile:
            return None
        
        return self.doc_generator.generate(profile, format)
    
    def bulk_import(self, source_path: str) -> Dict[str, Any]:
        """
        Import multiple profiles from a JSON file.
        
        Args:
            source_path: Path to the JSON file containing profiles
            
        Returns:
            Dictionary with import results
        """
        results = {
            'total': 0,
            'imported': 0,
            'failed': 0,
            'errors': []
        }
        
        try:
            with open(source_path, 'r') as f:
                profiles_data = json.load(f)
            
            if not isinstance(profiles_data, list):
                results['errors'].append("Source file must contain a JSON array of profiles")
                return results
            
            results['total'] = len(profiles_data)
            
            for profile_data in profiles_data:
                try:
                    profile = self.create_profile(profile_data)
                    if self.save_profile(profile):
                        results['imported'] += 1
                    else:
                        results['failed'] += 1
                        results['errors'].append(f"Failed to save profile {profile.profile_id}")
                except (ValidationError, KeyError, TypeError) as e:
                    results['failed'] += 1
                    results['errors'].append(str(e))
            
            return results
        
        except (IOError, json.JSONDecodeError) as e:
            results['errors'].append(f"Error reading source file: {str(e)}")
            return results
    
    def bulk_export(self, profile_ids: List[str], output_path: str) -> Dict[str, Any]:
        """
        Export multiple profiles to a JSON file.
        
        Args:
            profile_ids: List of profile IDs to export
            output_path: Path for the output file
            
        Returns:
            Dictionary with export results
        """
        results = {
            'total': len(profile_ids),
            'exported': 0,
            'failed': 0,
            'errors': []
        }
        
        profiles_data = []
        
        for profile_id in profile_ids:
            profile = self.get_profile(profile_id)
            if profile:
                profiles_data.append(profile.to_dict())
                results['exported'] += 1
            else:
                results['failed'] += 1
                results['errors'].append(f"Profile not found: {profile_id}")
        
        try:
            # Ensure directory exists
            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            
            with open(output_path, 'w') as f:
                json.dump(profiles_data, f, indent=2)
            
            return results
        
        except IOError as e:
            results['errors'].append(f"Error writing output file: {str(e)}")
            return results
    
    def migrate_profile(self, profile_id: str, target_version: str) -> Optional[SensitivityProfile]:
        """
        Migrate a profile to a different schema version.
        
        Args:
            profile_id: The ID of the profile to migrate
            target_version: The target version
            
        Returns:
            The migrated profile, or None if not found
            
        Raises:
            ValueError: If no migration path exists
        """
        profile = self.get_profile(profile_id)
        if not profile:
            return None
        
        # Perform migration
        migrated_profile = self.version_manager.migrate_to_version(profile, target_version)
        
        # Update cache
        self.cache[profile_id] = migrated_profile
        
        return migrated_profile
    
    def validate_profile(self, profile_id: str) -> ValidationResult:
        """
        Validate a profile against schema and consistency rules.
        
        Args:
            profile_id: The ID of the profile to validate
            
        Returns:
            ValidationResult, or a ValidationResult with is_valid=False if the profile wasn't found
        """
        profile = self.get_profile(profile_id)
        if not profile:
            return ValidationResult(False, ["Profile not found"], [])
        
        return self.validator.validate(profile)
    
    def clear_cache(self):
        """Clear the in-memory profile cache."""
        self.cache = {}
    
    def rebuild_index(self):
        """Rebuild the profile index."""
        self.index.rebuild_index()
    
    def get_profile_count(self) -> int:
        """
        Get the total number of profiles.
        
        Returns:
            The number of profiles
        """
        return len(self.storage.list())
