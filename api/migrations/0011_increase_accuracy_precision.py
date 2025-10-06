from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0010_update_location_precision'),
    ]

    operations = [
        migrations.AlterField(
            model_name='location',
            name='accuracy',
            field=models.DecimalField(null=True, blank=True, max_digits=20, decimal_places=8, help_text='GPS accuracy in meters'),
        ),
        migrations.AlterField(
            model_name='anonymouslocation',
            name='accuracy',
            field=models.DecimalField(null=True, blank=True, max_digits=20, decimal_places=8, help_text='Location accuracy in meters'),
        ),
        migrations.AlterField(
            model_name='locationupdate',
            name='accuracy',
            field=models.DecimalField(max_digits=20, decimal_places=8, help_text='Location accuracy in meters'),
        ),
    ]
