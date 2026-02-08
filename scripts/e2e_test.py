#!/usr/bin/env python3
"""
E2E Test Script for Phase 3 Complete System Test
Week 10 Part A - Session 14-A
"""

import requests
import json
import time
import sys
import os

# Configuration
BASE_URL = "http://localhost:8000/api/v1"
AI_SERVICE_URL = "http://localhost:8001"

class E2ETest:
    def __init__(self):
        self.token = None
        self.user_id = None
        self.email = None
        self.org_id = None
        self.project_id = None
        self.document_id = None
        self.results = []

    def log(self, test_name, success, message=""):
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")
        if message:
            print(f"   → {message}")
        self.results.append({
            "test": test_name,
            "success": success,
            "message": message
        })

    def headers(self, with_auth=True):
        h = {"Content-Type": "application/json"}
        if with_auth and self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    # =========== Scenario 1: New User Complete Workflow ===========

    def test_1_signup(self):
        """1. 회원가입"""
        self.email = f"e2e_test_{int(time.time())}@test.com"
        password = "TestPassword123"

        try:
            resp = requests.post(
                f"{BASE_URL}/auth/signup",
                headers=self.headers(with_auth=False),
                json={
                    "email": self.email,
                    "password": password,
                    "password_confirm": password,
                    "full_name": "E2E Test User"
                }
            )
            data = resp.json()
            if resp.status_code == 201 or "user" in data:
                self.user_id = data.get("user", {}).get("id")
                self.password = password
                self.log("1. 회원가입", True, f"User: {self.email}")
                return True
            else:
                self.log("1. 회원가입", False, str(data))
                return False
        except Exception as e:
            self.log("1. 회원가입", False, str(e))
            return False

    def test_2_login(self):
        """2. 로그인"""
        try:
            resp = requests.post(
                f"{BASE_URL}/auth/login",
                headers=self.headers(with_auth=False),
                json={
                    "email": self.email,
                    "password": self.password
                }
            )
            data = resp.json()
            if "access" in data:
                self.token = data["access"]
                self.log("2. 로그인", True, "Token obtained")
                return True
            else:
                self.log("2. 로그인", False, str(data))
                return False
        except Exception as e:
            self.log("2. 로그인", False, str(e))
            return False

    def test_3_get_user_info(self):
        """3. 현재 사용자 정보 확인"""
        try:
            resp = requests.get(
                f"{BASE_URL}/auth/me",
                headers=self.headers()
            )
            data = resp.json()
            if resp.status_code == 200 and "email" in data:
                self.log("3. 사용자 정보 확인", True, f"Email: {data['email']}")
                return True
            else:
                self.log("3. 사용자 정보 확인", False, str(data))
                return False
        except Exception as e:
            self.log("3. 사용자 정보 확인", False, str(e))
            return False

    def test_4_create_organization(self):
        """4. Organization 생성"""
        try:
            resp = requests.post(
                f"{BASE_URL}/organizations/",
                headers=self.headers(),
                json={"name": "E2E Test Organization"}
            )
            data = resp.json()
            if resp.status_code == 201 and "id" in data:
                self.org_id = data["id"]
                self.log("4. Organization 생성", True, f"ID: {self.org_id}")
                return True
            else:
                self.log("4. Organization 생성", False, str(data))
                return False
        except Exception as e:
            self.log("4. Organization 생성", False, str(e))
            return False

    def test_5_get_organization_members(self):
        """5. Organization 멤버 조회"""
        try:
            resp = requests.get(
                f"{BASE_URL}/organizations/{self.org_id}/members/",
                headers=self.headers()
            )
            data = resp.json()
            if resp.status_code == 200:
                member_count = len(data) if isinstance(data, list) else 0
                self.log("5. Organization 멤버 조회", True, f"Members: {member_count}")
                return True
            else:
                self.log("5. Organization 멤버 조회", False, str(data))
                return False
        except Exception as e:
            self.log("5. Organization 멤버 조회", False, str(e))
            return False

    def test_6_create_project(self):
        """6. Project 생성"""
        try:
            resp = requests.post(
                f"{BASE_URL}/projects/",
                headers=self.headers(),
                json={
                    "organization": self.org_id,
                    "name": "E2E Test Project",
                    "description": "Test project for E2E testing"
                }
            )
            data = resp.json()
            if resp.status_code == 201 and "id" in data:
                self.project_id = data["id"]
                self.log("6. Project 생성", True, f"ID: {self.project_id}")
                return True
            else:
                self.log("6. Project 생성", False, str(data))
                return False
        except Exception as e:
            self.log("6. Project 생성", False, str(e))
            return False

    def test_7_document_list(self):
        """7. Document 목록 조회"""
        try:
            resp = requests.get(
                f"{BASE_URL}/documents/",
                headers=self.headers()
            )
            data = resp.json()
            if resp.status_code == 200:
                count = len(data.get("results", data)) if isinstance(data, dict) else len(data)
                self.log("7. Document 목록 조회", True, f"Count: {count}")
                return True
            else:
                self.log("7. Document 목록 조회", False, str(data))
                return False
        except Exception as e:
            self.log("7. Document 목록 조회", False, str(e))
            return False

    def test_8_dashboard_overview(self):
        """8. Dashboard Overview (Phase 3-7)"""
        try:
            resp = requests.get(
                f"{BASE_URL}/dashboard/overview/",
                headers=self.headers()
            )
            data = resp.json()
            if resp.status_code == 200:
                total_docs = data.get("total_documents", "N/A")
                self.log("8. Dashboard Overview", True, f"Total docs: {total_docs}")
                return True
            else:
                self.log("8. Dashboard Overview", False, str(data))
                return False
        except Exception as e:
            self.log("8. Dashboard Overview", False, str(e))
            return False

    def test_9_ai_health_check(self):
        """9. AI Service Health Check"""
        try:
            resp = requests.get(f"{BASE_URL}/ai/health", headers=self.headers())
            data = resp.json()
            if resp.status_code == 200 and data.get("status") == "healthy":
                self.log("9. AI Service Health", True, "Healthy")
                return True
            else:
                self.log("9. AI Service Health", False, str(data))
                return False
        except Exception as e:
            self.log("9. AI Service Health", False, str(e))
            return False

    def test_10_llm_models_list(self):
        """10. LLM Models 목록 (Phase 3-5)"""
        try:
            resp = requests.get(
                f"{BASE_URL}/llm/models/",
                headers=self.headers()
            )
            data = resp.json()
            if resp.status_code == 200:
                count = len(data.get("results", data)) if isinstance(data, dict) else len(data)
                self.log("10. LLM Models 목록", True, f"Count: {count}")
                return True
            else:
                self.log("10. LLM Models 목록", False, str(data))
                return False
        except Exception as e:
            self.log("10. LLM Models 목록", False, str(e))
            return False

    def test_11_data_sources_list(self):
        """11. Data Sources 목록 (Phase 3-6)"""
        try:
            resp = requests.get(
                f"{BASE_URL}/data-sources/",
                headers=self.headers()
            )
            data = resp.json()
            if resp.status_code == 200:
                count = len(data.get("results", data)) if isinstance(data, dict) else len(data)
                self.log("11. Data Sources 목록", True, f"Count: {count}")
                return True
            else:
                self.log("11. Data Sources 목록", False, str(data))
                return False
        except Exception as e:
            self.log("11. Data Sources 목록", False, str(e))
            return False

    def test_12_crawl_jobs_list(self):
        """12. Crawl Jobs 목록 (Phase 3-6)"""
        try:
            resp = requests.get(
                f"{BASE_URL}/crawl-jobs/",
                headers=self.headers()
            )
            data = resp.json()
            if resp.status_code == 200:
                count = len(data.get("results", data)) if isinstance(data, dict) else len(data)
                self.log("12. Crawl Jobs 목록", True, f"Count: {count}")
                return True
            else:
                self.log("12. Crawl Jobs 목록", False, str(data))
                return False
        except Exception as e:
            self.log("12. Crawl Jobs 목록", False, str(e))
            return False

    def test_13_cases_list(self):
        """13. Cases 목록"""
        try:
            resp = requests.get(
                f"{BASE_URL}/cases/",
                headers=self.headers()
            )
            data = resp.json()
            if resp.status_code == 200:
                count = len(data.get("results", data)) if isinstance(data, dict) else len(data)
                self.log("13. Cases 목록", True, f"Count: {count}")
                return True
            else:
                self.log("13. Cases 목록", False, str(data))
                return False
        except Exception as e:
            self.log("13. Cases 목록", False, str(e))
            return False

    # =========== API Endpoint Tests ===========

    def test_rag_chat_api(self):
        """RAG Chat API Test (Phase 2)"""
        try:
            resp = requests.post(
                f"{BASE_URL}/ai/chat/rag",
                headers=self.headers(),
                json={
                    "query": "증거능력이란 무엇인가요?",
                    "top_k": 3
                },
                timeout=60
            )
            data = resp.json()
            if resp.status_code == 200 and "answer" in data:
                answer_preview = data["answer"][:50] + "..." if len(data.get("answer", "")) > 50 else data.get("answer", "")
                self.log("RAG Chat API", True, f"Answer: {answer_preview}")
                return True
            else:
                self.log("RAG Chat API", False, str(data)[:100])
                return False
        except Exception as e:
            self.log("RAG Chat API", False, str(e))
            return False

    def run_scenario_1(self):
        """Scenario 1: 신규 사용자 전체 워크플로우"""
        print("\n" + "="*60)
        print("Scenario 1: 신규 사용자 전체 워크플로우")
        print("="*60)

        self.test_1_signup()
        if not self.token:
            self.test_2_login()

        if self.token:
            self.test_3_get_user_info()
            self.test_4_create_organization()

            if self.org_id:
                self.test_5_get_organization_members()
                self.test_6_create_project()

            self.test_7_document_list()
            self.test_8_dashboard_overview()
            self.test_9_ai_health_check()
            self.test_10_llm_models_list()
            self.test_11_data_sources_list()
            self.test_12_crawl_jobs_list()
            self.test_13_cases_list()

    def run_scenario_3(self):
        """Scenario 3: RAG Chat + Precedent 검색 통합"""
        print("\n" + "="*60)
        print("Scenario 3: RAG Chat + Precedent 검색 통합")
        print("="*60)

        if not self.token:
            print("Skipping - no token available")
            return

        self.test_rag_chat_api()

    def print_summary(self):
        """테스트 결과 요약"""
        print("\n" + "="*60)
        print("E2E TEST SUMMARY")
        print("="*60)

        total = len(self.results)
        passed = sum(1 for r in self.results if r["success"])
        failed = total - passed

        print(f"Total: {total}")
        print(f"Passed: {passed} ✅")
        print(f"Failed: {failed} ❌")
        print(f"Success Rate: {(passed/total*100):.1f}%" if total > 0 else "N/A")

        if failed > 0:
            print("\nFailed Tests:")
            for r in self.results:
                if not r["success"]:
                    print(f"  - {r['test']}: {r['message'][:50]}")

        return passed, failed


def main():
    print("="*60)
    print("E2E Test Suite - Phase 3 Complete System Test")
    print("Week 10 Part A - Session 14-A")
    print("="*60)

    tester = E2ETest()

    # Run tests
    tester.run_scenario_1()
    tester.run_scenario_3()

    # Print summary
    passed, failed = tester.print_summary()

    # Exit code
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
