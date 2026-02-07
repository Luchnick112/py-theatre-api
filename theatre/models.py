import pathlib
import uuid

from django.conf import settings
from django.db import models
from django.utils.text import slugify
from rest_framework.exceptions import ValidationError


class Actor(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)

    def __str__(self):
        return self.first_name + " " + self.last_name

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class Genre(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name_plural = "genres"

    def __str__(self):
        return self.name


def play_image_path(instance: "Play" , filename: str) -> pathlib.Path:
    filename = (
        f"{slugify(instance.title)}-{uuid.uuid4()}"
        + pathlib.Path(filename).suffix
    )
    return pathlib.Path("uploads/performances/") / pathlib.Path(filename)


class Play(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField()
    genres = models.ManyToManyField(Genre)
    actors = models.ManyToManyField(Actor)
    image = models.ImageField(
        upload_to=play_image_path,
        null=True,
        blank=True
    )

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title

class TheatreHall(models.Model):
    name = models.CharField(max_length=100)
    rows = models.PositiveIntegerField()
    seats_in_row = models.PositiveIntegerField()

    @property
    def capacity(self) -> int:
        return self.rows * self.seats_in_row

    def __str__(self):
        return self.name


class Performance(models.Model):
    show_time = models.DateTimeField()
    play = models.ForeignKey(Play, on_delete=models.CASCADE)
    theatre_hall = models.ForeignKey(
        TheatreHall,
        on_delete=models.CASCADE
    )


class Reservation(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return str(self.created_at)


class Ticket(models.Model):
    row = models.IntegerField()
    seat = models.IntegerField()
    performance = models.ForeignKey(
        Performance,
        on_delete=models.CASCADE,
        related_name="tickets"
    )
    reservation = models.ForeignKey(
        Reservation,
        on_delete=models.CASCADE,
        related_name="tickets"
    )

    @staticmethod
    def validate_seat(
            seat: int,
            num_seats: int,
            field_name: str,
            error_to_raise
    ):
        if not (1 <= seat <= num_seats):
            raise error_to_raise(
                {
                    field_name: f"{field_name} "
                                f"must be in range [1, {num_seats}], "
                                f"not {seat}",
                }
            )

    def clean(self):
        Ticket.validate_seat(
            self.row,
            self.performance.theatre_hall.rows,
            "row", ValidationError
        )
        Ticket.validate_seat(
            self.seat,
            self.performance.theatre_hall.seats_in_row,
            "seat",
            ValidationError
        )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


    def __str__(self):
        return (
            f"{str(self.performance)} (row: {self.row}, seat: {self.seat})"
        )

    class Meta:
        unique_together = ("performance", "row", "seat")
