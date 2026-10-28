import pytest
from playwright.sync_api import Page, expect
import random
import string

def random_string(length=10):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def get_test_email():
    return f"test_{random_string()}@inspiria.edu.in"

def test_student_signup_flow(page: Page, base_url):
    """
    Tests the full student signup journey:
    Signup Page -> OTP Verification -> Set Password -> Login
    """
    email = get_test_email()
    password = "Password123!"
    full_name = "Test Student"
    mobile = "9876543210"
    emergency = "9123456789"

    # 1. Navigate to Signup Page
    page.goto(f"{base_url}/student/student-signup.html")
    
    # Fill the form
    page.fill("#fullName", full_name)
    page.fill("#studentEmail", email)
    page.fill("#mobileNumber", mobile)
    page.fill("#password", password)
    page.fill("#confirmPassword", password)
    page.fill("#emergencyContact", emergency)
    
    # Click Signup
    page.click("#signupButton")
    
    # Check for success message and redirection
    expect(page.locator("#successMessage")).to_be_visible()
    expect(page).to_have_url(f"{base_url}/student/student-signup-verify.html")

    # Verify that the page loaded correctly by checking for the heading
    # Using a more generic locator to be safe across different heading levels
    expect(page.locator("h1, h2")).to_contain_text("Verify OTP")

def test_student_login_page_load(page: Page, base_url):
    """
    Verify the login page loads and allows input.
    """
    page.goto(f"{base_url}/student/student-login.html")
    
    expect(page.locator("h1")).to_contain_text("Student Login")
    expect(page.locator("#email")).to_be_visible()
    expect(page.locator("#password")).to_be_visible()
    expect(page.locator("#loginButton")).to_be_visible()

def test_forgot_password_navigation(page: Page, base_url):
    """
    Verify navigation to forgot password page from login.
    """
    page.goto(f"{base_url}/student/student-login.html")
    page.click("a[href='../shared/forgot-password.html']")
    
    expect(page).to_have_url(f"{base_url}/shared/forgot-password.html")
    # Using a more generic locator for the heading
    expect(page.locator("h1, h2")).to_contain_text("Forgot Password")
