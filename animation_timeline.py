"""Animation Timeline and Planning - Phase 2

Generic timeline and key pose planning for arbitrary-length animations.

NO DRAWING. NO GROQ. NO KRITA. NO MCP.
This is a pure planning/data layer.
"""

from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


# Reuse existing pose type: Dict[str, Tuple[float, float]]
Pose = Dict[str, Tuple[float, float]]


@dataclass
class AnimationRequest:
    """Generic animation request.
    
    Represents user intent for an animation action.
    """
    action: str  # e.g., "walk", "run", "wave", "sit", "stand", "jump"
    frame_count: int
    loop: bool = True
    direction: str = "forward"  # "forward", "backward", "left", "right"
    speed: str = "normal"  # "slow", "normal", "fast"
    style: str = "natural"  # "natural", "energetic", "relaxed"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate animation request."""
        if self.frame_count < 1:
            raise ValueError(f"frame_count must be >= 1, got {self.frame_count}")
        if not self.action:
            raise ValueError("action cannot be empty")


@dataclass
class TimelineSegment:
    """Represents a meaningful action phase within a timeline.
    
    Generic segment that can represent any action phase.
    """
    name: str  # e.g., "walk_cycle", "stop", "wave", "transition"
    action: str  # e.g., "walk", "stop", "wave"
    start_frame: int
    end_frame: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate segment."""
        if self.start_frame < 1:
            raise ValueError(f"start_frame must be >= 1, got {self.start_frame}")
        if self.end_frame < self.start_frame:
            raise ValueError(
                f"end_frame ({self.end_frame}) must be >= start_frame ({self.start_frame})"
            )
    
    def duration(self) -> int:
        """Get segment duration in frames."""
        return self.end_frame - self.start_frame + 1
    
    def contains_frame(self, frame: int) -> bool:
        """Check if frame is within segment."""
        return self.start_frame <= frame <= self.end_frame
    
    def __str__(self) -> str:
        return (
            f"Segment({self.name}: {self.action} "
            f"[{self.start_frame}-{self.end_frame}] = {self.duration()} frames)"
        )


@dataclass
class KeyPose:
    """Represents an important pose at a specific frame.
    
    Key poses mark critical moments in animation (contacts, extremes, etc.)
    NOT every frame needs a key pose - interpolation fills the gaps.
    """
    frame: int
    pose: Pose  # Reuses existing Dict[str, Tuple[float, float]]
    label: str  # e.g., "contact", "passing", "extreme", "start", "end"
    segment: Optional[str] = None  # Associated segment name
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate key pose."""
        if self.frame < 1:
            raise ValueError(f"frame must be >= 1, got {self.frame}")
        if not self.pose:
            raise ValueError("pose cannot be empty")
        if not self.label:
            raise ValueError("label cannot be empty")
    
    def __str__(self) -> str:
        segment_info = f" ({self.segment})" if self.segment else ""
        return f"KeyPose(frame={self.frame}, label={self.label}{segment_info})"


@dataclass
class Timeline:
    """Complete animation timeline.
    
    Represents the full frame range and structure of an animation.
    """
    total_frames: int
    segments: List[TimelineSegment] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate timeline."""
        if self.total_frames < 1:
            raise ValueError(f"total_frames must be >= 1, got {self.total_frames}")
    
    def add_segment(self, segment: TimelineSegment):
        """Add a segment to the timeline."""
        # Validate segment is within timeline bounds
        if segment.end_frame > self.total_frames:
            raise ValueError(
                f"Segment end_frame ({segment.end_frame}) exceeds "
                f"timeline total_frames ({self.total_frames})"
            )
        self.segments.append(segment)
    
    def get_segment_at_frame(self, frame: int) -> Optional[TimelineSegment]:
        """Get segment containing the given frame."""
        for segment in self.segments:
            if segment.contains_frame(frame):
                return segment
        return None
    
    def __str__(self) -> str:
        seg_count = len(self.segments)
        return f"Timeline(1-{self.total_frames}, {seg_count} segments)"


@dataclass
class AnimationPlan:
    """Complete animation plan.
    
    Contains the full structure: request, timeline, segments, and key poses.
    This is a pure data structure - no rendering, no Krita, no MCP.
    """
    request: AnimationRequest
    timeline: Timeline
    key_poses: List[KeyPose] = field(default_factory=list)
    validated: bool = False
    validation_errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_key_pose(self, key_pose: KeyPose):
        """Add a key pose to the plan."""
        # Validate key pose is within timeline
        if key_pose.frame > self.timeline.total_frames:
            raise ValueError(
                f"KeyPose frame ({key_pose.frame}) exceeds "
                f"timeline total_frames ({self.timeline.total_frames})"
            )
        self.key_poses.append(key_pose)
    
    def get_key_poses_sorted(self) -> List[KeyPose]:
        """Get key poses sorted by frame number."""
        return sorted(self.key_poses, key=lambda kp: kp.frame)
    
    def get_key_pose_at_frame(self, frame: int) -> Optional[KeyPose]:
        """Get key pose at specific frame (if any)."""
        for kp in self.key_poses:
            if kp.frame == frame:
                return kp
        return None
    
    def __str__(self) -> str:
        action = self.request.action
        frames = self.timeline.total_frames
        seg_count = len(self.timeline.segments)
        kp_count = len(self.key_poses)
        status = "VALID" if self.validated else "NOT VALIDATED"
        return (
            f"AnimationPlan({action}, {frames} frames, "
            f"{seg_count} segments, {kp_count} key poses, {status})"
        )


class TimelineAllocator:
    """Deterministic timeline segment allocator.
    
    Allocates frame ranges to action phases within a requested budget.
    NO AI. NO GROQ. Pure deterministic logic.
    """
    
    def __init__(self):
        """Initialize allocator."""
        pass
    
    def allocate_simple(
        self,
        request: AnimationRequest
    ) -> Timeline:
        """Allocate a simple single-action timeline.
        
        For basic requests like "walk for 240 frames", creates a single segment.
        """
        timeline = Timeline(total_frames=request.frame_count)
        
        segment = TimelineSegment(
            name=f"{request.action}_main",
            action=request.action,
            start_frame=1,
            end_frame=request.frame_count
        )
        
        timeline.add_segment(segment)
        return timeline
    
    def allocate_compound(
        self,
        request: AnimationRequest,
        phases: List[Tuple[str, float]]  # [(action, weight), ...]
    ) -> Timeline:
        """Allocate timeline for compound actions.
        
        Args:
            request: Animation request with total frame budget
            phases: List of (action_name, weight) tuples
                   Weights determine proportional frame allocation
        
        Example:
            phases = [("walk", 0.6), ("stop", 0.1), ("wave", 0.3)]
            For 240 frames: walk=144, stop=24, wave=72
        """
        timeline = Timeline(total_frames=request.frame_count)
        
        if not phases:
            raise ValueError("phases cannot be empty")
        
        # Normalize weights
        total_weight = sum(w for _, w in phases)
        if total_weight <= 0:
            raise ValueError("total weight must be positive")
        
        # Allocate frames proportionally
        current_frame = 1
        for i, (action, weight) in enumerate(phases):
            # Calculate frames for this phase
            if i == len(phases) - 1:
                # Last phase gets remaining frames
                phase_frames = request.frame_count - current_frame + 1
            else:
                phase_frames = int((weight / total_weight) * request.frame_count)
                phase_frames = max(1, phase_frames)  # At least 1 frame
            
            end_frame = current_frame + phase_frames - 1
            
            # Ensure we don't exceed budget
            if end_frame > request.frame_count:
                end_frame = request.frame_count
            
            segment = TimelineSegment(
                name=f"{action}_{i+1}",
                action=action,
                start_frame=current_frame,
                end_frame=end_frame
            )
            
            timeline.add_segment(segment)
            current_frame = end_frame + 1
            
            # Break if we've reached the end
            if current_frame > request.frame_count:
                break
        
        return timeline
    
    def allocate_uniform(
        self,
        request: AnimationRequest,
        actions: List[str]
    ) -> Timeline:
        """Allocate timeline with equal distribution across actions.
        
        Args:
            request: Animation request with total frame budget
            actions: List of action names (each gets equal frames)
        """
        if not actions:
            raise ValueError("actions cannot be empty")
        
        phases = [(action, 1.0) for action in actions]
        return self.allocate_compound(request, phases)


class TimelineValidator:
    """Validates animation plans for correctness.
    
    Ensures timelines are complete, non-overlapping, and valid.
    """
    
    def validate_plan(self, plan: AnimationPlan) -> Tuple[bool, List[str]]:
        """Validate complete animation plan.
        
        Returns:
            (is_valid, error_messages)
        """
        errors = []
        
        # Validate timeline coverage
        coverage_errors = self._validate_coverage(plan.timeline)
        errors.extend(coverage_errors)
        
        # Validate no overlaps
        overlap_errors = self._validate_no_overlaps(plan.timeline)
        errors.extend(overlap_errors)
        
        # Validate segments within bounds
        bounds_errors = self._validate_bounds(plan.timeline)
        errors.extend(bounds_errors)
        
        # Validate key poses
        kp_errors = self._validate_key_poses(plan)
        errors.extend(kp_errors)
        
        is_valid = len(errors) == 0
        return is_valid, errors
    
    def _validate_coverage(self, timeline: Timeline) -> List[str]:
        """Validate timeline has complete coverage (no gaps)."""
        errors = []
        
        if not timeline.segments:
            errors.append("Timeline has no segments")
            return errors
        
        # Sort segments by start frame
        sorted_segments = sorted(timeline.segments, key=lambda s: s.start_frame)
        
        # Check first segment starts at frame 1
        if sorted_segments[0].start_frame != 1:
            errors.append(
                f"Timeline does not start at frame 1 "
                f"(first segment starts at {sorted_segments[0].start_frame})"
            )
        
        # Check for gaps between segments
        for i in range(len(sorted_segments) - 1):
            current = sorted_segments[i]
            next_seg = sorted_segments[i + 1]
            
            if current.end_frame + 1 < next_seg.start_frame:
                gap_start = current.end_frame + 1
                gap_end = next_seg.start_frame - 1
                errors.append(
                    f"Gap detected: frames {gap_start}-{gap_end} "
                    f"between '{current.name}' and '{next_seg.name}'"
                )
        
        # Check last segment ends at total_frames
        if sorted_segments[-1].end_frame != timeline.total_frames:
            errors.append(
                f"Timeline does not end at frame {timeline.total_frames} "
                f"(last segment ends at {sorted_segments[-1].end_frame})"
            )
        
        return errors
    
    def _validate_no_overlaps(self, timeline: Timeline) -> List[str]:
        """Validate segments don't overlap."""
        errors = []
        
        for i, seg1 in enumerate(timeline.segments):
            for j, seg2 in enumerate(timeline.segments):
                if i >= j:
                    continue
                
                # Check for overlap
                if seg1.start_frame <= seg2.end_frame and seg2.start_frame <= seg1.end_frame:
                    errors.append(
                        f"Segments overlap: '{seg1.name}' [{seg1.start_frame}-{seg1.end_frame}] "
                        f"and '{seg2.name}' [{seg2.start_frame}-{seg2.end_frame}]"
                    )
        
        return errors
    
    def _validate_bounds(self, timeline: Timeline) -> List[str]:
        """Validate all segments are within timeline bounds."""
        errors = []
        
        for segment in timeline.segments:
            if segment.start_frame < 1:
                errors.append(
                    f"Segment '{segment.name}' starts before frame 1 "
                    f"(start_frame={segment.start_frame})"
                )
            
            if segment.end_frame > timeline.total_frames:
                errors.append(
                    f"Segment '{segment.name}' exceeds timeline bounds "
                    f"(end_frame={segment.end_frame} > total={timeline.total_frames})"
                )
        
        return errors
    
    def _validate_key_poses(self, plan: AnimationPlan) -> List[str]:
        """Validate key poses are valid."""
        errors = []
        
        # Check key poses are within bounds
        for kp in plan.key_poses:
            if kp.frame < 1:
                errors.append(
                    f"KeyPose '{kp.label}' at frame {kp.frame} is before frame 1"
                )
            
            if kp.frame > plan.timeline.total_frames:
                errors.append(
                    f"KeyPose '{kp.label}' at frame {kp.frame} exceeds "
                    f"timeline bounds (total={plan.timeline.total_frames})"
                )
        
        # Check for duplicate frames
        frame_counts: Dict[int, List[str]] = {}
        for kp in plan.key_poses:
            if kp.frame not in frame_counts:
                frame_counts[kp.frame] = []
            frame_counts[kp.frame].append(kp.label)
        
        for frame, labels in frame_counts.items():
            if len(labels) > 1:
                errors.append(
                    f"Multiple key poses at frame {frame}: {', '.join(labels)}"
                )
        
        return errors


def create_simple_plan(request: AnimationRequest) -> AnimationPlan:
    """Create a simple animation plan for a single action.
    
    Convenience function for basic single-action animations.
    """
    allocator = TimelineAllocator()
    timeline = allocator.allocate_simple(request)
    
    plan = AnimationPlan(
        request=request,
        timeline=timeline
    )
    
    # Validate plan
    validator = TimelineValidator()
    is_valid, errors = validator.validate_plan(plan)
    plan.validated = is_valid
    plan.validation_errors = errors
    
    return plan


def create_compound_plan(
    request: AnimationRequest,
    phases: List[Tuple[str, float]]
) -> AnimationPlan:
    """Create animation plan for compound actions.
    
    Args:
        request: Animation request with total frame budget
        phases: List of (action_name, weight) tuples
    """
    allocator = TimelineAllocator()
    timeline = allocator.allocate_compound(request, phases)
    
    plan = AnimationPlan(
        request=request,
        timeline=timeline
    )
    
    # Validate plan
    validator = TimelineValidator()
    is_valid, errors = validator.validate_plan(plan)
    plan.validated = is_valid
    plan.validation_errors = errors
    
    return plan
