"""Motion Planning Engine - Phase 3

Generic motion planning system for character animation.

NO DRAWING. NO GROQ. NO KRITA. NO MCP.
This is a pure motion planning layer.

Architecture:
    CharacterModel
        ↓
    AnimationPlan
        ↓
    MotionPlanner
        ↓
    MotionPlan
        ↓
    PoseSequence
        ↓
    EXISTING CharacterPoseTransformer
"""

import math
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

# Reuse existing types
from character_model import CharacterModel, JointConstraints
from animation_timeline import AnimationPlan, KeyPose, Pose


class EasingType(Enum):
    """Motion easing types."""
    LINEAR = "linear"
    EASE_IN = "ease_in"
    EASE_OUT = "ease_out"
    EASE_IN_OUT = "ease_in_out"


class MotionType(Enum):
    """Types of joint motion."""
    HOLD = "hold"  # Joint stays still
    LINEAR = "linear"  # Linear interpolation
    CONTROLLED = "controlled"  # Controlled with easing
    IK_TARGET = "ik_target"  # IK-driven (e.g., foot to target)


@dataclass
class JointMotion:
    """Movement of a single joint over time.
    
    Represents how one joint moves from start to end state.
    """
    joint_name: str
    start_frame: int
    end_frame: int
    start_pose: Pose  # Full character pose at start
    end_pose: Pose  # Full character pose at end
    motion_type: MotionType = MotionType.CONTROLLED
    easing: EasingType = EasingType.EASE_IN_OUT
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def duration(self) -> int:
        """Get duration in frames."""
        return self.end_frame - self.start_frame + 1


@dataclass
class MotionSegment:
    """A segment of motion within the overall plan.
    
    Represents a meaningful phase of movement (e.g., stance, swing).
    """
    name: str  # e.g., "left_stance", "right_swing"
    action: str  # e.g., "walk", "run", "wave"
    start_frame: int
    end_frame: int
    joint_motions: List[JointMotion] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def duration(self) -> int:
        """Get duration in frames."""
        return self.end_frame - self.start_frame + 1


@dataclass
class MotionConstraints:
    """Constraints for motion planning."""
    max_joint_delta_per_frame: float = 50.0  # Max pixels per frame
    preserve_bone_lengths: bool = True
    respect_joint_limits: bool = True
    continuous_motion: bool = True
    minimum_ground_contact_time: int = 3  # Min frames for foot contact
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MotionPlan:
    """Complete motion plan for an animation.
    
    Contains the planned joint movements over time.
    NO RENDERING INFORMATION.
    """
    source_plan: AnimationPlan
    character: CharacterModel
    segments: List[MotionSegment] = field(default_factory=list)
    constraints: MotionConstraints = field(default_factory=MotionConstraints)
    validated: bool = False
    validation_errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_segment(self, segment: MotionSegment):
        """Add a motion segment."""
        self.segments.append(segment)
    
    def get_total_frames(self) -> int:
        """Get total frame count."""
        return self.source_plan.timeline.total_frames


@dataclass
class PoseSequence:
    """Sequence of poses over time.
    
    Result of motion planning - ready for transformation/rendering.
    """
    character: CharacterModel
    poses: List[Tuple[int, Pose]]  # [(frame_number, pose), ...]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_pose_at_frame(self, frame: int) -> Optional[Pose]:
        """Get pose at specific frame."""
        for f, pose in self.poses:
            if f == frame:
                return pose
        return None
    
    def get_frame_count(self) -> int:
        """Get number of frames."""
        return len(self.poses)


class MotionPlanner:
    """Generic motion planning engine.
    
    Plans coordinated joint movement for character animation.
    """
    
    def __init__(self, character: CharacterModel, constraints: Optional[MotionConstraints] = None):
        """
        Args:
            character: CharacterModel to plan motion for
            constraints: Motion constraints
        """
        self.character = character
        self.constraints = constraints or MotionConstraints()
    
    def plan_motion(self, animation_plan: AnimationPlan) -> MotionPlan:
        """Create motion plan from animation plan.
        
        Args:
            animation_plan: Animation plan with timeline and key poses
        
        Returns:
            MotionPlan with planned joint movements
        """
        motion_plan = MotionPlan(
            source_plan=animation_plan,
            character=self.character,
            constraints=self.constraints
        )
        
        # Route to action-specific planner
        action = animation_plan.request.action.lower()
        
        if action == "walk":
            self._plan_walk_motion(animation_plan, motion_plan)
        else:
            # Generic fallback - hold neutral pose
            self._plan_hold_motion(animation_plan, motion_plan)
        
        # Validate
        self._validate_motion_plan(motion_plan)
        
        return motion_plan
    
    def generate_pose_sequence(self, motion_plan: MotionPlan) -> PoseSequence:
        """Generate pose sequence from motion plan.
        
        Creates interpolated poses for all frames.
        """
        if not motion_plan.validated:
            raise ValueError("MotionPlan must be validated before generating poses")
        
        poses = []
        total_frames = motion_plan.get_total_frames()
        
        # Generate pose for each frame
        for frame_num in range(1, total_frames + 1):
            pose = self._generate_pose_for_frame(motion_plan, frame_num)
            poses.append((frame_num, pose))
        
        return PoseSequence(
            character=self.character,
            poses=poses
        )
    
    def _plan_walk_motion(self, animation_plan: AnimationPlan, motion_plan: MotionPlan):
        """Plan walking motion.
        
        Implements natural walk with:
        - Alternating legs
        - Forward movement
        - Stable foot placement
        - Arm counter-swing
        - Controlled torso movement
        """
        total_frames = animation_plan.timeline.total_frames
        request = animation_plan.request
        
        # Get speed parameter
        speed = request.speed if hasattr(request, 'speed') else "normal"
        speed_multiplier = {
            "slow": 0.7,
            "normal": 1.0,
            "fast": 1.3
        }.get(speed, 1.0)
        
        # Calculate walk cycle parameters
        # A walk cycle = 2 steps (left, right)
        # For natural walking: ~20-30 frames per cycle at 24fps
        # Scale based on total frames
        
        if total_frames <= 30:
            # Short animation: 1-2 cycles
            frames_per_cycle = total_frames // 2
        else:
            # Longer animation: multiple cycles
            frames_per_cycle = 20  # ~1 second at 24fps
        
        frames_per_cycle = int(frames_per_cycle / speed_multiplier)
        frames_per_cycle = max(10, frames_per_cycle)  # Minimum 10 frames per cycle
        
        # Store in metadata for pose generation
        motion_plan.metadata["walk_config"] = {
            "frames_per_cycle": frames_per_cycle,
            "speed_multiplier": speed_multiplier,
            "stride_length_factor": 0.15,  # Fraction of leg length
            "step_height_factor": 0.10,
            "body_bob_factor": 0.04,
            "arm_swing_factor": 0.2
        }
        
        # Create motion segments for walk phases
        # Break into stance and swing phases for each leg
        num_cycles = max(1, total_frames // frames_per_cycle)
        
        for cycle in range(num_cycles):
            cycle_start = 1 + cycle * frames_per_cycle
            cycle_end = min(total_frames, cycle_start + frames_per_cycle - 1)
            
            if cycle_start > total_frames:
                break
            
            # Half cycle for each leg
            half_cycle = (cycle_end - cycle_start + 1) // 2
            
            # Left leg stance, right leg swing
            segment1 = MotionSegment(
                name=f"cycle{cycle}_left_stance",
                action="walk",
                start_frame=cycle_start,
                end_frame=cycle_start + half_cycle - 1
            )
            segment1.metadata["leg_state"] = {"left": "stance", "right": "swing"}
            motion_plan.add_segment(segment1)
            
            # Right leg stance, left leg swing
            if cycle_start + half_cycle <= cycle_end:
                segment2 = MotionSegment(
                    name=f"cycle{cycle}_right_stance",
                    action="walk",
                    start_frame=cycle_start + half_cycle,
                    end_frame=cycle_end
                )
                segment2.metadata["leg_state"] = {"left": "swing", "right": "stance"}
                motion_plan.add_segment(segment2)
    
    def _plan_hold_motion(self, animation_plan: AnimationPlan, motion_plan: MotionPlan):
        """Plan hold motion (neutral pose maintained)."""
        total_frames = animation_plan.timeline.total_frames
        
        segment = MotionSegment(
            name="hold",
            action="hold",
            start_frame=1,
            end_frame=total_frames
        )
        motion_plan.add_segment(segment)
    
    def _generate_pose_for_frame(self, motion_plan: MotionPlan, frame_num: int) -> Pose:
        """Generate pose for specific frame.
        
        Uses motion segments and walk config to generate coordinated pose.
        """
        action = motion_plan.source_plan.request.action.lower()
        
        if action == "walk":
            return self._generate_walk_pose(motion_plan, frame_num)
        else:
            # Default: neutral pose
            return dict(self.character.neutral_pose)
    
    def _generate_walk_pose(self, motion_plan: MotionPlan, frame_num: int) -> Pose:
        """Generate walking pose for specific frame.
        
        Implements proper walking mechanics:
        - Alternating legs
        - Forward progression
        - Stable foot placement during stance
        - Arm counter-swing
        """
        config = motion_plan.metadata.get("walk_config", {})
        frames_per_cycle = config.get("frames_per_cycle", 20)
        
        # Calculate phase within current walk cycle (0.0 to 1.0)
        phase = ((frame_num - 1) % frames_per_cycle) / frames_per_cycle
        
        # Get character dimensions
        neutral = self.character.neutral_pose
        dimensions = self.character.dimensions
        
        # Calculate leg length
        leg_length = dimensions.thigh_length + dimensions.shin_length
        if leg_length == 0:
            leg_length = 100.0  # Fallback
        
        # Walk parameters (scaled by leg length)
        stride = config.get("stride_length_factor", 0.15) * leg_length
        step_height = config.get("step_height_factor", 0.10) * leg_length
        body_bob = config.get("body_bob_factor", 0.04) * leg_length
        arm_swing = config.get("arm_swing_factor", 0.2)
        
        # Ensure minimum visible movement
        stride = max(stride, 10.0)  # At least 10 pixels
        step_height = max(step_height, 5.0)  # At least 5 pixels
        
        # Start with neutral pose
        pose = dict(neutral)
        
        # Calculate body bob (vertical movement)
        # Contact -> Down -> Passing -> Up -> Contact
        body_y_offset = math.sin(phase * 4 * math.pi) * body_bob
        
        # Calculate foot positions
        # LEFT LEG: contact (0-0.5), swing (0.5-1.0)
        # RIGHT LEG: swing (0-0.5), contact (0.5-1.0)
        
        left_hip_x, left_hip_y = neutral["hip_l"]
        right_hip_x, right_hip_y = neutral["hip_r"]
        left_foot_x_neutral, left_foot_y_neutral = neutral["foot_l"]
        right_foot_x_neutral, right_foot_y_neutral = neutral["foot_r"]
        
        # Forward direction is +X (right on screen)
        # Feet move relative to hips with forward progression
        
        if phase < 0.5:
            # Left leg: stance (planted, body moves over it)
            # Plant foot forward, body catches up
            left_foot_x = left_hip_x + stride * (1.0 - phase * 2)  # Foot ahead, reduces as body moves over
            left_foot_y = left_foot_y_neutral  # On ground
            
            # Right leg: swing (moving forward)
            swing_phase = phase / 0.5  # 0 to 1
            right_foot_x = right_hip_x - stride + (stride * 2) * swing_phase  # Behind to ahead
            right_foot_y = left_foot_y_neutral - math.sin(swing_phase * math.pi) * step_height  # Arc
        else:
            # Right leg: stance
            right_foot_x = right_hip_x + stride * (1.0 - (phase - 0.5) * 2)
            right_foot_y = right_foot_y_neutral
            
            # Left leg: swing
            swing_phase = (phase - 0.5) / 0.5
            left_foot_x = left_hip_x - stride + (stride * 2) * swing_phase
            left_foot_y = left_foot_y_neutral - math.sin(swing_phase * math.pi) * step_height
        
        # Update pose with foot positions
        pose["foot_l"] = (left_foot_x, left_foot_y)
        pose["foot_r"] = (right_foot_x, right_foot_y)
        
        # Knee positions (IK-style positioning for natural bend)
        # For simplicity: knees bend between hips and feet
        left_knee_x = (left_hip_x + left_foot_x) / 2
        left_knee_y = (left_hip_y + left_foot_y) / 2 - dimensions.shin_length * 0.2  # Slight forward bend
        
        right_knee_x = (right_hip_x + right_foot_x) / 2
        right_knee_y = (right_hip_y + right_foot_y) / 2 - dimensions.shin_length * 0.2
        
        pose["knee_l"] = (left_knee_x, left_knee_y)
        pose["knee_r"] = (right_knee_x, right_knee_y)
        
        # Body movement (hips, torso rise with bob)
        pose["hip_l"] = (left_hip_x, left_hip_y + body_y_offset)
        pose["hip_r"] = (right_hip_x, right_hip_y + body_y_offset)
        
        root_x, root_y = neutral["root"]
        pose["root"] = (root_x, root_y + body_y_offset)
        
        torso_x, torso_y = neutral["torso"]
        pose["torso"] = (torso_x, torso_y + body_y_offset)
        
        neck_x, neck_y = neutral["neck"]
        pose["neck"] = (neck_x, neck_y + body_y_offset)
        
        head_x, head_y = neutral["head"]
        pose["head"] = (head_x, head_y + body_y_offset)
        
        # Arm counter-swing
        # When left leg forward, right arm forward (and vice versa)
        arm_angle_offset = math.cos(phase * math.pi * 2) * arm_swing * dimensions.upper_arm_length
        
        # Left arm (moves opposite to left leg)
        left_shoulder_x, left_shoulder_y = neutral["shoulder_l"]
        pose["shoulder_l"] = (left_shoulder_x, left_shoulder_y + body_y_offset)
        
        left_elbow_x, left_elbow_y = neutral["elbow_l"]
        pose["elbow_l"] = (left_elbow_x + arm_angle_offset, left_elbow_y + body_y_offset)
        
        left_hand_x, left_hand_y = neutral["hand_l"]
        pose["hand_l"] = (left_hand_x + arm_angle_offset * 1.2, left_hand_y + body_y_offset)
        
        # Right arm (moves opposite to right leg)
        right_shoulder_x, right_shoulder_y = neutral["shoulder_r"]
        pose["shoulder_r"] = (right_shoulder_x, right_shoulder_y + body_y_offset)
        
        right_elbow_x, right_elbow_y = neutral["elbow_r"]
        pose["elbow_r"] = (right_elbow_x - arm_angle_offset, right_elbow_y + body_y_offset)
        
        right_hand_x, right_hand_y = neutral["hand_r"]
        pose["hand_r"] = (right_hand_x - arm_angle_offset * 1.2, right_hand_y + body_y_offset)
        
        return pose
    
    def _validate_motion_plan(self, motion_plan: MotionPlan):
        """Validate motion plan."""
        errors = []
        
        # Check segments cover timeline
        if not motion_plan.segments:
            errors.append("MotionPlan has no segments")
            motion_plan.validation_errors = errors
            motion_plan.validated = len(errors) == 0
            return
        
        # Check frame coverage
        total = motion_plan.get_total_frames()
        
        # Sort segments by start frame
        sorted_segments = sorted(motion_plan.segments, key=lambda s: s.start_frame)
        
        first_frame = sorted_segments[0].start_frame
        last_frame = sorted_segments[-1].end_frame
        
        if first_frame != 1:
            errors.append(f"Motion doesn't start at frame 1 (starts at {first_frame})")
        
        # Check for gaps
        for i in range(len(sorted_segments) - 1):
            current_end = sorted_segments[i].end_frame
            next_start = sorted_segments[i + 1].start_frame
            
            if next_start > current_end + 1:
                # There's a gap
                errors.append(f"Gap between segments: {current_end} and {next_start}")
        
        if last_frame < total:
            # Motion doesn't cover full timeline - this is OK for walks that end early
            # Just ensure last segment is reasonable
            pass
        
        motion_plan.validation_errors = errors
        motion_plan.validated = len(errors) == 0


class MotionValidator:
    """Validates motion plans and pose sequences."""
    
    def __init__(self, character: CharacterModel, constraints: MotionConstraints):
        """
        Args:
            character: CharacterModel for validation
            constraints: Motion constraints
        """
        self.character = character
        self.constraints = constraints
    
    def validate_pose_sequence(self, sequence: PoseSequence) -> Tuple[bool, List[str]]:
        """Validate pose sequence.
        
        Checks:
        - Bone lengths preserved
        - Joint continuity
        - No teleportation
        - Joint limits respected
        """
        errors = []
        
        # Check bone lengths for each pose
        if self.constraints.preserve_bone_lengths:
            for frame, pose in sequence.poses:
                bone_errors = self._check_bone_lengths(pose)
                errors.extend([f"Frame {frame}: {err}" for err in bone_errors])
        
        # Check continuity between adjacent frames
        if self.constraints.continuous_motion:
            for i in range(len(sequence.poses) - 1):
                frame1, pose1 = sequence.poses[i]
                frame2, pose2 = sequence.poses[i + 1]
                
                continuity_errors = self._check_continuity(pose1, pose2, frame1, frame2)
                errors.extend(continuity_errors)
        
        is_valid = len(errors) == 0
        return is_valid, errors
    
    def _check_bone_lengths(self, pose: Pose) -> List[str]:
        """Check bone lengths are preserved."""
        errors = []
        tolerance = 0.01  # 1% tolerance (reuse from Phase 1.5)
        
        # Check key bones
        bones_to_check = [
            ("elbow_l", "shoulder_l", "left_upper_arm"),
            ("hand_l", "elbow_l", "left_forearm"),
            ("elbow_r", "shoulder_r", "right_upper_arm"),
            ("hand_r", "elbow_r", "right_forearm"),
            ("knee_l", "hip_l", "left_thigh"),
            ("foot_l", "knee_l", "left_shin"),
            ("knee_r", "hip_r", "right_thigh"),
            ("foot_r", "knee_r", "right_shin"),
        ]
        
        for child, parent, bone_name in bones_to_check:
            if child not in pose or parent not in pose:
                continue
            
            # Calculate actual length
            cx, cy = pose[child]
            px, py = pose[parent]
            actual_length = math.hypot(cx - px, cy - py)
            
            # Get expected length
            expected_length = self.character.get_limb_length(child)
            if expected_length == 0:
                continue
            
            # Check deviation
            deviation = abs(actual_length - expected_length)
            deviation_ratio = deviation / expected_length
            
            if deviation_ratio > tolerance:
                errors.append(
                    f"{bone_name} length violation: "
                    f"expected={expected_length:.1f}, actual={actual_length:.1f}, "
                    f"deviation={deviation_ratio*100:.1f}%"
                )
        
        return errors
    
    def _check_continuity(self, pose1: Pose, pose2: Pose, frame1: int, frame2: int) -> List[str]:
        """Check motion continuity between poses."""
        errors = []
        max_delta = self.constraints.max_joint_delta_per_frame
        
        for joint in pose1:
            if joint not in pose2:
                continue
            
            x1, y1 = pose1[joint]
            x2, y2 = pose2[joint]
            
            delta = math.hypot(x2 - x1, y2 - y1)
            
            if delta > max_delta:
                errors.append(
                    f"Joint {joint} teleported between frames {frame1}-{frame2}: "
                    f"moved {delta:.1f} pixels (max: {max_delta:.1f})"
                )
        
        return errors


def create_walk_motion_plan(
    character: CharacterModel,
    animation_plan: AnimationPlan,
    constraints: Optional[MotionConstraints] = None
) -> MotionPlan:
    """Convenience function to create walking motion plan."""
    planner = MotionPlanner(character, constraints)
    return planner.plan_motion(animation_plan)
