from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.panel_calculadora, name='panel_calculadora'),
    path('proyecto/<int:proyecto_id>/', views.gestion_ambientes_view, name='gestion_ambientes'),
    path('proyecto/<int:proyecto_id>/pdf/', views.exportar_pdf_view, name='exportar_pdf'),
    path('perfil/', views.configuracion_perfil_view, name='configuracion_perfil'),
    
    # --- RUTAS DE AUTENTICACIÓN CORREGIDAS PARA TU ESTRUCTURA ---
    # Le indicamos a la vista que busque el formulario en 'calculador/registration/login.html'
    path('login/', auth_views.LoginView.as_view(template_name='calculador/registration/login.html'), name='login'),
    path('proyecto/<int:proyecto_id>/excel/', views.exportar_excel_view, name='exportar_excel'),
    path('logout/', auth_views.LogoutView.as_view(http_method_names=['get', 'post'], next_page='login'), name='logout'),
    path('registro/', views.registro_view, name='registro'),
]
