"""Unit tests for CharacterModel - Phase 1.

These tests do NOT require:
- Krita
- MCP
- Groq
- Network access
- Reference images
"""

import unittest
import math
from character_model import (
    CharacterModel,
    CharacterDimensions,
    Skeleton,
    JointConstraints,
)
from animation_planner import BONE_HIERARCHY


class TestCharacterDimensions(unittest.TestCase):
    """Test CharacterDimensions validation."""
    
    def test_valid_dimensions(self):
        """Valid dimensions should not raise errors."""
        dims = CharacterDimensions(
            height=200.0,
            head_width=30.0,
            head_height=40.0,
            torso_width=50.0,
            torso_height=80.0,
            shoulder_width=60.0,
            hip_width=50.0,
            upper_arm_length=40.0,
            forearm_length=35.0,
            hand_length=15.0,
            thigh_length=50.0,
            shin_length=45.0,
            foot_length=20.0
        )
        self.assertTrue(dims.validate())
    
    def test_negative_height_raises_error(self):
        """Negative height should raise ValueError."""
        with self.assertRaises(ValueError):
            CharacterDimensions(
                height=-100.0,
                head_width=30.0,
                head_height=40.0,
                torso_width=50.0,
                torso_height=80.0,
                shoulder_width=60.0,
                hip_width=50.0,
                upper_arm_length=40.0,
                forearm_length=35.0,
                hand_length=15.0,
                thigh_length=50.0,
                shin_length=45.0,
                foot_length=20.0
            )
    
    def test_zero_height_raises_error(self):
        """Zero height should raise ValueError."""
        with self.assertRaises(ValueError):
            CharacterDimensions(
                height=0.0,
                head_width=30.0,
                head_height=40.0,
                torso_width=50.0,
                torso_height=80.0,
                shoulder_width=60.0,
                hip_width=50.0,
                upper_arm_length=40.0,
                forearm_length=35.0,
                hand_length=15.0,
                thigh_length=50.0,
                shin_length=45.0,
                foot_length=20.0
            )


class TestSkeleton(unittest.TestCase):
    """Test Skeleton structure and validation."""
    
    def test_valid_skeleton(self):
        """Valid skeleton should not raise errors."""
        skeleton = Skeleton(BONE_HIERARCHY)
        self.assertIsNotNone(skeleton)
    
    def test_has_required_joints(self):
        """Skeleton should have all required joints."""
        skeleton = Skeleton(BONE_HIERARCHY)
        required = ["root", "torso", "neck", "head",
                   "shoulder_l", "elbow_l", "hand_l",
                   "shoulder_r", "elbow_r", "hand_r",
                   "hip_l", "knee_l", "foot_l",
                   "hip_r", "knee_r", "foot_r"]
        
        for joint in required:
            self.assertTrue(skeleton.has_joint(joint), f"Missing joint: {joint}")
    
    def test_parent_child_relationships(self):
        """Test specific parent-child relationships."""
        skeleton = Skeleton(BONE_HIERARCHY)
        
        # Left arm chain
        self.assertEqual(skeleton.get_parent("shoulder_l"), "torso")
        self.assertEqual(skeleton.get_parent("elbow_l"), "shoulder_l")
        self.assertEqual(skeleton.get_parent("hand_l"), "elbow_l")
        
        # Right arm chain
        self.assertEqual(skeleton.get_parent("shoulder_r"), "torso")
        self.assertEqual(skeleton.get_parent("elbow_r"), "shoulder_r")
        self.assertEqual(skeleton.get_parent("hand_r"), "elbow_r")
        
        # Left leg chain
        self.assertEqual(skeleton.get_parent("hip_l"), "root")
        self.assertEqual(skeleton.get_parent("knee_l"), "hip_l")
        self.assertEqual(skeleton.get_parent("foot_l"), "knee_l")
        
        # Right leg chain
        self.assertEqual(skeleton.get_parent("hip_r"), "root")
        self.assertEqual(skeleton.get_parent("knee_r"), "hip_r")
        self.assertEqual(skeleton.get_parent("foot_r"), "knee_r")
        
        # Spine chain
        self.assertEqual(skeleton.get_parent("torso"), "root")
        self.assertEqual(skeleton.get_parent("neck"), "torso")
        self.assertEqual(skeleton.get_parent("head"), "neck")
    
    def test_circular_hierarchy_rejected(self):
        """Circular hierarchy should raise ValueError."""
        with self.assertRaises(ValueError):
            # Create circular dependency: A -> B -> C -> A
            Skeleton({
                "A": "C",
                "B": "A",
                "C": "B"
            })
    
    def test_get_children(self):
        """Test getting child joints."""
        skeleton = Skeleton(BONE_HIERARCHY)
        
        # Root should have torso and hips as children
        root_children = skeleton.get_children("root")
        self.assertIn("torso", root_children)
        self.assertIn("hip_l", root_children)
        self.assertIn("hip_r", root_children)
        
        # Torso should have neck and shoulders as children
        torso_children = skeleton.get_children("torso")
        self.assertIn("neck", torso_children)
        self.assertIn("shoulder_l", torso_children)
        self.assertIn("shoulder_r", torso_children)


class TestCharacterModel(unittest.TestCase):
    """Test CharacterModel creation and validation."""
    
    def setUp(self):
        """Create a simple test character."""
        self.test_joints = {
            "root": (400.0, 500.0),
            "torso": (400.0, 420.0),
            "neck": (400.0, 380.0),
            "head": (400.0, 350.0),
            "shoulder_l": (380.0, 395.0),
            "elbow_l": (360.0, 435.0),
            "hand_l": (350.0, 470.0),
            "shoulder_r": (420.0, 395.0),
            "elbow_r": (440.0, 435.0),
            "hand_r": (450.0, 470.0),
            "hip_l": (385.0, 500.0),
            "knee_l": (380.0, 550.0),
            "foot_l": (375.0, 590.0),
            "hip_r": (415.0, 500.0),
            "knee_r": (420.0, 550.0),
            "foot_r": (425.0, 590.0),
        }
    
    def test_create_from_rest_joints(self):
        """Test creating CharacterModel from rest joints."""
        model = CharacterModel.from_rest_joints(
            name="TestCharacter",
            rest_joints=self.test_joints
        )
        
        self.assertEqual(model.name, "TestCharacter")
        self.assertIsNotNone(model.skeleton)
        self.assertIsNotNone(model.dimensions)
        self.assertEqual(len(model.neutral_pose), len(self.test_joints))
    
    def test_required_joints_validated(self):
        """Missing required joints should raise ValueError."""
        incomplete_joints = {
            "root": (400.0, 500.0),
            "torso": (400.0, 420.0),
            # Missing other required joints
        }
        
        with self.assertRaises(ValueError):
            CharacterModel.from_rest_joints(
                name="Incomplete",
                rest_joints=incomplete_joints
            )
    
    def test_limb_lengths_positive(self):
        """Limb lengths should be positive."""
        model = CharacterModel.from_rest_joints(
            name="TestCharacter",
            rest_joints=self.test_joints
        )
        
        # Check left arm
        upper_arm = model.get_limb_length("elbow_l")
        forearm = model.get_limb_length("hand_l")
        self.assertGreater(upper_arm, 0, "Upper arm length should be positive")
        self.assertGreater(forearm, 0, "Forearm length should be positive")
        
        # Check left leg
        thigh = model.get_limb_length("knee_l")
        shin = model.get_limb_length("foot_l")
        self.assertGreater(thigh, 0, "Thigh length should be positive")
        self.assertGreater(shin, 0, "Shin length should be positive")
    
    def test_neutral_pose_contains_all_joints(self):
        """Neutral pose should contain all skeleton joints."""
        model = CharacterModel.from_rest_joints(
            name="TestCharacter",
            rest_joints=self.test_joints
        )
        
        for joint in model.skeleton.get_all_joints():
            self.assertIn(joint, model.neutral_pose,
                         f"Neutral pose missing joint: {joint}")
    
    def test_create_rig(self):
        """Test creating CharacterRig from model."""
        model = CharacterModel.from_rest_joints(
            name="TestCharacter",
            rest_joints=self.test_joints
        )
        
        rig = model.create_rig()
        self.assertIsNotNone(rig)
        self.assertEqual(len(rig.rest_joints), len(self.test_joints))
    
    def test_dimensions_calculated(self):
        """Test that dimensions are calculated from joints."""
        model = CharacterModel.from_rest_joints(
            name="TestCharacter",
            rest_joints=self.test_joints
        )
        
        dims = model.dimensions
        self.assertGreater(dims.height, 0)
        self.assertGreater(dims.upper_arm_length, 0)
        self.assertGreater(dims.forearm_length, 0)
        self.assertGreater(dims.thigh_length, 0)
        self.assertGreater(dims.shin_length, 0)


class TestJointConstraints(unittest.TestCase):
    """Test JointConstraints."""
    
    def test_create_constraints(self):
        """Test creating joint constraints."""
        constraints = JointConstraints(
            min_rotation=-math.pi / 2,
            max_rotation=math.pi / 2,
            preferred_bend_direction=0.0,
            locked=False
        )
        
        self.assertEqual(constraints.min_rotation, -math.pi / 2)
        self.assertEqual(constraints.max_rotation, math.pi / 2)
        self.assertFalse(constraints.locked)


class TestRegression(unittest.TestCase):
    """Test that existing functionality is not broken."""
    
    def test_imports_work(self):
        """Test that module imports don't break."""
        # These should not raise ImportError
        from character_model import CharacterModel, Skeleton
        from animation_planner import CharacterRig, BONE_HIERARCHY
        
        self.assertTrue(True)  # If we got here, imports work
    
    def test_existing_bone_hierarchy_unchanged(self):
        """Verify BONE_HIERARCHY still has expected structure."""
        self.assertIn("root", BONE_HIERARCHY)
        self.assertIn("torso", BONE_HIERARCHY)
        self.assertIn("head", BONE_HIERARCHY)
        self.assertEqual(BONE_HIERARCHY["torso"], "root")
        self.assertEqual(BONE_HIERARCHY["head"], "neck")


def run_tests():
    """Run all tests and print results."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(__import__(__name__))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "="*60)
    print("PHASE 1 TEST RESULTS")
    print("="*60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success: {result.wasSuccessful()}")
    print("="*60)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
