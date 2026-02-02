from django.urls import path, include
from rest_framework import routers

from theatre.views import ReservationViewSet, ActorViewSet, PlayViewSet, PerformanceViewSet, TicketViewSet, \
    TheatreHallViewSet, GenreViewSet

app_name = "theatre"

router = routers.DefaultRouter()
router.register("actors", ActorViewSet)
router.register("plays", PlayViewSet)
router.register("reservations", ReservationViewSet)
router.register("performances", PerformanceViewSet)
router.register("theatre_halls", TheatreHallViewSet)
router.register("genres", GenreViewSet)


urlpatterns = [path("", include(router.urls))]
