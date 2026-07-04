from django.urls import path
from portfolio import views

urlpatterns = [
    # Clean modern URLs
    path('', views.index_view, name='home'),
    path('graph/', views.graph_view, name='graph'),
    path('bio/', views.bio_view, name='bio'),
    path('skills/', views.skills_view, name='skills'),
    path('experience/', views.experience_view, name='experience'),
    path('education/', views.education_view, name='education'),
    path('projects/', views.projects_view, name='projects'),
    path('publications/', views.publications_view, name='publications'),
    path('workshops/', views.workshops_view, name='workshops'),
    path('summary/', views.summary_view, name='summary'),
    path('contact/', views.contact_view, name='contact'),
    path('languages/', views.languages_view, name='languages'),
    path('gallery/', views.gallery_view, name='gallery'),
    path('blogs/', views.blogs_view, name='blogs'),

    # Legacy fallback .html URLs
    path('index.html', views.index_view),
    path('graph.html', views.graph_view),
    path('bio.html', views.bio_view),
    path('skills.html', views.skills_view),
    path('experience.html', views.experience_view),
    path('education.html', views.education_view),
    path('projects.html', views.projects_view),
    path('publications.html', views.publications_view),
    path('workshops.html', views.workshops_view),
    path('summary.html', views.summary_view),
    path('contact.html', views.contact_view),
    path('languages.html', views.languages_view),
    path('gallery.html', views.gallery_view),
    path('blogs.html', views.blogs_view),
]
