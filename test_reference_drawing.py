"""Test script for image reference drawing feature.

This script demonstrates how to use the new image reference feature.
You can provide a reference image and the system will analyze it using
Groq Vision and recreate it in Krita using actual drawing operations.

Usage:
    python test_reference_drawing.py path/to/reference.png "Draw this character"
"""

import os
import sys

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_reference_drawing.py <image_path> [prompt]")
        print()
        print("Example:")
        print('  python test_reference_drawing.py reference.png "Recreate this in Krita"')
        sys.exit(1)
    
    image_path = sys.argv[1]
    prompt = sys.argv[2] if len(sys.argv) > 2 else "Recreate this reference image in Krita as accurately as possible."
    
    if not os.path.exists(image_path):
        print(f"Error: Image file not found: {image_path}")
        sys.exit(1)
    
    # Set environment variables for main.py
    os.environ["REFERENCE_IMAGE"] = image_path
    os.environ["AUTOMATION_PROMPT"] = prompt
    
    # Import and run main
    import main
    main.main()
