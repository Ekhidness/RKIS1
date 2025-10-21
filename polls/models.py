# polls/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import datetime

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    name = models.CharField(max_length=100, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)

    def __str__(self):
        return f"{self.user.username}'s profile"

class Question(models.Model):
    question_text = models.CharField(max_length=200)
    pub_date = models.DateTimeField('date published', auto_now_add=True) # Исправлено: добавлен auto_now_add=True
    image = models.ImageField(upload_to='question_images/', blank=True, null=True)
    lifespan_days = models.PositiveIntegerField(default=7, help_text="Сколько дней вопрос будет публичным")

    def was_published_recently(self):
        return self.pub_date >= timezone.now() - datetime.timedelta(days=1)

    def is_active(self):
        """
        Проверяет, активен ли вопрос (не истёк ли срок жизни).
        Возвращает True, если вопрос ещё публично доступен.
        """
        now = timezone.now()
        return now <= self.pub_date + datetime.timedelta(days=self.lifespan_days)

    def __str__(self):
        return self.question_text

class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choice_set')
    choice_text = models.CharField(max_length=200)
    votes = models.IntegerField(default=0)

    def __str__(self):
        return self.choice_text

class Vote(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    choice = models.ForeignKey(Choice, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('user', 'question')

    def __str__(self):
        return f"{self.user.username} voted for {self.choice.choice_text} in {self.question.question_text}"