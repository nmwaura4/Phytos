from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class ReceivedPredator(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending inspection"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"

    supplier_name = models.CharField(max_length=100)
    supplier_reference = models.CharField(max_length=100, blank=True)
    number_of_tubs = models.PositiveIntegerField()
    batch_number = models.CharField(max_length=100, unique=True)
    received_at = models.DateTimeField(default=timezone.now)

    live_predators = models.PositiveIntegerField()
    live_preys = models.PositiveIntegerField()
    dead_predators = models.PositiveIntegerField(default=0)
    dead_preys = models.PositiveIntegerField(default=0)
    contaminant = models.CharField(max_length=100, blank=True)
    contamination_level = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
    )
    mortality_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        editable=False,
        default=0,
    )

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )
    comments = models.TextField(blank=True)

    class Meta:
        ordering = ["-received_at"]

    def clean(self):
        super().clean()
        if self.number_of_tubs < 1:
            raise ValidationError({"number_of_tubs": "A reception must contain at least one tub."})

    def calculate_mortality_rate(self):
        total_population = (
            self.live_predators
            + self.dead_predators
            + self.live_preys
            + self.dead_preys
        )
        if total_population == 0:
            return 0
        return round((self.dead_predators / total_population) * 100, 2)

    @property
    def prey_mortality_rate(self):
        total_population = (
            self.live_predators
            + self.dead_predators
            + self.live_preys
            + self.dead_preys
        )
        if total_population == 0:
            return 0
        return round((self.dead_preys / total_population) * 100, 2)

    def save(self, *args, **kwargs):
        self.full_clean()
        self.mortality_rate = self.calculate_mortality_rate()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.batch_number} - {self.supplier_name}"