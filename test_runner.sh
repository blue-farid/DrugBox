#!/bin/bash

# Test runner script for Drug Box API
# This script runs all tests for the Drug Box API endpoints

echo "Running Drug Box API Tests..."
echo "=============================="

# Navigate to the Django project directory
cd drug_box

# Activate virtual environment
source ../venv/bin/activate

# Run Django tests
echo "Running Django tests..."
python manage.py test box.tests --verbosity=2

echo ""
echo "Test run completed!"
echo "=============================="
