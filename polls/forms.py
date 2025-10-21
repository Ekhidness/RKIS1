# polls/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import UserProfile, Question, Choice

class UserProfileCreationForm(forms.ModelForm):
    """Форма для создания профиля пользователя."""
    class Meta:
        model = UserProfile
        fields = ['name', 'avatar']
        # widgets = {
        #     'avatar': forms.FileInput(attrs={'accept': 'image/*'}),
        # }

class UserRegisterForm(UserCreationForm):
    """
    Форма регистрации пользователя, включающая поля для профиля.
    """
    email = forms.EmailField(required=True)
    name = forms.CharField(max_length=100, required=False)
    avatar = forms.ImageField(required=True)

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()

        profile = UserProfile(
            user=user,
            name=self.cleaned_data.get("name", ""),
            avatar=self.cleaned_data["avatar"]
        )
        if commit:
            profile.save()

        return user

class UserUpdateForm(forms.ModelForm):
    """
    Форма для обновления данных встроенной модели User.
    """
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ['username', 'email'] # Добавь другие поля User, которые хочешь редактировать

class ProfileUpdateForm(forms.ModelForm):
    """
    Форма для обновления данных профиля.
    """
    class Meta:
        model = UserProfile
        fields = ['name', 'avatar']
        # widgets = {
        #     'avatar': forms.FileInput(attrs={'accept': 'image/*'}),
        # }

class ProfileEditFormSet:
    """
    Объединяет UserUpdateForm и ProfileUpdateForm.
    """
    def __init__(self, user_data=None, profile_data=None, files=None):
        self.user_form = UserUpdateForm(user_data, instance=self.get_user_instance())
        self.profile_form = ProfileUpdateForm(profile_data, files=files, instance=self.get_profile_instance())

    def get_user_instance(self):
        # Предполагается, что instance будет установлен в представлении
        # Возвращаем None или вызываем ошибку, если instance не установлен
        return getattr(self, '_user_instance', None)

    def get_profile_instance(self):
        # Предполагается, что instance будет установлен в представлении
        # Возвращаем None или вызываем ошибку, если instance не установлен
        return getattr(self, '_profile_instance', None)

    def set_instances(self, user_instance, profile_instance):
        """Устанавливает экземпляры для форм."""
        self._user_instance = user_instance
        self._profile_instance = profile_instance
        # Пересоздаём формы с новыми инстансами
        self.user_form = UserUpdateForm(
            instance=self._user_instance,
            data=self.user_form.data if self.user_form.is_bound else None
        )
        self.profile_form = ProfileUpdateForm(
            instance=self._profile_instance,
            data=self.profile_form.data if self.profile_form.is_bound else None,
            files=self.profile_form.files if self.profile_form.is_bound else None
        )

    def is_valid(self):
        """Проверяет валидность обеих форм."""
        return self.user_form.is_valid() and self.profile_form.is_valid()

    def save(self):
        """Сохраняет обе формы."""
        user = self.user_form.save()
        profile = self.profile_form.save(commit=False)
        profile.user = user # Убедимся, что профиль связан с правильным пользователем
        profile.save()
        return user, profile

class QuestionCreateForm(forms.ModelForm):
    """
    Форма для создания нового вопроса.
    Включает поле для изображения и три поля для начальных вариантов ответа.
    """
    # Добавим поля для первых 3 вариантов ответа (опционально)
    choice1 = forms.CharField(max_length=200, label='Вариант 1', required=False)
    choice2 = forms.CharField(max_length=200, label='Вариант 2', required=False)
    choice3 = forms.CharField(max_length=200, label='Вариант 3', required=False)

    class Meta:
        model = Question
        fields = ['question_text', 'image', 'lifespan_days'] # Включаем image и lifespan_days
        labels = {
            'question_text': 'Текст вопроса',
            'image': 'Изображение к вопросу (опционально)',
            'lifespan_days': 'Время жизни (дней)',
        }
        help_texts = {
            'lifespan_days': 'Сколько дней вопрос будет публичным',
        }

    def save(self, commit=True):
        """
        Переопределяем save, чтобы создать варианты ответа.
        """
        question = super().save(commit=False)
        # В ТЗ не сказано, что вопрос должен быть привязан к пользователю-создателю.
        # Если это не требуется, эту строку можно убрать.
        # if user:
        #     question.author = user # Предполагаем, что в модели Question есть поле author
        if commit:
            question.save()

        # Создаем варианты ответа из формы
        for i in range(1, 4):
            choice_text = self.cleaned_data.get(f'choice{i}')
            if choice_text:
                Choice.objects.create(question=question, choice_text=choice_text)

        return question