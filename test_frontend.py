#!/usr/bin/env python3
"""
MediaVault Frontend Testing with Playwright
Tests all pages, navigation, and checks for console errors
"""

from playwright.sync_api import sync_playwright, expect
import sys
import json

def test_mediavault(base_url="http://localhost:3007"):
    """Test MediaVault frontend with Playwright"""

    print("🧪 Starting MediaVault Frontend Tests")
    print(f"📍 Base URL: {base_url}")
    print("-" * 60)

    with sync_playwright() as p:
        # Launch browser in headless mode
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # Track console errors
        console_errors = []
        page.on("console", lambda msg:
            console_errors.append(msg.text) if msg.type == "error" else None
        )

        # Track page errors
        page_errors = []
        page.on("pageerror", lambda exc: page_errors.append(str(exc)))

        try:
            # Test 1: Load homepage
            print("\n✓ Test 1: Homepage loads")
            page.goto(base_url, wait_until="networkidle")
            assert "MediaVault" in page.title()
            print("  ✅ Title contains 'MediaVault'")

            # Check for React root
            assert page.locator("#root").count() > 0
            print("  ✅ React root element found")

            # Test 2: Dashboard page
            print("\n✓ Test 2: Dashboard page")
            page.click("text=Dashboard")
            page.wait_for_load_state("networkidle")

            # Check for dashboard elements
            assert page.locator("text=Total Files").count() > 0
            print("  ✅ 'Total Files' stat found")

            assert page.locator("text=Duplicate Groups").count() > 0
            print("  ✅ 'Duplicate Groups' stat found")

            assert page.locator("text=Recent Scans").count() > 0
            print("  ✅ 'Recent Scans' section found")

            # Test 3: Library page
            print("\n✓ Test 3: Library page")
            page.click("text=Library")
            page.wait_for_load_state("networkidle")

            # Check for library elements
            assert page.locator("text=Media Library").count() > 0
            print("  ✅ 'Media Library' title found")

            # Check for search input
            search_input = page.locator("input[placeholder*='Search']")
            assert search_input.count() > 0
            print("  ✅ Search input found")

            # Test 4: Duplicates page
            print("\n✓ Test 4: Duplicates page")
            page.click("text=Duplicates")
            page.wait_for_load_state("networkidle")

            assert page.locator("text=Duplicate Groups").count() > 0
            print("  ✅ 'Duplicate Groups' title found")

            # Test 5: Scanner page
            print("\n✓ Test 5: Scanner page")
            page.click("text=Scanner")
            page.wait_for_load_state("networkidle")

            # Check for scanner elements
            assert page.locator("text=NAS Scan").count() > 0
            print("  ✅ 'NAS Scan' section found")

            assert page.locator("text=Duplicate Detection").count() > 0
            print("  ✅ 'Duplicate Detection' section found")

            # Check for textarea
            textarea = page.locator("textarea")
            assert textarea.count() > 0
            print("  ✅ NAS paths textarea found")

            # Check buttons
            assert page.locator("button:has-text('Start Scan')").count() > 0
            print("  ✅ 'Start Scan' button found")

            assert page.locator("button:has-text('Run Duplicate Detection')").count() > 0
            print("  ✅ 'Run Duplicate Detection' button found")

            # Test 6: Settings page
            print("\n✓ Test 6: Settings page")
            page.click("text=Settings")
            page.wait_for_load_state("networkidle")

            assert page.locator("text=NAS Configuration").count() > 0
            print("  ✅ 'NAS Configuration' section found")

            assert page.locator("text=Database").count() > 0
            print("  ✅ 'Database' section found")

            assert page.locator("text=10.27.10.11").count() > 0
            print("  ✅ NAS host displayed")

            # Test 7: Navigation back to Dashboard
            print("\n✓ Test 7: Navigation consistency")
            page.click("text=Dashboard")
            page.wait_for_load_state("networkidle")
            assert page.locator("text=Total Files").count() > 0
            print("  ✅ Can navigate back to Dashboard")

            # Test 8: Check for console errors
            print("\n✓ Test 8: Console errors")
            if console_errors:
                print(f"  ⚠️  Found {len(console_errors)} console errors:")
                for i, error in enumerate(console_errors[:5], 1):
                    print(f"     {i}. {error[:100]}...")
                if len(console_errors) > 5:
                    print(f"     ... and {len(console_errors) - 5} more")
            else:
                print("  ✅ No console errors found")

            # Test 9: Check for page errors
            print("\n✓ Test 9: Page errors")
            if page_errors:
                print(f"  ❌ Found {len(page_errors)} page errors:")
                for i, error in enumerate(page_errors, 1):
                    print(f"     {i}. {error}")
                return False
            else:
                print("  ✅ No page errors found")

            # Test 10: Take screenshot
            print("\n✓ Test 10: Screenshot capture")
            screenshot_path = "/home/mercury/projects/mediavault/test_screenshot.png"
            page.screenshot(path=screenshot_path, full_page=True)
            print(f"  ✅ Screenshot saved to {screenshot_path}")

            print("\n" + "=" * 60)
            print("🎉 All tests passed!")
            print("=" * 60)

            # Summary
            print("\n📊 Test Summary:")
            print(f"  ✅ All 5 pages loaded successfully")
            print(f"  ✅ Navigation works correctly")
            print(f"  ✅ All expected elements found")
            print(f"  ✅ Console errors: {len(console_errors)}")
            print(f"  ✅ Page errors: {len(page_errors)}")

            return True

        except Exception as e:
            print(f"\n❌ Test failed with error: {e}")
            print(f"\n   Error type: {type(e).__name__}")
            print(f"   Current URL: {page.url}")

            # Print console errors if any
            if console_errors:
                print(f"\n   Console errors encountered:")
                for err in console_errors[-5:]:
                    print(f"     - {err[:200]}")

            # Print page errors if any
            if page_errors:
                print(f"\n   Page errors encountered:")
                for err in page_errors:
                    print(f"     - {err[:200]}")

            print(f"\n📸 Taking error screenshot...")
            page.screenshot(path="/home/mercury/projects/mediavault/error_screenshot.png")
            print(f"  Saved to error_screenshot.png")
            import traceback
            traceback.print_exc()
            return False

        finally:
            browser.close()

def test_backend_health(base_url="http://localhost:8007"):
    """Test backend API health"""
    import urllib.request
    import json

    print("\n🔌 Testing Backend API")
    print("-" * 60)

    try:
        with urllib.request.urlopen(f"{base_url}/api/health") as response:
            data = json.loads(response.read())
            print(f"  ✅ Backend is healthy")
            print(f"  ✅ App: {data.get('app')}")
            print(f"  ✅ Version: {data.get('version')}")
            print(f"  ✅ Environment: {data.get('environment')}")
            return True
    except Exception as e:
        print(f"  ❌ Backend health check failed: {e}")
        return False

if __name__ == "__main__":
    print("""
╔═══════════════════════════════════════════════════════╗
║         MediaVault Frontend Test Suite               ║
║         Playwright Headless Browser Testing           ║
╚═══════════════════════════════════════════════════════╝
    """)

    # Test backend first
    backend_ok = test_backend_health()

    if not backend_ok:
        print("\n⚠️  Backend not responding. Make sure it's running on port 8007")
        sys.exit(1)

    # Test frontend
    frontend_ok = test_mediavault()

    if frontend_ok:
        print("\n✅ MediaVault is ready for production!")
        sys.exit(0)
    else:
        print("\n❌ Tests failed. Please review errors above.")
        sys.exit(1)
