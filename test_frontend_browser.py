#!/usr/bin/env python3
"""
Headless browser test for MediaVault frontend.

Tests:
1. Frontend loads correctly
2. Library page displays Red Dwarf files
3. File details modal shows correct data
4. Bitrate, audio channels, and MD5 are displayed properly
"""
import subprocess
import time
import os
import signal
from playwright.sync_api import sync_playwright, expect

# Configuration
FRONTEND_URL = "http://localhost:3007"
BACKEND_URL = "http://localhost:8007"


def start_backend():
    """Start the backend server."""
    print("Starting backend server...")
    backend_process = subprocess.Popen(
        ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8007"],
        cwd="/home/mercury/projects/mediavault/backend",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait for backend to be ready
    time.sleep(3)

    # Check if backend is running
    try:
        import requests
        response = requests.get(f"{BACKEND_URL}/docs", timeout=5)
        if response.status_code == 200:
            print("✓ Backend started successfully")
        else:
            print(f"⚠ Backend returned status code: {response.status_code}")
    except Exception as e:
        print(f"⚠ Could not verify backend: {e}")

    return backend_process


def start_frontend():
    """Start the frontend dev server."""
    print("Starting frontend dev server...")
    frontend_process = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd="/home/mercury/projects/mediavault/frontend",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait for frontend to be ready
    print("Waiting for frontend to start (20 seconds)...")
    time.sleep(20)

    return frontend_process


def test_frontend_with_browser():
    """Run headless browser tests."""
    print("\n" + "=" * 70)
    print("MediaVault Frontend Browser Test")
    print("=" * 70)
    print()

    with sync_playwright() as p:
        # Launch browser
        print("Launching headless browser...")
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()

        try:
            # Test 1: Load homepage
            print("\nTest 1: Loading homepage...")
            page.goto(FRONTEND_URL, timeout=30000)
            page.wait_for_load_state("networkidle")
            print(f"✓ Page loaded: {page.title()}")

            # Test 2: Navigate to Library
            print("\nTest 2: Navigating to Library page...")
            page.click('text=Library', timeout=10000)
            page.wait_for_load_state("networkidle")
            print("✓ Library page loaded")

            # Test 3: Check for Red Dwarf files
            print("\nTest 3: Checking for Red Dwarf files...")
            page.wait_for_selector("text=Red.Dwarf", timeout=10000)
            red_dwarf_rows = page.locator("text=Red.Dwarf").count()
            print(f"✓ Found {red_dwarf_rows} Red Dwarf entries")

            if red_dwarf_rows == 0:
                print("✗ No Red Dwarf files found in library!")
                return False

            # Test 4: Click info button on first file
            print("\nTest 4: Opening file details modal...")
            # Find first Red Dwarf row and click the info icon
            first_row = page.locator("tr:has-text('Red.Dwarf')").first
            info_button = first_row.locator("button[aria-label*=''], button:has(svg)").nth(2)  # Third button is info
            info_button.click()

            # Wait for modal
            page.wait_for_selector("text=File Details", timeout=5000)
            print("✓ File details modal opened")

            # Test 5: Verify modal content
            print("\nTest 5: Verifying file details content...")

            # Get modal content
            modal = page.locator('[role="dialog"]')
            modal_text = modal.inner_text()

            print("\nModal Content:")
            print("-" * 50)
            print(modal_text)
            print("-" * 50)

            # Check for required fields
            tests_passed = []
            tests_failed = []

            # Check Path
            if "Path:" in modal_text and "/mnt/nas-media" in modal_text:
                tests_passed.append("✓ Path displayed")
            else:
                tests_failed.append("✗ Path missing or incorrect")

            # Check Codec
            if "Codec:" in modal_text and ("h264" in modal_text or "H264" in modal_text.lower()):
                tests_passed.append("✓ Video codec displayed")
            else:
                tests_failed.append("✗ Video codec missing")

            # Check Bitrate (should show Mbps now)
            if "Bitrate:" in modal_text:
                if "Mbps" in modal_text and "kbps" not in modal_text:
                    tests_passed.append("✓ Bitrate displayed correctly (Mbps format)")
                elif "N/A" in modal_text:
                    tests_passed.append("✓ Bitrate shows N/A (acceptable)")
                else:
                    tests_failed.append("✗ Bitrate format incorrect (should be Mbps or N/A)")
            else:
                tests_failed.append("✗ Bitrate field missing")

            # Check Audio Channels
            if "Audio Channels:" in modal_text:
                if any(ch in modal_text for ch in ["2.0", "5.1", "7.1", "N/A"]):
                    tests_passed.append("✓ Audio channels displayed")
                else:
                    tests_failed.append("✗ Audio channels value missing or incorrect")
            else:
                tests_failed.append("✗ Audio Channels field missing")

            # Check MD5
            if "MD5:" in modal_text:
                if "Yes" in modal_text or "Copy Hash" in modal_text:
                    tests_passed.append("✓ MD5 hash indicator displayed")
                elif "Not calculated" in modal_text:
                    tests_passed.append("✓ MD5 shows 'Not calculated' (acceptable)")
                else:
                    tests_failed.append("✗ MD5 field present but no value/indicator")
            else:
                tests_failed.append("✗ MD5 field missing")

            # Test 6: Try clicking Copy Hash button if it exists
            print("\nTest 6: Testing MD5 copy functionality...")
            try:
                copy_button = page.locator("text=Copy Hash").first
                if copy_button.is_visible():
                    copy_button.click()
                    print("✓ Copy Hash button clicked")

                    # Wait for notification
                    page.wait_for_selector("text=MD5 Hash", timeout=3000)
                    print("✓ MD5 copy notification appeared")
                    tests_passed.append("✓ MD5 copy functionality works")
                else:
                    print("⚠ Copy Hash button not visible")
            except Exception as e:
                print(f"⚠ Could not test MD5 copy: {e}")

            # Take screenshot
            screenshot_path = "/home/mercury/projects/mediavault/test_screenshots"
            os.makedirs(screenshot_path, exist_ok=True)
            page.screenshot(path=f"{screenshot_path}/file_details_modal.png")
            print(f"\n✓ Screenshot saved to {screenshot_path}/file_details_modal.png")

            # Print results
            print("\n" + "=" * 70)
            print("Test Results Summary")
            print("=" * 70)
            print("\nPassed Tests:")
            for test in tests_passed:
                print(f"  {test}")

            if tests_failed:
                print("\nFailed Tests:")
                for test in tests_failed:
                    print(f"  {test}")

            print(f"\nTotal: {len(tests_passed)} passed, {len(tests_failed)} failed")
            print("=" * 70)

            return len(tests_failed) == 0

        except Exception as e:
            print(f"\n✗ Test failed with error: {e}")
            # Take error screenshot
            try:
                screenshot_path = "/home/mercury/projects/mediavault/test_screenshots"
                os.makedirs(screenshot_path, exist_ok=True)
                page.screenshot(path=f"{screenshot_path}/error_screenshot.png")
                print(f"Error screenshot saved to {screenshot_path}/error_screenshot.png")
            except:
                pass
            return False

        finally:
            browser.close()


def main():
    """Main test runner."""
    backend_process = None
    frontend_process = None

    try:
        # Start services
        backend_process = start_backend()
        frontend_process = start_frontend()

        # Run tests
        success = test_frontend_with_browser()

        # Return appropriate exit code
        return 0 if success else 1

    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        return 1

    except Exception as e:
        print(f"\n\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        # Cleanup
        print("\n\nCleaning up...")
        if frontend_process:
            print("Stopping frontend...")
            frontend_process.terminate()
            try:
                frontend_process.wait(timeout=5)
            except:
                frontend_process.kill()

        if backend_process:
            print("Stopping backend...")
            backend_process.terminate()
            try:
                backend_process.wait(timeout=5)
            except:
                backend_process.kill()

        print("Cleanup complete")


if __name__ == "__main__":
    import sys
    sys.exit(main())
