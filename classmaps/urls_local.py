"""Local development URL config - replaces CAS auth with Django built-in auth."""
from django.urls import path, re_path, include
from django.contrib.auth import views as auth_views
from classes import views

classes_patterns = ([
    path('accounts/login/', auth_views.LoginView.as_view(template_name='classes/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
    re_path(r'^$', views.index, name="index"),
    re_path(r'^remove/$', views.remove, name="remove"),
    re_path(r'^save/$', views.save, name="save"),
    re_path(r'^results/$', views.search, name="search"),
    re_path(r'^api/query/$', views.query, name='query'),
    re_path(r'^api/enroll/$', views.enroll, name='enroll'),
    re_path(r'^api/saved/$', views.saved_locations, name='saved_locations'),
    re_path(r'^course/(?P<id>.*)/$', views.course_details, name="course"),
    re_path(r'^building/(?P<id>.*)/$', views.building_details, name="building"),
    re_path(r'^about/$', views.about),
], 'classes')

urlpatterns = [
    path('', include(classes_patterns, namespace='classes')),
]
