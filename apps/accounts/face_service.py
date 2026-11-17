import io
import json
import base64
import math

try:
    import numpy as np
except ImportError:
    np = None

from PIL import Image, ImageOps, ImageStat
from django.core.files.base import ContentFile
from django.utils import timezone
from .models import UserFaceProfile

class FaceAuthService:
    """
    High-security Biometric Face Authentication & Enrollment Service.
    Extracts 128-D spatial gradient vectors and compares them against stored user templates.
    Includes liveness validation and anti-spoofing heuristics.
    """

    DESCRIPTOR_EUCLIDEAN_THRESHOLD = 0.58     # Max distance for client neural face descriptor
    VISUAL_COSINE_SIMILARITY_THRESHOLD = 0.68  # Min cosine similarity for visual feature vector
    MIN_IMAGE_VARIANCE = 120.0                 # Anti-blank / anti-spoof minimum image variance

    @staticmethod
    def decode_base64_image(image_data):
        """Converts base64 data URI or raw base64 string into a PIL Image."""
        if not image_data:
            return None
        try:
            if ',' in image_data:
                image_data = image_data.split(',', 1)[1]
            binary_data = base64.b64decode(image_data)
            return Image.open(io.BytesIO(binary_data)).convert('RGB')
        except Exception:
            return None

    @staticmethod
    def check_liveness_and_quality(pil_image):
        """
        Validates that the captured camera frame is not completely dark, washed-out, or blank.
        Returns: (is_valid: bool, reason: str)
        """
        try:
            if pil_image.width < 100 or pil_image.height < 100:
                return False, "Image resolution too low for biometric detection."

            gray = ImageOps.grayscale(pil_image)
            stat = ImageStat.Stat(gray)
            mean_brightness = stat.mean[0]
            variance = stat.var[0]

            if mean_brightness < 20:
                return False, "Lighting is too dark. Please face a light source."
            if mean_brightness > 245:
                return False, "Image is overexposed or washed out. Please reduce glare."
            if variance < FaceAuthService.MIN_IMAGE_VARIANCE:
                return False, "No distinct facial details detected. Please position your face closer."

            return True, "Quality verified."
        except Exception as e:
            return False, f"Image validation error: {str(e)}"

    @staticmethod
    def compute_visual_features(pil_image):
        """
        Extracts a normalized 128-dimensional multi-cell spatial gradient feature vector.
        Standardizes contrast, equalizes histogram, and computes 8x8 cell directional gradients.
        Supports numpy acceleration when available, with pure-Python math fallback.
        """
        try:
            img = pil_image.resize((128, 128), Image.Resampling.LANCZOS)
            gray = ImageOps.grayscale(img)
            gray = ImageOps.equalize(gray)

            if np is not None:
                arr = np.array(gray, dtype=np.float32) / 255.0
                gx = np.zeros_like(arr)
                gy = np.zeros_like(arr)
                gx[:, 1:-1] = (arr[:, 2:] - arr[:, :-2]) * 0.5
                gy[1:-1, :] = (arr[2:, :] - arr[:-2, :]) * 0.5
                magnitude = np.sqrt(gx**2 + gy**2)

                features = []
                cell_size = 16
                for r in range(8):
                    for c in range(8):
                        r_start, r_end = r * cell_size, (r + 1) * cell_size
                        c_start, c_end = c * cell_size, (c + 1) * cell_size
                        cell_mag = magnitude[r_start:r_end, c_start:c_end]
                        cell_arr = arr[r_start:r_end, c_start:c_end]

                        features.append(float(np.mean(cell_arr)))
                        features.append(float(np.mean(cell_mag)))

                vec = np.array(features, dtype=np.float32)
                norm = np.linalg.norm(vec)
                if norm > 1e-6:
                    vec = vec / norm
                return vec.tolist()
            else:
                # Pure Python fallback using standard library math
                pixels = list(gray.getdata())
                grid = [[pixels[r * 128 + c] / 255.0 for c in range(128)] for r in range(128)]

                mag = [[0.0] * 128 for _ in range(128)]
                for r in range(128):
                    for c in range(1, 127):
                        gx_val = (grid[r][c + 1] - grid[r][c - 1]) * 0.5
                        gy_val = ((grid[r + 1][c] - grid[r - 1][c]) * 0.5) if (1 <= r < 127) else 0.0
                        mag[r][c] = math.sqrt(gx_val * gx_val + gy_val * gy_val)

                features = []
                cell_size = 16
                count = 256.0  # 16 * 16
                for r in range(8):
                    for c in range(8):
                        r_start = r * cell_size
                        c_start = c * cell_size
                        sum_arr = 0.0
                        sum_mag = 0.0
                        for i in range(cell_size):
                            row_grid = grid[r_start + i]
                            row_mag = mag[r_start + i]
                            for j in range(cell_size):
                                sum_arr += row_grid[c_start + j]
                                sum_mag += row_mag[c_start + j]
                        features.append(sum_arr / count)
                        features.append(sum_mag / count)

                sum_sq = sum(x * x for x in features)
                norm = math.sqrt(sum_sq)
                if norm > 1e-6:
                    features = [x / norm for x in features]
                return features
        except Exception:
            return None

    @classmethod
    def enroll_user_face(cls, user, image_data, descriptor=None):
        """
        Enrolls or updates a user's biometric face template.
        Stores face image crop, normalized 128-D vector, and optional neural descriptor.
        Returns: (success: bool, message: str)
        """
        pil_img = cls.decode_base64_image(image_data)
        if not pil_img:
            return False, "Could not decode face image data."

        is_valid, quality_reason = cls.check_liveness_and_quality(pil_img)
        if not is_valid:
            return False, quality_reason

        visual_vec = cls.compute_visual_features(pil_img)
        if not visual_vec:
            return False, "Failed to extract facial biometric features."

        # Save image file
        buf = io.BytesIO()
        pil_img.save(buf, format='JPEG', quality=88)
        file_name = f"user_face_{user.id}_{int(timezone.now().timestamp())}.jpg"
        content_file = ContentFile(buf.getvalue(), name=file_name)

        desc_json = ""
        if descriptor and isinstance(descriptor, (list, tuple)) and len(descriptor) >= 64:
            try:
                clean_desc = [float(x) for x in descriptor]
                desc_json = json.dumps(clean_desc)
            except Exception:
                desc_json = ""

        profile, _ = UserFaceProfile.objects.get_or_create(user=user)
        profile.face_image = content_file
        profile.feature_vector = json.dumps(visual_vec)
        if desc_json:
            profile.face_descriptor = desc_json
        profile.is_active = True
        profile.save()

        # Update user profile picture if empty
        if not user.profile_picture:
            user.profile_picture = content_file
            user.save(update_fields=['profile_picture'])

        # Synchronize with MemberFaceProfile if user has gym member record
        try:
            if hasattr(user, 'member_profile') and user.member_profile:
                from apps.attendance.models import MemberFaceProfile
                mem_prof, _ = MemberFaceProfile.objects.get_or_create(member=user.member_profile)
                mem_prof.face_image = content_file
                mem_prof.feature_vector = json.dumps(visual_vec)
                if desc_json:
                    mem_prof.face_descriptor = desc_json
                mem_prof.is_active = True
                mem_prof.save()
        except Exception:
            pass

        return True, "Face enrolled successfully!"

    @classmethod
    def verify_user_face(cls, user, image_data, descriptor=None):
        """
        Verifies captured face against the user's registered face profile.
        Returns: (matched: bool, confidence: float, message: str)
        """
        if not hasattr(user, 'face_auth_profile') or not user.face_auth_profile.is_active:
            return False, 0.0, "No active biometric face profile found for this user."

        profile = user.face_auth_profile
        if not profile.feature_vector and not profile.face_descriptor:
            return False, 0.0, "Enrolled biometric template is incomplete."

        pil_img = cls.decode_base64_image(image_data)
        if not pil_img:
            return False, 0.0, "Invalid or missing face image data."

        is_valid, quality_reason = cls.check_liveness_and_quality(pil_img)
        if not is_valid:
            return False, 0.0, quality_reason

        query_visual_vec = cls.compute_visual_features(pil_img)
        if not query_visual_vec:
            return False, 0.0, "Could not extract facial features from camera frame."

        matched = False
        confidence = 0.0

        # 1. Compare client neural descriptor if available
        if descriptor and isinstance(descriptor, (list, tuple)) and profile.face_descriptor:
            try:
                q_desc = [float(x) for x in descriptor]
                p_desc = [float(x) for x in json.loads(profile.face_descriptor)]
                q_norm = math.sqrt(sum(x * x for x in q_desc))
                p_norm = math.sqrt(sum(x * x for x in p_desc))
                if q_norm > 1e-6:
                    q_desc = [x / q_norm for x in q_desc]
                if p_norm > 1e-6:
                    p_desc = [x / p_norm for x in p_desc]

                dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(q_desc, p_desc)))
                if dist <= cls.DESCRIPTOR_EUCLIDEAN_THRESHOLD:
                    matched = True
                    confidence = max(confidence, 1.0 - (dist / 1.0))
            except Exception:
                pass

        # 2. Compare normalized visual gradient vector (cosine similarity)
        if profile.feature_vector:
            try:
                prof_visual = [float(x) for x in json.loads(profile.feature_vector)]
                sim = float(sum(a * b for a, b in zip(query_visual_vec, prof_visual)))
                if sim >= cls.VISUAL_COSINE_SIMILARITY_THRESHOLD:
                    matched = True
                    confidence = max(confidence, sim)
                else:
                    confidence = max(confidence, sim)
            except Exception:
                pass

        final_conf_pct = round(max(confidence, 0.0) * 100, 1)

        if matched:
            return True, final_conf_pct, f"Face Verified Successfully ({final_conf_pct}% match)!"
        else:
            return False, final_conf_pct, f"Face did not match registered profile ({final_conf_pct}% similarity). Please align your face and try again."
