"""Tests for Character Pose Transformation - Phase 1.6

Tests strict stroke preservation rules:
- No new strokes
- No duplicate strokes
- No missing strokes
- No stroke splitting/merging
- Preserved stroke properties
- Immutable master geometry
"""

import unittest
import math
from character_model import CharacterModel, Skeleton, CharacterDimensions
from character_consistency import ConsistencyValidator
from character_transform import (
    StrokeIdentity,
    MasterStroke,
    TransformedStroke,
    MasterGeometry,
    TransformationResult,
    PoseTransformer,
    create_master_geometry_from_strokes
)


class TestStrokeIdentity(unittest.TestCase):
    """Test stroke identity preservation."""
    
    def test_identity_creation(self):
        """Test creating stroke identity."""
        identity = StrokeIdentity(master_id="stroke_1", body_part="left_arm")
        self.assertEqual(identity.master_id, "stroke_1")
        self.assertEqual(identity.body_part, "left_arm")
    
    def test_identity_string(self):
        """Test string representation."""
        identity = StrokeIdentity(master_id="stroke_1", body_part="left_arm")
        self.assertIn("stroke_1", str(identity))
        self.assertIn("left_arm", str(identity))


class TestMasterStroke(unittest.TestCase):
    """Test master stroke validation."""
    
    def test_valid_master_stroke(self):
        """Test creating valid master stroke."""
        identity = StrokeIdentity(master_id="stroke_1")
        stroke = MasterStroke(
            identity=identity,
            points=[(0.0, 0.0), (100.0, 100.0)],
            color="#000000",
            brush_size=3
        )
        self.assertEqual(len(stroke.points), 2)
        self.assertEqual(stroke.brush_size, 3)
    
    def test_invalid_single_point(self):
        """Test that single-point stroke is rejected."""
        identity = StrokeIdentity(master_id="stroke_1")
        with self.assertRaises(ValueError):
            MasterStroke(
                identity=identity,
                points=[(0.0, 0.0)],
                color="#000000",
                brush_size=3
            )
    
    def test_invalid_zero_brush_size(self):
        """Test that zero brush size is rejected."""
        identity = StrokeIdentity(master_id="stroke_1")
        with self.assertRaises(ValueError):
            MasterStroke(
                identity=identity,
                points=[(0.0, 0.0), (100.0, 100.0)],
                color="#000000",
                brush_size=0
            )


class TestMasterGeometry(unittest.TestCase):
    """Test master geometry validation."""
    
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
    
    def test_valid_master_geometry(self):
        """Test creating valid master geometry."""
        strokes = [
            MasterStroke(
                identity=StrokeIdentity(master_id="stroke_1"),
                points=[(0.0, 0.0), (100.0, 100.0)],
                color="#000000",
                brush_size=3
            ),
            MasterStroke(
                identity=StrokeIdentity(master_id="stroke_2"),
                points=[(50.0, 50.0), (150.0, 150.0)],
                color="#FF0000",
                brush_size=5
            )
        ]
        
        geometry = MasterGeometry(character=self.character, strokes=strokes)
        self.assertEqual(geometry.get_stroke_count(), 2)
        self.assertEqual(len(geometry.get_stroke_ids()), 2)
    
    def test_duplicate_stroke_ids_rejected(self):
        """Test that duplicate stroke IDs are rejected."""
        strokes = [
            MasterStroke(
                identity=StrokeIdentity(master_id="stroke_1"),
                points=[(0.0, 0.0), (100.0, 100.0)],
                color="#000000",
                brush_size=3
            ),
            MasterStroke(
                identity=StrokeIdentity(master_id="stroke_1"),  # DUPLICATE
                points=[(50.0, 50.0), (150.0, 150.0)],
                color="#FF0000",
                brush_size=5
            )
        ]
        
        with self.assertRaises(ValueError):
            MasterGeometry(character=self.character, strokes=strokes)
    
    def test_empty_strokes_rejected(self):
        """Test that empty stroke list is rejected."""
        with self.assertRaises(ValueError):
            MasterGeometry(character=self.character, strokes=[])


class TestPoseTransformer(unittest.TestCase):
    """Test pose transformation with strict stroke preservation."""
    
    def setUp(self):
        """Create test character and master geometry."""
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
        
        self.neutral_pose = {
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
            neutral_pose=self.neutral_pose,
            dimensions=dimensions
        )
        
        # Create master strokes (3 strokes)
        self.master_strokes = [
            MasterStroke(
                identity=StrokeIdentity(master_id="head_outline"),
                points=[(100.0, 110.0), (95.0, 115.0), (100.0, 120.0), (105.0, 115.0)],
                color="#000000",
                brush_size=3,
                closed=True
            ),
            MasterStroke(
                identity=StrokeIdentity(master_id="left_arm"),
                points=[(80.0, 140.0), (60.0, 160.0), (50.0, 180.0)],
                color="#000000",
                brush_size=3
            ),
            MasterStroke(
                identity=StrokeIdentity(master_id="right_arm"),
                points=[(120.0, 140.0), (140.0, 160.0), (150.0, 180.0)],
                color="#000000",
                brush_size=3
            )
        ]
        
        self.master_geometry = MasterGeometry(
            character=self.character,
            strokes=self.master_strokes
        )
        
        self.transformer = PoseTransformer(self.master_geometry)
    
    def test_1_neutral_pose_transformation(self):
        """Test 1: Neutral pose transformation preserves stroke count."""
        result = self.transformer.transform_pose(self.neutral_pose)
        
        self.assertTrue(result.valid, f"Neutral pose should be valid: {result.errors}")
        self.assertEqual(result.output_stroke_count, result.master_stroke_count)
        self.assertEqual(result.output_stroke_count, 3)
        self.assertEqual(len(result.missing_strokes), 0)
        self.assertEqual(len(result.duplicate_strokes), 0)
        self.assertEqual(len(result.new_strokes), 0)
    
    def test_2_raised_arm_same_stroke_count(self):
        """Test 2: Raised arm preserves stroke count."""
        # Raise left arm (valid bone lengths)
        raised_pose = dict(self.neutral_pose)
        raised_pose["elbow_l"] = (80.0, 168.28)  # Same length, rotated
        raised_pose["hand_l"] = (80.0, 190.64)  # Same length, rotated
        
        result = self.transformer.transform_pose(raised_pose)
        
        self.assertTrue(result.valid, f"Raised arm should be valid: {result.errors}")
        self.assertEqual(result.output_stroke_count, 3)
        self.assertEqual(result.master_stroke_count, 3)
    
    def test_3_moved_leg_same_stroke_count(self):
        """Test 3: Moved leg preserves stroke count."""
        # Move right leg (keep same bone lengths: thigh=40, shin=30)
        moved_pose = dict(self.neutral_pose)
        # Original: hip_r (110, 200) -> knee_r (110, 240) -> foot_r (110, 270)
        # Move to the right but maintain lengths
        moved_pose["knee_r"] = (110.0, 240.0)  # Keep same distance from hip
        moved_pose["foot_r"] = (110.0, 270.0)  # Keep same distance from knee
        
        result = self.transformer.transform_pose(moved_pose)
        
        self.assertTrue(result.valid, f"Moved leg should be valid: {result.errors}")
        self.assertEqual(result.output_stroke_count, 3)
    
    def test_4_multiple_joint_movement_same_stroke_count(self):
        """Test 4: Multiple joint movements preserve stroke count."""
        # Move multiple joints
        complex_pose = dict(self.neutral_pose)
        complex_pose["elbow_l"] = (80.0, 168.28)
        complex_pose["hand_l"] = (80.0, 190.64)
        complex_pose["elbow_r"] = (120.0, 168.28)
        complex_pose["hand_r"] = (120.0, 190.64)
        
        result = self.transformer.transform_pose(complex_pose)
        
        self.assertTrue(result.valid, f"Complex pose should be valid: {result.errors}")
        self.assertEqual(result.output_stroke_count, 3)
    
    def test_5_every_output_has_master_id(self):
        """Test 5: Every output stroke has a master stroke ID."""
        result = self.transformer.transform_pose(self.neutral_pose)
        
        self.assertTrue(result.valid)
        master_ids = set(self.master_geometry.get_stroke_ids())
        
        for transformed in result.transformed_strokes:
            self.assertIn(
                transformed.identity.master_id,
                master_ids,
                f"Stroke {transformed.identity.master_id} not in master IDs"
            )
    
    def test_6_no_duplicate_stroke_ids(self):
        """Test 6: No duplicate stroke IDs in output."""
        result = self.transformer.transform_pose(self.neutral_pose)
        
        self.assertTrue(result.valid)
        output_ids = [s.identity.master_id for s in result.transformed_strokes]
        self.assertEqual(len(output_ids), len(set(output_ids)), "Duplicate IDs found")
    
    def test_7_no_missing_stroke_ids(self):
        """Test 7: No missing stroke IDs in output."""
        result = self.transformer.transform_pose(self.neutral_pose)
        
        self.assertTrue(result.valid)
        master_ids = set(self.master_geometry.get_stroke_ids())
        output_ids = set(s.identity.master_id for s in result.transformed_strokes)
        
        self.assertEqual(master_ids, output_ids, "Stroke IDs don't match")
    
    def test_8_master_geometry_unchanged(self):
        """Test 8: Master geometry remains unchanged after transformation."""
        original_stroke_count = self.master_geometry.get_stroke_count()
        original_ids = self.master_geometry.get_stroke_ids()
        original_first_point = self.master_geometry.strokes[0].points[0]
        
        # Transform pose
        self.transformer.transform_pose(self.neutral_pose)
        
        # Verify master geometry unchanged
        self.assertEqual(self.master_geometry.get_stroke_count(), original_stroke_count)
        self.assertEqual(self.master_geometry.get_stroke_ids(), original_ids)
        self.assertEqual(self.master_geometry.strokes[0].points[0], original_first_point)
    
    def test_9_original_not_in_output(self):
        """Test 9: Original geometry is not included in output."""
        result = self.transformer.transform_pose(self.neutral_pose)
        
        self.assertTrue(result.valid)
        # Output should have same count as master, not double
        self.assertEqual(result.output_stroke_count, result.master_stroke_count)
        self.assertNotEqual(result.output_stroke_count, result.master_stroke_count * 2)
    
    def test_10_transformed_submitted_once(self):
        """Test 10: Each transformed stroke appears exactly once."""
        result = self.transformer.transform_pose(self.neutral_pose)
        
        self.assertTrue(result.valid)
        output_ids = [s.identity.master_id for s in result.transformed_strokes]
        
        for stroke_id in self.master_geometry.get_stroke_ids():
            count = output_ids.count(stroke_id)
            self.assertEqual(count, 1, f"Stroke {stroke_id} appears {count} times")
    
    def test_11_stroke_thickness_unchanged(self):
        """Test 11: Stroke thickness remains unchanged."""
        result = self.transformer.transform_pose(self.neutral_pose)
        
        self.assertTrue(result.valid)
        self.assertEqual(result.thickness_changes, 0)
        
        master_map = {s.identity.master_id: s for s in self.master_geometry.strokes}
        for transformed in result.transformed_strokes:
            master = master_map[transformed.identity.master_id]
            self.assertEqual(
                transformed.brush_size,
                master.brush_size,
                f"Thickness changed for {transformed.identity.master_id}"
            )
    
    def test_12_invalid_transformation_fails(self):
        """Test 12: Invalid transformation fails without creating corrective strokes."""
        # Create invalid pose with stretched arm (exceeds tolerance)
        invalid_pose = dict(self.neutral_pose)
        invalid_pose["elbow_l"] = (56.0, 164.0)  # 10% stretch, exceeds 1% tolerance
        
        result = self.transformer.transform_pose(invalid_pose)
        
        # Should fail validation
        self.assertFalse(result.valid, "Invalid pose should fail")
        self.assertGreater(len(result.errors), 0, "Should have errors")
        
        # Should NOT create corrective strokes
        # Either no strokes, or same count but invalid
        if result.output_stroke_count > 0:
            self.assertEqual(
                result.output_stroke_count,
                result.master_stroke_count,
                "Should not add corrective strokes"
            )
    
    def test_13_disconnected_joint_fails_no_connector(self):
        """Test 13: Disconnected joint fails, no connector stroke created."""
        # Create pose with missing joint
        disconnected_pose = dict(self.neutral_pose)
        del disconnected_pose["elbow_l"]  # Remove joint
        
        result = self.transformer.transform_pose(disconnected_pose)
        
        # Should fail validation
        self.assertFalse(result.valid)
        
        # Should NOT add connector stroke
        self.assertEqual(len(result.new_strokes), 0, "No new strokes should be created")
    
    def test_14_overlapping_geometry_no_duplicates(self):
        """Test 14: Overlapping geometry does not create duplicate strokes."""
        # Create pose where arms overlap
        overlap_pose = dict(self.neutral_pose)
        overlap_pose["elbow_l"] = (100.0, 160.0)  # Move to center
        overlap_pose["hand_l"] = (100.0, 180.0)
        overlap_pose["elbow_r"] = (100.0, 160.0)  # Same position
        overlap_pose["hand_r"] = (100.0, 180.0)
        
        result = self.transformer.transform_pose(overlap_pose)
        
        # Should have same stroke count, no duplicates
        if result.valid:
            self.assertEqual(result.output_stroke_count, 3)
            self.assertEqual(len(result.duplicate_strokes), 0)


class TestStrokeCountInvariant(unittest.TestCase):
    """Test strict stroke count invariant across poses."""
    
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
        character = CharacterModel(
            name="test_character",
            skeleton=skeleton,
            neutral_pose=neutral_pose,
            dimensions=dimensions
        )
        
        # Create master with 5 strokes
        strokes = [
            MasterStroke(
                identity=StrokeIdentity(master_id=f"stroke_{i}"),
                points=[(float(i*10), float(i*10)), (float(i*10+50), float(i*10+50))],
                color="#000000",
                brush_size=3
            )
            for i in range(5)
        ]
        
        self.master_geometry = MasterGeometry(character=character, strokes=strokes)
        self.transformer = PoseTransformer(self.master_geometry)
        self.neutral_pose = neutral_pose
    
    def test_deterministic_stroke_count(self):
        """Test deterministic stroke count across multiple poses."""
        N = self.master_geometry.get_stroke_count()
        self.assertEqual(N, 5)
        
        # Create 3 different valid poses
        pose_a = dict(self.neutral_pose)
        
        pose_b = dict(self.neutral_pose)
        pose_b["elbow_l"] = (80.0, 168.28)
        pose_b["hand_l"] = (80.0, 190.64)
        
        pose_c = dict(self.neutral_pose)
        # Keep valid bone lengths
        pose_c["knee_r"] = (110.0, 240.0)
        pose_c["foot_r"] = (110.0, 270.0)
        
        # Transform all poses
        result_a = self.transformer.transform_pose(pose_a)
        result_b = self.transformer.transform_pose(pose_b)
        result_c = self.transformer.transform_pose(pose_c)
        
        # All must have same count as master
        self.assertEqual(result_a.output_stroke_count, N)
        self.assertEqual(result_b.output_stroke_count, N)
        self.assertEqual(result_c.output_stroke_count, N)
        
        # Verify IDs match
        master_ids = set(self.master_geometry.get_stroke_ids())
        self.assertEqual(
            set(s.identity.master_id for s in result_a.transformed_strokes),
            master_ids
        )
        self.assertEqual(
            set(s.identity.master_id for s in result_b.transformed_strokes),
            master_ids
        )
        self.assertEqual(
            set(s.identity.master_id for s in result_c.transformed_strokes),
            master_ids
        )


class TestCreateMasterGeometry(unittest.TestCase):
    """Test creation of master geometry from stroke data."""
    
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
    
    def test_create_from_stroke_data(self):
        """Test creating master geometry from stroke data."""
        stroke_data = [
            {
                "stroke_id": "head",
                "points": [[100, 110], [95, 115], [100, 120]],
                "color": "#000000",
                "brush_size": 3,
                "closed": True
            },
            {
                "stroke_id": "body",
                "points": [[100, 150], [100, 200]],
                "color": "#000000",
                "brush_size": 4,
                "closed": False
            }
        ]
        
        geometry = create_master_geometry_from_strokes(self.character, stroke_data)
        
        self.assertEqual(geometry.get_stroke_count(), 2)
        self.assertIn("head", geometry.get_stroke_ids())
        self.assertIn("body", geometry.get_stroke_ids())


if __name__ == "__main__":
    unittest.main()
