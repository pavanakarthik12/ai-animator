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

class PoseInterpolator:
    @staticmethod
    def interpolate(keyframes: List[Dict[str, float]], num_frames: int = 20) -> List[Dict[str, float]]:
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
            # Ensure all joints get interpolated
            all_joints = set(k1.keys()) | set(k2.keys())
            for joint in all_joints:
                if joint == "name":
                    continue
                v1 = float(k1.get(joint, 0.0))
                v2 = float(k2.get(joint, 0.0))
                interp[joint] = v1 + (v2 - v1) * t
                
            frames.append(interp)
            
        return frames
