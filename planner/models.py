from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone


class CustomUserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, username=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    username = models.CharField(max_length=150, blank=True)
    name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    objects = CustomUserManager()

    def save(self, *args, **kwargs):
        self.username = self.email
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email


class Income(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="incomes")
    source = models.CharField(max_length=120)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField(default=timezone.localdate)
    month = models.CharField(max_length=20, blank=True)

    class Meta:
        ordering = ["-date", "-id"]

    def save(self, *args, **kwargs):
        self.month = self.date.strftime("%B %Y")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.source} - {self.amount}"


class Expense(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="expenses")
    name = models.CharField(max_length=120)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    category = models.CharField(max_length=80)
    date = models.DateField(default=timezone.localdate)

    class Meta:
        ordering = ["-date", "-id"]

    def __str__(self):
        return f"{self.name} - {self.amount}"


class Bill(models.Model):
    SOURCE_CHOICES = [
        ("manual", "Manual"),
        ("gmail", "Gmail"),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="bills")
    name = models.CharField(max_length=120)
    service = models.CharField(max_length=120)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    due_date = models.DateField()
    category = models.CharField(max_length=80)
    is_paid = models.BooleanField(default=False)
    is_recurring = models.BooleanField(default=True)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default="manual")
    gmail_message_id = models.CharField(max_length=120, blank=True)
    email_subject = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["is_paid", "due_date", "name"]

    @property
    def alert_level(self):
        today = timezone.localdate()
        days = (self.due_date - today).days
        if self.is_paid:
            return "paid"
        if days < 0:
            return "overdue"
        if days <= 3:
            return "soon"
        return "normal"

    def __str__(self):
        return f"{self.name} - {self.amount}"


class Budget(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="budgets")
    category = models.CharField(max_length=80)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    month = models.DateField(default=timezone.localdate)

    class Meta:
        ordering = ["-month", "category"]
        unique_together = ("user", "category", "month")

    def save(self, *args, **kwargs):
        self.month = self.month.replace(day=1)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.category} budget - {self.amount}"
