# polls/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseRedirect, HttpResponseForbidden
from django.urls import reverse
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views import generic
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import IntegrityError
from .models import Question, Choice, Vote, UserProfile
from .forms import UserRegisterForm, ProfileUpdateForm, QuestionCreateForm, UserUpdateForm, ProfileEditFormSet

class IndexView(generic.ListView):
    template_name = 'polls/index.html'
    context_object_name = 'latest_question_list'

    def get_queryset(self):
        """
        Показываем только активные вопросы (в пределах времени жизни).
        Фильтрация происходит на уровне базы данных (эффективно).
        """
        now = timezone.now()
        # Используем raw SQL через extra для вычисления даты истечения в БД
        # Это более эффективно, чем фильтрация в Python
        # Формула: pub_date + lifespan_days дней > now
        # В SQLite: datetime(pub_date, '+' || lifespan_days || ' days')
        now_str = now.strftime('%Y-%m-%d %H:%M:%S.%f')
        return Question.objects.extra(
            where=["datetime(pub_date, '+' || lifespan_days || ' days') > %s"],
            params=[now_str]
        ).order_by('-pub_date')

class DetailView(generic.DetailView):
    model = Question
    template_name = 'polls/detail.html'

    def get_queryset(self):
        return Question.objects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Проверяем, голосовал ли пользователь
        if self.request.user.is_authenticated:
            context['has_voted'] = Vote.objects.filter(user=self.request.user, question=self.object).exists()
        else:
            context['has_voted'] = False
        return context

class ResultsView(generic.DetailView):
    model = Question
    template_name = 'polls/results.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        total_votes = sum(choice.votes for choice in self.object.choice_set.all())
        results = []
        for choice in self.object.choice_set.all():
            percent = round((choice.votes / total_votes) * 100, 1) if total_votes > 0 else 0
            results.append({'choice': choice, 'percent': percent})
        context['results'] = results
        return context

def vote(request, question_id):
    question = get_object_or_404(Question, pk=question_id)

    # Проверяем, активен ли вопрос
    if not question.is_active():
        messages.error(request, "Голосование по этому вопросу завершено.")
        return redirect('polls:index')

    if not request.user.is_authenticated:
        return redirect('polls:login')

    try:
        selected_choice = question.choice_set.get(pk=request.POST['choice'])
    except (KeyError, Choice.DoesNotExist):
        return render(request, 'polls/detail.html', {
            'question': question,
            'error_message': 'Пожалуйста, выберите вариант.',
            # Пересчитываем has_voted при ошибке выбора
            'has_voted': Vote.objects.filter(user=request.user, question=question).exists() if request.user.is_authenticated else False,
        })

    # Проверяем, уже голосовал ли пользователь, используя уникальность (user, question)
    # Это делает запись в модели Vote уникальной для каждой пары пользователь-вопрос
    try:
        # Пытаемся создать голос. Если запись с таким user и question уже существует (уникальное ограничение),
        # база данных выбросит IntegrityError.
        new_vote = Vote.objects.create(user=request.user, question=question, choice=selected_choice)
        # Если создание прошло успешно, увеличиваем голос у Choice
        selected_choice.votes += 1
        selected_choice.save()
        messages.success(request, "Ваш голос учтён!")
    except IntegrityError:
        # Пользователь уже голосовал за этот вопрос
        messages.warning(request, "Вы уже голосовали в этом опросе.")
        return redirect('polls:results', pk=question.id)

    return HttpResponseRedirect(reverse('polls:results', args=(question.id,)))

def register(request):
    """
    Регистрация нового пользователя с аватаром.
    """
    if request.method == 'POST':
        form = UserRegisterForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Регистрация прошла успешно!")
            return redirect('polls:index')
    else:
        form = UserRegisterForm()
    return render(request, 'polls/register.html', {'form': form})

@login_required
def profile(request):
    """
    Просмотр профиля пользователя.
    Если пользователь - админ, показывает истёкшие вопросы.
    """
    user = request.user
    context = {'user': user}

    # Проверяем, является ли пользователь администратором
    if user.is_staff:
        now = timezone.now()
        # Используем raw SQL через extra для вычисления даты истечения в БД
        # для фильтрации истёкших вопросов
        now_str = now.strftime('%Y-%m-%d %H:%M:%S.%f')
        expired_questions = Question.objects.extra(
            where=["datetime(pub_date, '+' || lifespan_days || ' days') <= %s"],
            params=[now_str]
        ).order_by('-pub_date')
        context['expired_questions'] = expired_questions

    return render(request, 'polls/profile.html', context)

@login_required
def profile_edit(request):
    """
    Редактирование профиля пользователя.
    """
    # Получаем профиль пользователя, создавая его, если он не существует
    profile, created = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        # Создаём формы с данными из POST и FILES
        formset = ProfileEditFormSet(user_data=request.POST, profile_data=request.POST, files=request.FILES)
        # Устанавливаем инстансы для форм
        formset.set_instances(user_instance=request.user, profile_instance=profile)

        if formset.is_valid():
            user, profile = formset.save()
            messages.success(request, "Ваш профиль успешно обновлён!")
            return redirect('polls:profile') # Перенаправляем на страницу просмотра профиля
    else:
        # Создаём формы с текущими данными
        formset = ProfileEditFormSet()
        formset.set_instances(user_instance=request.user, profile_instance=profile)

    # Передаём обе формы в шаблон
    context = {
        'user_form': formset.user_form,
        'profile_form': formset.profile_form,
    }
    return render(request, 'polls/profile_edit.html', context)

@login_required
def profile_delete(request):
    """
    Удаление профиля пользователя.
    """
    if request.method == 'POST':
        user = request.user
        # Удаляем профиль (он удаляется каскадно при удалении User, если в модели UserProfile стоит CASCADE)
        # Но лучше удалить явно, если есть кастомная логика
        try:
            user.profile.delete() # Удаляем связанный профиль
        except UserProfile.DoesNotExist:
            pass # Профиль уже удалён или не существует (маловероятно, если мы находимся на этой странице)
        user.delete() # Удаляем пользователя
        logout(request) # Важно: выйти из системы, чтобы избежать проблем с сессией
        messages.success(request, "Ваш профиль успешно удалён.")
        return redirect('polls:index') # Перенаправляем на главную страницу
    else:
        # Показываем страницу подтверждения удаления
        return render(request, 'polls/profile_delete.html')

@login_required # Требуем аутентификацию для создания вопроса
def question_create(request):
    """
    Создание нового вопроса (требует аутентификации).
    """
    if request.method == 'POST':
        form = QuestionCreateForm(request.POST, request.FILES) # request.FILES для изображения
        if form.is_valid():
            # Сохраняем вопрос
            question = form.save(commit=True) # user=request.user если поле author добавлено в модель
            messages.success(request, f"Вопрос '{question.question_text}' успешно создан!")
            # Перенаправляем на главную страницу или на страницу созданного вопроса
            return redirect('polls:index') # Или redirect('polls:detail', pk=question.pk)
    else:
        form = QuestionCreateForm()

    return render(request, 'polls/question_create.html', {'form': form})

# Опциональное представление для выхода (можно использовать встроенное)
# def logout_view(request):
#     """
#     Выход из системы.
#     """
#     logout(request)
#     messages.info(request, "Вы вышли из системы.")
#     return redirect('polls:index')