# API tests
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

User = get_user_model()


class UserRegistrationTest(TestCase):
    """Test user registration"""
    
    def setUp(self):
        self.client = APIClient()
    
    def test_register_donator(self):
        """Test registering a donator"""
        data = {
            'email': 'donator@example.com',
            'password': 'TestPass123!',
            'password2': 'TestPass123!',
            'first_name': 'John',
            'last_name': 'Doe',
            'role': 'donator'
        }
        
        response = self.client.post('/api/auth/register/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('tokens', response.data)
        self.assertEqual(response.data['user']['role'], 'donator')
    
    def test_register_affected(self):
        """Test registering an affected user"""
        data = {
            'email': 'affected@example.com',
            'password': 'TestPass123!',
            'password2': 'TestPass123!',
            'first_name': 'Jane',
            'last_name': 'Smith',
            'role': 'affected'
        }
        
        response = self.client.post('/api/auth/register/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['user']['role'], 'affected')


class AuthenticationTest(TestCase):
    """Test authentication"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='TestPass123!',
            first_name='Test',
            last_name='User',
            role='donator'
        )
    
    def test_login_success(self):
        """Test successful login"""
        data = {
            'email': 'test@example.com',
            'password': 'TestPass123!'
        }
        
        response = self.client.post('/api/auth/login/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('tokens', response.data)
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        data = {
            'email': 'test@example.com',
            'password': 'WrongPassword'
        }
        
        response = self.client.post('/api/auth/login/', data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
