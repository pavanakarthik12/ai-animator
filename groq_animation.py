import json
import base64
import re
from typing import Dict, Any, Tuple, List

def analyze_character_rig(agent, img_path: str) -> Dict[str, Tuple[float, float]]:
    """Use Groq Vision to extract 2D joint coordinates from the reference image."""
    with open(img_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()
        
    prompt = """Analyze this character and extract the 2D joint coordinates.
Provide the [x, y] coordinates for each joint as values between 0.0 and 1.0 (where [0,0] is top-left and [1,1] is bottom-right).
If a joint is obscured or missing, estimate its logical position.

Required joints:
- root (pelvis/hips center)
- torso (upper chest center)
- neck (base of head)
- head (center of head)
- shoulder_l (left shoulder)
- elbow_l
- hand_l
- shoulder_r
- elbow_r
- hand_r
- hip_l
- knee_l
- foot_l
- hip_r
- knee_r
- foot_r

Output ONLY valid JSON in this exact format:
{
  "root": [0.5, 0.6],
  "torso": [0.5, 0.3],
  ...
}"""

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}}
            ]
        }
    ]
    
    print("[GROQ] Analyzing character rig joints...")
    resp = agent._post_with_retry(
        model=agent.vision_model,
        messages=messages,
        max_completion_tokens=2000,
        temperature=0.1
    )
    
    # Extract JSON
    content = resp.choices[0].message.content
    match = re.search(r'\{.*\}', content, re.DOTALL)
    if match:
        try:
            joints = json.loads(match.group(0))
            return joints
        except Exception as e:
            print(f"Error parsing joints JSON: {e}")
            print(f"Raw content: {content}")
    else:
        print(f"No JSON found in response. Raw content: {content}")
            
    # Fallback to hardcoded generic rig if parsing fails
    print("Warning: Failed to extract rig from Groq. Using fallback rig.")
    return {
        "root": [0.5, 0.55],
        "torso": [0.5, 0.35],
        "neck": [0.5, 0.25],
        "head": [0.5, 0.15],
        "shoulder_l": [0.4, 0.35],
        "elbow_l": [0.35, 0.45],
        "hand_l": [0.3, 0.55],
        "shoulder_r": [0.6, 0.35],
        "elbow_r": [0.65, 0.45],
        "hand_r": [0.7, 0.55],
        "hip_l": [0.45, 0.55],
        "knee_l": [0.45, 0.75],
        "foot_l": [0.45, 0.95],
        "hip_r": [0.55, 0.55],
        "knee_r": [0.55, 0.75],
        "foot_r": [0.55, 0.95]
    }

def plan_walk_cycle(agent, rest_joints: Dict[str, Tuple[float, float]]) -> List[Dict[str, float]]:
    """Use Groq Text to generate 5 keyframe poses (Contact, Down, Passing, Up, Contact)."""
    
    prompt = f"""You are a master 2D animator planning a standard 20-frame walk cycle.
The character is a 2D side-view or 3/4-view character.

I need you to output 5 keyframe poses.
The poses represent:
1. Contact (Left leg forward, right arm forward)
2. Down (Lowest point)
3. Passing (Right leg passing left)
4. Up (Highest point)
5. Contact (Right leg forward, left arm forward)

For each keyframe, provide the local rotation angle (in radians) for each joint, relative to its rest pose.
Positive values typically rotate clockwise.

Output ONLY valid JSON in this exact format:
[
  {{
    "name": "Contact L",
    "root_y": 0.0,
    "shoulder_l": 0.3,
    "elbow_l": 0.1,
    "shoulder_r": -0.3,
    "hip_l": -0.5,
    "knee_l": 0.1,
    "hip_r": 0.5,
    "knee_r": 0.3
  }},
  ...
]
Provide exactly 5 keyframes in the array."""

    messages = [{"role": "user", "content": prompt}]
    
    print("[GROQ] Planning walk cycle keyframes...")
    resp = agent.call_model(messages)
    
    # Extract JSON
    content = resp.choices[0].message.content
    match = re.search(r'\[.*\]', content, re.DOTALL)
    if match:
        try:
            keyframes = json.loads(match.group(0))
            if len(keyframes) == 5:
                return keyframes
        except Exception as e:
            print(f"Error parsing walk cycle JSON: {e}")
            print(f"Raw content: {content}")
    else:
        print(f"No JSON found in response. Raw content: {content}")
            
    print("Warning: Failed to extract walk cycle from Groq. Using fallback cycle.")
    return [
        {
            "name": "Contact L",
            "root_y": 0.0,
            "shoulder_l": 0.5, "elbow_l": 0.1, "shoulder_r": -0.5, "elbow_r": 0.2,
            "hip_l": -0.5, "knee_l": 0.0, "hip_r": 0.5, "knee_r": 0.2
        },
        {
            "name": "Down",
            "root_y": 0.03,
            "shoulder_l": 0.3, "elbow_l": 0.2, "shoulder_r": -0.3, "elbow_r": 0.3,
            "hip_l": -0.2, "knee_l": 0.3, "hip_r": 0.6, "knee_r": 0.8
        },
        {
            "name": "Passing",
            "root_y": -0.01,
            "shoulder_l": 0.0, "elbow_l": 0.1, "shoulder_r": 0.0, "elbow_r": 0.1,
            "hip_l": 0.0, "knee_l": 0.1, "hip_r": 0.2, "knee_r": 1.2
        },
        {
            "name": "Up",
            "root_y": -0.03,
            "shoulder_l": -0.3, "elbow_l": 0.1, "shoulder_r": 0.3, "elbow_r": 0.2,
            "hip_l": 0.3, "knee_l": 0.0, "hip_r": -0.3, "knee_r": 0.5
        },
        {
            "name": "Contact R",
            "root_y": 0.0,
            "shoulder_l": -0.5, "elbow_l": 0.1, "shoulder_r": 0.5, "elbow_r": 0.2,
            "hip_l": 0.5, "knee_l": 0.0, "hip_r": -0.5, "knee_r": 0.2
        }
    ]
