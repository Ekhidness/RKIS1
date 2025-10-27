# polls/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views # Импортируем встроенные представления аутентификации
from . import views

app_name = 'polls'

urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('<int:pk>/', views.DetailView.as_view(), name='detail'),
    path('<int:pk>/results/', views.ResultsView.as_view(), name='results'),
    path('<int:question_id>/vote/', views.vote, name='vote'),
    path('register/', views.register, name='register'),
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('profile/delete/', views.profile_delete, name='profile_delete'),
    # URL для выхода, используя встроенное представление LogoutView
    # next_page указывает, куда перенаправить после выхода
    path('logout/', auth_views.LogoutView.as_view(next_page='polls:index'), name='logout'),
    path('create/', views.question_create, name='create_question'),
    # path('create/', views.QuestionCreateView.as_view(), name='create_question'), # Старая строка, можно удалить
]