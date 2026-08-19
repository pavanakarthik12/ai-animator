"""Extract actual visual geometry from reference images using computer vision."""
import cv2
import numpy as np
from typing import List, Tuple, Dict, Any
from PIL import Image


def extract_contours_from_image(image_path: str, min_contour_points: int = 10, epsilon_factor: float = 0.002) -> Dict[str, Any]:
    """Extract actual contours/strokes from reference image using computer vision.
    
    Returns actual visual geometry, not semantic approximations.
    Uses multi-pass extraction to preserve internal lines and small details.
    """
    # Load image
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Could not load image: {image_path}")
    
    height, width = img.shape[:2]
    
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Detect if image is mostly line art or has colors
    color_variance = np.var(img, axis=(0, 1))
    is_line_art = np.mean(color_variance) < 1000
    
    extracted_strokes = []
    
    # --- MULTI-PASS EXTRACTION ---
    passes = []
    gray_inv = cv2.bitwise_not(gray) if np.mean(gray) > 127 else gray
    
    # PASS 1: Strong / Major contours
    _, b1 = cv2.threshold(gray_inv, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    passes.append(("Pass 1 (Otsu)", b1, 10))
    
    # PASS 2: Medium internal linework
    b2 = cv2.adaptiveThreshold(gray_inv, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, -4)
    passes.append(("Pass 2 (Adaptive 21)", b2, 5))
    
    # PASS 3: Thin linework and small details
    b3 = cv2.adaptiveThreshold(gray_inv, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 7, -3)
    passes.append(("Pass 3 (Adaptive 7)", b3, 3))
    
    all_strokes = []
    
    for pass_name, binary, min_pts in passes:
        dist_transform = cv2.distanceTransform(binary, cv2.DIST_L2, 5)
        
        # Centerline extraction (Skeletonization)
        # Prevents double-tracing of thick lines
        skel = np.zeros(binary.shape, np.uint8)
        img_copy = binary.copy()
        element = cv2.getStructuringElement(cv2.MORPH_CROSS, (3,3))
        while True:
            eroded = cv2.erode(img_copy, element)
            temp = cv2.dilate(eroded, element)
            temp = cv2.subtract(img_copy, temp)
            skel = cv2.bitwise_or(skel, temp)
            img_copy = eroded.copy()
            if cv2.countNonZero(img_copy) == 0:
                break
                
        # Connect dots in skeleton
        kernel = np.ones((3,3), np.uint8)
        closed_skel = cv2.morphologyEx(skel, cv2.MORPH_CLOSE, kernel)
        
        # Find contours on the connected centerline
        contours, _ = cv2.findContours(closed_skel, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for i, contour in enumerate(contours):
            if cv2.arcLength(contour, True) < min_pts:
                continue
                
            # Filter out the image boundary / canvas background rectangle
            x_min, y_min, w, h = cv2.boundingRect(contour)
            if x_min <= 2 and y_min <= 2 and (x_min + w) >= width - 2 and (y_min + h) >= height - 2:
                continue
                
            # Filter out adaptive thresholding artifacts on the image edges
            if (x_min <= 2 and w < 5) or (y_min <= 2 and h < 5) or (x_min + w >= width - 3 and w < 5) or (y_min + h >= height - 3 and h < 5):
                continue
                
            # ADAPTIVE SIMPLIFICATION
            length = cv2.arcLength(contour, True)
            if length > 500:
                epsilon = 0.003 * length # Large smooth contours can be simplified more
            elif length > 100:
                epsilon = 0.001 * length # Moderate
            else:
                epsilon = 0.0001 * length # Small details should receive much less simplification
                
            approx = cv2.approxPolyDP(contour, epsilon, False)
            if len(approx) < 2:
                continue
                
            # Convert folded boundary contours of 1px skeletons into single open paths
            N = len(approx)
            closed = False
            if N > 4:
                idx1 = N // 4
                idx2 = N - idx1
                dist = np.linalg.norm(approx[idx1][0] - approx[idx2][0])
                
                # Compare fold distance to the maximum span of the shape
                pts_array = np.array([p[0] for p in approx])
                span = np.linalg.norm(pts_array.max(axis=0) - pts_array.min(axis=0))
                
                if dist < max(10.0, span * 0.3):
                    # It's a folded path! Cut it in half to prevent double-tracing.
                    approx = approx[:N//2 + 1]
                    closed = False
                else:
                    # True loop
                    start = approx[0][0]
                    end = approx[-1][0]
                    closed = np.linalg.norm(start - end) < 10
            
            normalized_points = []
            for point in approx:
                x, y = point[0]
                norm_x = float(x) / width
                norm_y = float(y) / height
                normalized_points.append([norm_x, norm_y])
            
            # Accurate local stroke width from distance transform
            mask = np.zeros(binary.shape, dtype=np.uint8)
            cv2.drawContours(mask, [contour], -1, 255, 1)
            dist_values = dist_transform[mask == 255]
            if len(dist_values) > 0:
                # Use the 75th percentile instead of max to ignore huge intersections
                rep_val = np.percentile(dist_values, 75)
            else:
                rep_val = 1.0
            
            thickness = max(1, min(15, int(round(rep_val * 2))))
            
            # Sample color if not line art
            color = "#000000"
            if not is_line_art:
                mid_idx = len(approx) // 2
                x, y = int(approx[mid_idx][0][0]), int(approx[mid_idx][0][1])
                if 0 <= y < height and 0 <= x < width:
                    b, g, r = img[y, x]
                    if np.mean([b,g,r]) <= 230:
                        color = f"#{r:02x}{g:02x}{b:02x}"
                        
            all_strokes.append({
                "stroke_id": f"s_{len(all_strokes)}",
                "points": normalized_points,
                "closed": closed,
                "thickness": thickness,
                "color": color,
                "point_count": len(normalized_points),
                "pass": pass_name,
                "pts_raw": approx # For deduplication math
            })
            
    print(f"Raw extracted: {len(all_strokes)}")
    
    # --- DEDUPLICATION OF OVERLAPPING PASSES ---
    global_mask = np.zeros((height, width), dtype=np.uint8)
    
    for stroke in all_strokes:
        pts = stroke.pop("pts_raw")
        thickness = stroke["thickness"]
        
        check_mask = np.zeros((height, width), dtype=np.uint8)
        cv2.polylines(check_mask, [pts], False, 255, max(2, thickness + 2))
        
        overlap = cv2.bitwise_and(check_mask, global_mask)
        seg_area = cv2.countNonZero(check_mask)
        overlap_area = cv2.countNonZero(overlap)
        
        if seg_area == 0:
            continue
            
        # If less than 50% overlap with already-kept strokes, it's new geometry!
        if overlap_area / seg_area < 0.5:
            extracted_strokes.append(stroke)
            cv2.polylines(global_mask, [pts], False, 255, max(1, thickness))
            
    print(f"After duplicate removal: {len(extracted_strokes)}")
    counts = {}
    for s in extracted_strokes:
        counts[s.get("pass", "Unknown")] = counts.get(s.get("pass", "Unknown"), 0) + 1
    for k, v in counts.items():
        if k == "Pass 1 (Otsu)": print(f"  Outer / Major strokes: {v}")
        elif k == "Pass 2 (Adaptive 21)": print(f"  Internal strokes: {v}")
        elif k == "Pass 3 (Adaptive 7)": print(f"  Fine-detail strokes: {v}")
        else: print(f"  {k} strokes: {v}")
    
    extracted_regions = []
    
    if not is_line_art:
        # Basic region extraction using kmeans color quantization
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        pixels = img_rgb.reshape((-1, 3)).astype(np.float32)
        
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
        k = 5
        _, labels, centers = cv2.kmeans(pixels, k, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
        
        centers = np.uint8(centers)
        labels = labels.reshape((height, width))
        
        for k_idx in range(k):
            color = centers[k_idx]
            if np.mean(color) > 230:
                continue
                
            mask = (labels == k_idx).astype(np.uint8) * 255
            color_contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in color_contours:
                area = cv2.contourArea(contour)
                if area > 1000:
                    # Filter out the image boundary / canvas background rectangle
                    x_min, y_min, w, h = cv2.boundingRect(contour)
                    if x_min <= 2 and y_min <= 2 and (x_min + w) >= width - 2 and (y_min + h) >= height - 2:
                        continue
                        
                    # Filter out long thin lines (should be handled by stroke extraction)
                    perimeter = cv2.arcLength(contour, True)
                    if perimeter > 0 and (4 * np.pi * area) / (perimeter * perimeter) < 0.15:
                        continue
                        
                    epsilon = 0.005 * perimeter
                    approx = cv2.approxPolyDP(contour, epsilon, True)
                    
                    if len(approx) > 3:
                        normalized_points = []
                        for point in approx:
                            x, y = point[0]
                            norm_x = float(x) / width
                            norm_y = float(y) / height
                            normalized_points.append([norm_x, norm_y])
                            
                        hex_color = f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}"
                        
                        extracted_regions.append({
                            "points": normalized_points,
                            "color": hex_color,
                            "area": area
                        })

    return {
        "width": width,
        "height": height,
        "strokes": extracted_strokes,
        "regions": extracted_regions,
        "is_line_art": bool(is_line_art),
        "total_elements": len(extracted_strokes) + len(extracted_regions)
    }
def densify_stroke_points(points: List[List[float]], target_points: int = 20) -> List[List[float]]:
    """Add interpolated points to make curves smoother."""
    if len(points) >= target_points or len(points) < 2:
        return points
    
    densified = []
    points_array = np.array(points)
    
    # Calculate total path length
    segments = np.diff(points_array, axis=0)
    segment_lengths = np.linalg.norm(segments, axis=1)
    total_length = np.sum(segment_lengths)
    
    if total_length == 0:
        return points
    
    # Interpolate
    num_new_points = target_points
    step = total_length / (num_new_points - 1)
    
    densified.append(points[0])
    current_dist = 0
    target_dist = step
    
    for i in range(len(points) - 1):
        seg_start = points_array[i]
        seg_end = points_array[i + 1]
        seg_len = segment_lengths[i]
        
        while target_dist <= current_dist + seg_len:
            # Interpolate point on this segment
            t = (target_dist - current_dist) / seg_len if seg_len > 0 else 0
            interp_point = seg_start + t * (seg_end - seg_start)
            densified.append(interp_point.tolist())
            target_dist += step
            
            if len(densified) >= num_new_points - 1:
                break
        
        current_dist += seg_len
        
        if len(densified) >= num_new_points - 1:
            break
    
    densified.append(points[-1])
    
    return densified
