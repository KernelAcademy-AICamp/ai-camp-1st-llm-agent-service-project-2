#!/usr/bin/env python3
"""
확장된 인증 API 테스트
- 로그아웃
- 비밀번호 변경
- 비밀번호 재설정
- 계정 비활성화
"""

import requests
import json

BASE_URL = "http://localhost:8000"


def test_logout(token):
    """로그아웃 테스트"""
    print("\n=== Testing Logout ===")
    response = requests.post(
        f"{BASE_URL}/api/auth/logout", headers={"Authorization": f"Bearer {token}"}
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    return response.json()


def test_change_password(token, current_password, new_password):
    """비밀번호 변경 테스트"""
    print("\n=== Testing Change Password ===")
    response = requests.put(
        f"{BASE_URL}/api/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"current_password": current_password, "new_password": new_password},
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    return response.json()


def test_forgot_password(email):
    """비밀번호 재설정 요청 테스트"""
    print("\n=== Testing Forgot Password ===")
    response = requests.post(f"{BASE_URL}/api/auth/forgot-password", json={"email": email})
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response: {json.dumps(result, indent=2, ensure_ascii=False)}")
    return result


def test_reset_password(reset_token, new_password):
    """비밀번호 재설정 확인 테스트"""
    print("\n=== Testing Reset Password ===")
    response = requests.post(
        f"{BASE_URL}/api/auth/reset-password",
        json={"token": reset_token, "new_password": new_password},
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    return response.json()


def test_deactivate_account(token):
    """계정 비활성화 테스트"""
    print("\n=== Testing Account Deactivation ===")
    response = requests.delete(
        f"{BASE_URL}/api/auth/account", headers={"Authorization": f"Bearer {token}"}
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    return response.json()


def test_login(email, password):
    """로그인 (헬퍼 함수)"""
    print(f"\n=== Logging in as {email} ===")
    response = requests.post(f"{BASE_URL}/api/auth/login", data={"username": email, "password": password})
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Login failed: {response.text}")
        return None


def test_signup(email, password, full_name, specializations):
    """회원가입 (헬퍼 함수)"""
    print(f"\n=== Signing up as {email} ===")
    response = requests.post(
        f"{BASE_URL}/api/auth/signup",
        json={
            "email": email,
            "password": password,
            "full_name": full_name,
            "specializations": specializations,
        },
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 201:
        return response.json()
    else:
        print(f"Signup failed: {response.text}")
        return None


if __name__ == "__main__":
    print("=" * 60)
    print("확장된 인증 API 테스트 시작")
    print("=" * 60)

    # 1. 새 사용자 생성 (비밀번호 8자 이상)
    signup_result = test_signup(
        email="testuser@lawlaw.com",
        password="password123",
        full_name="테스트 변호사",
        specializations=["형사 일반"],
    )

    if signup_result:
        token = signup_result.get("access_token")

        # 2. 로그아웃 테스트
        test_logout(token)

        # 3. 다시 로그인
        login_result = test_login("testuser@lawlaw.com", "password123")
        if login_result:
            token = login_result.get("access_token")

            # 4. 비밀번호 변경 테스트 (잘못된 현재 비밀번호)
            print("\n--- Testing with wrong current password ---")
            test_change_password(token, "wrongpassword", "newpassword123")

            # 5. 비밀번호 변경 테스트 (올바른 비밀번호)
            print("\n--- Testing with correct current password ---")
            test_change_password(token, "password123", "newpassword123")

            # 6. 변경된 비밀번호로 로그인
            login_result = test_login("testuser@lawlaw.com", "newpassword123")
            if login_result:
                token = login_result.get("access_token")

    # 7. 비밀번호 재설정 플로우 테스트
    print("\n" + "=" * 60)
    print("비밀번호 재설정 플로우 테스트")
    print("=" * 60)

    forgot_result = test_forgot_password("testuser@lawlaw.com")
    if forgot_result.get("reset_token"):
        reset_token = forgot_result["reset_token"]
        test_reset_password(reset_token, "resetpassword123")

        # 8. 재설정된 비밀번호로 로그인
        login_result = test_login("testuser@lawlaw.com", "resetpassword123")
        if login_result:
            token = login_result.get("access_token")

            # 9. 계정 비활성화 테스트
            test_deactivate_account(token)

            # 10. 비활성화된 계정으로 로그인 시도
            print("\n--- Attempting login with deactivated account ---")
            test_login("testuser@lawlaw.com", "resetpassword123")

    # 11. 존재하지 않는 이메일로 비밀번호 재설정 요청
    print("\n--- Testing forgot password with non-existent email ---")
    test_forgot_password("nonexistent@lawlaw.com")

    print("\n" + "=" * 60)
    print("✅ 확장된 인증 API 테스트 완료!")
    print("=" * 60)
