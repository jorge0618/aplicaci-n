from django.urls import path
from . import views


urlpatterns = [
    path('menu/', views.menu, name='menu'),
    path('upload/', views.upload, name='upload'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('history/', views.history_files, name='history'),
    #path('auto_analysis/<int:file_id>/', views.auto_analysis, name='auto_analysis'),
    path('select/<int:file_id>/', views.select_variables, name='select_variables'),
]