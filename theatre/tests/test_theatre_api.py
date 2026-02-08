import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from theatre.models import Play, Performance, TheatreHall, Genre, Actor
from theatre.serializers import (
    PlaySerializer,
    PlayDetailSerializer,
)

PLAY_URL = reverse("theatre:play-list")
PERFORMANCE_URL = reverse("theatre:performance-list")


def sample_play(**params):
    defaults = {
        "title": "Sample play",
        "description": "Sample description",
    }
    defaults.update(params)

    return Play.objects.create(**defaults)


def sample_genre(**params):
    defaults = {
        "name": "Drama",
    }
    defaults.update(params)

    return Genre.objects.create(**defaults)


def sample_actor(**params):
    defaults = {"first_name": "George", "last_name": "Clooney"}
    defaults.update(params)

    return Actor.objects.create(**defaults)


def sample_performance(**params):
    theatre_hall = TheatreHall.objects.create(name="Blue", rows=20, seats_in_row=20)

    defaults = {
        "show_time": "2022-06-02 14:00:00",
        "play": None,
        "theatre_hall": theatre_hall,
    }
    defaults.update(params)

    return Performance.objects.create(**defaults)


def image_upload_url(play_id):
    """Return URL for recipe image upload"""
    return reverse("theatre:play-upload-image", args=[play_id])


def detail_url(play_id):
    return reverse("theatre:play-detail", args=[play_id])


class PlayImageUploadTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)
        self.play = sample_play()
        self.genre = sample_genre()
        self.actor = sample_actor()
        self.performance = sample_performance(play=self.play)

    def tearDown(self):
        self.play.image.delete()

    def test_upload_image_to_play(self):
        """Test uploading an image to play"""
        url = image_upload_url(self.play.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(url, {"image": ntf}, format="multipart")
        self.play.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data)
        self.assertTrue(os.path.exists(self.play.image.path))

    def test_upload_image_bad_request(self):
        """Test uploading an invalid image"""
        url = image_upload_url(self.play.id)
        res = self.client.post(url, {"image": "not image"}, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_image_to_play_list(self):
        url =  PLAY_URL
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(
                url,
                {
                    "title": "Title",
                    "description": "Description",
                    "image": ntf,
                },
                format="multipart",
            )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        play = Play.objects.get(title="Title")
        self.assertFalse(play.image)

    def test_image_url_is_shown_on_play_detail(self):
        url = image_upload_url(self.play.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(detail_url(self.play.id))

        self.assertIn("image", res.data)

    def test_image_url_is_shown_on_play_list(self):
        url = image_upload_url(self.play.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(PLAY_URL)
        self.assertGreater(len(res.data["results"]), 0)
        self.assertIn("image", res.data["results"][0].keys())

    def test_image_url_is_shown_on_performance_detail(self):
        url = image_upload_url(self.play.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")

        detail_session_url = reverse(
            "theatre:performance-detail", args=[self.performance.id]
        )
        res = self.client.get(detail_session_url)
        self.assertIn("image", res.data["play"].keys())


class PublicPlayApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get( PLAY_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivatePlayApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user("user@test.com", "password123")
        self.client.force_authenticate(self.user)

    def test_retrieve_play_list(self):
        sample_play(title="Play 1")
        sample_play(title="Play 2")
        res = self.client.get( PLAY_URL)
        plays = Play.objects.all()
        serializer = PlaySerializer(plays, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["results"], serializer.data)

    def test_retrieve_play_detail(self):
        play = sample_play()
        play.genres.add(sample_genre())
        play.actors.add(sample_actor())
        res = self.client.get(detail_url(play.id))
        serializer = PlayDetailSerializer(play)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_play_filter_by_title(self):
        play_1 = sample_play(title="play 1")
        play_2 = sample_play(title="play 2")
        res = self.client.get(PLAY_URL, {"title": "play 1"})
        serializer1 = PlaySerializer(play_1)
        serializer2 = PlaySerializer(play_2)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer1.data, res.data["results"])
        self.assertNotIn(serializer2.data, res.data["results"])

    def test_play_filter_by_genre(self):
        play_1 = sample_play(title="play 1")
        play_2 = sample_play(title="play 2")
        genre_1 = sample_genre(name="Drama")
        genre_2 = sample_genre(name="Fiction")
        play_1.genres.add(genre_1)
        play_2.genres.add(genre_2)
        res = self.client.get( PLAY_URL, {"genres": genre_1.id})
        serializer1 = PlaySerializer(play_1)
        serializer2 = PlaySerializer(play_2)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer1.data, res.data["results"])
        self.assertNotIn(serializer2.data, res.data["results"])

    def test_play_filter_by_actor(self):
        play_1 = sample_play(title="play 1")
        play_2 = sample_play(title="play 2")
        actor_1 = sample_actor(first_name="George", last_name="Clooney")
        actor_2 = sample_actor(first_name="Bradley", last_name="Cooper")
        play_1.actors.add(actor_1)
        play_2.actors.add(actor_2)
        res = self.client.get( PLAY_URL, {"actors": actor_1.id})
        serializer1 = PlaySerializer(play_1)
        serializer2 = PlaySerializer(play_2)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer1.data, res.data["results"])
        self.assertNotIn(serializer2.data, res.data["results"])

    def test_create_play_forbidden_for_regular_user(self):
        genre = sample_genre()
        actor = sample_actor()
        payload = {
            "title": "play 1",
            "genres": [genre.id],
            "actors": [actor.id],
            "description": "play description",
            "duration": 90,
        }

        res = self.client.post(PLAY_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminPlayApiTests(TestCase):
    """Test that admin user can create and manage plays successfully"""

    def setUp(self):
        self.client = APIClient()
        self.admin_user = get_user_model().objects.create_superuser(
            "admin@test.com",
            "password123"
        )
        self.client.force_authenticate(self.admin_user)

    def test_create_play_successful(self):
        """Test that an admin can successfully create a play"""
        genre = sample_genre(name="Sci-Fi")
        actor = sample_actor(first_name="Keanu", last_name="Reeves")

        payload = {
            "title": "The Matrix",
            "description": "A sci-fi classic",
            "genres": [genre.id],
            "actors": [actor.id],
        }

        res = self.client.post(PLAY_URL, payload)

        # Check response
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        # Verify the play was created correctly in the DB
        play = Play.objects.get(id=res.data["id"])
        self.assertEqual(play.title, payload["title"])
        self.assertEqual(play.description, payload["description"])


    def test_create_play_missing_required_field(self):
        """Test that creating a play fails if required fields are missing"""
        payload = {
            "description": "No title provided",
            "duration": 90,
        }

        res = self.client.post(PLAY_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("title", res.data)
