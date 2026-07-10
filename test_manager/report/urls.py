from django.urls import path

from . import views

urlpatterns = [
    path(
        "scene-executions/<int:execution_id>/generate-report/",
        views.generate_scene_execution_report,
        name="generate_scene_execution_report",
    ),
]
