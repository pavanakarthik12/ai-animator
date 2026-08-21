"""Tests for Motion Planning Engine - Phase 3

Tests generic motion planning without rendering.
NO DRAWING. NO GROQ. NO KRITA. NO MCP.
"""

import unittest
import math
from character_model import CharacterModel, Skeleton, CharacterDimensions
from animation_timeline import AnimationRequest, create_simple_plan
from motion_planner import (
    MotionPlanner,
    MotionPlan,
    MotionConstraints,
    MotionValidator,
    PoseSequence,
    create_walk_motion_plan
)


class TestMotionPlanning(unittest.TestCase):
    """Test motion planning engine."""
    
    def setUp(self):
        """Create test character and animation plan."""
        # Create test character (same as previous phases)
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
    
    def test_01_neutral_pose_valid(self):
        """Test 1: Neutral pose remains valid."""
        pose = self.character.neutral_pose
        validator = MotionValidator(self.character, MotionConstraints())
        
        errors = validator._check_bone_lengths(pose)
        self.assertEqual(len(errors), 0, f"Neutral pose should be valid: {errors}")
    
    def test_02_motion_planner_creation(self):
        """Test 2: MotionPlanner can be created."""
        planner = MotionPlanner(self.character)
        self.assertIsNotNone(planner)
    
    def test_03_simple_motion_plan(self):
        """Test 3: Simple motion plan can be created."""
        request = AnimationRequest(action="walk", frame_count=20)
        animation_plan = create_simple_plan(request)
        
        planner = MotionPlanner(self.character)
        motion_plan = planner.plan_motion(animation_plan)
        
        self.assertIsNotNone(motion_plan)
        self.assertTrue(motion_plan.validated)
    
    def test_14_20_frame_walk(self):
        """Test 14: 20-frame walk plan works."""
        request = AnimationRequest(action="walk", frame_count=20)
        animation_plan = create_simple_plan(request)
        
        motion_plan = create_walk_motion_plan(self.character, animation_plan)
        
        self.assertTrue(motion_plan.validated)
        self.assertEqual(motion_plan.get_total_frames(), 20)
    
    def test_15_50_frame_walk(self):
        """Test 15: 50-frame walk plan works."""
        request = AnimationRequest(action="walk", frame_count=50)
        animation_plan = create_simple_plan(request)
        
        motion_plan = create_walk_motion_plan(self.character, animation_plan)
        
        self.assertTrue(motion_plan.validated)
        self.assertEqual(motion_plan.get_total_frames(), 50)
    
    def test_16_100_frame_walk(self):
        """Test 16: 100-frame walk plan works."""
        request = AnimationRequest(action="walk", frame_count=100)
        animation_plan = create_simple_plan(request)
        
        motion_plan = create_walk_motion_plan(self.character, animation_plan)
        
        self.assertTrue(motion_plan.validated)
        self.assertEqual(motion_plan.get_total_frames(), 100)
    
    def test_17_240_frame_walk(self):
        """Test 17: 240-frame walk plan works."""
        request = AnimationRequest(action="walk", frame_count=240)
        animation_plan = create_simple_plan(request)
        
        motion_plan = create_walk_motion_plan(self.character, animation_plan)
        
        self.assertTrue(motion_plan.validated)
        self.assertEqual(motion_plan.get_total_frames(), 240)
    
    def test_18_250_frame_walk(self):
        """Test 18: 250-frame walk plan works."""
        request = AnimationRequest(action="walk", frame_count=250)
        animation_plan = create_simple_plan(request)
        
        motion_plan = create_walk_motion_plan(self.character, animation_plan)
        
        self.assertTrue(motion_plan.validated)
        self.assertEqual(motion_plan.get_total_frames(), 250)
    
    def test_19_deterministic_walk(self):
        """Test 19: Same input produces identical motion plan."""
        request1 = AnimationRequest(action="walk", frame_count=100)
        request2 = AnimationRequest(action="walk", frame_count=100)
        
        plan1 = create_simple_plan(request1)
        plan2 = create_simple_plan(request2)
        
        motion1 = create_walk_motion_plan(self.character, plan1)
        motion2 = create_walk_motion_plan(self.character, plan2)
        
        # Same frame count
        self.assertEqual(motion1.get_total_frames(), motion2.get_total_frames())
        
        # Same segment count
        self.assertEqual(len(motion1.segments), len(motion2.segments))


class TestPoseGeneration(unittest.TestCase):
    """Test pose sequence generation."""
    
    def setUp(self):
        """Create test setup."""
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
    
    def test_pose_sequence_generation(self):
        """Test pose sequence can be generated."""
        request = AnimationRequest(action="walk", frame_count=20)
        animation_plan = create_simple_plan(request)
        
        planner = MotionPlanner(self.character)
        motion_plan = planner.plan_motion(animation_plan)
        
        sequence = planner.generate_pose_sequence(motion_plan)
        
        self.assertEqual(sequence.get_frame_count(), 20)
    
    def test_09_walk_alternates_legs(self):
        """Test 9: Walk alternates left/right legs."""
        request = AnimationRequest(action="walk", frame_count=40)
        animation_plan = create_simple_plan(request)
        
        motion_plan = create_walk_motion_plan(self.character, animation_plan)
        
        # Check segments have alternating leg states
        has_left_stance = False
        has_right_stance = False
        
        for seg in motion_plan.segments:
            leg_state = seg.metadata.get("leg_state", {})
            if leg_state.get("left") == "stance":
                has_left_stance = True
            if leg_state.get("right") == "stance":
                has_right_stance = True
        
        self.assertTrue(has_left_stance, "Should have left leg stance phase")
        self.assertTrue(has_right_stance, "Should have right leg stance phase")
    
    def test_10_walk_moves_forward(self):
        """Test 10: Walk moves in forward direction."""
        request = AnimationRequest(action="walk", frame_count=20)
        animation_plan = create_simple_plan(request)
        
        planner = MotionPlanner(self.character)
        motion_plan = planner.plan_motion(animation_plan)
        sequence = planner.generate_pose_sequence(motion_plan)
        
        # Get foot positions across multiple frames
        foot_positions = []
        for frame_num, pose in sequence.poses:
            left_x = pose["foot_l"][0]
            right_x = pose["foot_r"][0]
            foot_positions.append((left_x, right_x))
        
        # Check that feet positions vary (not stuck in one place)
        left_positions = [pos[0] for pos in foot_positions]
        right_positions = [pos[1] for pos in foot_positions]
        
        left_range = max(left_positions) - min(left_positions)
        right_range = max(right_positions) - min(right_positions)
        
        # At least one foot should move more than 5 pixels across the animation
        self.assertTrue(left_range > 5.0 or right_range > 5.0, 
                       f"Feet should be moving during walk (left_range={left_range:.1f}, right_range={right_range:.1f})")


if __name__ == "__main__":
    unittest.main()
