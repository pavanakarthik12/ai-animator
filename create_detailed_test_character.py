"""Create a detailed cartoon character for testing the upgraded vision system."""

try:
    from PIL import Image, ImageDraw
except ImportError:
    print("Error: PIL (Pillow) is required.")
    print("Install it with: pip install pillow")
    exit(1)

def create_detailed_expressive_character():
    """Create a detailed character with expressive features for accuracy testing."""
    width, height = 600, 700
    img = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(img)
    
    # === HEAD ===
    # Head contour (not a perfect ellipse - irregular cartoon shape)
    head_points = [
        (300, 100),   # top
        (350, 120),   # top right
        (380, 160),   # right cheek
        (370, 210),   # jaw right
        (340, 240),   # chin right
        (300, 250),   # chin center
        (260, 240),   # chin left
        (230, 210),   # jaw left
        (220, 160),   # left cheek
        (250, 120),   # top left
        (300, 100)    # back to top
    ]
    draw.polygon(head_points, outline='#000000', fill='#f5d7b8', width=4)
    
    # === HAIR (multiple strands) ===
    hair_color = '#8b4513'
    # Hair strand 1
    draw.line([(280, 105), (270, 90), (265, 75), (268, 60)], fill=hair_color, width=6)
    # Hair strand 2  
    draw.line([(300, 100), (300, 80), (302, 60), (305, 45)], fill=hair_color, width=6)
    # Hair strand 3
    draw.line([(320, 105), (330, 90), (335, 75), (332, 60)], fill=hair_color, width=6)
    # Hair mass on top
    draw.ellipse([260, 50, 340, 110], outline=hair_color, fill=hair_color, width=3)
    
    # === EYEBROWS (expressive, thick) ===
    # Left eyebrow (worried/raised)
    left_brow_points = [(250, 150), (270, 145), (285, 148)]
    draw.line(left_brow_points, fill='#000000', width=5)
    # Right eyebrow (worried/raised)
    right_brow_points = [(315, 148), (330, 145), (350, 150)]
    draw.line(right_brow_points, fill='#000000', width=5)
    
    # === EYES (detailed with whites, iris, pupils) ===
    # Left eye
    # White
    draw.ellipse([250, 160, 280, 185], fill='white', outline='#000000', width=3)
    # Iris
    draw.ellipse([258, 165, 272, 180], fill='#4a90e2', outline='#000000', width=2)
    # Pupil
    draw.ellipse([262, 168, 268, 177], fill='#000000')
    # Highlight
    draw.ellipse([263, 170, 266, 173], fill='white')
    
    # Right eye
    # White
    draw.ellipse([320, 160, 350, 185], fill='white', outline='#000000', width=3)
    # Iris
    draw.ellipse([328, 165, 342, 180], fill='#4a90e2', outline='#000000', width=2)
    # Pupil
    draw.ellipse([332, 168, 338, 177], fill='#000000')
    # Highlight
    draw.ellipse([333, 170, 336, 173], fill='white')
    
    # === NOSE ===
    nose_points = [(300, 190), (305, 205), (295, 208)]
    draw.line(nose_points, fill='#000000', width=3)
    # Nostril
    draw.arc([296, 204, 304, 210], 0, 180, fill='#000000', width=2)
    
    # === MOUTH (expressive smile with detail) ===
    # Upper lip curve
    mouth_points = [(270, 220), (285, 215), (300, 213), (315, 215), (330, 220)]
    draw.line(mouth_points, fill='#000000', width=4)
    # Lower lip curve
    lower_lip = [(270, 220), (285, 228), (300, 230), (315, 228), (330, 220)]
    draw.line(lower_lip, fill='#000000', width=4)
    # Lip line
    draw.line([(270, 220), (300, 218), (330, 220)], fill='#000000', width=2)
    # Teeth (small)
    draw.rectangle([285, 215, 315, 220], fill='white')
    
    # === NECK ===
    draw.line([(280, 245), (280, 280)], fill='#f5d7b8', width=25)
    draw.line([(320, 245), (320, 280)], fill='#f5d7b8', width=25)
    draw.line([(270, 245), (270, 280)], fill='#000000', width=3)
    draw.line([(330, 245), (330, 280)], fill='#000000', width=3)
    
    # === BODY/SHIRT (with collar and folds) ===
    # Shirt body
    shirt_points = [
        (200, 290),  # left shoulder
        (200, 480),  # left bottom
        (400, 480),  # right bottom
        (400, 290),  # right shoulder
        (320, 280),  # neck right
        (280, 280),  # neck left
        (200, 290)   # back to start
    ]
    draw.polygon(shirt_points, outline='#000000', fill='#ff6b6b', width=4)
    
    # Collar
    draw.line([(280, 280), (260, 300), (240, 320)], fill='#000000', width=4)
    draw.line([(320, 280), (340, 300), (360, 320)], fill='#000000', width=4)
    
    # Clothing fold lines (detail)
    draw.line([(250, 350), (270, 355), (290, 350)], fill='#000000', width=2)
    draw.line([(310, 350), (330, 355), (350, 350)], fill='#000000', width=2)
    draw.line([(300, 380), (300, 450)], fill='#000000', width=2)
    
    # === LEFT ARM ===
    # Upper arm
    draw.line([(200, 310), (150, 380)], fill='#f5d7b8', width=30)
    draw.line([(185, 310), (135, 380)], fill='#000000', width=3)
    draw.line([(215, 310), (165, 380)], fill='#000000', width=3)
    
    # Forearm
    draw.line([(150, 380), (120, 470)], fill='#f5d7b8', width=28)
    draw.line([(137, 380), (107, 470)], fill='#000000', width=3)
    draw.line([(163, 380), (133, 470)], fill='#000000', width=3)
    
    # Left hand (detailed)
    hand_points = [
        (120, 470),
        (110, 475),
        (105, 485),  # thumb
        (108, 495),
        (115, 500),
        (120, 498),  # palm
        (118, 510),  # finger 1
        (120, 520),
        (125, 518),
        (127, 510),
        (130, 520),  # finger 2
        (135, 528),
        (138, 518),
        (140, 510),
        (143, 520),  # finger 3
        (148, 525),
        (150, 515),
        (152, 510),
        (153, 520),  # finger 4
        (155, 523),
        (157, 513),
        (155, 505),
        (150, 498),
        (145, 490),
        (135, 480),
        (125, 473),
        (120, 470)
    ]
    draw.polygon(hand_points, outline='#000000', fill='#f5d7b8', width=3)
    
    # === RIGHT ARM ===
    # Upper arm
    draw.line([(400, 310), (450, 380)], fill='#f5d7b8', width=30)
    draw.line([(415, 310), (465, 380)], fill='#000000', width=3)
    draw.line([(385, 310), (435, 380)], fill='#000000', width=3)
    
    # Forearm
    draw.line([(450, 380), (480, 470)], fill='#f5d7b8', width=28)
    draw.line([(463, 380), (493, 470)], fill='#000000', width=3)
    draw.line([(437, 380), (467, 470)], fill='#000000', width=3)
    
    # Right hand (simplified fist)
    draw.ellipse([470, 465, 500, 490], outline='#000000', fill='#f5d7b8', width=3)
    # Knuckle lines
    draw.line([(475, 472), (495, 472)], fill='#000000', width=2)
    draw.line([(475, 478), (495, 478)], fill='#000000', width=2)
    
    # === LEGS ===
    # Left leg
    draw.rectangle([250, 480, 280, 620], outline='#000000', fill='#2c3e50', width=3)
    # Right leg
    draw.rectangle([320, 480, 350, 620], outline='#000000', fill='#2c3e50', width=3)
    
    # === FEET ===
    # Left foot
    draw.ellipse([235, 615, 285, 645], outline='#000000', fill='#000000', width=3)
    # Right foot
    draw.ellipse([315, 615, 365, 645], outline='#000000', fill='#000000', width=3)
    
    # === GROUND LINE ===
    draw.line([(50, 650), (550, 650)], fill='#666666', width=3)
    
    # === SMALL DETAILS ===
    # Freckles/beauty marks
    draw.ellipse([275, 195, 278, 198], fill='#8b6f47')
    draw.ellipse([325, 192, 328, 195], fill='#8b6f47')
    
    # Shirt button
    draw.ellipse([297, 330, 303, 336], outline='#000000', fill='white', width=2)
    draw.ellipse([297, 370, 303, 376], outline='#000000', fill='white', width=2)
    draw.ellipse([297, 410, 303, 416], outline='#000000', fill='white', width=2)
    
    return img

if __name__ == "__main__":
    print("Creating detailed test character...")
    
    detailed = create_detailed_expressive_character()
    detailed.save("test_detailed_reference.png")
    print("✓ Created: test_detailed_reference.png")
    print("  - Detailed facial features (expressive eyebrows, eyes with iris/pupils, mouth with lips)")
    print("  - Hair with individual strands")
    print("  - Detailed hands with visible fingers")
    print("  - Clothing with folds and buttons")
    print("  - Multiple colors")
    print("  - Varied line weights")
    print("  - Small details (freckles, highlights)")
    print("\nTest with:")
    print('  python test_reference_drawing.py test_detailed_reference.png "Recreate this character accurately"')
