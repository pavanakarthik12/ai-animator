"""Character Pose Transformation - Phase 1.6

Transforms character strokes from neutral pose to target pose while preserving:
- Exact stroke count
- Stroke identity
- Stroke thickness
- No invented strokes
- No duplicate strokes
- No stroke splitting/merging

CRITICAL: The output must contain ONLY transformed versions of master strokes.
"""

import math
from typing import Dict, Tuple, List, Optional
from dataclasses import dataclass, field
from character_model import CharacterModel
from character_consistency import ConsistencyValidator, ConsistencyResult


@dataclass
class StrokeIdentity:
    """Immutable stroke identity."""
    master_id: str  # Original stroke ID from master geometry
    body_part: Optional[str] = None  # Associated body part (if known)
    
    def __str__(self) -> str:
        if self.body_part:
            return f"{self.master_id} ({self.body_part})"
        return self.master_id


@dataclass
class MasterStroke:
    """Master stroke from neutral pose geometry.
    
    This is the immutable source of truth for stroke identity and properties.
    """
    identity: StrokeIdentity
    points: List[Tuple[float, float]]  # Original points in neutral pose
    color: str
    brush_size: int
    closed: bool = False
    
    def __post_init__(self):
        """Validate master stroke."""
        if len(self.points) < 2:
            raise ValueError(f"Stroke {self.identity} must have at least 2 points")
        if self.brush_size <= 0:
            raise ValueError(f"Stroke {self.identity} must have positive brush size")


@dataclass
class TransformedStroke:
    """Transformed stroke for a specific pose.
    
    Maintains identity and properties from master, with transformed points.
    """
    identity: StrokeIdentity  # MUST match master stroke identity
    points: List[Tuple[float, float]]  # Transformed points
    color: str  # MUST match master stroke color
    brush_size: int  # MUST match master stroke brush_size
    closed: bool  # MUST match master stroke closed
    
    def to_dict(self) -> Dict:
        """Convert to renderer-compatible dict format."""
        return {
            "stroke_id": self.identity.master_id,
            "points": [[int(round(x)), int(round(y))] for x, y in self.points],
            "color": self.color,
            "brush_size": self.brush_size,
            "closed": self.closed
        }


@dataclass
class MasterGeometry:
    """Immutable master character geometry.
    
    This represents the character in neutral pose and is NEVER modified.
    """
    character: CharacterModel
    strokes: List[MasterStroke]
    
    def __post_init__(self):
        """Validate master geometry."""
        if len(self.strokes) == 0:
            raise ValueError("Master geometry must contain at least one stroke")
        
        # Verify unique stroke IDs
        ids = [s.identity.master_id for s in self.strokes]
        if len(ids) != len(set(ids)):
            raise ValueError("Master geometry contains duplicate stroke IDs")
    
    def get_stroke_count(self) -> int:
        """Get number of strokes in master geometry."""
        return len(self.strokes)
    
    def get_stroke_ids(self) -> List[str]:
        """Get list of all stroke IDs."""
        return [s.identity.master_id for s in self.strokes]


@dataclass
class TransformationResult:
    """Result of pose transformation."""
    valid: bool
    transformed_strokes: List[TransformedStroke] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Validation metrics
    master_stroke_count: int = 0
    output_stroke_count: int = 0
    missing_strokes: List[str] = field(default_factory=list)
    duplicate_strokes: List[str] = field(default_factory=list)
    new_strokes: List[str] = field(default_factory=list)
    thickness_changes: int = 0
    color_changes: int = 0
    
    # Consistency validation result
    consistency_result: Optional[ConsistencyResult] = None
    
    def add_error(self, message: str):
        """Add an error message."""
        self.errors.append(message)
        self.valid = False
    
    def add_warning(self, message: str):
        """Add a warning message."""
        self.warnings.append(message)
    
    def to_dict_list(self) -> List[Dict]:
        """Convert transformed strokes to dict list for rendering."""
        if not self.valid:
            raise ValueError("Cannot convert invalid transformation to dict list")
        return [s.to_dict() for s in self.transformed_strokes]


class PoseTransformer:
    """Transforms character geometry from neutral pose to target pose.
    
    CRITICAL RULES:
    1. NO new strokes created
    2. NO strokes deleted
    3. NO strokes duplicated
    4. NO strokes split
    5. NO strokes merged
    6. Stroke identity preserved
    7. Stroke properties preserved
    8. Master geometry remains immutable
    """
    
    def __init__(
        self,
        master_geometry: MasterGeometry,
        consistency_validator: Optional[ConsistencyValidator] = None
    ):
        """
        Args:
            master_geometry: Immutable master character geometry
            consistency_validator: Optional validator for pose consistency
        """
        self.master_geometry = master_geometry
        self.consistency_validator = consistency_validator or ConsistencyValidator()
    
    def transform_pose(
        self,
        target_pose: Dict[str, Tuple[float, float]]
    ) -> TransformationResult:
        """Transform master geometry to target pose.
        
        Args:
            target_pose: Target joint positions {joint_name: (x, y)}
        
        Returns:
            TransformationResult with validation and transformed strokes
        """
        result = TransformationResult(
            valid=True,
            master_stroke_count=self.master_geometry.get_stroke_count()
        )
        
        # Step 1: Validate pose consistency
        consistency = self.consistency_validator.validate_pose(
            self.master_geometry.character,
            target_pose
        )
        result.consistency_result = consistency
        
        if not consistency.valid:
            result.add_error("Target pose fails consistency validation")
            for error in consistency.errors:
                result.add_error(f"Consistency: {error}")
            for violation in consistency.violations:
                result.add_error(f"Consistency: {violation}")
            return result
        
        # Step 2: Build joint transformation maps
        neutral_pose = self.master_geometry.character.neutral_pose
        skeleton = self.master_geometry.character.skeleton
        
        # Calculate per-joint transformations (rotation + translation)
        joint_transforms = self._calculate_joint_transforms(
            neutral_pose,
            target_pose,
            skeleton
        )
        
        # Step 3: Transform each master stroke exactly once
        transformed_strokes = []
        for master_stroke in self.master_geometry.strokes:
            try:
                transformed = self._transform_stroke(
                    master_stroke,
                    joint_transforms,
                    neutral_pose,
                    target_pose,
                    skeleton
                )
                transformed_strokes.append(transformed)
            except Exception as e:
                result.add_error(
                    f"Failed to transform stroke {master_stroke.identity}: {e}"
                )
        
        result.transformed_strokes = transformed_strokes
        result.output_stroke_count = len(transformed_strokes)
        
        # Step 4: Validate transformation
        self._validate_transformation(result)
        
        return result
    
    def _calculate_joint_transforms(
        self,
        neutral_pose: Dict[str, Tuple[float, float]],
        target_pose: Dict[str, Tuple[float, float]],
        skeleton
    ) -> Dict[str, Dict]:
        """Calculate transformation for each joint."""
        transforms = {}
        
        for joint in neutral_pose:
            parent = skeleton.get_parent(joint)
            
            # Get positions
            neutral_pos = neutral_pose[joint]
            target_pos = target_pose.get(joint, neutral_pos)
            
            # Calculate rotation if parent exists
            angle = 0.0
            if parent and parent in neutral_pose and parent in target_pose:
                # Vector from parent to joint in neutral
                n_parent = neutral_pose[parent]
                n_dx = neutral_pos[0] - n_parent[0]
                n_dy = neutral_pos[1] - n_parent[1]
                neutral_angle = math.atan2(n_dy, n_dx)
                
                # Vector from parent to joint in target
                t_parent = target_pose[parent]
                t_dx = target_pos[0] - t_parent[0]
                t_dy = target_pos[1] - t_parent[1]
                target_angle = math.atan2(t_dy, t_dx)
                
                angle = target_angle - neutral_angle
            
            transforms[joint] = {
                "neutral_pos": neutral_pos,
                "target_pos": target_pos,
                "rotation": angle,
                "translation": (
                    target_pos[0] - neutral_pos[0],
                    target_pos[1] - neutral_pos[1]
                )
            }
        
        return transforms
    
    def _transform_stroke(
        self,
        master_stroke: MasterStroke,
        joint_transforms: Dict,
        neutral_pose: Dict[str, Tuple[float, float]],
        target_pose: Dict[str, Tuple[float, float]],
        skeleton
    ) -> TransformedStroke:
        """Transform a single master stroke to target pose.
        
        Uses skinning-like transformation based on nearest joint influence.
        """
        transformed_points = []
        
        for point in master_stroke.points:
            # Find nearest joint in neutral pose
            nearest_joint = self._find_nearest_joint(point, neutral_pose)
            
            # Get transformation for that joint
            transform = joint_transforms.get(nearest_joint)
            if not transform:
                # Fallback: no transformation
                transformed_points.append(point)
                continue
            
            # Get pivot point (parent joint in target pose)
            parent = skeleton.get_parent(nearest_joint)
            if parent and parent in target_pose:
                pivot = target_pose[parent]
            else:
                pivot = transform["target_pos"]
            
            # Transform point relative to pivot
            dx = point[0] - transform["neutral_pos"][0]
            dy = point[1] - transform["neutral_pos"][1]
            
            # Apply rotation around pivot
            angle = transform["rotation"]
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)
            
            rotated_x = dx * cos_a - dy * sin_a
            rotated_y = dx * sin_a + dy * cos_a
            
            # Translate to target position
            final_x = rotated_x + transform["target_pos"][0]
            final_y = rotated_y + transform["target_pos"][1]
            
            transformed_points.append((final_x, final_y))
        
        # Create transformed stroke with preserved identity and properties
        return TransformedStroke(
            identity=master_stroke.identity,  # PRESERVED
            points=transformed_points,  # TRANSFORMED
            color=master_stroke.color,  # PRESERVED
            brush_size=master_stroke.brush_size,  # PRESERVED
            closed=master_stroke.closed  # PRESERVED
        )
    
    def _find_nearest_joint(
        self,
        point: Tuple[float, float],
        joints: Dict[str, Tuple[float, float]]
    ) -> str:
        """Find nearest joint to a point."""
        min_dist = float('inf')
        nearest = "root"
        
        for joint_name, joint_pos in joints.items():
            dx = point[0] - joint_pos[0]
            dy = point[1] - joint_pos[1]
            dist = math.hypot(dx, dy)
            
            if dist < min_dist:
                min_dist = dist
                nearest = joint_name
        
        return nearest
    
    def _validate_transformation(self, result: TransformationResult):
        """Validate transformation result against strict rules."""
        master_ids = set(self.master_geometry.get_stroke_ids())
        output_ids = [s.identity.master_id for s in result.transformed_strokes]
        output_id_set = set(output_ids)
        
        # Check stroke count
        if result.output_stroke_count != result.master_stroke_count:
            result.add_error(
                f"Stroke count mismatch: master={result.master_stroke_count}, "
                f"output={result.output_stroke_count}"
            )
        
        # Check for missing strokes
        missing = master_ids - output_id_set
        if missing:
            result.missing_strokes = list(missing)
            result.add_error(f"Missing strokes: {missing}")
        
        # Check for new strokes (should never happen)
        new = output_id_set - master_ids
        if new:
            result.new_strokes = list(new)
            result.add_error(f"New strokes detected (FORBIDDEN): {new}")
        
        # Check for duplicate strokes
        if len(output_ids) != len(output_id_set):
            duplicates = [sid for sid in output_id_set if output_ids.count(sid) > 1]
            result.duplicate_strokes = duplicates
            result.add_error(f"Duplicate strokes detected: {duplicates}")
        
        # Check property preservation
        master_map = {s.identity.master_id: s for s in self.master_geometry.strokes}
        for transformed in result.transformed_strokes:
            master = master_map.get(transformed.identity.master_id)
            if not master:
                continue
            
            if transformed.brush_size != master.brush_size:
                result.thickness_changes += 1
                result.add_error(
                    f"Stroke {transformed.identity.master_id} thickness changed: "
                    f"{master.brush_size} -> {transformed.brush_size}"
                )
            
            if transformed.color != master.color:
                result.color_changes += 1
                result.add_error(
                    f"Stroke {transformed.identity.master_id} color changed: "
                    f"{master.color} -> {transformed.color}"
                )


def create_master_geometry_from_strokes(
    character: CharacterModel,
    stroke_data: List[Dict]
) -> MasterGeometry:
    """Create MasterGeometry from stroke data.
    
    Args:
        character: CharacterModel in neutral pose
        stroke_data: List of stroke dicts with points, color, brush_size, etc.
    
    Returns:
        MasterGeometry instance
    """
    master_strokes = []
    
    for i, stroke_dict in enumerate(stroke_data):
        # Extract stroke ID or generate one
        stroke_id = stroke_dict.get("stroke_id", f"stroke_{i}")
        
        # Extract points
        points_raw = stroke_dict.get("points", [])
        if isinstance(points_raw[0], list):
            points = [(float(p[0]), float(p[1])) for p in points_raw]
        else:
            # Flat list: [x1, y1, x2, y2, ...]
            points = [
                (float(points_raw[j]), float(points_raw[j+1]))
                for j in range(0, len(points_raw), 2)
            ]
        
        # Create identity
        identity = StrokeIdentity(
            master_id=stroke_id,
            body_part=stroke_dict.get("body_part")
        )
        
        # Create master stroke
        master_stroke = MasterStroke(
            identity=identity,
            points=points,
            color=stroke_dict.get("color", "#000000"),
            brush_size=stroke_dict.get("brush_size", 3),
            closed=stroke_dict.get("closed", False)
        )
        
        master_strokes.append(master_stroke)
    
    return MasterGeometry(
        character=character,
        strokes=master_strokes
    )
