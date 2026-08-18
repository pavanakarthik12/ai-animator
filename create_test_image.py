"""Create a simple test reference image for testing the vision drawing feature.

This creates a basic cartoon-style character that can be used to test
the image reference drawing functionality.
"""

try:
    from PIL import Image, ImageDraw
except ImportError:
    print("Error: PIL (Pillow) is required.")
    print("Install it with: pip install pillow")
    exit(1)

def create_simple_character():
    """Create a simple stick figure character for testing."""
    # Create white canvas
    width, height = 400, 500
    img = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(img)
    
    # Head (circle)
    head_center = (200, 100)
    head_radius = 60
    draw.ellipse([
        head_center[0] - head_radius,
        head_center[1] - head_radius,
        head_center[0] + head_radius,
        head_center[1] + head_radius
    ], outline='black', width=3, fill='#f5d7b8')
    
    # Eyes
    left_eye = (180, 90)
    right_eye = (220, 90)
    eye_radius = 5
    for eye in [left_eye, right_eye]:
        draw.ellipse([
            eye[0] - eye_radius,
            eye[1] - eye_radius,
            eye[0] + eye_radius,
            eye[1] + eye_radius
        ], fill='black')
    
    # Smile
    draw.arc([170, 95, 230, 120], 0, 180, fill='black', width=2)
    
    # Body (rectangle)
    body_top = 160
    body_bottom = 320
    body_left = 160
    body_right = 240
    draw.rectangle([body_left, body_top, body_right, body_bottom], 
                   outline='black', width=3, fill='#4a90e2')
    
    # Arms
    # Left arm
    draw.line([body_left, body_top + 20, body_left - 40, body_top + 80], 
              fill='black', width=3)
    # Right arm
    draw.line([body_right, body_top + 20, body_right + 40, body_top + 80], 
              fill='black', width=3)
    
    # Legs
    # Left leg
    draw.line([body_left + 20, body_bottom, body_left + 20, body_bottom + 100], 
              fill='black', width=3)
    # Right leg
    draw.line([body_right - 20, body_bottom, body_right - 20, body_bottom + 100], 
              fill='black', width=3)
    
    return img

def create_detailed_character():
    """Create a more detailed character for testing."""
    width, height = 500, 600
    img = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(img)
    
    # Head
    head_center = (250, 120)
    head_width = 140
    head_height = 160
    draw.ellipse([
        head_center[0] - head_width//2,
        head_center[1] - head_height//2,
        head_center[0] + head_width//2,
        head_center[1] + head_height//2
    ], outline='black', width=4, fill='#f5d7b8')
    
    # Hair
    draw.ellipse([
        head_center[0] - head_width//2,
        head_center[1] - head_height//2 - 30,
        head_center[0] + head_width//2,
        head_center[1] - 10
    ], outline='black', width=3, fill='#8b4513')
    
    # Eyes
    left_eye_center = (220, 110)
    right_eye_center = (280, 110)
    for eye_center in [left_eye_center, right_eye_center]:
        # White of eye
        draw.ellipse([
            eye_center[0] - 12, eye_center[1] - 8,
            eye_center[0] + 12, eye_center[1] + 8
        ], fill='white', outline='black', width=2)
        # Pupil
        draw.ellipse([
            eye_center[0] - 5, eye_center[1] - 5,
            eye_center[0] + 5, eye_center[1] + 5
        ], fill='black')
    
    # Eyebrows
    draw.arc([210, 95, 230, 105], 180, 360, fill='black', width=3)
    draw.arc([270, 95, 290, 105], 180, 360, fill='black', width=3)
    
    # Nose
    draw.line([250, 120, 250, 140], fill='black', width=2)
    draw.line([250, 140, 260, 145], fill='black', width=2)
    
    # Mouth (smile)
    draw.arc([220, 140, 280, 170], 0, 180, fill='#ff0000', width=3)
    
    # Body (shirt)
    body_points = [
        (250, 200),  # neck
        (180, 220),  # left shoulder
        (180, 380),  # left hip
        (320, 380),  # right hip
        (320, 220),  # right shoulder
        (250, 200)   # back to neck
    ]
    draw.polygon(body_points, outline='black', fill='#ff6b6b')
    
    # Arms
    # Left arm
    draw.line([180, 240, 140, 340], fill='#f5d7b8', width=20)
    draw.line([180, 240, 140, 340], fill='black', width=3)
    # Right arm
    draw.line([320, 240, 360, 340], fill='#f5d7b8', width=20)
    draw.line([320, 240, 360, 340], fill='black', width=3)
    
    # Hands (circles)
    draw.ellipse([130, 330, 150, 350], fill='#f5d7b8', outline='black', width=2)
    draw.ellipse([350, 330, 370, 350], fill='#f5d7b8', outline='black', width=2)
    
    # Legs
    # Left leg
    draw.rectangle([210, 380, 240, 520], fill='#2c3e50', outline='black', width=3)
    # Right leg
    draw.rectangle([260, 380, 290, 520], fill='#2c3e50', outline='black', width=3)
    
    # Feet
    draw.ellipse([200, 510, 250, 540], fill='black', outline='black')
    draw.ellipse([250, 510, 300, 540], fill='black', outline='black')
    
    return img

if __name__ == "__main__":
    import sys
    
    print("Creating test reference images...")
    
    # Create simple character
    simple = create_simple_character()
    simple.save("test_simple_character.png")
    print("✓ Created: test_simple_character.png (simple stick figure)")
    
    # Create detailed character
    detailed = create_detailed_character()
    detailed.save("test_detailed_character.png")
    print("✓ Created: test_detailed_character.png (detailed character)")
    
    print("\nYou can now test with:")
    print('  python test_reference_drawing.py test_simple_character.png "Draw this character"')
    print('  python test_reference_drawing.py test_detailed_character.png "Recreate this character"')
