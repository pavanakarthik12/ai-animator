import math
import numpy as np
from typing import Dict, List, Tuple, Any

# Standard 2D hierarchy
BONE_HIERARCHY = {
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
    "foot_r": "knee_r"
}

class CharacterRig:
    def __init__(self, rest_joints: Dict[str, Tuple[float, float]]):
        self.rest_joints = rest_joints
        self.hierarchy = BONE_HIERARCHY
        
        # Calculate rest lengths and rest angles (relative to parent)
        self.rest_lengths = {}
        self.rest_angles = {}
        self.local_angles = {} # The animated rotation relative to rest angle
        
        for joint, parent in self.hierarchy.items():
            self.local_angles[joint] = 0.0
            if parent and joint in self.rest_joints and parent in self.rest_joints:
                px, py = self.rest_joints[parent]
                jx, jy = self.rest_joints[joint]
                dx, dy = jx - px, jy - py
                self.rest_lengths[joint] = math.hypot(dx, dy)
                self.rest_angles[joint] = math.atan2(dy, dx)
            else:
                self.rest_lengths[joint] = 0.0
                self.rest_angles[joint] = 0.0

    def set_pose(self, angles: Dict[str, float]):
        """Set local rotation angles (in radians) for each joint."""
        for joint, angle in angles.items():
            if joint in self.local_angles:
                self.local_angles[joint] = angle
        # Root translation
        if "root_y" in angles:
            self.local_angles["root_y"] = angles["root_y"]
        if "root_x" in angles:
            self.local_angles["root_x"] = angles["root_x"]

    def get_global_transforms(self) -> Dict[str, Tuple[float, float, float]]:
        """Calculate global position (x, y) and absolute angle for each joint."""
        globals = {}
        processed = set()
        
        def compute_global(joint):
            if joint in processed:
                return globals[joint]
            
            parent = self.hierarchy[joint]
            if not parent:
                # Root is absolute
                rx, ry = self.rest_joints.get(joint, (0,0))
                globals[joint] = (
                    rx + self.local_angles.get("root_x", 0.0), 
                    ry + self.local_angles.get("root_y", 0.0), 
                    self.local_angles.get(joint, 0.0)
                )
            else:
                px, py, p_angle = compute_global(parent)
                total_rotation = p_angle + self.local_angles.get(joint, 0.0)
                # The position of THIS joint depends on the parent's total rotation,
                # NOT this joint's local rotation.
                bone_dir = self.rest_angles[joint] + p_angle
                
                length = self.rest_lengths[joint]
                x = px + length * math.cos(bone_dir)
                y = py + length * math.sin(bone_dir)
                
                globals[joint] = (x, y, total_rotation)
                
            processed.add(joint)
            return globals[joint]
            
        for joint in self.hierarchy:
            if joint in self.rest_joints:
                compute_global(joint)
                
        return globals

class LinearBlendSkinning:
    def __init__(self, rig: CharacterRig, strokes: List[Dict]):
        self.rig = rig
        self.strokes = strokes
        self.weights = []
        self._bind()
        
    def _bind(self):
        bones = []
        for j, p in self.rig.hierarchy.items():
            if p and j in self.rig.rest_joints and p in self.rig.rest_joints:
                bones.append({
                    "name": j,
                    "p1": np.array(self.rig.rest_joints[p]),
                    "p2": np.array(self.rig.rest_joints[j])
                })
        
        for stroke in self.strokes:
            stroke_weights = []
            points = stroke.get("points", [])
            for pt in points:
                pt_arr = np.array(pt)
                min_dist = float('inf')
                best_bone = "root"
                
                for b in bones:
                    p1 = b["p1"]
                    p2 = b["p2"]
                    l2 = np.sum((p1 - p2)**2)
                    if l2 == 0:
                        dist = np.linalg.norm(pt_arr - p1)
                    else:
                        t = max(0, min(1, np.dot(pt_arr - p1, p2 - p1) / l2))
                        projection = p1 + t * (p2 - p1)
                        dist = np.linalg.norm(pt_arr - projection)
                        
                    if dist < min_dist:
                        min_dist = dist
                        best_bone = b["name"]
                        
                root_pos = np.array(self.rig.rest_joints.get("root", [0,0]))
                if np.linalg.norm(pt_arr - root_pos) < min_dist:
                    best_bone = "root"
                    
                stroke_weights.append(best_bone)
            self.weights.append(stroke_weights)
            
    def deform(self) -> List[Dict]:
        globals = self.rig.get_global_transforms()
        deformed_strokes = []
        for i, stroke in enumerate(self.strokes):
            new_stroke = stroke.copy()
            new_points = []
            for j, pt in enumerate(stroke.get("points", [])):
                bone_name = self.weights[i][j]
                
                pivot_name = self.rig.hierarchy.get(bone_name, "root")
                if pivot_name not in globals:
                    pivot_name = "root"
                
                pivot_rest = self.rig.rest_joints.get(pivot_name, (0,0))
                pivot_curr = globals.get(pivot_name, (0,0,0))
                
                dx = pt[0] - pivot_rest[0]
                dy = pt[1] - pivot_rest[1]
                
                angle = pivot_curr[2]
                cos_a = math.cos(angle)
                sin_a = math.sin(angle)
                
                nx = dx * cos_a - dy * sin_a + pivot_curr[0]
                ny = dx * sin_a + dy * cos_a + pivot_curr[1]
                
                new_points.append([int(round(nx)), int(round(ny))])
                
            new_stroke["points"] = new_points
            deformed_strokes.append(new_stroke)
            
        return deformed_strokes

class WalkConfig:
    STRIDE_LENGTH = 0.15      # Fraction of leg length (conservative for front-facing)
    STEP_HEIGHT = 0.10        # Fraction of leg length
    HIP_SHIFT_X = 0.02        # Small horizontal weight shift
    BODY_BOB_Y = 0.04         # Small vertical bob
    ARM_SWING = 0.2           # Conservative arm swing

def solve_2d_ik(root_pos, target_pos, l1, l2, flip_knee=False):
    dx = target_pos[0] - root_pos[0]
    dy = target_pos[1] - root_pos[1]
    dist = math.hypot(dx, dy)
    
    if dist > l1 + l2: dist = l1 + l2 - 0.001
    if dist < abs(l1 - l2): dist = abs(l1 - l2) + 0.001
        
    val = (l1*l1 + l2*l2 - dist*dist) / (2 * l1 * l2)
    val = max(-1.0, min(1.0, val))
    knee_inner_angle = math.acos(val)
    
    val2 = (l1*l1 + dist*dist - l2*l2) / (2 * l1 * dist)
    val2 = max(-1.0, min(1.0, val2))
    alpha = math.acos(val2)
    
    base_angle = math.atan2(dy, dx)
    
    if flip_knee:
        angle1 = base_angle + alpha
        angle2 = angle1 - math.pi + knee_inner_angle
    else:
        angle1 = base_angle - alpha
        angle2 = angle1 + math.pi - knee_inner_angle
        
    return angle1, angle2

class PoseInterpolator:
    @staticmethod
    def interpolate(keyframes: List[Dict[str, float]], num_frames: int = 20, rig: CharacterRig = None) -> List[Dict[str, float]]:
        if not rig:
            # Fallback to linear
            frames = []
            num_keys = len(keyframes)
            for i in range(num_frames):
                cycle_pos = (i / num_frames) * num_keys
                k1_idx = int(math.floor(cycle_pos)) % num_keys
                k2_idx = (k1_idx + 1) % num_keys
                t = cycle_pos - math.floor(cycle_pos)
                k1 = keyframes[k1_idx]
                k2 = keyframes[k2_idx]
                interp = {}
                all_joints = set(k1.keys()) | set(k2.keys())
                for joint in all_joints:
                    if joint == "name": continue
                    interp[joint] = float(k1.get(joint, 0.0)) + (float(k2.get(joint, 0.0)) - float(k1.get(joint, 0.0))) * t
                frames.append(interp)
            return frames

        # --- Procedural Walk Cycle using IK ---
        frames = []
        
        # 1. Analyze Rig Dimensions
        l_thigh = rig.rest_lengths.get("knee_l", 0)
        l_calf = rig.rest_lengths.get("foot_l", 0)
        r_thigh = rig.rest_lengths.get("knee_r", 0)
        r_calf = rig.rest_lengths.get("foot_r", 0)
        
        l_leg = l_thigh + l_calf
        r_leg = r_thigh + r_calf
        avg_leg = (l_leg + r_leg) / 2.0
        if avg_leg == 0: avg_leg = 1.0 # fallback
        
        stride = WalkConfig.STRIDE_LENGTH * avg_leg
        step_h = WalkConfig.STEP_HEIGHT * avg_leg
        bob_y = WalkConfig.BODY_BOB_Y * avg_leg
        
        # We need the global rest positions of hips and feet to know baseline
        # Assume root is (0,0) in local space, get_global_transforms uses local_angles=0
        rest_globals = rig.get_global_transforms()
        l_hip_pos = rest_globals.get("hip_l", (0,0,0))
        r_hip_pos = rest_globals.get("hip_r", (0,0,0))
        l_foot_pos = rest_globals.get("foot_l", (0,0,0))
        r_foot_pos = rest_globals.get("foot_r", (0,0,0))
        
        ground_y = max(l_foot_pos[1], r_foot_pos[1])
        
        print("\n============================================================")
        print("DEBUG MODE: WALK CYCLE FOOT TRAJECTORY TABLE")
        print("Frame | Left Foot | Right Foot | Left Knee | Right Knee | Hip | Phase")
        print("------------------------------------------------------------")
        
        for i in range(num_frames):
            phase = i / num_frames # 0.0 to 1.0
            
            # Root bobbing: Contact->Down(lowest)->Passing(mid)->Up(highest)->Contact
            # Let's map 0..0.5 to a curve:
            # 0.0: 0
            # 0.15: +bob_y (Down)
            # 0.25: 0 (Passing)
            # 0.35: -bob_y (Up)
            # 0.5: 0
            # This is roughly: bob_y * math.sin(phase * 4 * math.pi)
            root_y_shift = math.sin(phase * 4 * math.pi) * bob_y
            
            # Left foot (contact 0-0.5, swing 0.5-1.0)
            if phase < 0.5:
                l_foot_x = l_hip_pos[0] + stride * (0.5 - (phase / 0.5))
                l_foot_y = ground_y
                l_state = "contact"
            else:
                swing_p = (phase - 0.5) / 0.5
                l_foot_x = l_hip_pos[0] - stride + (stride * 2) * swing_p
                l_foot_y = ground_y - math.sin(swing_p * math.pi) * step_h
                l_state = "swing"
                
            # Right foot (swing 0-0.5, contact 0.5-1.0)
            if phase < 0.5:
                swing_p = phase / 0.5
                r_foot_x = r_hip_pos[0] - stride + (stride * 2) * swing_p
                r_foot_y = ground_y - math.sin(swing_p * math.pi) * step_h
                r_state = "swing"
            else:
                r_foot_x = r_hip_pos[0] + stride * (0.5 - ((phase - 0.5) / 0.5))
                r_foot_y = ground_y
                r_state = "contact"

            # Apply IK
            # IK is relative to current hip positions (which bob with root)
            l_hip_curr = (l_hip_pos[0], l_hip_pos[1] + root_y_shift)
            r_hip_curr = (r_hip_pos[0], r_hip_pos[1] + root_y_shift)
            
            # Left knee bends LEFT (flip_knee=True), Right knee bends RIGHT (flip_knee=False)
            l_angle1, l_angle2 = solve_2d_ik(l_hip_curr, (l_foot_x, l_foot_y), l_thigh, l_calf, flip_knee=True)
            r_angle1, r_angle2 = solve_2d_ik(r_hip_curr, (r_foot_x, r_foot_y), r_thigh, r_calf, flip_knee=False)
            
            l_hip_local = l_angle1 - rig.rest_angles.get("knee_l", 0)
            r_hip_local = r_angle1 - rig.rest_angles.get("knee_r", 0)
            l_knee_local = (l_angle2 - rig.rest_angles.get("foot_l", 0)) - (l_angle1 - rig.rest_angles.get("knee_l", 0))
            r_knee_local = (r_angle2 - rig.rest_angles.get("foot_r", 0)) - (r_angle1 - rig.rest_angles.get("knee_r", 0))
            
            # Arms (FK oscillation)
            arm_angle = math.cos(phase * math.pi * 2) * WalkConfig.ARM_SWING
            
            angles = {
                "root_y": root_y_shift, # Now directly in pixels
                "root_x": 0.0,
                "hip_l": l_hip_local,
                "knee_l": l_knee_local,
                "hip_r": r_hip_local,
                "knee_r": r_knee_local,
                "shoulder_l": arm_angle,
                "shoulder_r": -arm_angle,
                "elbow_l": abs(arm_angle) * 0.5,
                "elbow_r": abs(arm_angle) * 0.5,
                "torso": 0.0,
                "neck": 0.0,
                "head": 0.0
            }
            frames.append(angles)
            
            # Phase Name
            cycle_p = phase % 0.5
            if cycle_p < 0.05 or cycle_p > 0.45: phase_name = "CONTACT"
            elif cycle_p < 0.2: phase_name = "DOWN"
            elif cycle_p < 0.35: phase_name = "PASSING"
            else: phase_name = "UP"
            
            print(f"{i+1:02d} | {l_state:7s} | {r_state:7s} | {l_knee_local:+.2f} | {r_knee_local:+.2f} | {root_y_shift:+.1f} | {phase_name}")
            
        print("============================================================\n")
        
        return frames
