from django.urls import path, include
from . import views

urlpatterns = [
    # Dashboard
    path('', views.home, name='home'),
    
    path('dashboard/', views.dashboard, name='dashboard'),

    path('material-summary/', views.material_summary, name='material_summary'),

    # CRUD Material
    path('materials/', views.material_list, name='material_list'),
    path('materials/create/', views.material_create, name='material_create'),
    path('materials/<int:pk>/edit/', views.material_edit, name='material_edit'),
    path('materials/<int:pk>/delete/', views.material_delete, name='material_delete'),

    # Import Excel
    path('import/', views.import_excel, name='import_excel'),

    # Order Material
    path('order/', views.order_material, name='order_material'),

    # Real-time Material Search
    path('search/', views.search_materials, name='search_materials'),
    path('order/<int:pk>/edit/', views.order_edit, name='order_edit'),
    path('order/<int:pk>/delete/', views.order_delete, name='order_delete'),

]
