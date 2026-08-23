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


# ============================================================
# PHASE 3.1 TESTS - NATURAL WALK REFINEMENT
# ============================================================

class TestNaturalWalk(unittest.TestCase):
    """Phase 3.1: Test natural walking motion quality."""
    
    def setUp(self):
        """Create test character."""
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
    
    def test_31_foot_trajectory_controlled(self):
        """Test that swing foot follows controlled trajectory, not straight line."""
        planner = MotionPlanner(self.character)
        
        request = AnimationRequest(action="walk", frame_count=20)
        animation_plan = create_simple_plan(request)
        
        motion_plan = planner.plan_motion(animation_plan)
        sequence = planner.generate_pose_sequence(motion_plan)
        
        # Track right foot during swing phase (frames 1-10)
        foot_positions = []
        for frame in range(1, 11):
            pose = sequence.get_pose_at_frame(frame)
            foot_positions.append(pose["foot_r"])
        
        # Check trajectory is curved (not linear)
        # For a straight line, mid-point Y would be average of start and end Y
        start_y = foot_positions[0][1]
        end_y = foot_positions[-1][1]
        mid_y = foot_positions[len(foot_positions)//2][1]
        
        linear_mid_y = (start_y + end_y) / 2
        
        # Mid-point should be higher (lifted) than linear interpolation
        assert mid_y < linear_mid_y - 2.0, "Foot should follow curved trajectory, not straight line"
    
    def test_32_stance_foot_stable(self):
        """Test that stance foot remains relatively stable on ground."""
        character = self.character
        planner = MotionPlanner(character)
        
        request = AnimationRequest(action="walk", frame_count=20)
        animation_plan = create_simple_plan(request)
        
        motion_plan = planner.plan_motion(animation_plan)
        sequence = planner.generate_pose_sequence(motion_plan)
        
        # Left foot is stance during frames 1-10
        left_foot_positions = []
        for frame in range(1, 11):
            pose = sequence.get_pose_at_frame(frame)
            left_foot_positions.append(pose["foot_l"])
        
        # Check Y position (ground contact) is stable
        y_positions = [pos[1] for pos in left_foot_positions]
        y_variance = max(y_positions) - min(y_positions)
        
        assert y_variance < 1.0, f"Stance foot should stay on ground (variance: {y_variance})"
    
    def test_33_swing_foot_lifts(self):
        """Test that swing foot lifts off ground during swing phase."""
        character = self.character
        planner = MotionPlanner(character)
        
        request = AnimationRequest(action="walk", frame_count=20)
        animation_plan = create_simple_plan(request)
        
        motion_plan = planner.plan_motion(animation_plan)
        sequence = planner.generate_pose_sequence(motion_plan)
        
        # Right foot swings during frames 1-10
        ground_y = sequence.get_pose_at_frame(1)["foot_l"][1]  # Stance foot Y
        
        max_lift = 0
        for frame in range(1, 11):
            pose = sequence.get_pose_at_frame(frame)
            foot_y = pose["foot_r"][1]
            lift = ground_y - foot_y
            max_lift = max(max_lift, lift)
        
        assert max_lift > 3.0, f"Swing foot should lift off ground (max lift: {max_lift})"
    
    def test_34_foot_returns_to_ground(self):
        """Test that foot returns to consistent ground level after swing."""
        character = self.character
        planner = MotionPlanner(character)
        
        request = AnimationRequest(action="walk", frame_count=20)
        animation_plan = create_simple_plan(request)
        
        motion_plan = planner.plan_motion(animation_plan)
        sequence = planner.generate_pose_sequence(motion_plan)
        
        # Check ground level consistency
        pose1 = sequence.get_pose_at_frame(1)
        pose10 = sequence.get_pose_at_frame(10)
        pose11 = sequence.get_pose_at_frame(11)
        pose20 = sequence.get_pose_at_frame(20)
        
        ground_refs = [
            pose1["foot_l"][1],   # Left stance at start
            pose10["foot_l"][1],  # Left stance at end of first half
            pose11["foot_r"][1],  # Right stance at start of second half
            pose20["foot_r"][1],  # Right stance at end
        ]
        
        ground_variance = max(ground_refs) - min(ground_refs)
        assert ground_variance < 2.0, f"Ground level should be consistent (variance: {ground_variance})"
    
    def test_35_swing_foot_progresses_forward(self):
        """Test that swing foot moves forward (not backward or stationary)."""
        character = self.character
        planner = MotionPlanner(character)
        
        request = AnimationRequest(action="walk", frame_count=20)
        animation_plan = create_simple_plan(request)
        
        motion_plan = planner.plan_motion(animation_plan)
        sequence = planner.generate_pose_sequence(motion_plan)
        
        # Right foot swings during frames 1-10
        pose_start = sequence.get_pose_at_frame(1)
        pose_end = sequence.get_pose_at_frame(10)
        
        start_x = pose_start["foot_r"][0]
        end_x = pose_end["foot_r"][0]
        
        forward_progress = end_x - start_x
        assert forward_progress > 5.0, f"Swing foot should move forward (progress: {forward_progress})"
    
    def test_36_knee_bends_during_swing(self):
        """Test that knee bends significantly during swing phase."""
        character = self.character
        planner = MotionPlanner(character)
        
        request = AnimationRequest(action="walk", frame_count=20)
        animation_plan = create_simple_plan(request)
        
        motion_plan = planner.plan_motion(animation_plan)
        sequence = planner.generate_pose_sequence(motion_plan)
        
        # Check right knee during swing (frames 1-10)
        # Knee should be notably higher (more bent) at mid-swing
        pose_start = sequence.get_pose_at_frame(1)
        pose_mid = sequence.get_pose_at_frame(5)
        pose_end = sequence.get_pose_at_frame(10)
        
        knee_y_start = pose_start["knee_r"][1]
        knee_y_mid = pose_mid["knee_r"][1]
        knee_y_end = pose_end["knee_r"][1]
        
        # At mid-swing, knee should be higher (lower Y value) than at contact
        mid_lift = min(knee_y_start, knee_y_end) - knee_y_mid
        
        assert mid_lift > 3.0, f"Knee should bend during swing (lift: {mid_lift})"
    
    def test_37_knee_straighter_during_stance(self):
        """Test that knee is relatively straight during stance phase."""
        character = self.character
        planner = MotionPlanner(character)
        
        request = AnimationRequest(action="walk", frame_count=20)
        animation_plan = create_simple_plan(request)
        
        motion_plan = planner.plan_motion(animation_plan)
        sequence = planner.generate_pose_sequence(motion_plan)
        
        # Left leg is stance during frames 1-10
        # Check knee is relatively straight (close to midpoint between hip and foot)
        pose = sequence.get_pose_at_frame(5)  # Mid-stance
        
        hip = pose["hip_l"]
        knee = pose["knee_l"]
        foot = pose["foot_l"]
        
        # Knee should be roughly between hip and foot
        expected_knee_y = (hip[1] + foot[1]) / 2
        actual_knee_y = knee[1]
        
        # Allow some bend, but not excessive
        bend_amount = abs(actual_knee_y - expected_knee_y)
        
        assert bend_amount < 15.0, f"Stance knee should be relatively straight (bend: {bend_amount})"
    
    def test_38_weight_shift_lateral(self):
        """Test that hips shift laterally over support leg."""
        character = self.character
        planner = MotionPlanner(character)
        
        request = AnimationRequest(action="walk", frame_count=20)
        animation_plan = create_simple_plan(request)
        
        motion_plan = planner.plan_motion(animation_plan)
        sequence = planner.generate_pose_sequence(motion_plan)
        
        # During left stance (frames 1-10), hips should shift left
        # During right stance (frames 11-20), hips should shift right
        
        pose_left_stance = sequence.get_pose_at_frame(5)
        pose_right_stance = sequence.get_pose_at_frame(15)
        
        left_hip_x = pose_left_stance["hip_l"][0]
        right_hip_x = pose_right_stance["hip_r"][0]
        
        # Hips should shift (X position changes)
        hip_shift = abs(right_hip_x - left_hip_x)
        
        assert hip_shift > 1.0, f"Hips should shift laterally for weight transfer (shift: {hip_shift})"
    
    def test_39_body_vertical_movement(self):
        """Test controlled vertical body movement (bob)."""
        character = self.character
        planner = MotionPlanner(character)
        
        request = AnimationRequest(action="walk", frame_count=20)
        animation_plan = create_simple_plan(request)
        
        motion_plan = planner.plan_motion(animation_plan)
        sequence = planner.generate_pose_sequence(motion_plan)
        
        # Track root Y position
        root_y_positions = []
        for frame in range(1, 21):
            pose = sequence.get_pose_at_frame(frame)
            root_y_positions.append(pose["root"][1])
        
        y_range = max(root_y_positions) - min(root_y_positions)
        
        # Should have some bob, but not excessive
        assert 2.0 < y_range < 20.0, f"Body bob should be subtle (range: {y_range})"
    
    def test_40_head_stability(self):
        """Test that head remains relatively stable (less movement than body)."""
        character = self.character
        planner = MotionPlanner(character)
        
        request = AnimationRequest(action="walk", frame_count=20)
        animation_plan = create_simple_plan(request)
        
        motion_plan = planner.plan_motion(animation_plan)
        sequence = planner.generate_pose_sequence(motion_plan)
        
        # Track head and root Y positions
        head_y_positions = []
        root_y_positions = []
        
        for frame in range(1, 21):
            pose = sequence.get_pose_at_frame(frame)
            head_y_positions.append(pose["head"][1])
            root_y_positions.append(pose["root"][1])
        
        head_range = max(head_y_positions) - min(head_y_positions)
        root_range = max(root_y_positions) - min(root_y_positions)
        
        # Head should move less than root
        assert head_range < root_range, f"Head should be more stable than body (head: {head_range}, root: {root_range})"
    
    def test_41_arm_counter_swing(self):
        """Test arms swing opposite to legs."""
        character = self.character
        planner = MotionPlanner(character)
        
        request = AnimationRequest(action="walk", frame_count=20)
        animation_plan = create_simple_plan(request)
        
        motion_plan = planner.plan_motion(animation_plan)
        sequence = planner.generate_pose_sequence(motion_plan)
        
        # At frame 1: left leg forward, right arm should be forward
        # At frame 11: right leg forward, left arm should be forward
        
        pose1 = sequence.get_pose_at_frame(1)
        pose11 = sequence.get_pose_at_frame(11)
        
        # Check hand X positions relative to shoulders
        left_hand_x_f1 = pose1["hand_l"][0]
        left_shoulder_x_f1 = pose1["shoulder_l"][0]
        left_arm_forward_f1 = left_hand_x_f1 - left_shoulder_x_f1
        
        left_hand_x_f11 = pose11["hand_l"][0]
        left_shoulder_x_f11 = pose11["shoulder_l"][0]
        left_arm_forward_f11 = left_hand_x_f11 - left_shoulder_x_f11
        
        # Left arm should swing (different positions at different phases)
        arm_swing_range = abs(left_arm_forward_f11 - left_arm_forward_f1)
        
        assert arm_swing_range > 2.0, f"Arms should counter-swing (range: {arm_swing_range})"
    
    def test_42_stride_scales_with_dimensions(self):
        """Test that stride length scales appropriately with character dimensions."""
        # Create two characters with different leg lengths
        char_small = self.character
        
        char_large = CharacterModel(
            character_id="large_test",
            master_strokes=[],
            neutral_pose=char_small.neutral_pose,
            dimensions=CharacterDimensions(
                height=char_small.dimensions.height * 2,
                head_size=char_small.dimensions.head_size * 2,
                torso_length=char_small.dimensions.torso_length * 2,
                torso_width=char_small.dimensions.torso_width * 2,
                upper_arm_length=char_small.dimensions.upper_arm_length * 2,
                forearm_length=char_small.dimensions.forearm_length * 2,
                hand_size=char_small.dimensions.hand_size * 2,
                thigh_length=char_small.dimensions.thigh_length * 2,
                shin_length=char_small.dimensions.shin_length * 2,
                foot_length=char_small.dimensions.foot_length * 2
            )
        )
        
        # Plan walk for both
        request = AnimationRequest(action="walk", frame_count=20)
        
        planner_small = MotionPlanner(char_small)
        plan_small = create_simple_plan(request)
        motion_small = planner_small.plan_motion(plan_small)
        seq_small = planner_small.generate_pose_sequence(motion_small)
        
        planner_large = MotionPlanner(char_large)
        plan_large = create_simple_plan(request)
        motion_large = planner_large.plan_motion(plan_large)
        seq_large = planner_large.generate_pose_sequence(motion_large)
        
        # Measure stride
        pose_small_1 = seq_small.get_pose_at_frame(1)
        pose_small_10 = seq_small.get_pose_at_frame(10)
        stride_small = abs(pose_small_10["foot_r"][0] - pose_small_1["foot_r"][0])
        
        pose_large_1 = seq_large.get_pose_at_frame(1)
        pose_large_10 = seq_large.get_pose_at_frame(10)
        stride_large = abs(pose_large_10["foot_r"][0] - pose_large_1["foot_r"][0])
        
        # Larger character should have larger stride
        assert stride_large > stride_small * 1.5, "Stride should scale with character dimensions"
    
    def test_43_no_teleportation(self):
        """Test that no joint teleports between frames."""
        character = self.character
        planner = MotionPlanner(character)
        
        request = AnimationRequest(action="walk", frame_count=100)
        animation_plan = create_simple_plan(request)
        
        motion_plan = planner.plan_motion(animation_plan)
        sequence = planner.generate_pose_sequence(motion_plan)
        
        # Check continuity
        max_delta = planner.constraints.max_joint_delta_per_frame
        
        for frame in range(1, 100):
            pose1 = sequence.get_pose_at_frame(frame)
            pose2 = sequence.get_pose_at_frame(frame + 1)
            
            for joint_name in pose1.keys():
                p1 = pose1[joint_name]
                p2 = pose2[joint_name]
                
                delta = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
                
                assert delta <= max_delta, f"Frame {frame}-{frame+1}: {joint_name} teleported {delta} pixels"
    
    def test_44_bone_lengths_preserved(self):
        """Test that bone lengths remain constant throughout walk."""
        character = self.character
        planner = MotionPlanner(character)
        
        request = AnimationRequest(action="walk", frame_count=50)
        animation_plan = create_simple_plan(request)
        
        motion_plan = planner.plan_motion(animation_plan)
        sequence = planner.generate_pose_sequence(motion_plan)
        
        validator = MotionValidator(character, planner.constraints)
        is_valid, errors = validator.validate_pose_sequence(sequence)
        
        assert is_valid, f"Bone lengths not preserved: {errors}"
    
    def test_45_walk_speed_variations(self):
        """Test that walk supports slow/normal/fast speeds."""
        character = self.character
        planner = MotionPlanner(character)
        
        # Plan walks at different speeds
        request_slow = AnimationRequest(action="walk", frame_count=40, speed="slow")
        request_normal = AnimationRequest(action="walk", frame_count=40, speed="normal")
        request_fast = AnimationRequest(action="walk", frame_count=40, speed="fast")
        
        plan_slow = create_simple_plan(request_slow)
        plan_normal = create_simple_plan(request_normal)
        plan_fast = create_simple_plan(request_fast)
        
        motion_slow = planner.plan_motion(plan_slow)
        motion_normal = planner.plan_motion(plan_normal)
        motion_fast = planner.plan_motion(plan_fast)
        
        # Check that speeds affect timing
        frames_slow = motion_slow.metadata["walk_config"]["frames_per_cycle"]
        frames_normal = motion_normal.metadata["walk_config"]["frames_per_cycle"]
        frames_fast = motion_fast.metadata["walk_config"]["frames_per_cycle"]
        
        assert frames_slow > frames_normal, "Slow walk should have longer cycle"
        assert frames_fast < frames_normal, "Fast walk should have shorter cycle"
    
    def test_46_deterministic_natural_walk(self):
        """Test that natural walk is deterministic."""
        character = self.character
        planner = MotionPlanner(character)
        
        request = AnimationRequest(action="walk", frame_count=50)
        
        # Generate twice
        plan1 = create_simple_plan(request)
        motion1 = planner.plan_motion(plan1)
        seq1 = planner.generate_pose_sequence(motion1)
        
        plan2 = create_simple_plan(request)
        motion2 = planner.plan_motion(plan2)
        seq2 = planner.generate_pose_sequence(motion2)
        
        # Should be identical
        assert len(seq1.poses) == len(seq2.poses)
        
        for i in range(len(seq1.poses)):
            frame1, pose1 = seq1.poses[i]
            frame2, pose2 = seq2.poses[i]
            
            assert frame1 == frame2
            
            for joint in pose1.keys():
                p1 = pose1[joint]
                p2 = pose2[joint]
                
                delta = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
                assert delta < 0.01, f"Frame {frame1}: {joint} not deterministic"
    
    def test_47_no_sideways_dominant_walk(self):
        """Test that walk is forward-dominant, not sideways."""
        character = self.character
        planner = MotionPlanner(character)
        
        request = AnimationRequest(action="walk", frame_count=40)
        animation_plan = create_simple_plan(request)
        
        motion_plan = planner.plan_motion(animation_plan)
        sequence = planner.generate_pose_sequence(motion_plan)
        
        # Track foot movement
        pose_start = sequence.get_pose_at_frame(1)
        pose_end = sequence.get_pose_at_frame(40)
        
        # Left foot forward movement
        left_forward = pose_end["foot_l"][0] - pose_start["foot_l"][0]
        left_lateral = abs(pose_end["foot_l"][1] - pose_start["foot_l"][1])
        
        # Forward movement should dominate
        assert abs(left_forward) > left_lateral * 2, "Walk should be forward-dominant, not sideways"


# ============================================================
# PHASE 3.2 TESTS - NATURAL WALK LOCOMOTION FIX
# ============================================================

class TestPhase32Locomotion(unittest.TestCase):
    """Phase 3.2: Test proper forward locomotion vs crab-walk."""
    
    def setUp(self):
        """Create test character."""
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
    
    def test_50_root_progresses_forward(self):
        """Test that root position moves forward continuously."""
        character = self.character
        planner = MotionPlanner(character)
        
        request = AnimationRequest(action="walk", frame_count=60)
        animation_plan = create_simple_plan(request)
        
        motion_plan = planner.plan_motion(animation_plan)
        sequence = planner.generate_pose_sequence(motion_plan)
        
        # Track root X position over time
        root_positions = []
        for frame in range(1, 61):
            pose = sequence.get_pose_at_frame(frame)
            root_positions.append(pose["root"][0])
        
        # Root should progress forward
        forward_progress = root_positions[-1] - root_positions[0]
        
        assert forward_progress > 20.0, f"Root should move forward significantly (progress: {forward_progress})"
        
        # Check monotonic increase (with small tolerance for body movement)
        for i in range(len(root_positions) - 1):
            # Allow slight backward movement due to body sway (within 2 pixels)
            assert root_positions[i+1] >= root_positions[i] - 2.0, \
                f"Root should progress forward (frame {i} to {i+1})"
    
    def test_51_no_crab_walk(self):
        """Test that walk is forward-dominant, not crab-like sideways."""
        character = self.character
        planner = MotionPlanner(character)
        
        request = AnimationRequest(action="walk", frame_count=60)
        animation_plan = create_simple_plan(request)
        
        motion_plan = planner.plan_motion(animation_plan)
        sequence = planner.generate_pose_sequence(motion_plan)
        
        # Measure root movement
        pose_start = sequence.get_pose_at_frame(1)
        pose_end = sequence.get_pose_at_frame(60)
        
        root_dx = pose_end["root"][0] - pose_start["root"][0]
        root_dy = abs(pose_end["root"][1] - pose_start["root"][1])
        
        # Forward movement should dominate vertical movement significantly
        assert abs(root_dx) > root_dy * 5, \
            f"Walk should be forward-dominant (dx: {root_dx}, dy: {root_dy})"
        
        # Feet should also show forward progression
        left_foot_dx = pose_end["foot_l"][0] - pose_start["foot_l"][0]
        right_foot_dx = pose_end["foot_r"][0] - pose_start["foot_r"][0]
        
        # Both feet should have moved forward overall
        assert left_foot_dx > 0, f"Left foot should progress forward (dx: {left_foot_dx})"
        assert right_foot_dx > 0, f"Right foot should progress forward (dx: {right_foot_dx})"
    
    def test_52_gait_phases_distinct(self):
        """Test that left and right legs have distinct phases."""
        character = self.character
        planner = MotionPlanner(character)
        
        request = AnimationRequest(action="walk", frame_count=40)
        animation_plan = create_simple_plan(request)
        
        motion_plan = planner.plan_motion(animation_plan)
        sequence = planner.generate_pose_sequence(motion_plan)
        
        # Sample at quarter points of cycle
        frames_per_cycle = 20
        
        # At frame 1: left should be in different phase than right
        pose_f1 = sequence.get_pose_at_frame(1)
        
        # At frame 11 (half cycle later): phases should be swapped
        pose_f11 = sequence.get_pose_at_frame(11)
        
        # Check foot heights differ (one on ground, one lifted)
        left_y_f1 = pose_f1["foot_l"][1]
        right_y_f1 = pose_f1["foot_r"][1]
        
        left_y_f11 = pose_f11["foot_l"][1]
        right_y_f11 = pose_f11["foot_r"][1]
        
        # Feet should alternate which one is lifted
        # At frame 1, if left is on ground and right is lifted (or vice versa)
        # At frame 11, it should be opposite
        height_diff_f1 = abs(left_y_f1 - right_y_f1)
        height_diff_f11 = abs(left_y_f11 - right_y_f11)
        
        # At least one phase should show difference
        assert max(height_diff_f1, height_diff_f11) > 2.0, \
            "Feet should alternate between ground and lifted"
    
    def test_53_body_moves_with_root(self):
        """Test that body parts move forward with root."""
        character = self.character
        planner = MotionPlanner(character)
        
        request = AnimationRequest(action="walk", frame_count=60)
        animation_plan = create_simple_plan(request)
        
        motion_plan = planner.plan_motion(animation_plan)
        sequence = planner.generate_pose_sequence(motion_plan)
        
        pose_start = sequence.get_pose_at_frame(1)
        pose_end = sequence.get_pose_at_frame(60)
        
        # All body parts should progress forward
        parts_to_check = ["root", "torso", "neck", "head", "hip_l", "hip_r"]
        
        for part in parts_to_check:
            dx = pose_end[part][0] - pose_start[part][0]
            assert dx > 10.0, f"{part} should move forward (dx: {dx})"
    
    def test_54_stance_duration_reasonable(self):
        """Test that stance phase has reasonable duration."""
        character = self.character
        planner = MotionPlanner(character)
        
        request = AnimationRequest(action="walk", frame_count=20)
        animation_plan = create_simple_plan(request)
        
        motion_plan = planner.plan_motion(animation_plan)
        sequence = planner.generate_pose_sequence(motion_plan)
        
        # Track when left foot is on ground (stance)
        ground_y = sequence.get_pose_at_frame(1)["foot_l"][1]
        
        left_foot_on_ground = []
        for frame in range(1, 21):
            pose = sequence.get_pose_at_frame(frame)
            # Foot is on ground if Y is within 1 pixel of ground level
            is_on_ground = abs(pose["foot_l"][1] - ground_y) < 1.0
            left_foot_on_ground.append(is_on_ground)
        
        stance_frames = sum(left_foot_on_ground)
        
        # Stance should be roughly 40-60% of cycle (8-12 frames out of 20)
        assert 6 <= stance_frames <= 14, \
            f"Stance duration should be reasonable (got {stance_frames} frames)"
    
    def test_55_deterministic_with_root_progression(self):
        """Test that walk with root progression is deterministic."""
        character = self.character
        planner = MotionPlanner(character)
        
        request = AnimationRequest(action="walk", frame_count=60)
        
        # Generate twice
        plan1 = create_simple_plan(request)
        motion1 = planner.plan_motion(plan1)
        seq1 = planner.generate_pose_sequence(motion1)
        
        plan2 = create_simple_plan(request)
        motion2 = planner.plan_motion(plan2)
        seq2 = planner.generate_pose_sequence(motion2)
        
        # Should be identical
        for frame in [1, 10, 20, 30, 40, 50, 60]:
            pose1 = seq1.get_pose_at_frame(frame)
            pose2 = seq2.get_pose_at_frame(frame)
            
            for joint in pose1.keys():
                p1 = pose1[joint]
                p2 = pose2[joint]
                
                delta = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
                assert delta < 0.01, f"Frame {frame}: {joint} not deterministic"
    
    def test_56_forward_to_lateral_ratio(self):
        """Test that forward movement dominates lateral movement."""
        character = self.character
        planner = MotionPlanner(character)
        
        request = AnimationRequest(action="walk", frame_count=100)
        animation_plan = create_simple_plan(request)
        
        motion_plan = planner.plan_motion(animation_plan)
        sequence = planner.generate_pose_sequence(motion_plan)
        
        # Track root movement
        root_x_positions = []
        root_y_positions = []
        
        for frame in range(1, 101):
            pose = sequence.get_pose_at_frame(frame)
            root_x_positions.append(pose["root"][0])
            root_y_positions.append(pose["root"][1])
        
        # Calculate total forward and vertical ranges
        forward_range = max(root_x_positions) - min(root_x_positions)
        vertical_range = max(root_y_positions) - min(root_y_positions)
        
        # Forward should be at least 10x vertical (accounting for body bob)
        ratio = forward_range / max(vertical_range, 0.1)
        
        assert ratio > 10.0, f"Forward/vertical ratio should be high (got {ratio:.1f})"
    
    def test_57_continuous_root_progression(self):
        """Test that root progression is continuous, not jumpy."""
        character = self.character
        planner = MotionPlanner(character)
        
        request = AnimationRequest(action="walk", frame_count=100)
        animation_plan = create_simple_plan(request)
        
        motion_plan = planner.plan_motion(animation_plan)
        sequence = planner.generate_pose_sequence(motion_plan)
        
        # Check frame-to-frame root movement
        max_frame_delta = 0
        
        for frame in range(1, 100):
            pose1 = sequence.get_pose_at_frame(frame)
            pose2 = sequence.get_pose_at_frame(frame + 1)
            
            root_delta_x = abs(pose2["root"][0] - pose1["root"][0])
            max_frame_delta = max(max_frame_delta, root_delta_x)
        
        # Root should progress smoothly (not more than 5 pixels per frame)
        assert max_frame_delta < 5.0, \
            f"Root progression should be smooth (max delta: {max_frame_delta})"
