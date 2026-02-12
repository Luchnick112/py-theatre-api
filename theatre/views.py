from datetime import datetime

from django.db.models import F, Count
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from theatre.models import (
    Genre,
    Actor,
    Play,
    Performance,
    TheatreHall,
    Reservation
)
from theatre.serializers import (
    GenreSerializer,
    ActorSerializer,
    PerformanceSerializer,
    TheatreHallSerializer,
    ReservationSerializer,
    PlaySerializer,
    PlayDetailSerializer,
    PerformanceListSerializer,
    PerformanceDetailSerializer,
    TheatreHallDetailSerializer,
    ReservationListSerializer,
    PlayImageSerializer,
)


class GenreViewSet(viewsets.ModelViewSet):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer


class ActorViewSet(viewsets.ModelViewSet):
    queryset = Actor.objects.all()
    serializer_class = ActorSerializer


class PlayViewSet(viewsets.ModelViewSet):
    queryset = Play.objects.all()
    serializer_class = PlaySerializer

    @staticmethod
    def _params_to_ints(query_string):
        """Converts a string of format '1,2,3' to a list of integers [1,2,3]."""
        return [int(str_id) for str_id in query_string.split(",")]

    def get_serializer_class(self):
        if self.action == "list":
            return PlaySerializer

        elif self.action == "retrieve":
            return PlayDetailSerializer

        elif self.action == "upload_image":
            return PlayImageSerializer

        return PlaySerializer

    def get_queryset(self):
        queryset = self.queryset

        actors = self.request.query_params.get("actors")
        genres = self.request.query_params.get("genres")
        title = self.request.query_params.get("title")

        if actors:
            actors = self._params_to_ints(actors)
            queryset = queryset.filter(actors__id__in=actors)

        if genres:
            genres = self._params_to_ints(genres)
            queryset = queryset.filter(genres__id__in=genres)

        if title:
            queryset = queryset.filter(title__icontains=title)

        return queryset.distinct()

    @action(
        methods=["post"],
        detail=True,
        permission_classes=[IsAdminUser],
        url_path="upload-image"
    )
    def upload_image(self, request, pk=None):
        movie = self.get_object()
        serializer = self.get_serializer(movie, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "actors",
                required=False,
                type=OpenApiTypes.INT,
                description="Filter by theatre actors ID (ex. ?actors=3)",
            ),
            OpenApiParameter(
                "genres",
                required=False,
                type=OpenApiTypes.INT,
                description="Filter by genres IDs (ex. ?genres=2)",
            ),
            OpenApiParameter(
                "titles",
                required=False,
                type=OpenApiTypes.STR,
                description="Filter by play title (ex. ?titles='gamlet')",
            ),
        ],
        description="Retrieve a list of theatre plays with optional filters.",
        responses={200: PlaySerializer},
    )
    def list(self, request, *args, **kwargs):
        """Get list of movie sessions"""
        return super().list(request, *args, **kwargs)

class PerformanceViewSet(viewsets.ModelViewSet):
    queryset = Performance.objects.all()
    serializer_class = PerformanceSerializer

    @staticmethod
    def _params_to_ints(query_string):
        """Converts a string of format '1,2,3' to a list of integers [1,2,3]."""
        return [int(str_id) for str_id in query_string.split(",")]

    def get_serializer_class(self):
        if self.action == "list":
            return PerformanceListSerializer

        if self.action == "retrieve":
            return PerformanceDetailSerializer

        return PerformanceListSerializer

    def get_queryset(self):
        queryset = self.queryset
        date = self.request.query_params.get("date")
        play = self.request.query_params.get("play")

        if play:
            play = self._params_to_ints(play)
            queryset = queryset.filter(play__id__in=play)
        if date:
            try:
                date = datetime.strptime(date, "%Y-%m-%d").date()
                queryset = queryset.filter(show_time__date=date)
            except ValueError:
                pass

        if self.action == "list":
            queryset = (queryset
                        .select_related("play", "theatre_hall")
                        .annotate(tickets_available= (F("theatre_hall__rows") * F("theatre_hall__seats_in_row")) - Count("tickets"))
                        )

        return queryset.distinct()

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "play",
                required=False,
                type=OpenApiTypes.INT,
                description="Filter by theatre play ID (ex. ?play=3)",
            ),
            OpenApiParameter(
                "date",
                required=False,
                type=OpenApiTypes.DATE,
                description="Filter by date of performance (ex. ?date=2026-02-21)",
            ),
        ],
        description="Retrieve a list of theatre performances with optional filters.",
        responses={200: PerformanceListSerializer},
    )
    def list(self, request, *args, **kwargs):
        """Get list of movie sessions"""
        return super().list(request, *args, **kwargs)


class TheatreHallViewSet(viewsets.ModelViewSet):
    queryset = TheatreHall.objects.all()
    serializer_class = TheatreHallSerializer

    def get_serializer_class(self):
        if self.action == "list":
            return TheatreHallSerializer

        if self.action == "retrieve":
            return TheatreHallDetailSerializer

        return TheatreHallSerializer


class ReservationViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    GenericViewSet,
):
    queryset = Reservation.objects.prefetch_related(
        "tickets__performance__theatre_hall",
        "tickets__performance__play"
    ).select_related("user")
    serializer_class = ReservationSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        queryset = self.queryset.filter(user=self.request.user)

        if self.action == "list":
            queryset = queryset.prefetch_related("tickets__performance__play")
        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_serializer_class(self):
        if self.action == "list":
            return ReservationListSerializer

        return ReservationSerializer
