"""
Test module for the exposure tracking system.

This module contains tests for the core functionality of the exposure tracking system,
including record creation, history management, metrics calculation, and integration
with sensitivity profiles.
"""

import unittest
import os
import json
import tempfile
import shutil
from datetime import datetime, timedelta

from envirosense.core.exposure.records import (
    ExposureRecord,
    ExposureHistory
)
from envirosense.core.exposure.assessment import (
    ExposureAssessment,
    PersonalizedExposureAssessment,
    RiskLevel
)
from envirosense.core.exposure.storage import (
    ExposureStorage
)


class TestExposureRecords(unittest.TestCase):
    """Test case for ExposureRecord class."""
    
    def test_record_creation(self):
        """Test creation of exposure records."""
        # Create a simple record
        record = ExposureRecord(
            chemical_id="formaldehyde",
            concentration=0.05,
            duration=1800,  # 30 minutes in seconds
            location_id="kitchen"
        )
        
        # Check the basic properties
        self.assertIsNotNone(record.record_id)
        self.assertEqual(record.chemical_id, "formaldehyde")
        self.assertEqual(record.concentration, 0.05)
        self.assertEqual(record.duration, 1800)
        self.assertEqual(record.location_id, "kitchen")
        
        # Check automatic fields
        self.assertIsNotNone(record.timestamp)
        
        # Check computed properties
        self.assertEqual(record.dose, record.concentration * record.duration)
        
        # Check serialization/deserialization
        record_dict = record.to_dict()
        new_record = ExposureRecord.from_dict(record_dict)
        self.assertEqual(record.record_id, new_record.record_id)
        self.assertEqual(record.chemical_id, new_record.chemical_id)
        self.assertEqual(record.concentration, new_record.concentration)


class TestExposureHistory(unittest.TestCase):
    """Test case for ExposureHistory class."""
    
    def setUp(self):
        """Set up test data."""
        self.history = ExposureHistory()
        
        # Create some test records at different times
        self.now = datetime.now()
        
        # Record 1: 8 hours ago
        self.record1 = ExposureRecord(
            timestamp=(self.now - timedelta(hours=8)).isoformat(),
            chemical_id="formaldehyde",
            concentration=0.05,
            duration=1800
        )
        
        # Record 2: 4 hours ago
        self.record2 = ExposureRecord(
            timestamp=(self.now - timedelta(hours=4)).isoformat(),
            chemical_id="formaldehyde",
            concentration=0.1,
            duration=1800
        )
        
        # Record 3: 2 hours ago
        self.record3 = ExposureRecord(
            timestamp=(self.now - timedelta(hours=2)).isoformat(),
            chemical_id="formaldehyde",
            concentration=0.15,
            duration=1800
        )
        
        # Record 4: 1 hour ago, different chemical
        self.record4 = ExposureRecord(
            timestamp=(self.now - timedelta(hours=1)).isoformat(),
            chemical_id="co",
            concentration=15.0,
            duration=1800
        )
        
        # Add records to history
        self.history.add_records([self.record1, self.record2, self.record3, self.record4])
    
    def test_add_record(self):
        """Test adding records to history."""
        # Create a new history
        history = ExposureHistory()
        self.assertEqual(len(history.records), 0)
        
        # Add a single record
        history.add_record(self.record1)
        self.assertEqual(len(history.records), 1)
        
        # Add multiple records
        history.add_records([self.record2, self.record3])
        self.assertEqual(len(history.records), 3)
    
    def test_get_records_by_chemical(self):
        """Test filtering records by chemical."""
        # Get formaldehyde records
        formaldehyde_records = self.history.get_records_by_chemical("formaldehyde")
        self.assertEqual(len(formaldehyde_records), 3)
        
        # Get CO records
        co_records = self.history.get_records_by_chemical("co")
        self.assertEqual(len(co_records), 1)
    
    def test_get_records_by_timerange(self):
        """Test filtering records by time range."""
        # Get records from last 3 hours
        recent_records = self.history.get_records_by_timerange(
            self.now - timedelta(hours=3),
            self.now
        )
        self.assertEqual(len(recent_records), 2)  # Should include record3 and record4
    
    def test_calculate_twa(self):
        """Test time-weighted average calculation."""
        # Create a history with evenly spaced readings
        history = ExposureHistory()
        
        # Add records at 1-hour intervals with varying concentrations
        base_time = datetime.now() - timedelta(hours=8)
        
        for i in range(9):  # 0 to 8 hours
            record = ExposureRecord(
                timestamp=(base_time + timedelta(hours=i)).isoformat(),
                chemical_id="test_chemical",
                concentration=i * 0.1,  # 0.0, 0.1, 0.2, ..., 0.8
                duration=3600  # 1 hour in seconds
            )
            history.add_record(record)
        
        # Calculate 8-hour TWA
        twa = history.calculate_twa(
            "test_chemical", 
            8 * 3600,  # 8 hours in seconds
            end_time=base_time + timedelta(hours=8)
        )
        
        # Expected value: average of 0.0, 0.1, 0.2, ..., 0.7 = 0.4 using trapezoid rule
        # Note: The trapezoid rule gives a different result than a simple average
        self.assertAlmostEqual(twa, 0.4, places=2)
    
    def test_calculate_peak(self):
        """Test peak concentration calculation."""
        # The peak formaldehyde concentration should be from record3
        peak = self.history.calculate_peak("formaldehyde")
        self.assertEqual(peak, 0.15)
    
    def test_serialization(self):
        """Test serialization and deserialization of history."""
        # Convert to dictionary
        history_dict = self.history.to_dict()
        
        # Create new history from dictionary
        new_history = ExposureHistory.from_dict(history_dict)
        
        # Check that the new history has the same number of records
        self.assertEqual(len(self.history.records), len(new_history.records))
        
        # Check that the records have the same chemical IDs
        self.assertEqual(
            set(r.chemical_id for r in self.history.records),
            set(r.chemical_id for r in new_history.records)
        )


class TestExposureAssessment(unittest.TestCase):
    """Test case for ExposureAssessment class."""
    
    def setUp(self):
        """Set up test data."""
        self.history = ExposureHistory()
        
        # Create some test records at different times
        self.now = datetime.now()
        
        # Create formaldehyde records with increasing concentration
        for i in range(8):
            record = ExposureRecord(
                timestamp=(self.now - timedelta(hours=8-i)).isoformat(),
                chemical_id="formaldehyde",
                concentration=0.05 * (i+1),  # 0.05, 0.1, 0.15, ..., 0.4
                duration=3600  # 1 hour in seconds
            )
            self.history.add_record(record)
        
        # Create a standard assessment
        self.assessment = ExposureAssessment(self.history)
    
    def test_assess_chemical(self):
        """Test standard chemical assessment."""
        # Assess formaldehyde
        result = self.assessment.assess_chemical("formaldehyde")
        
        # Check basic structure
        self.assertEqual(result["chemical_id"], "formaldehyde")
        self.assertIn("metrics", result)
        self.assertIn("risk_level", result)
        
        # Check metrics
        metrics = result["metrics"]
        self.assertIn("8hr_twa", metrics)
        self.assertIn("peak_concentration", metrics)
        
        # Expected 8hr TWA: average of 0.05, 0.1, 0.15, ..., 0.4 = 0.24375 using trapezoid rule
        # Note: The trapezoid rule gives a different result than a simple average
        self.assertAlmostEqual(metrics["8hr_twa"], 0.24375, places=2)
        
        # Expected peak: 0.4
        self.assertEqual(metrics["peak_concentration"], 0.4)


class TestPersonalizedAssessment(unittest.TestCase):
    """Test case for PersonalizedExposureAssessment class."""
    
    def setUp(self):
        """Set up test data."""
        self.history = ExposureHistory()
        
        # Create some test records
        self.now = datetime.now()
        
        # Create formaldehyde records with concentration above NIOSH REL
        for i in range(8):
            # NIOSH REL for formaldehyde is 0.016 ppm
            # We'll set concentrations to exceed this
            record = ExposureRecord(
                timestamp=(self.now - timedelta(hours=8-i)).isoformat(),
                chemical_id="formaldehyde",
                concentration=0.02 * (i+1),  # 0.02, 0.04, 0.06, ..., 0.16
                duration=3600  # 1 hour in seconds
            )
            self.history.add_record(record)
        
        # Create a test sensitivity profile
        self.profile = {
            "profile_id": "test_profile",
            "demographics": {
                "age": 72,
                "age_group": "elderly"
            },
            "conditions": ["copd"],
            "sensitivity_scores": {
                "respiratory": 2.0
            }
        }
        
        # Create personalized assessment
        self.personalized = PersonalizedExposureAssessment(self.history, self.profile)
    
    def test_get_sensitivity_factor(self):
        """Test sensitivity factor calculation."""
        # Get sensitivity factor for formaldehyde
        factor = self.personalized.get_sensitivity_factor("formaldehyde")
        
        # Should be higher than 1.0 due to elderly + copd condition
        self.assertGreater(factor, 1.0)
    
    def test_personalized_assessment(self):
        """Test personalized assessment."""
        # Get standard and personalized assessments
        standard = ExposureAssessment(self.history).assess_chemical("formaldehyde")
        personalized = self.personalized.assess_chemical("formaldehyde")
        
        # Check that personalized assessment is marked as such
        self.assertTrue(personalized.get("personalized", False))
        
        # Check that sensitivity factor is included
        self.assertIn("sensitivity_factor", personalized)
        
        # Check that adjusted metrics are included
        self.assertIn("adjusted_8hr_twa", personalized["metrics"])
        
        # The personalized adjusted TWA should be higher than the standard TWA
        self.assertGreater(
            personalized["metrics"]["adjusted_8hr_twa"],
            standard["metrics"]["8hr_twa"]
        )
        
        # The risk level might be escalated
        risk_levels = list(RiskLevel.__members__.keys())
        standard_idx = risk_levels.index(standard["risk_level"])
        personalized_idx = risk_levels.index(personalized["risk_level"])
        
        # The personalized risk level should be at least as high as the standard one
        self.assertGreaterEqual(personalized_idx, standard_idx)


class TestExposureStorage(unittest.TestCase):
    """Test case for ExposureStorage class."""
    
    def setUp(self):
        """Set up test data and temporary directory."""
        # Create temporary directory for testing
        self.temp_dir = tempfile.mkdtemp()
        self.storage = ExposureStorage(base_dir=self.temp_dir)
        
        # Create a test history with some records
        self.history = ExposureHistory()
        self.record = ExposureRecord(
            chemical_id="formaldehyde",
            concentration=0.05,
            duration=1800
        )
        self.history.add_record(self.record)
    
    def tearDown(self):
        """Clean up after tests."""
        # Remove temporary directory
        shutil.rmtree(self.temp_dir)
    
    def test_save_load_record(self):
        """Test saving and loading individual records."""
        # Save record as JSON
        filepath = self.storage.save_record(self.record, format="json")
        
        # Check that file exists
        self.assertTrue(os.path.exists(filepath))
        
        # Load record
        loaded_record = self.storage.load_record(filepath)
        
        # Check that loaded record matches original
        self.assertEqual(self.record.record_id, loaded_record.record_id)
        self.assertEqual(self.record.chemical_id, loaded_record.chemical_id)
        self.assertEqual(self.record.concentration, loaded_record.concentration)
    
    def test_save_load_history(self):
        """Test saving and loading exposure histories."""
        # Save history as JSON
        filepath = self.storage.save_history(self.history, format="json")
        
        # Check that file exists
        self.assertTrue(os.path.exists(filepath))
        
        # Load history
        loaded_history = self.storage.load_history(filepath)
        
        # Check that loaded history has the same ID
        self.assertEqual(self.history.history_id, loaded_history.history_id)
        
        # Check that loaded history has same number of records
        self.assertEqual(len(self.history.records), len(loaded_history.records))
    
    def test_backup_creation(self):
        """Test creating backups."""
        # Save some data first
        self.storage.save_record(self.record)
        self.storage.save_history(self.history)
        
        # Create backup
        backup_dir = self.storage.create_backup()
        
        # Check that backup directory exists
        self.assertTrue(os.path.exists(backup_dir))
        
        # Check that files were copied
        records_dir = os.path.join(backup_dir, "records")
        histories_dir = os.path.join(backup_dir, "histories")
        
        self.assertTrue(os.path.exists(records_dir))
        self.assertTrue(os.path.exists(histories_dir))
        
        # Should have at least one file in each directory
        self.assertGreater(len(os.listdir(records_dir)), 0)
        self.assertGreater(len(os.listdir(histories_dir)), 0)


if __name__ == "__main__":
    unittest.main()
