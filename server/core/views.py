from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

from .services import start_focus_session


@csrf_exempt
def check_focus_view(request):
    if request.method == "POST":
        body = json.loads(request.body.decode("utf-8"))

        result = start_focus_session(
            body.get("domain"),
            body.get("title"),
            body.get("snippet"),
        )

        return JsonResponse(result)
    
def home(request):
    return JsonResponse({"status": "Desktop Pet Backend Running"})
