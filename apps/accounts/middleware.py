from django.shortcuts import redirect
from django.urls import reverse

class FaceAuthProtectionMiddleware:
    """
    Guarantees that any user whose login is awaiting Face Verification
    cannot navigate to protected dashboard pages until verification completes.
    """

    ALLOWED_PATH_PREFIXES = [
        '/accounts/face-verify/',
        '/accounts/api/face-verify/',
        '/accounts/face-fallback/',
        '/accounts/logout/',
        '/static/',
        '/media/',
        '/healthz/',
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        pending_user_id = request.session.get('face_auth_pending_user_id')
        if pending_user_id:
            path = request.path_info
            is_allowed = any(path.startswith(prefix) for prefix in self.ALLOWED_PATH_PREFIXES)
            if not is_allowed:
                return redirect('accounts:face_verify')

        return self.get_response(request)
