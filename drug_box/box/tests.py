"""
Test cases for Drug Box API endpoints
"""
from datetime import date
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from .models import User, DosageSchedule, EventLog


class TestAddUserFromDeviceAPIView(TestCase):
    """Test cases for AddUserFromDeviceAPIView endpoint"""
    
    def setUp(self):
        """Setup test data before each test method"""
        self.client = APIClient()
        self.url = reverse('add-user')
        self.valid_data = {
            'rfid_code': 'RFID123456',
            'fingerprint_id': 12345,
            'name': 'Test User'
        }
    
    def test_add_user_success(self):
        """Test successful user creation"""
        response = self.client.post(self.url, self.valid_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'success')
        self.assertEqual(response.data['message'], 'User added successfully')
        
        # Verify user was created in database
        user = User.objects.get(rfid_code='RFID123456')
        self.assertEqual(user.name, 'Test User')
        self.assertEqual(user.fingerprint_id, 12345)
        
        # Verify event log was created
        event_log = EventLog.objects.filter(event_type='ADD_USER').last()
        self.assertIsNotNone(event_log)
        self.assertEqual(event_log.status, 'Success')
        self.assertEqual(event_log.user, user)
    
    def test_add_user_missing_rfid(self):
        """Test user creation with missing RFID code"""
        data = {
            'fingerprint_id': 12345,
            'name': 'Test User'
        }
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['message'], 'Missing required fields')
        
        # Verify no user was created
        self.assertEqual(User.objects.count(), 0)
        
        # Verify event log was created
        event_log = EventLog.objects.filter(event_type='ADD_USER').last()
        self.assertIsNotNone(event_log)
        self.assertEqual(event_log.status, 'Failed')
    
    def test_add_user_duplicate_rfid(self):
        """Test user creation with duplicate RFID code"""
        # Create first user
        User.objects.create(
            name='First User',
            rfid_code='RFID123456',
            fingerprint_id=12345
        )
        
        # Try to create second user with same RFID but different fingerprint
        duplicate_data = {
            'rfid_code': 'RFID123456',  # Same RFID
            'fingerprint_id': 67890,    # Different fingerprint
            'name': 'Second User'
        }
        response = self.client.post(self.url, duplicate_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['message'], 'RFID or fingerprint already exists')
        
        # Verify only one user exists
        self.assertEqual(User.objects.count(), 1)


class TestHandleRequestAPIView(TestCase):
    """Test cases for HandleRequestAPIView endpoint"""
    
    def setUp(self):
        """Setup test data before each test method"""
        self.client = APIClient()
        self.url = reverse('handle-request')
        
        # Create test user
        self.user = User.objects.create(
            name='Test User',
            rfid_code='RFID123456',
            fingerprint_id=12345
        )
        
        # Create test dosage schedule
        self.dosage_schedule = DosageSchedule.objects.create(
            user=self.user,
            date=date.today(),
            dosage=2.5,
            used=False
        )
        
        self.valid_data = {
            'rfid_code': 'RFID123456',
            'fingerprint_id': 12345,
            'timestamp': f'{date.today()}T10:30:00'
        }
    
    def test_handle_request_success(self):
        """Test successful request handling"""
        response = self.client.post(self.url, self.valid_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')
        self.assertEqual(response.data['dosage'], 2.5)
        
        # Verify dosage schedule was marked as used
        self.dosage_schedule.refresh_from_db()
        self.assertTrue(self.dosage_schedule.used)
        
        # Verify event log was created
        event_log = EventLog.objects.filter(event_type='HANDLE_REQUEST').last()
        self.assertIsNotNone(event_log)
        self.assertEqual(event_log.status, 'Success')
        self.assertEqual(event_log.user, self.user)
    
    def test_handle_request_missing_rfid(self):
        """Test request handling with missing RFID code"""
        data = {
            'fingerprint_id': 12345,
            'timestamp': f'{date.today()}T10:30:00'
        }
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['message'], 'Missing required fields')
    
    def test_handle_request_rfid_not_found(self):
        """Test request handling with non-existent RFID"""
        data = {
            'rfid_code': 'NONEXISTENT',
            'fingerprint_id': 12345,
            'timestamp': f'{date.today()}T10:30:00'
        }
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data['message'], 'RFID not found')
    
    def test_handle_request_fingerprint_mismatch(self):
        """Test request handling with wrong fingerprint ID"""
        data = {
            'rfid_code': 'RFID123456',
            'fingerprint_id': 99999,  # Wrong fingerprint
            'timestamp': f'{date.today()}T10:30:00'
        }
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data['message'], 'Fingerprint mismatch')
    
    def test_handle_request_no_dosage_for_date(self):
        """Test request handling when no dosage is defined for the date"""
        # Delete the dosage schedule
        self.dosage_schedule.delete()
        
        response = self.client.post(self.url, self.valid_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['message'], 'No dosage defined for the specified date')


class TestIntegrationWorkflow(TestCase):
    """Integration tests for complete user workflows"""
    
    def setUp(self):
        """Setup test data before each test method"""
        self.client = APIClient()
        self.add_user_url = reverse('add-user')
        self.handle_request_url = reverse('handle-request')
    
    def test_complete_user_workflow(self):
        """Test complete workflow: add user -> create dosage -> handle request"""
        # Step 1: Add user
        user_data = {
            'rfid_code': 'RFID123456',
            'fingerprint_id': 12345,
            'name': 'John Doe'
        }
        response = self.client.post(self.add_user_url, user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify user was created
        user = User.objects.get(rfid_code='RFID123456')
        self.assertEqual(user.name, 'John Doe')
        self.assertEqual(user.fingerprint_id, 12345)
        
        # Step 2: Create dosage schedule (simulating admin action)
        dosage = DosageSchedule.objects.create(
            user=user,
            date=date.today(),
            dosage=2.5,
            used=False
        )
        self.assertFalse(dosage.used)
        
        # Step 3: Handle request from device
        request_data = {
            'rfid_code': 'RFID123456',
            'fingerprint_id': 12345,
            'timestamp': f'{date.today()}T10:30:00'
        }
        response = self.client.post(self.handle_request_url, request_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')
        self.assertEqual(response.data['dosage'], 2.5)
        
        # Verify dosage was marked as used
        dosage.refresh_from_db()
        self.assertTrue(dosage.used)
        
        # Verify event logs
        add_user_log = EventLog.objects.filter(event_type='ADD_USER').last()
        handle_request_log = EventLog.objects.filter(event_type='HANDLE_REQUEST').last()
        
        self.assertEqual(add_user_log.status, 'Success')
        self.assertEqual(handle_request_log.status, 'Success')
    
    def test_user_tries_to_get_dosage_twice(self):
        """Test that user cannot get dosage twice for the same date"""
        # Add user
        user_data = {
            'rfid_code': 'RFID123456',
            'fingerprint_id': 12345,
            'name': 'Test User'
        }
        self.client.post(self.add_user_url, user_data, format='json')
        
        # Create dosage schedule
        user = User.objects.get(rfid_code='RFID123456')
        DosageSchedule.objects.create(
            user=user,
            date=date.today(),
            dosage=2.5,
            used=False
        )
        
        # First request - should succeed
        request_data = {
            'rfid_code': 'RFID123456',
            'fingerprint_id': 12345,
            'timestamp': f'{date.today()}T10:30:00'
        }
        response = self.client.post(self.handle_request_url, request_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Second request - should fail
        response = self.client.post(self.handle_request_url, request_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['message'], 'No dosage defined for the specified date')