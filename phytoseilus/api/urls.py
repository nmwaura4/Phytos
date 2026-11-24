from django.urls import path

from .views import (
    dashboard,
    create_received_predator,
    received_predator_detail,
    edit_received_predator,
    delete_received_predator,
    report,
    download_qc_workbook,
)

urlpatterns = [
    path('', dashboard, name='api_dashboard'),
    path('received/new/', create_received_predator, name='received_predator_create'),
    path('received/<int:pk>/', received_predator_detail, name='received_predator_detail'),
    path('received/<int:pk>/edit/', edit_received_predator, name='received_predator_edit'),
    path('received/<int:pk>/delete/', delete_received_predator, name='received_predator_delete'),
    path('reports/', report, name='qc_reports'),
    path('reports/<str:period>/download/', download_qc_workbook, name='qc_report_download'),
]
