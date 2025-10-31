import requests
import sys
import json
import io
import time
from datetime import datetime

class SalesCallAPITester:
    def __init__(self, base_url="https://salescallanalyzer.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name, success, details=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
        
        result = {
            "test": name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {name}")
        if details:
            print(f"    Details: {details}")

    def test_api_root(self):
        """Test API root endpoint"""
        try:
            response = requests.get(f"{self.api_url}/", timeout=10)
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            if success:
                data = response.json()
                details += f", Message: {data.get('message', 'N/A')}"
            self.log_test("API Root Endpoint", success, details)
            return success
        except Exception as e:
            self.log_test("API Root Endpoint", False, f"Error: {str(e)}")
            return False

    def test_upload_call(self):
        """Test file upload endpoint"""
        try:
            # Create a small test audio file (simulate MP3)
            test_audio_content = b"fake_mp3_content_for_testing"
            files = {
                'file': ('test_call.mp3', io.BytesIO(test_audio_content), 'audio/mpeg')
            }
            
            response = requests.post(f"{self.api_url}/upload-call", files=files, timeout=30)
            success = response.status_code == 200
            
            if success:
                data = response.json()
                call_id = data.get('call_id')
                details = f"Status: {response.status_code}, Call ID: {call_id}"
                self.log_test("Upload Call", success, details)
                return call_id
            else:
                details = f"Status: {response.status_code}, Response: {response.text[:200]}"
                self.log_test("Upload Call", success, details)
                return None
                
        except Exception as e:
            self.log_test("Upload Call", False, f"Error: {str(e)}")
            return None

    def test_transcribe_call(self, call_id):
        """Test transcription endpoint"""
        if not call_id:
            self.log_test("Transcribe Call", False, "No call ID provided")
            return False
            
        try:
            response = requests.post(f"{self.api_url}/transcribe/{call_id}", timeout=60)
            success = response.status_code == 200
            
            if success:
                data = response.json()
                details = f"Status: {response.status_code}, Message: {data.get('message', 'N/A')}"
            else:
                details = f"Status: {response.status_code}, Response: {response.text[:200]}"
                
            self.log_test("Transcribe Call", success, details)
            return success
            
        except Exception as e:
            self.log_test("Transcribe Call", False, f"Error: {str(e)}")
            return False

    def test_analyze_call(self, call_id):
        """Test analysis endpoint"""
        if not call_id:
            self.log_test("Analyze Call", False, "No call ID provided")
            return False
            
        try:
            response = requests.post(f"{self.api_url}/analyze/{call_id}", timeout=120)
            success = response.status_code == 200
            
            if success:
                data = response.json()
                details = f"Status: {response.status_code}, Score: {data.get('score', 'N/A')}"
            else:
                details = f"Status: {response.status_code}, Response: {response.text[:200]}"
                
            self.log_test("Analyze Call", success, details)
            return success
            
        except Exception as e:
            self.log_test("Analyze Call", False, f"Error: {str(e)}")
            return False

    def test_get_calls(self):
        """Test get all calls endpoint"""
        try:
            response = requests.get(f"{self.api_url}/calls", timeout=10)
            success = response.status_code == 200
            
            if success:
                data = response.json()
                call_count = len(data) if isinstance(data, list) else 0
                details = f"Status: {response.status_code}, Calls found: {call_count}"
            else:
                details = f"Status: {response.status_code}, Response: {response.text[:200]}"
                
            self.log_test("Get All Calls", success, details)
            return success, data if success else []
            
        except Exception as e:
            self.log_test("Get All Calls", False, f"Error: {str(e)}")
            return False, []

    def test_get_call_details(self, call_id):
        """Test get specific call details"""
        if not call_id:
            self.log_test("Get Call Details", False, "No call ID provided")
            return False
            
        try:
            response = requests.get(f"{self.api_url}/calls/{call_id}", timeout=10)
            success = response.status_code == 200
            
            if success:
                data = response.json()
                details = f"Status: {response.status_code}, Filename: {data.get('filename', 'N/A')}"
            else:
                details = f"Status: {response.status_code}, Response: {response.text[:200]}"
                
            self.log_test("Get Call Details", success, details)
            return success
            
        except Exception as e:
            self.log_test("Get Call Details", False, f"Error: {str(e)}")
            return False

    def test_export_pdf(self, call_id):
        """Test PDF export"""
        if not call_id:
            self.log_test("Export PDF", False, "No call ID provided")
            return False
            
        try:
            response = requests.get(f"{self.api_url}/export/{call_id}/pdf", timeout=30)
            success = response.status_code == 200
            
            if success:
                content_type = response.headers.get('content-type', '')
                details = f"Status: {response.status_code}, Content-Type: {content_type}"
            else:
                details = f"Status: {response.status_code}, Response: {response.text[:200]}"
                
            self.log_test("Export PDF", success, details)
            return success
            
        except Exception as e:
            self.log_test("Export PDF", False, f"Error: {str(e)}")
            return False

    def test_export_csv(self, call_id):
        """Test CSV export"""
        if not call_id:
            self.log_test("Export CSV", False, "No call ID provided")
            return False
            
        try:
            response = requests.get(f"{self.api_url}/export/{call_id}/csv", timeout=30)
            success = response.status_code == 200
            
            if success:
                content_type = response.headers.get('content-type', '')
                details = f"Status: {response.status_code}, Content-Type: {content_type}"
            else:
                details = f"Status: {response.status_code}, Response: {response.text[:200]}"
                
            self.log_test("Export CSV", success, details)
            return success
            
        except Exception as e:
            self.log_test("Export CSV", False, f"Error: {str(e)}")
            return False

    def run_full_test_suite(self):
        """Run complete test suite"""
        print("🚀 Starting Sales Call Performance Analysis API Tests")
        print(f"📍 Testing against: {self.base_url}")
        print("=" * 60)
        
        # Test 1: API Root
        if not self.test_api_root():
            print("❌ API Root failed - stopping tests")
            return self.generate_report()
        
        # Test 2: Upload Call
        call_id = self.test_upload_call()
        if not call_id:
            print("❌ Upload failed - stopping tests")
            return self.generate_report()
        
        # Wait a moment for upload to process
        time.sleep(2)
        
        # Test 3: Get Calls List
        calls_success, calls_data = self.test_get_calls()
        
        # Test 4: Get Call Details
        self.test_get_call_details(call_id)
        
        # Test 5: Transcribe Call (this might fail due to fake audio)
        transcribe_success = self.test_transcribe_call(call_id)
        
        # Test 6: Analyze Call (depends on transcription)
        if transcribe_success:
            analyze_success = self.test_analyze_call(call_id)
            
            # Test 7 & 8: Export functions (only if analysis completed)
            if analyze_success:
                self.test_export_pdf(call_id)
                self.test_export_csv(call_id)
            else:
                self.log_test("Export PDF", False, "Analysis not completed")
                self.log_test("Export CSV", False, "Analysis not completed")
        else:
            self.log_test("Analyze Call", False, "Transcription not completed")
            self.log_test("Export PDF", False, "Prerequisites not met")
            self.log_test("Export CSV", False, "Prerequisites not met")
        
        return self.generate_report()

    def generate_report(self):
        """Generate final test report"""
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {self.tests_run}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%" if self.tests_run > 0 else "0%")
        
        # Detailed results
        print("\n📋 DETAILED RESULTS:")
        for result in self.test_results:
            status = "✅" if result['success'] else "❌"
            print(f"{status} {result['test']}")
            if result['details']:
                print(f"   {result['details']}")
        
        return {
            "total_tests": self.tests_run,
            "passed_tests": self.tests_passed,
            "failed_tests": self.tests_run - self.tests_passed,
            "success_rate": (self.tests_passed/self.tests_run*100) if self.tests_run > 0 else 0,
            "detailed_results": self.test_results
        }

def main():
    """Main test execution"""
    tester = SalesCallAPITester()
    results = tester.run_full_test_suite()
    
    # Return appropriate exit code
    return 0 if results['success_rate'] > 50 else 1

if __name__ == "__main__":
    sys.exit(main())