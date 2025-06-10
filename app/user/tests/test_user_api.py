"""
Tests for user API.
"""


from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status


CREATE_USER_URL = reverse("user:create")
TOKEN_URL = reverse("user:token")
ME_URL = reverse("user:me")


def create_user(**kwargs):
    """Create and return a new user."""
    return get_user_model().objects.create_user(**kwargs)


class PublicUserApiTests(TestCase):
    """Test public feature of the user API."""

    def setUp(self):
        self.client = APIClient()

    def test_create_user_success(self):
        """Test creating user is successful."""
        payload = {
            "email": "test@example.com",
            "password": "testpass123",
            "name": "Test Name"
        }
        res = self.client.post(CREATE_USER_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        user = get_user_model().objects.get(email=payload['email'])
        self.assertTrue(user.check_password(payload['password']))
        self.assertNotIn('password', res.data)

    def test_user_with_email_exists_error(self):
        """Test error return if user with email exists"""
        payload = {
            "email": "test@example.com",
            "password": "testpass123",
            "name": "Test Name"
        }
        create_user(**payload)
        res = self.client.post(CREATE_USER_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_too_short_error(self):
        """Test error is returned if password length is less than 5 chars"""
        payload = {
            "email": "test@example.com",
            "password": "pa",
            "name": "Test name"
        }
        res = self.client.post(CREATE_USER_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        user_exists = get_user_model().objects.filter(
            email=payload['email']
        ).exists()
        self.assertFalse(user_exists)

    def test_create_token_for_user(self):
        """Test generates token for a valid credentials."""
        user_details = {
            "name": "Test Name",
            "email": "test@example.com",
            "password": "testpass123",
        }
        create_user(**user_details)
        payload = {
            "email": user_details['email'],
            "password": user_details['password']
        }
        res = self.client.post(TOKEN_URL, payload)

        self.assertIn('token', res.data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_create_token_bad_credentials(self):
        """Test an error on creating token for invalid credentials."""
        user_detail = {
            "email": "test@example.com",
            "password": "testpass123",
        }
        create_user(**user_detail)
        payload = {
            "email": "wrong@example.com",
            "password": "testpass123"
        }
        res = self.client.post(TOKEN_URL, payload)

        self.assertNotIn('token', res.data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_token_blank_password(self):
        """Test an error on creating token with blank password."""
        user_details = {
            "email": "test@example.com",
            "password": "testpass123"
        }
        create_user(**user_details)
        payload = {
            "email": user_details['email'],
            "password": " "
        }
        res = self.client.post(TOKEN_URL, payload)

        self.assertNotIn('token', res.data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_user_unathorized(self):
        """Test authentication is required for a user."""
        res = self.client.get(ME_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateUserAPITests(TestCase):
    """Test private feature of the user API."""

    def setUp(self):
        self.user = create_user(
            email="test@example.com",
            password="testpass123",
            name="Test Name"
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrieve_user_profile(self):
        """Test retrieving profile for logged in user."""
        res = self.client.get(ME_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, {
            "name": self.user.name,
            "email": self.user.email
        })

    def test_me_post_not_allowed(self):
        """Test post method not allowed to me endpoint."""
        res = self.client.post(ME_URL, {})

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_update_user_profile(self):
        """Test updating profile for authenticated user."""
        payload = {
            "name": "Updated Name",
            "password": "newpass123"
        }

        res = self.client.patch(ME_URL, payload)

        self.user.refresh_from_db()
        self.assertEqual(self.user.name, payload['name'])
        self.assertTrue(self.user.check_password(payload['password']))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
