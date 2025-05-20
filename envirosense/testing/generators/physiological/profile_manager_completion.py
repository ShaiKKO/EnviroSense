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
