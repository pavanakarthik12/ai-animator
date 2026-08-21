"""Character Consistency Validation - Phase 1.5

Validates that different poses maintain constant character proportions.

CRITICAL: Different poses must not create different characters.
Bone lengths, skeleton topology, and character proportions must remain stable.
"""

import math
from typing import Dict, Tuple, List, Optional
from dataclasses import dataclass, field
from character_model import CharacterModel


@dataclass
class BoneViolation:
    """Records a bone length violation."""
    bone_name: str
    parent_joint: str
    child_joint: str
    expected_length: float
    actual_length: float
    deviation: float
    deviation_ratio: float
    
    def __str__(self) -> str:
        return (
            f"{self.bone_name}: expected={self.expected_length:.2f}, "
            f"actual={self.actual_length:.2f}, "
            f"deviation={self.deviation:.2f} ({self.deviation_ratio*100:.1f}%)"
        )


@dataclass
class ConsistencyResult:
    """Result of consistency validation."""
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    violations: List[BoneViolation] = field(default_factory=list)
    frame_index: Optional[int] = None
    
    def add_error(self, message: str):
        """Add an error message."""
        self.errors.append(message)
        self.valid = False
    
    def add_warning(self, message: str):
        """Add a warning message."""
        self.warnings.append(message)
    
    def add_violation(self, violation: BoneViolation):
        """Add a bone length violation."""
        self.violations.append(violation)
        self.valid = False
    
    def __str__(self) -> str:
        status = "VALID" if self.valid else "INVALID"
        frame_info = f" (frame {self.frame_index})" if self.frame_index is not None else ""
        parts = [f"ConsistencyResult: {status}{frame_info}"]
        
        if self.errors:
            parts.append(f"  Errors: {len(self.errors)}")
            for err in self.errors:
                parts.append(f"    - {err}")
        
        if self.violations:
            parts.append(f"  Violations: {len(self.violations)}")
            for v in self.violations:
                parts.append(f"    - {v}")
        
        if self.warnings:
            parts.append(f"  Warnings: {len(self.warnings)}")
            for warn in self.warnings:
                parts.append(f"    - {warn}")
        
        return "\n".join(parts)


class ConsistencyValidator:
    """Validates character consistency across poses.
    
    Ensures that changing poses does not change character proportions.
    """
    
    # Bones to validate (child -> parent relationships)
    BONES_TO_VALIDATE = [
        ("elbow_l", "shoulder_l", "left_upper_arm"),
        ("hand_l", "elbow_l", "left_forearm"),
        ("elbow_r", "shoulder_r", "right_upper_arm"),
        ("hand_r", "elbow_r", "right_forearm"),
        ("knee_l", "hip_l", "left_thigh"),
        ("foot_l", "knee_l", "left_shin"),
        ("knee_r", "hip_r", "right_thigh"),
        ("foot_r", "knee_r", "right_shin"),
    ]
    
    def __init__(self, length_tolerance_ratio: float = 0.01):
        """
        Args:
            length_tolerance_ratio: Maximum allowed deviation ratio (default 1%)
        """
        if length_tolerance_ratio < 0:
            raise ValueError("length_tolerance_ratio must be non-negative")
        
        self.length_tolerance_ratio = length_tolerance_ratio
    
    def validate_pose(
        self,
        character: CharacterModel,
        pose: Dict[str, Tuple[float, float]]
    ) -> ConsistencyResult:
        """Validate a single pose against the character model.
        
        Args:
            character: Reference character model
            pose: Joint positions {joint_name: (x, y)}
        
        Returns:
            ConsistencyResult with validation outcome
        """
        result = ConsistencyResult(valid=True)
        
        # Validate skeleton topology
        self._validate_topology(character, pose, result)
        
        # Validate bone lengths
        self._validate_bone_lengths(character, pose, result)
        
        # Validate head dimensions if available
        self._validate_head_dimensions(character, pose, result)
        
        return result
    
    def validate_sequence(
        self,
        character: CharacterModel,
        poses: List[Dict[str, Tuple[float, float]]]
    ) -> List[ConsistencyResult]:
        """Validate a sequence of poses against the character model.
        
        Each pose is validated independently against the reference model.
        This detects cumulative drift across frames.
        
        Args:
            character: Reference character model
            poses: List of pose dictionaries
        
        Returns:
            List of ConsistencyResult, one per frame
        """
        results = []
        for i, pose in enumerate(poses):
            result = self.validate_pose(character, pose)
            result.frame_index = i
            results.append(result)
        return results
    
    def _validate_topology(
        self,
        character: CharacterModel,
        pose: Dict[str, Tuple[float, float]],
        result: ConsistencyResult
    ):
        """Validate skeleton topology matches character model."""
        skeleton = character.skeleton
        
        # Check all required joints exist
        for joint in CharacterModel.REQUIRED_JOINTS:
            if joint not in pose:
                result.add_error(f"Missing required joint: {joint}")
        
        # Check parent-child relationships remain valid
        for joint in pose:
            if not skeleton.has_joint(joint):
                result.add_error(f"Unknown joint in pose: {joint}")
                continue
            
            parent = skeleton.get_parent(joint)
            if parent is not None and parent not in pose:
                result.add_error(
                    f"Joint {joint} requires parent {parent} which is missing from pose"
                )
    
    def _validate_bone_lengths(
        self,
        character: CharacterModel,
        pose: Dict[str, Tuple[float, float]],
        result: ConsistencyResult
    ):
        """Validate bone lengths match reference within tolerance."""
        for child_joint, parent_joint, bone_name in self.BONES_TO_VALIDATE:
            # Skip if joints missing (topology validation will catch this)
            if child_joint not in pose or parent_joint not in pose:
                continue
            
            # Get expected length from character model
            expected_length = character.get_limb_length(child_joint)
            if expected_length == 0:
                # Skip validation if reference length is zero
                continue
            
            # Calculate actual length in pose
            cx, cy = pose[child_joint]
            px, py = pose[parent_joint]
            actual_length = math.hypot(cx - px, cy - py)
            
            # Calculate deviation
            deviation = abs(actual_length - expected_length)
            deviation_ratio = deviation / expected_length if expected_length > 0 else 0
            
            # Check against tolerance
            if deviation_ratio > self.length_tolerance_ratio:
                violation = BoneViolation(
                    bone_name=bone_name,
                    parent_joint=parent_joint,
                    child_joint=child_joint,
                    expected_length=expected_length,
                    actual_length=actual_length,
                    deviation=deviation,
                    deviation_ratio=deviation_ratio
                )
                result.add_violation(violation)
            elif deviation > 0.001:  # Tiny float differences as warnings
                result.add_warning(
                    f"Small deviation in {bone_name}: {deviation:.4f} pixels "
                    f"({deviation_ratio*100:.2f}%)"
                )
    
    def _validate_head_dimensions(
        self,
        character: CharacterModel,
        pose: Dict[str, Tuple[float, float]],
        result: ConsistencyResult
    ):
        """Validate head dimensions remain consistent."""
        # Check if we can validate head
        if "neck" not in pose or "head" not in pose:
            return
        
        # Get expected head height from character model
        expected_head_height = character.get_limb_length("head")
        if expected_head_height == 0:
            return
        
        # Calculate actual head height in pose
        nx, ny = pose["neck"]
        hx, hy = pose["head"]
        actual_head_height = math.hypot(hx - nx, hy - ny)
        
        # Calculate deviation
        deviation = abs(actual_head_height - expected_head_height)
        deviation_ratio = deviation / expected_head_height
        
        # Check against tolerance
        if deviation_ratio > self.length_tolerance_ratio:
            violation = BoneViolation(
                bone_name="head",
                parent_joint="neck",
                child_joint="head",
                expected_length=expected_head_height,
                actual_length=actual_head_height,
                deviation=deviation,
                deviation_ratio=deviation_ratio
            )
            result.add_violation(violation)
        elif deviation > 0.001:
            result.add_warning(
                f"Small deviation in head: {deviation:.4f} pixels "
                f"({deviation_ratio*100:.2f}%)"
            )


def validate_pose(
    character: CharacterModel,
    pose: Dict[str, Tuple[float, float]],
    tolerance: float = 0.01
) -> ConsistencyResult:
    """Convenience function to validate a single pose.
    
    Args:
        character: Reference character model
        pose: Joint positions {joint_name: (x, y)}
        tolerance: Maximum allowed deviation ratio (default 1%)
    
    Returns:
        ConsistencyResult
    """
    validator = ConsistencyValidator(length_tolerance_ratio=tolerance)
    return validator.validate_pose(character, pose)


def validate_sequence(
    character: CharacterModel,
    poses: List[Dict[str, Tuple[float, float]]],
    tolerance: float = 0.01
) -> List[ConsistencyResult]:
    """Convenience function to validate a pose sequence.
    
    Args:
        character: Reference character model
        poses: List of pose dictionaries
        tolerance: Maximum allowed deviation ratio (default 1%)
    
    Returns:
        List of ConsistencyResult
    """
    validator = ConsistencyValidator(length_tolerance_ratio=tolerance)
    return validator.validate_sequence(character, poses)
