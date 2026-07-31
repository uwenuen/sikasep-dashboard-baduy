from django.urls import path
from . import views


urlpatterns = [
    path('', views.dashboard_home, name='dashboard_home'),
    path("login/", views.login_view, name="login"),
    path("signup/", views.signup_view, name="signup"),
    path("logout/", views.logout_view, name="logout"),
    path('citizens/', views.dashboard_citizens, name='dashboard_citizens'),
    path('reports/', views.dashboard_reports, name='dashboard_reports'),
    path("reports/pdf/", views.export_screening_pdf, name="export_screening_pdf"),
    path('education/', views.dashboard_education, name='dashboard_education'),
    path('education/add/', views.add_education_material, name='add_education_material'),
    path('education/edit/<int:material_id>/', views.edit_education_material, name='edit_education_material'),
    path('education/delete/<int:material_id>/', views.delete_education_material, name='delete_education_material'),
    path('cadres/', views.dashboard_cadres, name='dashboard_cadres'),
    path('cadres/add/', views.add_cadre, name='add_cadre'),
    path('cadres/edit/<int:cadre_id>/', views.edit_cadre, name='edit_cadre'),
    path('cadres/delete/<int:cadre_id>/', views.delete_cadre, name='delete_cadre'),
]

"""
urlpatterns = [
    path("", views.dashboard_home, name="dashboard"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),

    path("citizens/", views.dashboard_citizens, name="citizens"),
    path("screenings/", views.dashboard_screenings, name="screenings"),
    path("reports/", views.dashboard_reports, name="reports"),
]
"""