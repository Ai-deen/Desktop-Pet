from django.urls import path
from .views import home,check_focus_view

urlpatterns = [
    path("", home),                  # <-- handles /
    path("focus/", check_focus_view) # existing API
]