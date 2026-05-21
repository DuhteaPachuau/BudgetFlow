from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ("planner", "0002_bill_gmail_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="Budget",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("category", models.CharField(max_length=80)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("month", models.DateField(default=django.utils.timezone.localdate)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="budgets", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-month", "category"],
                "unique_together": {("user", "category", "month")},
            },
        ),
    ]
