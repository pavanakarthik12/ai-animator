"""Extract actual visual geometry from reference images using computer vision."""
import cv2
import numpy as np
from typing import List, Tuple, Dict, Any
from PIL import Image


def extract_contours_from_image(image_path: str, 
                                min_contour_points: int = 10,
                                epsilon_factor: float = 0.002) -> Dict[str, Any]:
    """Extract actual contours/strokes from reference image using computer vision.
    
    Returns actual visual geometry, not semantic approximations.
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
    extracted_regions = []
    
    if is_line_art:
        # Line art processing - extract dark strokes
        # Invert if lines are dark on light background
        if np.mean(gray) > 127:
            gray = cv2.bitwise_not(gray)
        
        # Threshold to get strokes
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Find contours
        contours, hierarchy = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
        
        print(f"Found {len(contours)} raw contours in line art")
        
        for contour in contours:
            if len(contour) < min_contour_points:
                continue
            
            # Simplify contour slightly to remove noise but preserve shape
            epsilon = epsilon_factor * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, False)
            
            if len(approx) < 3:
                continue
            
            # Convert to normalized coordinates (0-1)
            normalized_points = []
            for point in approx:
                x, y = point[0]
                norm_x = float(x) / width
                norm_y = float(y) / height
                normalized_points.append([norm_x, norm_y])
            
            # Estimate if this is a closed contour
            start = approx[0][0]
            end = approx[-1][0]
            dist = np.linalg.norm(start - end)
            closed = dist < 10
            
            # Estimate line thickness from contour area
            area = cv2.contourArea(contour)
            perimeter = cv2.arcLength(contour, True)
            if perimeter > 0:
                thickness = max(2, min(8, int(area / perimeter * 2)))
            else:
                thickness = 3
            
            extracted_strokes.append({
                "points": normalized_points,
                "closed": closed,
                "thickness": thickness,
                "point_count": len(normalized_points)
            })
    
    else:
        # Colored image processing
        # Extract edges for line work
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        
        print(f"Found {len(contours)} edge contours in colored image")
        
        for contour in contours:
            if len(contour) < min_contour_points:
                continue
            
            epsilon = epsilon_factor * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, False)
            
            if len(approx) < 3:
                continue
            
            normalized_points = []
            for point in approx:
                x, y = point[0]
                norm_x = float(x) / width
                norm_y = float(y) / height
                normalized_points.append([norm_x, norm_y])
            
            # Sample color along the contour
            mid_idx = len(approx) // 2
            x, y = approx[mid_idx][0]
            x, y = int(x), int(y)
            if 0 <= y < height and 0 <= x < width:
                b, g, r = img[y, x]
                color = f"#{r:02x}{g:02x}{b:02x}"
            else:
                color = "#000000"
            
            extracted_strokes.append({
                "points": normalized_points,
                "closed": False,
                "thickness": 3,
                "color": color,
                "point_count": len(normalized_points)
            })
        
        # Extract color regions
        # Quantize colors
        img_quant = img.reshape((-1, 3))
        img_quant = np.float32(img_quant)
        
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
        K = min(8, len(np.unique(img_quant, axis=0)))  # Max 8 colors
        
        if K > 1:
            _, labels, centers = cv2.kmeans(img_quant, K, None, criteria, 10, cv2.KMEANS_PP_CENTERS)
            
            # Find regions for each color
            labels = labels.reshape((height, width))
            
            for k in range(K):
                mask = (labels == k).astype(np.uint8) * 255
                
                # Find contours of this color region
                color_contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                for contour in color_contours:
                    area = cv2.contourArea(contour)
                    if area < 100:  # Skip very small regions
                        continue
                    
                    epsilon = 0.01 * cv2.arcLength(contour, True)
                    approx = cv2.approxPolyDP(contour, epsilon, True)
                    
                    normalized_points = []
                    for point in approx:
                        x, y = point[0]
                        norm_x = float(x) / width
                        norm_y = float(y) / height
                        normalized_points.append([norm_x, norm_y])
                    
                    # Get color
                    b, g, r = centers[k].astype(int)
                    color = f"#{r:02x}{g:02x}{b:02x}"
                    
                    extracted_regions.append({
                        "points": normalized_points,
                        "color": color,
                        "area": area,
                        "closed": True
                    })
    
    print(f"Extracted {len(extracted_strokes)} strokes, {len(extracted_regions)} filled regions")
    
    return {
        "width": width,
        "height": height,
        "is_line_art": is_line_art,
        "strokes": extracted_strokes,
        "regions": extracted_regions,
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
