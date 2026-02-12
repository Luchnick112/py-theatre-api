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


class PlayImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Play
        fields = ("id", "image")


class PlaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Play
        fields = ("id", "title", "description", "image")
        read_only_fields = ("image",)


class PlayDetailSerializer(serializers.ModelSerializer):
    genres = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field="name"
    )
    actors = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field="full_name"
    )

    class Meta:
        model = Play
        fields = ("id", "title", "description", "genres", "actors", "image")


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
    tickets_available = serializers.IntegerField(read_only=True)

    class Meta:
        model = Performance
        fields = ("id", "play", "theatre_hall", "show_time", "tickets_available")


class PerformanceDetailSerializer(PerformanceListSerializer):
    play = PlayDetailSerializer(read_only=True)
    taken_seats = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field="seat",
        source="tickets",
    )

    class Meta:
        model = Performance
        fields = ("id", "play", "theatre_hall", "show_time", "taken_seats")


class TicketSerializer(serializers.ModelSerializer):
    performance = PerformanceListSerializer(read_only=True)
    performance_id = serializers.PrimaryKeyRelatedField(
        source="performance",
        queryset=Performance.objects.all(),
        write_only=True
    )

    class Meta:
        model = Ticket
        fields = ("id", "row", "seat", "performance_id", "performance", "reservation")
        read_only_fields = ("reservation",)

    def validate(self, attrs):
        performance = attrs.get("performance")
        if performance:
            Ticket.validate_seat(
                attrs["seat"],
                performance.theatre_hall.seats_in_row,
                "seat",
                serializers.ValidationError
            )
            Ticket.validate_seat(
                attrs["row"],
                performance.theatre_hall.rows,
                "row",
                serializers.ValidationError
            )
        return attrs


class ReservationSerializer(serializers.ModelSerializer):
    tickets = TicketSerializer(many=True, allow_empty=False)

    class Meta:
        model = Reservation
        fields = ("id", "created_at", "user", "tickets")
        read_only_fields = ("user", "created_at")

    def create(self, validated_data):
        with transaction.atomic():
            tickets_data = validated_data.pop("tickets")
            reservation = Reservation.objects.create(**validated_data)
            for ticket_data in tickets_data:
                Ticket.objects.create(reservation=reservation, **ticket_data)
            return reservation


class TicketListSerializer(TicketSerializer):
    performance = PerformanceListSerializer(read_only=True)


class ReservationListSerializer(ReservationSerializer):
    tickets = TicketListSerializer(many=True, read_only=False)
