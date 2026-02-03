from django.db import transaction
from django.db.models.fields import CharField
from rest_framework import serializers

from theatre.models import (
    Actor,
    Play,
    Performance,
    Genre,
    TheatreHall,
    Ticket,
    Reservation
)


class ActorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Actor
        fields = ("id", "first_name", "last_name")


class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ("id", "name")


class PlaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Play
        fields = ("id", "title", "description")


class PlayDetailSerializer(serializers.ModelSerializer):
    genres = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field="name"
    )
    actors = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field="full_name"
    )

    class Meta:
        model = Play
        fields = ("id", "title", "description", "genres", "actors")


class TheatreHallSerializer(serializers.ModelSerializer):
    class Meta:
        model = TheatreHall
        fields = ("id", "name", "rows", "seats_in_row")


class TheatreHallDetailSerializer(serializers.ModelSerializer):
    plays = serializers.SerializerMethodField()

    class Meta:
        model = TheatreHall
        fields = ("id", "name", "rows", "seats_in_row", "plays")

    def get_plays(self, obj):
        performances = Performance.objects.filter(theatre_hall=obj)
        return PlayDetailSerializer([performance.play for performance in performances], many=True).data



class PerformanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Performance
        fields = ("id", "play", "theatre_hall", "show_time")


class PerformanceListSerializer(serializers.ModelSerializer):
    show_time = serializers.DateTimeField(format="%d.%m.%Y %H:%M")
    theatre_hall = serializers.CharField(read_only=True, source="theatre_hall.name")
    play = serializers.CharField(read_only=True, source="play.title")

    class Meta:
        model = Performance
        fields = ("id", "play", "theatre_hall", "show_time")


class PerformanceDetailSerializer(PerformanceListSerializer):
    play = PlayDetailSerializer(read_only=True)

    class Meta:
        model = Performance
        fields = ("id", "play", "theatre_hall", "show_time")


class TicketSerializer(serializers.ModelSerializer):

    class Meta:
        model = Ticket
        fields = ("id", "row", "seat", "performance", "reservation")

    def validate(self, attrs):
        Ticket.validate_seat(
            attrs["seat"], attrs["trip"].bus.num_seats, serializers.ValidationError
        )


class ReservationSerializer(serializers.ModelSerializer):
    tickets = serializers.TicketSerializer(many=True)

    class Meta:
        model = Reservation
        fields = ("id", "created_at", "user", "tickets")

    def create(self, validated_data):
        with transaction.atomic():
            tickets_data = validated_data.pop("tickets")
            order = Reservation.objects.create(**validated_data)
            for ticket_data in tickets_data:
                Ticket.objects.create(order=order, **ticket_data)
            return order
