# Generated for the Budget Planner starter app.
from django.conf import settings
import django.contrib.auth.models
import django.contrib.auth.validators
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import planner.models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="CustomUser",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("password", models.CharField(max_length=128, verbose_name="password")),
                ("last_login", models.DateTimeField(blank=True, null=True, verbose_name="last login")),
                ("is_superuser", models.BooleanField(default=False, help_text="Designates that this user has all permissions without explicitly assigning them.", verbose_name="superuser status")),
                ("username", models.CharField(blank=True, max_length=150)),
                ("first_name", models.CharField(blank=True, max_length=150, verbose_name="first name")),
                ("last_name", models.CharField(blank=True, max_length=150, verbose_name="last name")),
                ("is_staff", models.BooleanField(default=False, help_text="Designates whether the user can log into this admin site.", verbose_name="staff status")),
                ("is_active", models.BooleanField(default=True, help_text="Designates whether this user should be treated as active. Unselect this instead of deleting accounts.", verbose_name="active")),
                ("date_joined", models.DateTimeField(default=django.utils.timezone.now, verbose_name="date joined")),
                ("name", models.CharField(max_length=150)),
                ("email", models.EmailField(max_length=254, unique=True)),
                ("groups", models.ManyToManyField(blank=True, help_text="The groups this user belongs to.", related_name="user_set", related_query_name="user", to="auth.group", verbose_name="groups")),
                ("user_permissions", models.ManyToManyField(blank=True, help_text="Specific permissions for this user.", related_name="user_set", related_query_name="user", to="auth.permission", verbose_name="user permissions")),
            ],
            options={
                "verbose_name": "user",
                "verbose_name_plural": "users",
                "abstract": False,
            },
            managers=[
                ("objects", planner.models.CustomUserManager()),
            ],
        ),
        migrations.CreateModel(
            name="Bill",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("service", models.CharField(max_length=120)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("due_date", models.DateField()),
                ("category", models.CharField(max_length=80)),
                ("is_paid", models.BooleanField(default=False)),
                ("is_recurring", models.BooleanField(default=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="bills", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["is_paid", "due_date", "name"]},
        ),
        migrations.CreateModel(
            name="Expense",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("category", models.CharField(max_length=80)),
                ("date", models.DateField(default=django.utils.timezone.localdate)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="expenses", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-date", "-id"]},
        ),
        migrations.CreateModel(
            name="Income",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source", models.CharField(max_length=120)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("date", models.DateField(default=django.utils.timezone.localdate)),
                ("month", models.CharField(blank=True, max_length=20)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="incomes", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-date", "-id"]},
        ),
    ]
