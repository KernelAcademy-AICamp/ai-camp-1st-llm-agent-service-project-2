#!/usr/bin/env python3
"""
Test authentication API endpoints
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_signup():
    """Test signup endpoint"""
    print("\n=== Testing Signup ===")
    response = requests.post(
        f"{BASE_URL}/api/auth/signup",
        json={
            "email": "newuser@lawlaw.com",
            "password": "password123",
            "full_name": "이변호사",
            "specializations": ["형사 일반", "성범죄"],
            "lawyer_registration_number": "54321"
        }
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    return response.json()

def test_login():
    """Test login endpoint"""
    print("\n=== Testing Login ===")
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        data={
            "username": "test@lawlaw.com",
            "password": "test1234"
        }
    )
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response: {json.dumps(result, indent=2, ensure_ascii=False)}")
    return result

def test_me(token):
    """Test /me endpoint"""
    print("\n=== Testing /me ===")
    response = requests.get(
        f"{BASE_URL}/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    return response.json()

def test_update_profile(token):
    """Test profile update endpoint"""
    print("\n=== Testing Profile Update ===")
    response = requests.put(
        f"{BASE_URL}/api/auth/profile",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "full_name": "김변호사 (수정됨)",
            "specializations": ["형사 일반", "교통사고", "마약범죄"]
        }
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    return response.json()

if __name__ == "__main__":
    # Test login with existing user
    login_result = test_login()
    token = login_result.get("access_token")

    if token:
        # Test /me endpoint
        test_me(token)

        # Test profile update
        test_update_profile(token)

        # Check updated profile
        test_me(token)

    # Test signup (may fail if user already exists)
    try:
        signup_result = test_signup()
        new_token = signup_result.get("access_token")
        if new_token:
            test_me(new_token)
    except Exception as e:
        print(f"Signup test failed (may already exist): {e}")

    print("\n✅ Authentication API testing complete!")
