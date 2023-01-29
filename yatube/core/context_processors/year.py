from django.utils import timezone


def year(request):
    """Добавляем переменную с текущим годом."""
    return {
        "year": timezone.now().year,
    }
