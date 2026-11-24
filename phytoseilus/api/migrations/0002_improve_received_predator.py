from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='receivedpredator',
            old_name='Batch_number',
            new_name='batch_number',
        ),
        migrations.AlterField(
            model_name='receivedpredator',
            name='batch_number',
            field=models.CharField(max_length=100, unique=True),
        ),
        migrations.AddField(
            model_name='receivedpredator',
            name='supplier_reference',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='receivedpredator',
            name='received_at',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AddField(
            model_name='receivedpredator',
            name='status',
            field=models.CharField(choices=[('pending', 'Pending inspection'), ('accepted', 'Accepted'), ('rejected', 'Rejected')], default='pending', max_length=10),
        ),
        migrations.AddField(
            model_name='receivedpredator',
            name='comments',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='receivedpredator',
            name='number_of_tubs',
            field=models.PositiveIntegerField(),
        ),
        migrations.AlterField(
            model_name='receivedpredator',
            name='live_predators',
            field=models.PositiveIntegerField(),
        ),
        migrations.AlterField(
            model_name='receivedpredator',
            name='live_preys',
            field=models.PositiveIntegerField(),
        ),
        migrations.AlterField(
            model_name='receivedpredator',
            name='dead_predators',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='receivedpredator',
            name='dead_preys',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='receivedpredator',
            name='mortality_rate',
            field=models.DecimalField(decimal_places=2, default=0, editable=False, max_digits=5),
        ),
        migrations.AlterModelOptions(
            name='receivedpredator',
            options={'ordering': ['-received_at']},
        ),
    ]
