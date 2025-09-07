# Drug Box API Testing Guide

This document describes the testing setup for the Drug Box API project.

## Overview

The project includes comprehensive tests for all API endpoints using Django's built-in testing framework. The tests cover:

- **AddUserFromDeviceAPIView** - User creation endpoint
- **HandleRequestAPIView** - Request handling endpoint
- **Integration workflows** - Complete user workflows
- **Model integrity** - Database constraints and relationships
- **Event logging** - System event tracking

## Test Structure

### Test Files

- `drug_box/box/tests.py` - Main test file containing all test cases
- `pytest.ini` - Pytest configuration file
- `test_runner.sh` - Convenient test runner script

### Test Classes

1. **TestAddUserFromDeviceAPIView**
   - Tests user creation functionality
   - Validates input data
   - Tests duplicate prevention
   - Verifies event logging

2. **TestHandleRequestAPIView**
   - Tests request handling functionality
   - Validates authentication (RFID + fingerprint)
   - Tests dosage management
   - Verifies error handling

3. **TestIntegrationWorkflow**
   - Tests complete user workflows
   - End-to-end scenarios
   - Multiple user interactions

## Running Tests

### Method 1: Using Django's Test Runner (Recommended)

```bash
# Navigate to the Django project directory
cd drug_box

# Activate virtual environment
source ../venv/bin/activate

# Run all tests
python manage.py test box.tests --verbosity=2

# Run specific test class
python manage.py test box.tests.TestAddUserFromDeviceAPIView --verbosity=2

# Run specific test method
python manage.py test box.tests.TestAddUserFromDeviceAPIView.test_add_user_success --verbosity=2
```

### Method 2: Using the Test Runner Script

```bash
# Make the script executable (if not already)
chmod +x test_runner.sh

# Run all tests
./test_runner.sh
```

### Method 3: Using Pytest (Alternative)

```bash
# Install pytest if not already installed
pip install pytest pytest-django pytest-cov

# Run tests with pytest
python -m pytest drug_box/box/tests.py -v
```

## Test Coverage

The tests cover the following scenarios:

### AddUserFromDeviceAPIView Tests
- ✅ Successful user creation
- ✅ Missing RFID code validation
- ✅ Missing fingerprint ID validation
- ✅ Duplicate RFID prevention
- ✅ Duplicate fingerprint prevention
- ✅ User creation without name (optional field)

### HandleRequestAPIView Tests
- ✅ Successful request handling
- ✅ Missing RFID code validation
- ✅ Missing fingerprint ID validation
- ✅ Missing timestamp validation
- ✅ Non-existent RFID handling
- ✅ Fingerprint mismatch handling
- ✅ No dosage for date handling
- ✅ Already used dosage handling

### Integration Tests
- ✅ Complete user workflow (add user → create dosage → handle request)
- ✅ Double dosage prevention
- ✅ Event logging verification

## Test Data

Tests use the following test data:

### Valid User Data
```json
{
    "rfid_code": "RFID123456",
    "fingerprint_id": 12345,
    "name": "Test User"
}
```

### Valid Request Data
```json
{
    "rfid_code": "RFID123456",
    "fingerprint_id": 12345,
    "timestamp": "2024-01-15T10:30:00"
}
```

## Expected Test Results

When all tests pass, you should see:

```
Found 10 test(s).
...
----------------------------------------------------------------------
Ran 10 tests in 0.077s

OK
```

## Test Database

Tests use an in-memory SQLite database that is created and destroyed for each test run. This ensures:
- Tests are isolated from each other
- No interference with development data
- Fast test execution
- Clean test environment

## Troubleshooting

### Common Issues

1. **Import Errors**: Make sure you're in the correct directory (`drug_box/`) when running tests
2. **Virtual Environment**: Ensure the virtual environment is activated
3. **Database Issues**: Tests create their own database, so no setup is required
4. **Transaction Errors**: Fixed by using proper transaction handling in views

### Debug Mode

To run tests with more verbose output:

```bash
python manage.py test box.tests --verbosity=3
```

## Adding New Tests

To add new tests:

1. Open `drug_box/box/tests.py`
2. Add new test methods to existing test classes or create new test classes
3. Follow the existing naming convention: `test_<description>`
4. Use Django's `TestCase` class for database tests
5. Use `self.client` for API calls
6. Use `self.assertEqual()`, `self.assertTrue()`, etc. for assertions

### Example Test Method

```python
def test_new_functionality(self):
    """Test description"""
    # Setup test data
    data = {'key': 'value'}
    
    # Make API call
    response = self.client.post('/api/endpoint/', data, format='json')
    
    # Assertions
    self.assertEqual(response.status_code, 200)
    self.assertEqual(response.data['status'], 'success')
```

## Continuous Integration

For CI/CD pipelines, use:

```bash
cd drug_box && python manage.py test box.tests --verbosity=1
```

This provides a clean exit code (0 for success, 1 for failure) suitable for automated testing.
