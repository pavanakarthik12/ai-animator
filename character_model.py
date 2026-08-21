"""Character Model - Generic character representation for animation.

This module defines the stable properties of a character that remain constant
across animation frames. It wraps the existing CharacterRig with additional
metadata about proportions, dimensions, and constraints.

Phase 1: Foundation only - no animation, no drawing, no MCP/Groq calls.
"""

import math
from typing import Dict, Tuple, Optional, List
from animation_planner import CharacterRig, BONE_HIERARCHY


class CharacterDimensions:
    """Character proportions and measurements."""
    
    def __init__(
        self,
        height: float,
        head_width: float,
        head_height: float,
        torso_width: float,
        torso_height: float,
        shoulder_width: float,
        hip_width: float,
        upper_arm_length: float,
        forearm_length: float,
        hand_length: float,
        thigh_length: float,
        shin_length: float,
        foot_length: float
    ):
        # Validation
        if height <= 0:
            raise ValueError(f"Character height must be positive, got {height}")
        if any(v < 0 for v in [head_width, head_height, torso_width, torso_height,
                                shoulder_width, hip_width, upper_arm_length, 
                                forearm_length, hand_length, thigh_length, 
                                shin_length, foot_length]):
            raise ValueError("All dimension values must be non-negative")
        
        self.height = height
        self.head_width = head_width
        self.head_height = head_height
        self.torso_width = torso_width
        self.torso_height = torso_height
        self.shoulder_width = shoulder_width
        self.hip_width = hip_width
        self.upper_arm_length = upper_arm_length
        self.forearm_length = forearm_length
        self.hand_length = hand_length
        self.thigh_length = thigh_length
        self.shin_length = shin_length
        self.foot_length = foot_length
    
    def validate(self) -> bool:
        """Validate that dimensions are reasonable."""
        if self.height <= 0:
            return False
        if self.upper_arm_length <= 0 or self.forearm_length <= 0:
            return False
        if self.thigh_length <= 0 or self.shin_length <= 0:
            return False
        return True


class JointConstraints:
    """Constraints for a joint (rotation limits, preferred bend direction)."""
    
    def __init__(
        self,
        min_rotation: Optional[float] = None,
        max_rotation: Optional[float] = None,
        preferred_bend_direction: Optional[float] = None,
        locked: bool = False
    ):
        self.min_rotation = min_rotation  # radians
        self.max_rotation = max_rotation  # radians
        self.preferred_bend_direction = preferred_bend_direction  # radians
        self.locked = locked


class Skeleton:
    """Generic 2D skeleton representation."""
    
    def __init__(self, hierarchy: Dict[str, Optional[str]]):
        """
        Args:
            hierarchy: Dict mapping joint name to parent joint name (None for root)
        """
        self.hierarchy = hierarchy
        self._validate_hierarchy()
    
    def _validate_hierarchy(self):
        """Validate skeleton has no circular dependencies."""
        for joint in self.hierarchy:
            visited = set()
            current = joint
            while current is not None:
                if current in visited:
                    raise ValueError(f"Circular hierarchy detected involving joint: {joint}")
                visited.add(current)
                current = self.hierarchy.get(current)
    
    def get_parent(self, joint: str) -> Optional[str]:
        """Get parent joint name."""
        return self.hierarchy.get(joint)
    
    def get_children(self, joint: str) -> List[str]:
        """Get all child joints."""
        return [j for j, p in self.hierarchy.items() if p == joint]
    
    def get_joint_path_to_root(self, joint: str) -> List[str]:
        """Get list of joints from this joint to root."""
        path = []
        current = joint
        while current is not None:
            path.append(current)
            current = self.hierarchy.get(current)
        return path
    
    def has_joint(self, joint: str) -> bool:
        """Check if joint exists in skeleton."""
        return joint in self.hierarchy
    
    def get_all_joints(self) -> List[str]:
        """Get list of all joint names."""
        return list(self.hierarchy.keys())


class CharacterModel:
    """Generic character model containing stable properties for animation.
    
    This represents WHAT the character IS, not WHERE it is at any moment.
    Pose information is separate and changes per frame.
    """
    
    # Required joints for a valid humanoid character
    REQUIRED_JOINTS = [
        "root", "torso", "neck", "head",
        "shoulder_l", "elbow_l", "hand_l",
        "shoulder_r", "elbow_r", "hand_r",
        "hip_l", "knee_l", "foot_l",
        "hip_r", "knee_r", "foot_r"
    ]
    
    def __init__(
        self,
        name: str,
        skeleton: Skeleton,
        neutral_pose: Dict[str, Tuple[float, float]],
        dimensions: CharacterDimensions,
        joint_constraints: Optional[Dict[str, JointConstraints]] = None
    ):
        """
        Args:
            name: Character identifier
            skeleton: Skeleton structure
            neutral_pose: Joint positions in neutral/reference pose {joint_name: (x, y)}
            dimensions: Character proportions and measurements
            joint_constraints: Optional constraints per joint
        """
        self.name = name
        self.skeleton = skeleton
        self.neutral_pose = neutral_pose
        self.dimensions = dimensions
        self.joint_constraints = joint_constraints or {}
        
        self._validate()
    
    def _validate(self):
        """Validate character model consistency."""
        # Check dimensions are valid
        if not self.dimensions.validate():
            raise ValueError("Invalid character dimensions")
        
        # Check all required joints exist in skeleton
        for joint in self.REQUIRED_JOINTS:
            if not self.skeleton.has_joint(joint):
                raise ValueError(f"Required joint missing from skeleton: {joint}")
        
        # Check neutral pose has all skeleton joints
        for joint in self.skeleton.get_all_joints():
            if joint not in self.neutral_pose:
                raise ValueError(f"Neutral pose missing joint: {joint}")
        
        # Validate parent-child relationships
        required_relationships = [
            ("neck", "torso"),
            ("head", "neck"),
            ("shoulder_l", "torso"),
            ("elbow_l", "shoulder_l"),
            ("hand_l", "elbow_l"),
            ("shoulder_r", "torso"),
            ("elbow_r", "shoulder_r"),
            ("hand_r", "elbow_r"),
            ("hip_l", "root"),
            ("knee_l", "hip_l"),
            ("foot_l", "knee_l"),
            ("hip_r", "root"),
            ("knee_r", "hip_r"),
            ("foot_r", "knee_r"),
        ]
        
        for child, expected_parent in required_relationships:
            actual_parent = self.skeleton.get_parent(child)
            if actual_parent != expected_parent:
                raise ValueError(
                    f"Invalid parent for {child}: expected {expected_parent}, got {actual_parent}"
                )
    
    def get_limb_length(self, joint_name: str) -> float:
        """Calculate bone length from joint to its parent in neutral pose."""
        parent = self.skeleton.get_parent(joint_name)
        if parent is None:
            return 0.0
        
        if joint_name not in self.neutral_pose or parent not in self.neutral_pose:
            return 0.0
        
        jx, jy = self.neutral_pose[joint_name]
        px, py = self.neutral_pose[parent]
        return math.hypot(jx - px, jy - py)
    
    def get_constraint(self, joint_name: str) -> Optional[JointConstraints]:
        """Get constraints for a joint."""
        return self.joint_constraints.get(joint_name)
    
    def create_rig(self) -> CharacterRig:
        """Create a CharacterRig instance from this model.
        
        This bridges to the existing animation system.
        """
        return CharacterRig(self.neutral_pose)
    
    @classmethod
    def from_rest_joints(
        cls,
        name: str,
        rest_joints: Dict[str, Tuple[float, float]],
        hierarchy: Optional[Dict[str, Optional[str]]] = None
    ) -> 'CharacterModel':
        """Create CharacterModel from existing rest joints data.
        
        Args:
            name: Character name
            rest_joints: Joint positions {joint_name: (x, y)}
            hierarchy: Optional skeleton hierarchy (uses BONE_HIERARCHY if None)
        
        Returns:
            CharacterModel instance
        """
        if hierarchy is None:
            hierarchy = BONE_HIERARCHY
        
        skeleton = Skeleton(hierarchy)
        
        # Calculate dimensions from rest joints
        dimensions = cls._calculate_dimensions_from_joints(rest_joints)
        
        return cls(
            name=name,
            skeleton=skeleton,
            neutral_pose=rest_joints,
            dimensions=dimensions
        )
    
    @staticmethod
    def _calculate_dimensions_from_joints(
        joints: Dict[str, Tuple[float, float]]
    ) -> CharacterDimensions:
        """Calculate character dimensions from joint positions."""
        
        def distance(j1: str, j2: str) -> float:
            if j1 not in joints or j2 not in joints:
                return 0.0
            x1, y1 = joints[j1]
            x2, y2 = joints[j2]
            return math.hypot(x2 - x1, y2 - y1)
        
        # Calculate limb lengths
        upper_arm_l = distance("shoulder_l", "elbow_l")
        forearm_l = distance("elbow_l", "hand_l")
        hand_l = 0.0  # Not represented as separate segment yet
        
        thigh_l = distance("hip_l", "knee_l")
        shin_l = distance("knee_l", "foot_l")
        foot_l = 0.0  # Not represented as separate segment yet
        
        # Torso dimensions
        torso_height = distance("root", "torso")
        shoulder_width = distance("shoulder_l", "shoulder_r")
        hip_width = distance("hip_l", "hip_r")
        torso_width = max(shoulder_width, hip_width)
        
        # Head dimensions
        head_height = distance("neck", "head")
        head_width = head_height * 0.8 if head_height > 0 else 0.0  # Estimate
        
        # Total height (rough approximation)
        leg_length = thigh_l + shin_l
        height = torso_height + head_height + leg_length
        
        return CharacterDimensions(
            height=height,
            head_width=head_width,
            head_height=head_height,
            torso_width=torso_width,
            torso_height=torso_height,
            shoulder_width=shoulder_width,
            hip_width=hip_width,
            upper_arm_length=upper_arm_l,
            forearm_length=forearm_l,
            hand_length=hand_l,
            thigh_length=thigh_l,
            shin_length=shin_l,
            foot_length=foot_l
        )
    
    def __repr__(self) -> str:
        return (
            f"CharacterModel(name={self.name!r}, "
            f"height={self.dimensions.height:.1f}, "
            f"joints={len(self.neutral_pose)})"
        )
