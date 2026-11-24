from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('cajeros', '0003_bitacoraauditoria_alter_cajero_estado_and_more')]
    operations = [migrations.AddField(model_name='personaljefatura', name='password_hash', field=models.CharField(blank=True, default='', max_length=128))]
