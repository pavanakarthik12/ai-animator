"""Tests for Animation Timeline and Planning - Phase 2

Tests generic timeline and key pose planning.
NO DRAWING. NO GROQ. NO KRITA. NO MCP.
"""

import unittest
from animation_timeline import (
    AnimationRequest,
    TimelineSegment,
    KeyPose,
    Timeline,
    AnimationPlan,
    TimelineAllocator,
    TimelineValidator,
    create_simple_plan,
    create_compound_plan
)


class TestAnimationRequest(unittest.TestCase):
    """Test animation request validation."""
    
    def test_valid_request(self):
        """Test creating valid animation request."""
        request = AnimationRequest(
            action="walk",
            frame_count=240,
            loop=True
        )
        self.assertEqual(request.action, "walk")
        self.assertEqual(request.frame_count, 240)
        self.assertTrue(request.loop)
    
    def test_minimal_request(self):
        """Test minimal request with defaults."""
        request = AnimationRequest(action="wave", frame_count=40)
        self.assertEqual(request.action, "wave")
        self.assertEqual(request.frame_count, 40)
        self.assertTrue(request.loop)  # Default
    
    def test_invalid_frame_count(self):
        """Test that zero/negative frame count is rejected."""
        with self.assertRaises(ValueError):
            AnimationRequest(action="walk", frame_count=0)
        
        with self.assertRaises(ValueError):
            AnimationRequest(action="walk", frame_count=-10)
    
    def test_empty_action(self):
        """Test that empty action is rejected."""
        with self.assertRaises(ValueError):
            AnimationRequest(action="", frame_count=20)


class TestTimelineSegment(unittest.TestCase):
    """Test timeline segment validation."""
    
    def test_valid_segment(self):
        """Test creating valid segment."""
        segment = TimelineSegment(
            name="walk_cycle",
            action="walk",
            start_frame=1,
            end_frame=120
        )
        self.assertEqual(segment.name, "walk_cycle")
        self.assertEqual(segment.duration(), 120)
    
    def test_single_frame_segment(self):
        """Test segment with single frame."""
        segment = TimelineSegment(
            name="hold",
            action="hold",
            start_frame=50,
            end_frame=50
        )
        self.assertEqual(segment.duration(), 1)
    
    def test_invalid_start_frame(self):
        """Test that start_frame < 1 is rejected."""
        with self.assertRaises(ValueError):
            TimelineSegment(
                name="test",
                action="test",
                start_frame=0,
                end_frame=10
            )
    
    def test_invalid_end_before_start(self):
        """Test that end_frame < start_frame is rejected."""
        with self.assertRaises(ValueError):
            TimelineSegment(
                name="test",
                action="test",
                start_frame=50,
                end_frame=40
            )
    
    def test_contains_frame(self):
        """Test frame containment check."""
        segment = TimelineSegment(
            name="test",
            action="test",
            start_frame=10,
            end_frame=20
        )
        self.assertTrue(segment.contains_frame(10))
        self.assertTrue(segment.contains_frame(15))
        self.assertTrue(segment.contains_frame(20))
        self.assertFalse(segment.contains_frame(9))
        self.assertFalse(segment.contains_frame(21))


class TestKeyPose(unittest.TestCase):
    """Test key pose validation."""
    
    def test_valid_key_pose(self):
        """Test creating valid key pose."""
        pose = {"root": (100.0, 200.0), "torso": (100.0, 150.0)}
        kp = KeyPose(
            frame=20,
            pose=pose,
            label="contact"
        )
        self.assertEqual(kp.frame, 20)
        self.assertEqual(kp.label, "contact")
    
    def test_invalid_frame(self):
        """Test that frame < 1 is rejected."""
        pose = {"root": (100.0, 200.0)}
        with self.assertRaises(ValueError):
            KeyPose(frame=0, pose=pose, label="test")
    
    def test_empty_pose(self):
        """Test that empty pose is rejected."""
        with self.assertRaises(ValueError):
            KeyPose(frame=10, pose={}, label="test")
    
    def test_empty_label(self):
        """Test that empty label is rejected."""
        pose = {"root": (100.0, 200.0)}
        with self.assertRaises(ValueError):
            KeyPose(frame=10, pose=pose, label="")


class TestTimeline(unittest.TestCase):
    """Test timeline validation."""
    
    def test_valid_timeline(self):
        """Test creating valid timeline."""
        timeline = Timeline(total_frames=240)
        self.assertEqual(timeline.total_frames, 240)
        self.assertEqual(len(timeline.segments), 0)
    
    def test_add_segment(self):
        """Test adding valid segment."""
        timeline = Timeline(total_frames=100)
        segment = TimelineSegment(
            name="walk",
            action="walk",
            start_frame=1,
            end_frame=100
        )
        timeline.add_segment(segment)
        self.assertEqual(len(timeline.segments), 1)
    
    def test_segment_exceeds_bounds(self):
        """Test that segment exceeding timeline is rejected."""
        timeline = Timeline(total_frames=100)
        segment = TimelineSegment(
            name="walk",
            action="walk",
            start_frame=1,
            end_frame=150  # Exceeds timeline
        )
        with self.assertRaises(ValueError):
            timeline.add_segment(segment)
    
    def test_get_segment_at_frame(self):
        """Test finding segment at specific frame."""
        timeline = Timeline(total_frames=100)
        
        seg1 = TimelineSegment(name="a", action="a", start_frame=1, end_frame=50)
        seg2 = TimelineSegment(name="b", action="b", start_frame=51, end_frame=100)
        
        timeline.add_segment(seg1)
        timeline.add_segment(seg2)
        
        self.assertEqual(timeline.get_segment_at_frame(25), seg1)
        self.assertEqual(timeline.get_segment_at_frame(75), seg2)
        self.assertIsNone(timeline.get_segment_at_frame(200))


class TestTimelineAllocator(unittest.TestCase):
    """Test timeline allocation."""
    
    def test_1_20_frame_request(self):
        """TEST 1: 20-frame request produces valid timeline."""
        request = AnimationRequest(action="walk", frame_count=20)
        allocator = TimelineAllocator()
        timeline = allocator.allocate_simple(request)
        
        self.assertEqual(timeline.total_frames, 20)
        self.assertEqual(len(timeline.segments), 1)
        self.assertEqual(timeline.segments[0].start_frame, 1)
        self.assertEqual(timeline.segments[0].end_frame, 20)
    
    def test_2_100_frame_request(self):
        """TEST 2: 100-frame request produces valid timeline."""
        request = AnimationRequest(action="run", frame_count=100)
        allocator = TimelineAllocator()
        timeline = allocator.allocate_simple(request)
        
        self.assertEqual(timeline.total_frames, 100)
        self.assertEqual(timeline.segments[0].start_frame, 1)
        self.assertEqual(timeline.segments[0].end_frame, 100)
    
    def test_3_240_frame_request(self):
        """TEST 3: 240-frame request produces valid timeline."""
        request = AnimationRequest(action="walk", frame_count=240)
        allocator = TimelineAllocator()
        timeline = allocator.allocate_simple(request)
        
        self.assertEqual(timeline.total_frames, 240)
        self.assertEqual(timeline.segments[0].start_frame, 1)
        self.assertEqual(timeline.segments[0].end_frame, 240)
    
    def test_4_250_frame_request(self):
        """TEST 4: 250-frame request produces valid timeline."""
        request = AnimationRequest(action="wave", frame_count=250)
        allocator = TimelineAllocator()
        timeline = allocator.allocate_simple(request)
        
        self.assertEqual(timeline.total_frames, 250)
        self.assertEqual(timeline.segments[0].start_frame, 1)
        self.assertEqual(timeline.segments[0].end_frame, 250)
    
    def test_compound_allocation(self):
        """Test compound action allocation."""
        request = AnimationRequest(action="compound", frame_count=120)
        allocator = TimelineAllocator()
        
        phases = [("walk", 0.5), ("stop", 0.2), ("wave", 0.3)]
        timeline = allocator.allocate_compound(request, phases)
        
        self.assertEqual(timeline.total_frames, 120)
        self.assertEqual(len(timeline.segments), 3)
        
        # Verify all frames covered
        self.assertEqual(timeline.segments[0].start_frame, 1)
        self.assertEqual(timeline.segments[-1].end_frame, 120)
    
    def test_uniform_allocation(self):
        """Test uniform distribution across actions."""
        request = AnimationRequest(action="compound", frame_count=90)
        allocator = TimelineAllocator()
        
        actions = ["walk", "stop", "wave"]
        timeline = allocator.allocate_uniform(request, actions)
        
        self.assertEqual(timeline.total_frames, 90)
        self.assertEqual(len(timeline.segments), 3)


class TestTimelineValidator(unittest.TestCase):
    """Test timeline validation."""
    
    def test_5_complete_coverage(self):
        """TEST 5: Multiple segments covering complete timeline."""
        timeline = Timeline(total_frames=100)
        
        timeline.add_segment(TimelineSegment("a", "a", 1, 50))
        timeline.add_segment(TimelineSegment("b", "b", 51, 100))
        
        validator = TimelineValidator()
        is_valid, errors = validator.validate_plan(
            AnimationPlan(
                request=AnimationRequest(action="test", frame_count=100),
                timeline=timeline
            )
        )
        
        self.assertTrue(is_valid, f"Should be valid: {errors}")
        self.assertEqual(len(errors), 0)
    
    def test_6_gap_detection(self):
        """TEST 6: Segments with gap are detected."""
        timeline = Timeline(total_frames=100)
        
        timeline.add_segment(TimelineSegment("a", "a", 1, 40))
        timeline.add_segment(TimelineSegment("b", "b", 45, 100))  # Gap 41-44
        
        validator = TimelineValidator()
        is_valid, errors = validator.validate_plan(
            AnimationPlan(
                request=AnimationRequest(action="test", frame_count=100),
                timeline=timeline
            )
        )
        
        self.assertFalse(is_valid, "Should detect gap")
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("Gap" in err or "gap" in err for err in errors))
    
    def test_7_overlap_detection(self):
        """TEST 7: Overlapping segments are detected."""
        timeline = Timeline(total_frames=100)
        
        timeline.add_segment(TimelineSegment("a", "a", 1, 50))
        timeline.add_segment(TimelineSegment("b", "b", 40, 100))  # Overlap 40-50
        
        validator = TimelineValidator()
        is_valid, errors = validator.validate_plan(
            AnimationPlan(
                request=AnimationRequest(action="test", frame_count=100),
                timeline=timeline
            )
        )
        
        self.assertFalse(is_valid, "Should detect overlap")
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("overlap" in err.lower() for err in errors))
    
    def test_8_segment_outside_budget(self):
        """TEST 8: Segment exceeding frame budget is detected."""
        timeline = Timeline(total_frames=100)
        
        # Segment goes beyond timeline
        # Note: add_segment already validates this, but validator should catch it too
        timeline.segments.append(
            TimelineSegment("a", "a", 1, 150)  # Exceeds 100
        )
        
        validator = TimelineValidator()
        is_valid, errors = validator.validate_plan(
            AnimationPlan(
                request=AnimationRequest(action="test", frame_count=100),
                timeline=timeline
            )
        )
        
        self.assertFalse(is_valid, "Should detect out of bounds segment")
        self.assertGreater(len(errors), 0)
    
    def test_9_valid_key_pose(self):
        """TEST 9: Key pose inside timeline is valid."""
        request = AnimationRequest(action="test", frame_count=100)
        timeline = Timeline(total_frames=100)
        timeline.add_segment(TimelineSegment("a", "a", 1, 100))
        
        plan = AnimationPlan(request=request, timeline=timeline)
        
        pose = {"root": (100.0, 200.0)}
        kp = KeyPose(frame=50, pose=pose, label="mid")
        plan.add_key_pose(kp)
        
        validator = TimelineValidator()
        is_valid, errors = validator.validate_plan(plan)
        
        self.assertTrue(is_valid, f"Should be valid: {errors}")
    
    def test_10_key_pose_outside_timeline(self):
        """TEST 10: Key pose outside timeline is detected."""
        request = AnimationRequest(action="test", frame_count=100)
        timeline = Timeline(total_frames=100)
        timeline.add_segment(TimelineSegment("a", "a", 1, 100))
        
        plan = AnimationPlan(request=request, timeline=timeline)
        
        pose = {"root": (100.0, 200.0)}
        kp = KeyPose(frame=150, pose=pose, label="invalid")
        
        # add_key_pose validates immediately
        with self.assertRaises(ValueError):
            plan.add_key_pose(kp)
    
    def test_11_duplicate_key_pose_frame(self):
        """TEST 11: Duplicate key pose at same frame is detected."""
        request = AnimationRequest(action="test", frame_count=100)
        timeline = Timeline(total_frames=100)
        timeline.add_segment(TimelineSegment("a", "a", 1, 100))
        
        plan = AnimationPlan(request=request, timeline=timeline)
        
        pose = {"root": (100.0, 200.0)}
        plan.add_key_pose(KeyPose(frame=50, pose=pose, label="a"))
        plan.add_key_pose(KeyPose(frame=50, pose=pose, label="b"))  # Duplicate frame
        
        validator = TimelineValidator()
        is_valid, errors = validator.validate_plan(plan)
        
        self.assertFalse(is_valid, "Should detect duplicate frame")
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("frame 50" in err for err in errors))
    
    def test_12_compound_action_plan(self):
        """TEST 12: Compound action (walk → stop → wave) plan is valid."""
        request = AnimationRequest(action="compound", frame_count=150)
        allocator = TimelineAllocator()
        
        phases = [("walk", 0.6), ("stop", 0.1), ("wave", 0.3)]
        timeline = allocator.allocate_compound(request, phases)
        
        plan = AnimationPlan(request=request, timeline=timeline)
        
        validator = TimelineValidator()
        is_valid, errors = validator.validate_plan(plan)
        
        self.assertTrue(is_valid, f"Should be valid: {errors}")
        self.assertEqual(len(timeline.segments), 3)
        
        # Verify actions
        actions = [seg.action for seg in timeline.segments]
        self.assertIn("walk", actions)
        self.assertIn("stop", actions)
        self.assertIn("wave", actions)
    
    def test_13_deterministic_behavior(self):
        """TEST 13: Same input produces identical output."""
        request1 = AnimationRequest(action="walk", frame_count=120)
        request2 = AnimationRequest(action="walk", frame_count=120)
        
        allocator = TimelineAllocator()
        timeline1 = allocator.allocate_simple(request1)
        timeline2 = allocator.allocate_simple(request2)
        
        # Verify identical results
        self.assertEqual(timeline1.total_frames, timeline2.total_frames)
        self.assertEqual(len(timeline1.segments), len(timeline2.segments))
        
        for seg1, seg2 in zip(timeline1.segments, timeline2.segments):
            self.assertEqual(seg1.start_frame, seg2.start_frame)
            self.assertEqual(seg1.end_frame, seg2.end_frame)
            self.assertEqual(seg1.action, seg2.action)


class TestConvenienceFunctions(unittest.TestCase):
    """Test convenience functions."""
    
    def test_create_simple_plan(self):
        """Test creating simple plan."""
        request = AnimationRequest(action="walk", frame_count=60)
        plan = create_simple_plan(request)
        
        self.assertIsNotNone(plan)
        self.assertTrue(plan.validated)
        self.assertEqual(len(plan.validation_errors), 0)
        self.assertEqual(plan.timeline.total_frames, 60)
    
    def test_create_compound_plan(self):
        """Test creating compound plan."""
        request = AnimationRequest(action="compound", frame_count=180)
        phases = [("walk", 0.5), ("wave", 0.5)]
        plan = create_compound_plan(request, phases)
        
        self.assertIsNotNone(plan)
        self.assertTrue(plan.validated)
        self.assertEqual(len(plan.validation_errors), 0)
        self.assertEqual(len(plan.timeline.segments), 2)


class Test240FrameTimeline(unittest.TestCase):
    """Test 240-frame timeline specifically."""
    
    def test_240_frame_deterministic_plan(self):
        """IMPORTANT: 240-frame walk produces valid deterministic plan."""
        request = AnimationRequest(action="walk", frame_count=240)
        plan = create_simple_plan(request)
        
        # Verify plan is valid
        self.assertTrue(plan.validated, f"Plan invalid: {plan.validation_errors}")
        self.assertEqual(len(plan.validation_errors), 0)
        
        # Verify timeline bounds
        self.assertEqual(plan.timeline.total_frames, 240)
        self.assertEqual(plan.timeline.segments[0].start_frame, 1)
        self.assertEqual(plan.timeline.segments[0].end_frame, 240)
        
        # Verify no gaps or overlaps
        validator = TimelineValidator()
        is_valid, errors = validator.validate_plan(plan)
        self.assertTrue(is_valid, f"Validation errors: {errors}")


class TestAnimationPlan(unittest.TestCase):
    """Test animation plan features."""
    
    def test_key_pose_sorting(self):
        """Test key poses are sorted by frame."""
        request = AnimationRequest(action="test", frame_count=100)
        timeline = Timeline(total_frames=100)
        timeline.add_segment(TimelineSegment("a", "a", 1, 100))
        
        plan = AnimationPlan(request=request, timeline=timeline)
        
        pose = {"root": (100.0, 200.0)}
        plan.add_key_pose(KeyPose(frame=80, pose=pose, label="c"))
        plan.add_key_pose(KeyPose(frame=20, pose=pose, label="a"))
        plan.add_key_pose(KeyPose(frame=50, pose=pose, label="b"))
        
        sorted_kps = plan.get_key_poses_sorted()
        self.assertEqual(sorted_kps[0].frame, 20)
        self.assertEqual(sorted_kps[1].frame, 50)
        self.assertEqual(sorted_kps[2].frame, 80)
    
    def test_get_key_pose_at_frame(self):
        """Test finding key pose at specific frame."""
        request = AnimationRequest(action="test", frame_count=100)
        timeline = Timeline(total_frames=100)
        timeline.add_segment(TimelineSegment("a", "a", 1, 100))
        
        plan = AnimationPlan(request=request, timeline=timeline)
        
        pose = {"root": (100.0, 200.0)}
        plan.add_key_pose(KeyPose(frame=50, pose=pose, label="mid"))
        
        kp = plan.get_key_pose_at_frame(50)
        self.assertIsNotNone(kp)
        self.assertEqual(kp.label, "mid")
        
        kp_none = plan.get_key_pose_at_frame(75)
        self.assertIsNone(kp_none)


if __name__ == "__main__":
    unittest.main()
