#!/usr/bin/env python3
"""
Script to create a test user in the database.
This can be run manually to ensure the test user exists without restarting the application.
"""
import asyncio
import sys
import os

# Add the current directory to the Python path so we can import from app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.create_test_user import create_test_user

if __name__ == "__main__":
    print("Creating test user...")
    asyncio.run(create_test_user())
    print("Done.")
