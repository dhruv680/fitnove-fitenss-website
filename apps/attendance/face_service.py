import io
import json
import base64
import numpy as np
from PIL import Image, ImageOps
from django.core.files.base import ContentFile
from django.utils import timezone
from .models import MemberFaceProfile, Attendance
from apps.members.models import Member


class FaceRecognitionService:
    """
    High-performance facial feature extraction, enrollment, and verification engine.
    Supports both client-side 128-D neural embeddings and server-side normalized visual feature vectors.
    """

    DESCRIPTOR_EUCLIDEAN_THRESHOLD = 0.58  # Maximum distance for neural face descriptor match
    VISUAL_COSINE_SIMILARITY_THRESHOLD = 0.70  # Minimum similarity for visual feature match

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
        except Exception as e:
            return None

    @staticmethod
    def compute_visual_features(pil_image):
        """
        Extracts a robust, normalized 128-dimensional multi-cell spatial gradient feature vector.
        Standardizes contrast, equalizes histogram, and analyzes directional spatial gradients.
        """
        try:
            # 1. Resize to canonical 128x128
            img = pil_image.resize((128, 128), Image.Resampling.LANCZOS)
            # 2. Convert to grayscale and equalize histogram
            gray = ImageOps.grayscale(img)
            gray = ImageOps.equalize(gray)
            arr = np.array(gray, dtype=np.float32) / 255.0

            # 3. Compute horizontal and vertical Sobel gradients
            gx = np.zeros_like(arr)
            gy = np.zeros_like(arr)
            gx[:, 1:-1] = (arr[:, 2:] - arr[:, :-2]) * 0.5
            gy[1:-1, :] = (arr[2:, :] - arr[:-2, :]) * 0.5
            magnitude = np.sqrt(gx**2 + gy**2)

            # 4. Divide into 8x8 grid of 16x16 cells -> 64 cells * 2 stats = 128 dimensions
            features = []
            cell_size = 16
            for r in range(8):
                for c in range(8):
                    r_start, r_end = r * cell_size, (r + 1) * cell_size
                    c_start, c_end = c * cell_size, (c + 1) * cell_size
                    cell_mag = magnitude[r_start:r_end, c_start:c_end]
                    cell_arr = arr[r_start:r_end, c_start:c_end]

                    # Mean intensity and mean gradient magnitude
                    features.append(float(np.mean(cell_arr)))
                    features.append(float(np.mean(cell_mag)))

            vec = np.array(features, dtype=np.float32)
            norm = np.linalg.norm(vec)
            if norm > 1e-6:
                vec = vec / norm
            return vec.tolist()
        except Exception as e:
            return None

    @staticmethod
    def enroll_member_face(member, image_data, descriptor=None):
        """
        Enrolls or updates a member's face profile.
        Stores face crop image, visual feature vector, and optional neural descriptor.
        Returns: (success: bool, message: str)
        """
        pil_img = FaceRecognitionService.decode_base64_image(image_data)
        if not pil_img:
            return False, "Could not decode face image data."

        visual_vec = FaceRecognitionService.compute_visual_features(pil_img)
        if not visual_vec:
            return False, "Failed to extract facial features from image."

        # Prepare image file for storage
        buf = io.BytesIO()
        pil_img.save(buf, format='JPEG', quality=90)
        file_name = f"face_{member.member_id}_{int(timezone.now().timestamp())}.jpg"
        content_file = ContentFile(buf.getvalue(), name=file_name)

        desc_json = ""
        if descriptor and isinstance(descriptor, (list, tuple)):
            try:
                # Ensure floats
                clean_desc = [float(x) for x in descriptor]
                desc_json = json.dumps(clean_desc)
            except Exception:
                desc_json = ""

        profile, created = MemberFaceProfile.objects.get_or_create(member=member)
        profile.face_image = content_file
        profile.feature_vector = json.dumps(visual_vec)
        if desc_json:
            profile.face_descriptor = desc_json
        profile.is_active = True
        profile.save()

        # Also update user's profile picture if not already set
        if not member.user.profile_picture:
            member.user.profile_picture = content_file
            member.user.save(update_fields=['profile_picture'])

        return True, f"Face profile enrolled successfully for {member.full_name} ({member.member_id})."

    @staticmethod
    def verify_and_recognize_face(image_data, descriptor=None, organization=None):
        """
        Matches a query face against enrolled member face profiles.
        Returns: (member: Member|None, confidence: float, error_message: str|None)
        """
        pil_img = FaceRecognitionService.decode_base64_image(image_data)
        if not pil_img:
            return None, 0.0, "Invalid or missing face image data."

        query_visual_vec = FaceRecognitionService.compute_visual_features(pil_img)
        if not query_visual_vec:
            return None, 0.0, "Could not extract facial features from camera frame."

        query_visual_arr = np.array(query_visual_vec, dtype=np.float32)

        query_desc_arr = None
        if descriptor and isinstance(descriptor, (list, tuple)) and len(descriptor) >= 64:
            try:
                query_desc_arr = np.array([float(x) for x in descriptor], dtype=np.float32)
                qnorm = np.linalg.norm(query_desc_arr)
                if qnorm > 1e-6:
                    query_desc_arr = query_desc_arr / qnorm
            except Exception:
                query_desc_arr = None

        # Fetch enrolled face profiles
        profiles_qs = MemberFaceProfile.objects.filter(is_active=True).select_related(
            'member__user', 'member__organization', 'member__branch'
        )
        if organization:
            profiles_qs = profiles_qs.filter(member__organization=organization)

        best_member = None
        best_confidence = 0.0
        min_distance = float('inf')

        for prof in profiles_qs:
            matched = False
            confidence = 0.0

            # 1. Compare neural face descriptor if available on both sides
            if query_desc_arr is not None and prof.face_descriptor:
                try:
                    prof_desc = np.array(json.loads(prof.face_descriptor), dtype=np.float32)
                    pnorm = np.linalg.norm(prof_desc)
                    if pnorm > 1e-6:
                        prof_desc = prof_desc / pnorm
                    dist = float(np.linalg.norm(query_desc_arr - prof_desc))
                    if dist <= FaceRecognitionService.DESCRIPTOR_EUCLIDEAN_THRESHOLD:
                        matched = True
                        confidence = max(confidence, 1.0 - (dist / 1.0))
                except Exception:
                    pass

            # 2. Compare normalized visual feature vectors
            if prof.feature_vector:
                try:
                    prof_visual = np.array(json.loads(prof.feature_vector), dtype=np.float32)
                    sim = float(np.dot(query_visual_arr, prof_visual))
                    if sim >= FaceRecognitionService.VISUAL_COSINE_SIMILARITY_THRESHOLD:
                        matched = True
                        confidence = max(confidence, sim)
                except Exception:
                    pass

            if matched and confidence > best_confidence:
                best_confidence = confidence
                best_member = prof.member

        if best_member:
            return best_member, round(best_confidence * 100, 1), None

        return None, 0.0, "Face Not Recognized: Unregistered Face."
