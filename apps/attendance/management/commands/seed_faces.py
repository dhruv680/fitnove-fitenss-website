import io
import base64
import numpy as np
from PIL import Image, ImageDraw
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from apps.members.models import Member
from apps.attendance.models import MemberFaceProfile
from apps.attendance.face_service import FaceRecognitionService


class Command(BaseCommand):
    help = 'Seeds initial face recognition biometric profiles for gym members'

    def handle(self, *args, **options):
        members = Member.objects.filter(status=Member.Status.ACTIVE)
        self.stdout.write(f"Enrolling face profiles for {members.count()} active members...")

        colors = [
            ((220, 180, 150), (45, 30, 20)),
            ((240, 200, 170), (20, 20, 20)),
            ((180, 130, 95), (30, 20, 10)),
            ((210, 160, 130), (50, 40, 30)),
            ((160, 110, 80), (15, 15, 15)),
        ]

        enrolled = 0
        for idx, m in enumerate(members):
            if hasattr(m, 'face_profile') and m.face_profile:
                continue

            # Generate synthetic realistic biometric portrait crop
            skin_color, hair_color = colors[idx % len(colors)]
            img = Image.new('RGB', (160, 160), color=(15, 23, 42))
            draw = ImageDraw.Draw(img)

            # Neck
            draw.rectangle([65, 110, 95, 150], fill=skin_color)
            # Head oval
            draw.ellipse([40, 30, 120, 125], fill=skin_color)
            # Hair
            draw.pieslice([38, 25, 122, 100], start=180, end=360, fill=hair_color)
            # Eyes
            draw.ellipse([54, 65, 68, 75], fill=(255, 255, 255))
            draw.ellipse([58, 68, 64, 73], fill=(30, 30, 30))
            draw.ellipse([92, 65, 106, 75], fill=(255, 255, 255))
            draw.ellipse([96, 68, 102, 73], fill=(30, 30, 30))
            # Eyebrows
            draw.line([52, 60, 70, 62], fill=hair_color, width=3)
            draw.line([90, 62, 108, 60], fill=hair_color, width=3)
            # Nose
            draw.line([80, 75, 78, 88], fill=(180, 130, 100), width=2)
            draw.line([78, 88, 84, 88], fill=(180, 130, 100), width=2)
            # Mouth
            draw.arc([66, 92, 94, 108], start=0, end=180, fill=(160, 60, 60), width=3)

            buf = io.BytesIO()
            img.save(buf, format='JPEG', quality=92)
            b64_str = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode('utf-8')

            # Generate deterministic unique neural descriptor based on member_id
            rng = np.random.RandomState(abs(hash(m.member_id)) % (2**31))
            desc = (rng.randn(128) * 0.1).tolist()

            success, msg = FaceRecognitionService.enroll_member_face(m, b64_str, descriptor=desc)
            if success:
                enrolled += 1

        self.stdout.write(self.style.SUCCESS(f"Successfully seeded {enrolled} biometric face profiles."))
