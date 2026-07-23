# fungsi membersihkan gamber
import cv2
import numpy as np

def deskew_img(cv_img):
    gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
    gray = cv2.bitwise_not(gray)

    coords = cv2.findNonZero(gray)
    angle = cv2.minAreaRect(coords)[-1]

    if angle < -45:
        angle = -(90+angle)
    else:
        angle = -angle

    (h, w) = cv_img.shape[:2]
    center = (w // 2, h// 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(cv_img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

    return rotated

def clean_image(image_input):
    if isinstance(image_input, str):
        img = cv2.imread(image_input)
        img = deskew_img(img)
        if img is None:
            raise ValueError("Image not found at path: " + image_input)
    elif isinstance(image_input, np.ndarray):
        img = deskew_img(image_input)
    else:
        # Assume it's a PIL Image
        img = deskew_img(cv2.cvtColor(np.array(image_input), cv2.COLOR_RGB2BGR))

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
    
    return thresh 

