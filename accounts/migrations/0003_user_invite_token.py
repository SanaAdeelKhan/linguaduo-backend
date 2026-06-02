from django.db import migrations, models
import uuid

def gen_unique_invite_tokens(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    for user in User.objects.all():
        user.invite_token = uuid.uuid4()
        user.save(update_fields=['invite_token'])

class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_user_email_verify_token_user_is_email_verified_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='invite_token',
            field=models.UUIDField(default=uuid.uuid4, editable=False, null=True),
        ),
        migrations.RunPython(gen_unique_invite_tokens),
        migrations.AlterField(
            model_name='user',
            name='invite_token',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
