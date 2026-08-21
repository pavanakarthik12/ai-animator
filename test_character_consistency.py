"""Tests for Character Consistency Validation - Phase 1.5

All tests are deterministic with no random data.
"""

import unittest
import math
from character_model import CharacterModel, Skeleton, CharacterDimensions
from character_consistency import (
    ConsistencyValidator,
    ConsistencyResult,
    BoneViolation,
    validate_pose,
    validate_sequence
)


class TestConsistencyValidator(unittest.TestCase):
    """Test suite for character consistency validation."""
    
    def setUp(self):
        """Create a standard test character."""
        # Define skeleton hierarchy
        hierarchy = {
            "root": None,
            "torso": "root",
            "neck": "torso",
            "head": "neck",
            "shoulder_l": "torso",
            "elbow_l": "shoulder_l",
            "hand_l": "elbow_l",
            "shoulder_r": "torso",
            "elbow_r": "shoulder_r",
            "hand_r": "elbow_r",
            "hip_l": "root",
            "knee_l": "hip_l",
            "foot_l": "knee_l",
            "hip_r": "root",
            "knee_r": "hip_r",
            "foot_r": "knee_r",
        }
        
        # Define neutral pose with known measurements
        neutral_pose = {
            "root": (100.0, 200.0),
            "torso": (100.0, 150.0),
            "neck": (100.0, 130.0),
            "head": (100.0, 110.0),
            "shoulder_l": (80.0, 140.0),
            "elbow_l": (60.0, 160.0),
            "hand_l": (50.0, 180.0),
            "shoulder_r": (120.0, 140.0),
            "elbow_r": (140.0, 160.0),
            "hand_r": (150.0, 180.0),
            "hip_l": (90.0, 200.0),
            "knee_l": (90.0, 240.0),
            "foot_l": (90.0, 270.0),
            "hip_r": (110.0, 200.0),
            "knee_r": (110.0, 240.0),
            "foot_r": (110.0, 270.0),
        }
        
        # Calculate dimensions
        dimensions = CharacterDimensions(
            height=160.0,
            head_width=16.0,
            head_height=20.0,
            torso_width=40.0,
            torso_height=50.0,
            shoulder_width=40.0,
            hip_width=20.0,
            upper_arm_length=28.28,  # sqrt(20^2 + 20^2)
            forearm_length=22.36,    # sqrt(10^2 + 20^2)
            hand_length=0.0,
            thigh_length=40.0,
            shin_length=30.0,
            foot_length=0.0
        )
        
        skeleton = Skeleton(hierarchy)
        self.character = CharacterModel(
            name="test_character",
            skeleton=skeleton,
            neutral_pose=neutral_pose,
            dimensions=dimensions
        )
        
        self.validator = ConsistencyValidator(length_tolerance_ratio=0.01)
    
    def test_1_valid_neutral_pose(self):
        """Test 1: Valid neutral pose should pass."""
        result = self.validator.validate_pose(self.character, self.character.neutral_pose)
        self.assertTrue(result.valid, f"Neutral pose should be valid: {result}")
        self.assertEqual(len(result.errors), 0)
        self.assertEqual(len(result.violations), 0)
    
    def test_2_rotated_limbs_unchanged_lengths(self):
        """Test 2: Rotated limbs with unchanged bone lengths should pass."""
        # Create a pose with rotated left arm but same bone lengths
        pose = dict(self.character.neutral_pose)
        
        # Rotate left arm: keep upper arm length = 28.28, forearm length = 22.36
        # Upper arm: shoulder_l (80, 140) -> elbow_l at distance 28.28
        # Calculate exact position: dx=-20, dy=20 originally, rotate to dx=0, dy=28.28
        pose["elbow_l"] = (80.0, 168.28)  # Directly below shoulder
        # Forearm: elbow_l -> hand_l at distance 22.36
        # Keep same relative length
        pose["hand_l"] = (80.0, 190.64)  # Directly below elbow
        
        result = self.validator.validate_pose(self.character, pose)
        self.assertTrue(result.valid, f"Rotated pose should be valid: {result}")
        self.assertEqual(len(result.errors), 0)
        self.assertEqual(len(result.violations), 0)
    
    def test_3_float_variation_within_tolerance(self):
        """Test 3: Slight floating-point variation within tolerance should pass."""
        pose = dict(self.character.neutral_pose)
        
        # Add 0.5% deviation to left forearm (within 1% tolerance)
        # Original: elbow_l (60, 160) -> hand_l (50, 180), length = 22.36
        # New length: 22.36 * 1.005 = 22.47
        pose["hand_l"] = (50.0, 180.11)  # Tiny adjustment
        
        result = self.validator.validate_pose(self.character, pose)
        self.assertTrue(result.valid, f"Small deviation should be valid: {result}")
        self.assertEqual(len(result.violations), 0)
    
    def test_4_stretched_upper_arm(self):
        """Test 4: Significantly stretched upper arm should fail."""
        pose = dict(self.character.neutral_pose)
        
        # Stretch left upper arm by 10% (exceeds 1% tolerance)
        # Original: shoulder_l (80, 140) -> elbow_l (60, 160), length = 28.28
        # New length: 28.28 * 1.10 = 31.11
        pose["elbow_l"] = (56.0, 164.0)  # Stretched
        
        result = self.validator.validate_pose(self.character, pose)
        self.assertFalse(result.valid, "Stretched upper arm should be invalid")
        self.assertGreater(len(result.violations), 0)
        
        # Check that left_upper_arm violation was detected
        violation_bones = [v.bone_name for v in result.violations]
        self.assertIn("left_upper_arm", violation_bones)
    
    def test_5_shortened_forearm(self):
        """Test 5: Significantly shortened forearm should fail."""
        pose = dict(self.character.neutral_pose)
        
        # Shorten right forearm by 15% (exceeds 1% tolerance)
        # Original: elbow_r (140, 160) -> hand_r (150, 180), length = 22.36
        # New length: 22.36 * 0.85 = 19.0
        pose["hand_r"] = (145.0, 175.0)  # Shortened
        
        result = self.validator.validate_pose(self.character, pose)
        self.assertFalse(result.valid, "Shortened forearm should be invalid")
        self.assertGreater(len(result.violations), 0)
        
        # Check that right_forearm violation was detected
        violation_bones = [v.bone_name for v in result.violations]
        self.assertIn("right_forearm", violation_bones)
    
    def test_6_stretched_leg(self):
        """Test 6: Significantly stretched leg segment should fail."""
        pose = dict(self.character.neutral_pose)
        
        # Stretch left thigh by 20% (exceeds 1% tolerance)
        # Original: hip_l (90, 200) -> knee_l (90, 240), length = 40.0
        # New length: 40.0 * 1.20 = 48.0
        pose["knee_l"] = (90.0, 248.0)  # Stretched
        
        result = self.validator.validate_pose(self.character, pose)
        self.assertFalse(result.valid, "Stretched leg should be invalid")
        self.assertGreater(len(result.violations), 0)
        
        # Check that left_thigh violation was detected
        violation_bones = [v.bone_name for v in result.violations]
        self.assertIn("left_thigh", violation_bones)
    
    def test_7_missing_joint(self):
        """Test 7: Missing required joint should fail."""
        pose = dict(self.character.neutral_pose)
        del pose["elbow_l"]  # Remove required joint
        
        result = self.validator.validate_pose(self.character, pose)
        self.assertFalse(result.valid, "Missing joint should be invalid")
        self.assertGreater(len(result.errors), 0)
        
        # Check error message mentions missing joint
        error_text = " ".join(result.errors)
        self.assertIn("elbow_l", error_text)
    
    def test_8_invalid_parent(self):
        """Test 8: Pose missing parent joint should fail."""
        pose = dict(self.character.neutral_pose)
        del pose["shoulder_l"]  # Remove parent of elbow_l
        
        result = self.validator.validate_pose(self.character, pose)
        self.assertFalse(result.valid, "Missing parent should be invalid")
        self.assertGreater(len(result.errors), 0)
        
        # Check error mentions parent requirement
        error_text = " ".join(result.errors)
        self.assertIn("shoulder_l", error_text)
    
    def test_9_invalid_hierarchy(self):
        """Test 9: Pose with unknown joint should fail."""
        pose = dict(self.character.neutral_pose)
        pose["unknown_joint"] = (0.0, 0.0)  # Add invalid joint
        
        result = self.validator.validate_pose(self.character, pose)
        self.assertFalse(result.valid, "Unknown joint should be invalid")
        self.assertGreater(len(result.errors), 0)
        
        # Check error mentions unknown joint
        error_text = " ".join(result.errors)
        self.assertIn("unknown_joint", error_text)
    
    def test_10_sequence_with_one_invalid_frame(self):
        """Test 10: Sequence with one invalid frame should identify it."""
        # Create sequence with 3 valid frames and 1 invalid
        valid_pose = dict(self.character.neutral_pose)
        invalid_pose = dict(self.character.neutral_pose)
        
        # Make frame 2 invalid by stretching left upper arm
        invalid_pose["elbow_l"] = (56.0, 164.0)  # 10% stretch
        
        sequence = [valid_pose, valid_pose, invalid_pose, valid_pose]
        
        results = self.validator.validate_sequence(self.character, sequence)
        
        self.assertEqual(len(results), 4)
        self.assertTrue(results[0].valid, "Frame 0 should be valid")
        self.assertTrue(results[1].valid, "Frame 1 should be valid")
        self.assertFalse(results[2].valid, "Frame 2 should be invalid")
        self.assertTrue(results[3].valid, "Frame 3 should be valid")
        
        # Check frame index is recorded
        self.assertEqual(results[2].frame_index, 2)
    
    def test_11_gradual_cumulative_drift(self):
        """Test 11: Gradual drift should be detected against reference."""
        # Create sequence where each frame drifts slightly from previous
        # but all are compared against the stable reference
        
        base_pose = dict(self.character.neutral_pose)
        sequence = []
        
        # Original left upper arm: (80, 140) -> (60, 160), length = 28.28
        
        # Frame 0: valid (no drift)
        sequence.append(dict(base_pose))
        
        # Frame 1: 0.5% drift (valid, within 1% tolerance)
        # New length: 28.28 * 1.005 = 28.42
        pose1 = dict(base_pose)
        pose1["elbow_l"] = (60.0, 160.14)  # Slight stretch
        sequence.append(pose1)
        
        # Frame 2: 1.5% drift from reference (should fail, exceeds 1%)
        # New length: 28.28 * 1.015 = 28.70
        pose2 = dict(base_pose)
        pose2["elbow_l"] = (60.0, 160.42)  # More stretch
        sequence.append(pose2)
        
        # Frame 3: 2.5% drift from reference (should fail, exceeds 1%)
        # New length: 28.28 * 1.025 = 28.99
        pose3 = dict(base_pose)
        pose3["elbow_l"] = (60.0, 160.71)  # Even more stretch
        sequence.append(pose3)
        
        results = self.validator.validate_sequence(self.character, sequence)
        
        # Frame 0 should be valid
        self.assertTrue(results[0].valid)
        
        # Frame 1 should be valid (within tolerance)
        self.assertTrue(results[1].valid)
        
        # Frame 2 should be invalid (exceeds 1% tolerance)
        self.assertFalse(results[2].valid)
        
        # Frame 3 should be invalid (exceeds 1% tolerance)
        self.assertFalse(results[3].valid)
        
        # This proves we're comparing against reference, not frame-to-frame


class TestConvenienceFunctions(unittest.TestCase):
    """Test convenience functions."""
    
    def setUp(self):
        """Create a minimal test character."""
        hierarchy = {
            "root": None,
            "torso": "root",
            "neck": "torso",
            "head": "neck",
            "shoulder_l": "torso",
            "elbow_l": "shoulder_l",
            "hand_l": "elbow_l",
            "shoulder_r": "torso",
            "elbow_r": "shoulder_r",
            "hand_r": "elbow_r",
            "hip_l": "root",
            "knee_l": "hip_l",
            "foot_l": "knee_l",
            "hip_r": "root",
            "knee_r": "hip_r",
            "foot_r": "knee_r",
        }
        
        neutral_pose = {
            "root": (100.0, 200.0),
            "torso": (100.0, 150.0),
            "neck": (100.0, 130.0),
            "head": (100.0, 110.0),
            "shoulder_l": (80.0, 140.0),
            "elbow_l": (60.0, 160.0),
            "hand_l": (50.0, 180.0),
            "shoulder_r": (120.0, 140.0),
            "elbow_r": (140.0, 160.0),
            "hand_r": (150.0, 180.0),
            "hip_l": (90.0, 200.0),
            "knee_l": (90.0, 240.0),
            "foot_l": (90.0, 270.0),
            "hip_r": (110.0, 200.0),
            "knee_r": (110.0, 240.0),
            "foot_r": (110.0, 270.0),
        }
        
        dimensions = CharacterDimensions(
            height=160.0,
            head_width=16.0,
            head_height=20.0,
            torso_width=40.0,
            torso_height=50.0,
            shoulder_width=40.0,
            hip_width=20.0,
            upper_arm_length=28.28,
            forearm_length=22.36,
            hand_length=0.0,
            thigh_length=40.0,
            shin_length=30.0,
            foot_length=0.0
        )
        
        skeleton = Skeleton(hierarchy)
        self.character = CharacterModel(
            name="test_character",
            skeleton=skeleton,
            neutral_pose=neutral_pose,
            dimensions=dimensions
        )
    
    def test_validate_pose_function(self):
        """Test validate_pose convenience function."""
        result = validate_pose(self.character, self.character.neutral_pose)
        self.assertIsInstance(result, ConsistencyResult)
        self.assertTrue(result.valid)
    
    def test_validate_sequence_function(self):
        """Test validate_sequence convenience function."""
        poses = [self.character.neutral_pose, self.character.neutral_pose]
        results = validate_sequence(self.character, poses)
        self.assertEqual(len(results), 2)
        self.assertIsInstance(results[0], ConsistencyResult)
        self.assertTrue(all(r.valid for r in results))


class TestConsistencyResult(unittest.TestCase):
    """Test ConsistencyResult class."""
    
    def test_result_creation(self):
        """Test basic result creation."""
        result = ConsistencyResult(valid=True)
        self.assertTrue(result.valid)
        self.assertEqual(len(result.errors), 0)
        self.assertEqual(len(result.warnings), 0)
        self.assertEqual(len(result.violations), 0)
    
    def test_add_error(self):
        """Test adding errors invalidates result."""
        result = ConsistencyResult(valid=True)
        result.add_error("test error")
        self.assertFalse(result.valid)
        self.assertEqual(len(result.errors), 1)
    
    def test_add_violation(self):
        """Test adding violations invalidates result."""
        result = ConsistencyResult(valid=True)
        violation = BoneViolation(
            bone_name="test",
            parent_joint="a",
            child_joint="b",
            expected_length=10.0,
            actual_length=12.0,
            deviation=2.0,
            deviation_ratio=0.2
        )
        result.add_violation(violation)
        self.assertFalse(result.valid)
        self.assertEqual(len(result.violations), 1)
    
    def test_str_representation(self):
        """Test string representation."""
        result = ConsistencyResult(valid=True, frame_index=5)
        result_str = str(result)
        self.assertIn("VALID", result_str)
        self.assertIn("frame 5", result_str)


if __name__ == "__main__":
    unittest.main()
