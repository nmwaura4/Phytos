from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0002_improve_received_predator'),
    ]

    operations = [
        migrations.AddField(
            model_name='receivedpredator',
            name='contaminant',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='receivedpredator',
            name='contamination_level',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5),
        ),
    ]
