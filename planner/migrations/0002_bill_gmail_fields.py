from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("planner", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="bill",
            name="email_subject",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="bill",
            name="gmail_message_id",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="bill",
            name="source",
            field=models.CharField(choices=[("manual", "Manual"), ("gmail", "Gmail")], default="manual", max_length=20),
        ),
    ]
