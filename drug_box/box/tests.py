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


class TestAdminPanel(TestCase):
    """Test cases for Django Admin Panel functionality"""
    
    def setUp(self):
        """Setup test data before each test method"""
        from django.contrib.auth.models import User as DjangoUser
        
        # Create superuser for admin tests
        self.admin_user = DjangoUser.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='admin123'
        )
        
        # Create test data
        self.test_user = User.objects.create(
            name='Test User',
            rfid_code='RFID123456',
            fingerprint_id=12345
        )
        
        self.dosage_schedule = DosageSchedule.objects.create(
            user=self.test_user,
            date=date.today(),
            dosage=2.5,
            used=False
        )
        
        self.event_log = EventLog.objects.create(
            event_type='TEST_EVENT',
            user=self.test_user,
            rfid_code='RFID123456',
            fingerprint_id=12345,
            status='Success',
            message='Test message'
        )
    
    def test_admin_user_creation(self):
        """Test creating user through admin panel"""
        # Test that we can create a user
        user_data = {
            'name': 'Admin Created User',
            'rfid_code': 'RFID789012',
            'fingerprint_id': 67890
        }
        
        # Simulate admin creation
        new_user = User.objects.create(**user_data)
        
        self.assertEqual(new_user.name, 'Admin Created User')
        self.assertEqual(new_user.rfid_code, 'RFID789012')
        self.assertEqual(new_user.fingerprint_id, 67890)
        
        # Verify user appears in admin
        self.assertTrue(User.objects.filter(rfid_code='RFID789012').exists())
    
    def test_admin_dosage_schedule_creation(self):
        """Test creating dosage schedule through admin panel"""
        # Create new user for dosage schedule
        new_user = User.objects.create(
            name='Dosage User',
            rfid_code='RFID111111',
            fingerprint_id=11111
        )
        
        # Create dosage schedule
        dosage_data = {
            'user': new_user,
            'date': date.today(),
            'dosage': 3.0,
            'used': False
        }
        
        new_dosage = DosageSchedule.objects.create(**dosage_data)
        
        self.assertEqual(new_dosage.user, new_user)
        self.assertEqual(new_dosage.dosage, 3.0)
        self.assertFalse(new_dosage.used)
        
        # Verify dosage appears in admin
        self.assertTrue(DosageSchedule.objects.filter(user=new_user).exists())
    
    def test_admin_event_log_readonly(self):
        """Test that event_time is readonly in admin"""
        # EventLog should have event_time as readonly
        from .admin import EventLogAdmin
        
        admin_instance = EventLogAdmin(EventLog, None)
        self.assertIn('event_time', admin_instance.readonly_fields)
    
    def test_admin_list_display_configuration(self):
        """Test admin list display configurations"""
        from .admin import UserAdmin, DosageScheduleAdmin, EventLogAdmin
        
        # Test UserAdmin list_display
        user_admin = UserAdmin(User, None)
        expected_user_fields = ('name', 'rfid_code', 'fingerprint_id')
        self.assertEqual(user_admin.list_display, expected_user_fields)
        
        # Test DosageScheduleAdmin list_display
        dosage_admin = DosageScheduleAdmin(DosageSchedule, None)
        expected_dosage_fields = ('user', 'date', 'dosage', 'used')
        self.assertEqual(dosage_admin.list_display, expected_dosage_fields)
        
        # Test EventLogAdmin list_display
        event_admin = EventLogAdmin(EventLog, None)
        expected_event_fields = ('event_type', 'user', 'status', 'event_time')
        self.assertEqual(event_admin.list_display, expected_event_fields)
    
    def test_admin_search_fields_configuration(self):
        """Test admin search fields configurations"""
        from .admin import UserAdmin, DosageScheduleAdmin, EventLogAdmin
        
        # Test UserAdmin search_fields
        user_admin = UserAdmin(User, None)
        expected_user_search = ('name', 'rfid_code', 'fingerprint_id')
        self.assertEqual(user_admin.search_fields, expected_user_search)
        
        # Test DosageScheduleAdmin search_fields
        dosage_admin = DosageScheduleAdmin(DosageSchedule, None)
        expected_dosage_search = ('user__name', 'date')
        self.assertEqual(dosage_admin.search_fields, expected_dosage_search)
        
        # Test EventLogAdmin search_fields
        event_admin = EventLogAdmin(EventLog, None)
        expected_event_search = ('event_type', 'user__name', 'message')
        self.assertEqual(event_admin.search_fields, expected_event_search)
    
    def test_admin_list_filter_configuration(self):
        """Test admin list filter configurations"""
        from .admin import UserAdmin, DosageScheduleAdmin, EventLogAdmin
        
        # Test UserAdmin list_filter
        user_admin = UserAdmin(User, None)
        expected_user_filters = ('name',)
        self.assertEqual(user_admin.list_filter, expected_user_filters)
        
        # Test DosageScheduleAdmin list_filter
        dosage_admin = DosageScheduleAdmin(DosageSchedule, None)
        expected_dosage_filters = ('date', 'user')
        self.assertEqual(dosage_admin.list_filter, expected_dosage_filters)
        
        # Test EventLogAdmin list_filter
        event_admin = EventLogAdmin(EventLog, None)
        expected_event_filters = ('event_type', 'status', 'event_time')
        self.assertEqual(event_admin.list_filter, expected_event_filters)
    
    def test_admin_date_hierarchy_configuration(self):
        """Test admin date hierarchy configurations"""
        from .admin import DosageScheduleAdmin, EventLogAdmin
        
        # Test DosageScheduleAdmin date_hierarchy
        dosage_admin = DosageScheduleAdmin(DosageSchedule, None)
        self.assertEqual(dosage_admin.date_hierarchy, 'date')
        
        # Test EventLogAdmin date_hierarchy
        event_admin = EventLogAdmin(EventLog, None)
        self.assertEqual(event_admin.date_hierarchy, 'event_time')
    
    def test_admin_model_registration(self):
        """Test that models are properly registered in admin"""
        from django.contrib import admin
        
        # Check if models are registered
        self.assertTrue(admin.site.is_registered(User))
        self.assertTrue(admin.site.is_registered(DosageSchedule))
        self.assertTrue(admin.site.is_registered(EventLog))
    
    def test_admin_bulk_operations(self):
        """Test admin bulk operations functionality"""
        # Create multiple users
        users_data = [
            {'name': 'User 1', 'rfid_code': 'RFID001', 'fingerprint_id': 1001},
            {'name': 'User 2', 'rfid_code': 'RFID002', 'fingerprint_id': 1002},
            {'name': 'User 3', 'rfid_code': 'RFID003', 'fingerprint_id': 1003},
        ]
        
        created_users = []
        for user_data in users_data:
            user = User.objects.create(**user_data)
            created_users.append(user)
        
        # Verify all users were created
        self.assertEqual(User.objects.count(), 4)  # 3 new + 1 from setUp
        
        # Test bulk dosage creation
        for user in created_users:
            DosageSchedule.objects.create(
                user=user,
                date=date.today(),
                dosage=1.0,
                used=False
            )
        
        # Verify all dosages were created
        self.assertEqual(DosageSchedule.objects.count(), 4)  # 3 new + 1 from setUp
    
    def test_admin_validation_constraints(self):
        """Test that admin respects model validation constraints"""
        # Test unique RFID constraint
        with self.assertRaises(Exception):
            User.objects.create(
                name='Duplicate RFID User',
                rfid_code='RFID123456',  # Same as existing user
                fingerprint_id=99999
            )
        
        # Test unique fingerprint constraint
        with self.assertRaises(Exception):
            User.objects.create(
                name='Duplicate Fingerprint User',
                rfid_code='RFID999999',
                fingerprint_id=12345  # Same as existing user
            )
        
        # Test unique_together constraint for DosageSchedule
        with self.assertRaises(Exception):
            DosageSchedule.objects.create(
                user=self.test_user,
                date=date.today(),  # Same user and date
                dosage=5.0,
                used=False
            )
    
    def test_admin_event_log_creation(self):
        """Test creating event logs through admin"""
        # Create event log
        event_data = {
            'event_type': 'ADMIN_CREATED',
            'user': self.test_user,
            'rfid_code': 'RFID123456',
            'fingerprint_id': 12345,
            'status': 'Success',
            'message': 'Created by admin'
        }
        
        new_event = EventLog.objects.create(**event_data)
        
        self.assertEqual(new_event.event_type, 'ADMIN_CREATED')
        self.assertEqual(new_event.user, self.test_user)
        self.assertEqual(new_event.status, 'Success')
        self.assertIsNotNone(new_event.event_time)
    
    def test_admin_model_str_representations(self):
        """Test model string representations in admin"""
        # Test User string representation
        self.assertEqual(str(self.test_user), 'Test User')
        
        # Test DosageSchedule string representation
        expected_dosage_str = f"{self.test_user} - {date.today()}: 2.5"
        self.assertEqual(str(self.dosage_schedule), expected_dosage_str)
        
        # Test EventLog string representation
        event_str = str(self.event_log)
        self.assertIn('TEST_EVENT', event_str)
        self.assertIn('Success', event_str)
    
    def test_admin_foreign_key_relationships(self):
        """Test foreign key relationships in admin"""
        # Test DosageSchedule -> User relationship
        self.assertEqual(self.dosage_schedule.user, self.test_user)
        self.assertIn(self.dosage_schedule, self.test_user.dosage_schedules.all())
        
        # Test EventLog -> User relationship
        self.assertEqual(self.event_log.user, self.test_user)
        self.assertIn(self.event_log, self.test_user.event_logs.all())
    
    def test_admin_queryset_filtering(self):
        """Test admin queryset filtering capabilities"""
        # Test filtering users by name
        users_by_name = User.objects.filter(name__icontains='Test')
        self.assertIn(self.test_user, users_by_name)
        
        # Test filtering dosages by date
        dosages_by_date = DosageSchedule.objects.filter(date=date.today())
        self.assertIn(self.dosage_schedule, dosages_by_date)
        
        # Test filtering events by status
        events_by_status = EventLog.objects.filter(status='Success')
        self.assertIn(self.event_log, events_by_status)
    
    def test_admin_ordering_and_sorting(self):
        """Test admin ordering and sorting functionality"""
        # Create multiple users with different names
        User.objects.create(name='Alice', rfid_code='RFID_A', fingerprint_id=2001)
        User.objects.create(name='Bob', rfid_code='RFID_B', fingerprint_id=2002)
        User.objects.create(name='Charlie', rfid_code='RFID_C', fingerprint_id=2003)
        
        # Test ordering by name
        users_ordered = User.objects.all().order_by('name')
        user_names = [user.name for user in users_ordered]
        self.assertEqual(user_names, ['Alice', 'Bob', 'Charlie', 'Test User'])
        
        # Test ordering by RFID
        users_by_rfid = User.objects.all().order_by('rfid_code')
        rfid_codes = [user.rfid_code for user in users_by_rfid]
        self.assertEqual(rfid_codes, ['RFID123456', 'RFID_A', 'RFID_B', 'RFID_C'])