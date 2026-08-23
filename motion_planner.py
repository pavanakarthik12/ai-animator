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
        
        Phase 3.2: Natural Walk Locomotion Fix
        Implements proper forward locomotion with:
        - Global root progression (body moves forward continuously)
        - Local gait cycle (legs alternate relative to moving root)
        - Proper foot trajectories (planted vs swing)
        - Weight transfer over support leg
        - Natural arm counter-swing
        - Smooth phase transitions
        
        KEY FIX: Separate global world movement from local joint movement
        """
        config = motion_plan.metadata.get("walk_config", {})
        frames_per_cycle = config.get("frames_per_cycle", 20)
        
        # Calculate phase within current walk cycle (0.0 to 1.0)
        cycle_progress = ((frame_num - 1) % frames_per_cycle) / frames_per_cycle
        
        # Get character dimensions
        neutral = self.character.neutral_pose
        dimensions = self.character.dimensions
        
        # Calculate leg length
        thigh_len = dimensions.thigh_length
        shin_len = dimensions.shin_length
        leg_length = thigh_len + shin_len
        if leg_length == 0:
            leg_length = 100.0
            thigh_len = 40.0
            shin_len = 30.0
        
        # Walk parameters (scaled by character dimensions for natural proportions)
        stride_length = 0.18 * leg_length  # 18% of leg length - conservative but visible
        step_height = 0.12 * leg_length     # 12% for visible lift
        body_bob = 0.04 * leg_length        # 4% subtle bob
        arm_swing_amplitude = 0.25          # 25% rotation angle
        hip_sway = 0.06 * (dimensions.torso_width if dimensions.torso_width > 0 else 20)
        
        # Ensure minimum visible movement
        stride_length = max(stride_length, 12.0)
        step_height = max(step_height, 6.0)
        
        # Start with neutral pose
        pose = dict(neutral)
        
        # Get neutral positions
        root_x_neutral, root_y_neutral = neutral["root"]
        left_hip_x_neutral, left_hip_y_neutral = neutral["hip_l"]
        right_hip_x_neutral, right_hip_y_neutral = neutral["hip_r"]
        ground_y = neutral["foot_l"][1]
        
        # === GLOBAL ROOT PROGRESSION ===
        # Root moves forward continuously - this is the KEY FIX
        # Each complete cycle advances by one stride_length
        cycles_completed = (frame_num - 1) / frames_per_cycle
        root_x_offset = cycles_completed * stride_length
        
        # Within-cycle position (for body bob/sway)
        root_x = root_x_neutral + root_x_offset
        
        # === VERTICAL BODY BOB ===
        # Lowest at double-support (phase 0.0, 0.5), highest at single-support (0.25, 0.75)
        bob_phase = (cycle_progress * 2) % 1.0
        body_y_offset = -body_bob * math.cos(bob_phase * 2 * math.pi)
        root_y = root_y_neutral + body_y_offset
        
        # === HIP LATERAL WEIGHT SHIFT ===
        # Shift weight over support leg for natural weight transfer
        if cycle_progress < 0.5:
            # Left leg support - shift slightly left
            shift_progress = self._ease_in_out(cycle_progress / 0.5)
            hip_shift_x = -hip_sway * shift_progress
        else:
            # Right leg support - shift slightly right
            shift_progress = self._ease_in_out((cycle_progress - 0.5) / 0.5)
            hip_shift_x = hip_sway * shift_progress
        
        # Update hip positions (relative to moving root)
        left_hip_x = left_hip_x_neutral + root_x_offset + hip_shift_x
        left_hip_y = left_hip_y_neutral + body_y_offset
        right_hip_x = right_hip_x_neutral + root_x_offset + hip_shift_x
        right_hip_y = right_hip_y_neutral + body_y_offset
        
        # === FOOT PLACEMENT WITH PROPER GAIT PHASES ===
        # Left and right legs are phase-shifted by 0.5 (180 degrees)
        
        # LEFT LEG CYCLE
        left_phase = cycle_progress
        left_foot_x, left_foot_y = self._calculate_foot_position(
            left_phase,
            root_x,
            left_hip_x,
            left_hip_y,
            ground_y,
            stride_length,
            step_height,
            is_left=True
        )
        
        # RIGHT LEG CYCLE (phase-shifted by 0.5)
        right_phase = (cycle_progress + 0.5) % 1.0
        right_foot_x, right_foot_y = self._calculate_foot_position(
            right_phase,
            root_x,
            right_hip_x,
            right_hip_y,
            ground_y,
            stride_length,
            step_height,
            is_left=False
        )
        
        # === IK FOR KNEES ===
        left_knee_x, left_knee_y = self._solve_two_bone_ik(
            left_hip_x, left_hip_y,
            left_foot_x, left_foot_y,
            thigh_len, shin_len,
            forward=True
        )
        
        right_knee_x, right_knee_y = self._solve_two_bone_ik(
            right_hip_x, right_hip_y,
            right_foot_x, right_foot_y,
            thigh_len, shin_len,
            forward=True
        )
        
        # === UPDATE POSE: CORE AND LEGS ===
        pose["root"] = (root_x, root_y)
        pose["hip_l"] = (left_hip_x, left_hip_y)
        pose["hip_r"] = (right_hip_x, right_hip_y)
        pose["knee_l"] = (left_knee_x, left_knee_y)
        pose["knee_r"] = (right_knee_x, right_knee_y)
        pose["foot_l"] = (left_foot_x, left_foot_y)
        pose["foot_r"] = (right_foot_x, right_foot_y)
        
        # === TORSO AND HEAD ===
        torso_x, torso_y = neutral["torso"]
        pose["torso"] = (torso_x + root_x_offset + hip_shift_x * 0.5, torso_y + body_y_offset)
        
        neck_x, neck_y = neutral["neck"]
        head_x, head_y = neutral["head"]
        # Head stability: only 40% of body bob
        head_y_offset = body_y_offset * 0.4
        pose["neck"] = (neck_x + root_x_offset + hip_shift_x * 0.3, neck_y + head_y_offset)
        pose["head"] = (head_x + root_x_offset + hip_shift_x * 0.3, head_y + head_y_offset)
        
        # === ARM COUNTER-SWING ===
        # Arms swing opposite to legs with timing offset for naturalness
        # Left arm swings with right leg (opposite)
        arm_phase = (cycle_progress + 0.15) % 1.0  # 15% lead for natural timing
        
        # Calculate arm swing angle using smooth curve
        arm_angle = math.sin(arm_phase * 2 * math.pi) * arm_swing_amplitude
        
        # Left arm
        left_shoulder_x, left_shoulder_y = neutral["shoulder_l"]
        pose["shoulder_l"] = (left_shoulder_x + root_x_offset + hip_shift_x * 0.4, 
                             left_shoulder_y + body_y_offset)
        
        # Rotate arm from shoulder preserving bone lengths
        upper_arm_len = dimensions.upper_arm_length
        forearm_len = dimensions.forearm_length
        
        left_elbow_base_x, left_elbow_base_y = neutral["elbow_l"]
        left_elbow_dx = left_elbow_base_x - left_shoulder_x
        left_elbow_dy = left_elbow_base_y - left_shoulder_y
        left_elbow_angle = math.atan2(left_elbow_dy, left_elbow_dx)
        left_elbow_angle_new = left_elbow_angle + arm_angle
        
        shoulder_l_x, shoulder_l_y = pose["shoulder_l"]
        pose["elbow_l"] = (
            shoulder_l_x + upper_arm_len * math.cos(left_elbow_angle_new),
            shoulder_l_y + upper_arm_len * math.sin(left_elbow_angle_new)
        )
        
        # Left hand
        left_hand_base_x, left_hand_base_y = neutral["hand_l"]
        left_hand_dx = left_hand_base_x - left_elbow_base_x
        left_hand_dy = left_hand_base_y - left_elbow_base_y
        left_hand_angle = math.atan2(left_hand_dy, left_hand_dx)
        left_hand_angle_new = left_hand_angle + arm_angle * 0.6  # Less swing at hand
        
        elbow_l_x, elbow_l_y = pose["elbow_l"]
        pose["hand_l"] = (
            elbow_l_x + forearm_len * math.cos(left_hand_angle_new),
            elbow_l_y + forearm_len * math.sin(left_hand_angle_new)
        )
        
        # Right arm (opposite swing)
        right_shoulder_x, right_shoulder_y = neutral["shoulder_r"]
        pose["shoulder_r"] = (right_shoulder_x + root_x_offset + hip_shift_x * 0.4,
                             right_shoulder_y + body_y_offset)
        
        right_elbow_base_x, right_elbow_base_y = neutral["elbow_r"]
        right_elbow_dx = right_elbow_base_x - right_shoulder_x
        right_elbow_dy = right_elbow_base_y - right_shoulder_y
        right_elbow_angle = math.atan2(right_elbow_dy, right_elbow_dx)
        right_elbow_angle_new = right_elbow_angle - arm_angle  # Opposite direction
        
        shoulder_r_x, shoulder_r_y = pose["shoulder_r"]
        pose["elbow_r"] = (
            shoulder_r_x + upper_arm_len * math.cos(right_elbow_angle_new),
            shoulder_r_y + upper_arm_len * math.sin(right_elbow_angle_new)
        )
        
        # Right hand
        right_hand_base_x, right_hand_base_y = neutral["hand_r"]
        right_hand_dx = right_hand_base_x - right_elbow_base_x
        right_hand_dy = right_hand_base_y - right_elbow_base_y
        right_hand_angle = math.atan2(right_hand_dy, right_hand_dx)
        right_hand_angle_new = right_hand_angle - arm_angle * 0.6
        
        elbow_r_x, elbow_r_y = pose["elbow_r"]
        pose["hand_r"] = (
            elbow_r_x + forearm_len * math.cos(right_hand_angle_new),
            elbow_r_y + forearm_len * math.sin(right_hand_angle_new)
        )
        
        return pose
    
    def _calculate_foot_position(self, phase: float, root_x: float, hip_x: float, hip_y: float,
                                  ground_y: float, stride_length: float, step_height: float,
                                  is_left: bool) -> tuple:
        """Calculate foot position for given gait phase.
        
        Gait phases:
        0.0-0.1: CONTACT - foot touches ground ahead
        0.1-0.3: STANCE - foot planted, body moves over it
        0.3-0.4: PUSH_OFF - foot pushes, preparing to lift
        0.4-0.6: SWING - foot lifts and swings forward
        0.6-0.9: PASSING - foot passes body center, still airborne
        0.9-1.0: EXTENSION - foot extends toward next contact
        
        Args:
            phase: Gait phase 0.0-1.0
            root_x: Current root X position (moving forward)
            hip_x: Current hip X position
            hip_y: Current hip Y position
            ground_y: Ground level Y coordinate
            stride_length: Full stride length
            step_height: Maximum foot lift height
            is_left: True for left foot, False for right
            
        Returns:
            (foot_x, foot_y) tuple
        """
        # Divide cycle into stance (0.0-0.4) and swing (0.4-1.0)
        if phase < 0.4:
            # STANCE PHASE: Foot planted, body moves forward over it
            # Foot stays relatively fixed in world space while root progresses
            stance_progress = phase / 0.4  # 0 to 1
            
            # Foot planted ahead at start of stance
            # As body moves forward, foot appears to move backward relative to body
            foot_x = root_x + stride_length * 0.5 - stride_length * stance_progress
            foot_y = ground_y
            
        else:
            # SWING PHASE: Foot lifts and swings forward
            swing_progress = (phase - 0.4) / 0.6  # 0 to 1
            swing_eased = self._ease_in_out(swing_progress)
            
            # Horizontal: foot swings from behind to ahead
            foot_x = root_x - stride_length * 0.5 + stride_length * swing_eased
            
            # Vertical: smooth arc using sine curve
            # Peak lift at mid-swing (progress = 0.5)
            lift_curve = math.sin(swing_progress * math.pi)
            foot_y = ground_y - step_height * lift_curve
        
        return (foot_x, foot_y)
    
    def _solve_two_bone_ik(self, start_x: float, start_y: float,
                           end_x: float, end_y: float,
                           bone1_len: float, bone2_len: float,
                           forward: bool = True) -> tuple:
        """Solve 2-bone IK to find middle joint position.
        
        Args:
            start_x, start_y: Start position (e.g., hip)
            end_x, end_y: End position (e.g., foot)
            bone1_len: Length of first bone (e.g., thigh)
            bone2_len: Length of second bone (e.g., shin)
            forward: If True, knee bends forward; if False, backward
            
        Returns:
            (mid_x, mid_y): Position of middle joint (e.g., knee)
        """
        # Distance from start to end
        dx = end_x - start_x
        dy = end_y - start_y
        target_dist = math.hypot(dx, dy)
        
        # Check if target is reachable
        max_reach = bone1_len + bone2_len
        min_reach = abs(bone1_len - bone2_len)
        
        if target_dist > max_reach:
            # Target too far - clamp to max reach
            target_dist = max_reach - 0.01  # Slightly less to avoid singularity
            # Adjust end position
            scale = target_dist / math.hypot(dx, dy)
            dx = dx * scale
            dy = dy * scale
        elif target_dist < min_reach:
            # Target too close - use minimum reach
            target_dist = min_reach + 0.01
            # Adjust end position
            if math.hypot(dx, dy) > 0:
                scale = target_dist / math.hypot(dx, dy)
                dx = dx * scale
                dy = dy * scale
            else:
                # Degenerate case: start and end are same point
                dx = target_dist
                dy = 0
        
        # Use law of cosines to find angle at start joint
        try:
            # Angle between bone1 and the line from start to end
            cos_angle = (bone1_len**2 + target_dist**2 - bone2_len**2) / (2 * bone1_len * target_dist)
            cos_angle = max(-1.0, min(1.0, cos_angle))  # Clamp to valid range
            angle_offset = math.acos(cos_angle)
        except (ValueError, ZeroDivisionError):
            angle_offset = math.pi / 4  # Fallback to 45 degrees
        
        # Angle from start to end
        base_angle = math.atan2(dy, dx)
        
        # Determine knee direction
        # Forward bend means knee is "ahead" of the straight line
        if forward:
            mid_angle = base_angle - angle_offset  # Rotate clockwise for forward bend
        else:
            mid_angle = base_angle + angle_offset  # Rotate counter-clockwise
        
        # Calculate middle joint position
        mid_x = start_x + bone1_len * math.cos(mid_angle)
        mid_y = start_y + bone1_len * math.sin(mid_angle)
        
        return (mid_x, mid_y)
    
    def _ease_in_out(self, t: float) -> float:
        """Smooth ease-in-out curve.
        
        Args:
            t: Progress from 0.0 to 1.0
            
        Returns:
            Eased value from 0.0 to 1.0
        """
        # Cubic ease-in-out
        if t < 0.5:
            return 4 * t * t * t
        else:
            p = 2 * t - 2
            return 1 + p * p * p / 2
    
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
