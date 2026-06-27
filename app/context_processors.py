from django.conf import settings


def demo_mode(request):
    return {"demo_mode": getattr(settings, "DEMO_MODE", False)}
