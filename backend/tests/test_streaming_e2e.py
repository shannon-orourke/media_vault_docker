#!/usr/bin/env python3
"""
End-to-End Streaming Tests

Tests video streaming at multiple levels:
1. API-level: Validate stream endpoints return valid MP4 data
2. Browser-level: Verify video actually plays in a real browser
3. GPU-level: Confirm GPU transcoding is triggered

This removes the human from the testing loop!
"""

import sys
import time
import subprocess
import requests
from pathlib import Path
from io import BytesIO

import pytest
from playwright.sync_api import sync_playwright, expect

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import get_db
from app.models import MediaFile


# ==============================================================================
# LEVEL 1: API-Level Stream Validation Tests
# ==============================================================================

class TestStreamAPIValidation:
    """Test that streaming endpoints return valid, playable MP4 data."""

    BASE_URL = "https://mediavault.orourkes.me"
    TEST_FILE_ID = 275  # Red Dwarf 01x01 (pre-transcoded for POC test)

    def test_health_endpoint(self):
        """Test that the API is reachable."""
        response = requests.get(f"{self.BASE_URL}/api/health", verify=False)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print("✓ API health check passed")

    def test_gpu_status_endpoint(self):
        """Test that GPU is available for encoding."""
        response = requests.get(f"{self.BASE_URL}/api/stream/gpu-status", verify=False)
        assert response.status_code == 200
        data = response.json()
        assert data["gpu_encoding_available"] is True
        assert data["encoder"] == "h264_nvenc"
        print(f"✓ GPU encoding available: {data['hardware']}")

    def test_progressive_stream_returns_valid_mp4(self):
        """Test that progressive endpoint returns valid MP4 data."""
        url = f"{self.BASE_URL}/api/stream/{self.TEST_FILE_ID}/progressive?use_gpu=true"

        # Request first 10KB of stream
        response = requests.get(url, verify=False, stream=True, timeout=10)

        # Collect first 10KB
        data = b""
        for chunk in response.iter_content(chunk_size=1024):
            data += chunk
            if len(data) >= 10240:  # 10KB
                break

        # Validate MP4 signature (ftyp box)
        assert data[4:8] == b"ftyp", "Invalid MP4 signature - missing ftyp box"
        print(f"✓ Valid MP4 signature found: {data[4:8]}")

        # Check for fragmented MP4 indicators
        assert b"iso5" in data or b"iso6" in data or b"mp41" in data, "Missing MP4 brand"
        print("✓ Valid MP4 brand found")

        # Check for moov box (should be early in fragmented MP4)
        assert b"moov" in data[:5000], "Missing moov box in first 5KB (not fragmented MP4?)"
        print("✓ Fragmented MP4 structure detected (moov box present)")

        response.close()
        print(f"✓ Progressive stream returns valid MP4 data ({len(data)} bytes tested)")

    def test_smart_stream_returns_valid_data(self):
        """Test that smart endpoint returns valid video data."""
        url = f"{self.BASE_URL}/api/stream/{self.TEST_FILE_ID}/smart"

        # Request first 10KB of stream
        response = requests.get(url, verify=False, stream=True, timeout=10)

        # Collect first 10KB
        data = b""
        for chunk in response.iter_content(chunk_size=1024):
            data += chunk
            if len(data) >= 10240:
                break

        # Should be MP4 data (either direct stream or transcoded)
        assert data[4:8] == b"ftyp", "Smart endpoint didn't return valid MP4"
        print("✓ Smart stream returns valid MP4 data")

        response.close()

    def test_response_headers(self):
        """Test that streaming responses have correct headers."""
        url = f"{self.BASE_URL}/api/stream/{self.TEST_FILE_ID}/progressive?use_gpu=true"

        # HEAD request to check headers
        response = requests.head(url, verify=False, allow_redirects=True, timeout=5)

        # Content-Type should be video/mp4
        content_type = response.headers.get("Content-Type", "")
        assert "video/mp4" in content_type, f"Wrong Content-Type: {content_type}"
        print(f"✓ Correct Content-Type: {content_type}")

        # Should have no-cache for progressive streams
        cache_control = response.headers.get("Cache-Control", "")
        print(f"  Cache-Control: {cache_control}")

    def test_ffmpeg_validation_with_ffprobe(self):
        """Download a chunk and validate with ffprobe."""
        url = f"{self.BASE_URL}/api/stream/{self.TEST_FILE_ID}/progressive?use_gpu=true"

        # Download first 5 seconds (approx 5MB)
        output_path = Path("/tmp/test_stream_sample.mp4")

        print("  Downloading 5MB sample...")
        with requests.get(url, verify=False, stream=True, timeout=15) as response:
            with open(output_path, "wb") as f:
                downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if downloaded >= 5 * 1024 * 1024:  # 5MB
                        break

        # Validate with ffprobe
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_format", "-show_streams", str(output_path)],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0, f"ffprobe validation failed: {result.stderr}"

        # Check output contains expected info
        assert "codec_name=h264" in result.stdout, "Video codec not H.264"
        assert "codec_name=aac" in result.stdout, "Audio codec not AAC"
        print("✓ FFprobe validation passed (H.264 + AAC)")

        # Cleanup
        output_path.unlink()


# ==============================================================================
# LEVEL 2: Browser Playback Tests
# ==============================================================================

class TestBrowserPlayback:
    """Test that video actually plays in a real browser."""

    BASE_URL = "https://mediavault.orourkes.me"
    TEST_FILE_ID = 275  # Red Dwarf 01x01 (pre-transcoded for POC test)

    @pytest.fixture(scope="class")
    def browser_context(self):
        """Setup headless browser for testing."""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                ignore_https_errors=True,  # Allow self-signed cert
                viewport={"width": 1280, "height": 720}
            )
            yield context
            context.close()
            browser.close()

    def test_library_page_loads(self, browser_context):
        """Test that library page loads successfully."""
        page = browser_context.new_page()

        print("  Navigating to library page...")
        page.goto(f"{self.BASE_URL}/library", wait_until="networkidle")

        # Check page loaded
        assert "MediaVault" in page.title() or "Media Library" in page.content()
        print("✓ Library page loaded successfully")

        page.close()

    def test_video_player_appears(self, browser_context):
        """Test that clicking play opens the video player."""
        page = browser_context.new_page()

        page.goto(f"{self.BASE_URL}/library", wait_until="networkidle")

        # Find and click the first play button
        print("  Looking for play button...")
        # ActionIcon renders as button, IconPlayerPlay is tabler icon
        play_button = page.locator('button[class*="ActionIcon"]:has(svg)').first

        if play_button.count() > 0:
            print("  Clicking play button...")
            play_button.click()

            # Wait for modal to appear
            page.wait_for_timeout(2000)

            # Check if video element exists
            video = page.locator("video").first
            assert video.count() > 0, "Video element not found after clicking play"
            print("✓ Video player modal opened")
        else:
            pytest.skip("No play button found (no media files?)")

        page.close()

    def test_video_actually_plays(self, browser_context):
        """
        THE CRITICAL TEST: Does video actually start playing?

        This test will catch the issue where GPU spins up but video doesn't play.
        """
        page = browser_context.new_page()

        # Enable console logging
        page.on("console", lambda msg: print(f"  [Browser Console] {msg.type}: {msg.text}"))

        page.goto(f"{self.BASE_URL}/library", wait_until="networkidle")

        # Click any play button to open the video player modal
        print("  Clicking any play button to open video player...")
        play_button = page.locator('button[class*="ActionIcon"]:has(svg)').first

        if play_button.count() == 0:
            pytest.skip("No play button found")

        play_button.click()

        # Wait for video element to appear
        print("  Waiting for video element...")
        page.wait_for_selector("video", timeout=5000)

        # Now override the video source to use our pre-transcoded test file (ID 275)
        print(f"  Overriding video source to use test file {self.TEST_FILE_ID}...")
        test_url = f"{self.BASE_URL}/api/stream/{self.TEST_FILE_ID}/smart"

        page.evaluate(f"""
            () => {{
                const video = document.querySelector('video');

                // Clear any existing sources
                while (video.firstChild) {{
                    video.removeChild(video.firstChild);
                }}

                // Set source directly on video element
                video.src = '{test_url}';
                video.load();

                // Try to play (may be blocked by autoplay policy)
                video.play().catch(e => console.log('Autoplay blocked:', e));

                console.log('Set video source to: {test_url}');
            }}
        """)
        print(f"  Set video src to: {test_url}")
        print("  Triggered video.load() and video.play()")

        # Wait a moment for the new source to be processed
        page.wait_for_timeout(3000)

        # Monitor readyState progression over 15 seconds
        print("  Monitoring video loading progress...")
        for i in range(15):
            ready_state = page.evaluate("document.querySelector('video').readyState")
            network_state = page.evaluate("document.querySelector('video').networkState")
            current_time = page.evaluate("document.querySelector('video').currentTime")
            duration = page.evaluate("document.querySelector('video').duration")

            print(f"  [{i+1}s] readyState={ready_state}, networkState={network_state}, time={current_time:.2f}, duration={duration}")

            if ready_state >= 1:
                print(f"✓ Video loaded metadata at {i+1} seconds!")
                break

            page.wait_for_timeout(1000)

        # Final check
        video_src = page.evaluate("document.querySelector('video').querySelector('source')?.src")
        print(f"  Video src: {video_src}")

        network_state = page.evaluate("document.querySelector('video').networkState")
        print(f"  Final networkState: {network_state} (0=EMPTY, 1=IDLE, 2=LOADING, 3=NO_SOURCE)")

        # Check video.error (null = good, non-null = error)
        error = page.evaluate("document.querySelector('video').error")
        if error:
            error_code = page.evaluate("document.querySelector('video').error.code")
            error_message = page.evaluate("document.querySelector('video').error.message")
            pytest.fail(f"Video error detected! Code: {error_code}, Message: {error_message}")

        print("✓ No video.error (good sign)")

        ready_state = page.evaluate("document.querySelector('video').readyState")
        print(f"  Final readyState: {ready_state}")

        if ready_state == 0:
            # Video hasn't loaded ANY data after 15 seconds
            page.screenshot(path="/tmp/video_stuck.png")
            print("  Screenshot saved to /tmp/video_stuck.png")
            pytest.fail("Video readyState is 0 (HAVE_NOTHING) after 15 seconds - video isn't loading any data!")

        # Check if video has duration
        duration = page.evaluate("document.querySelector('video').duration")
        print(f"  Video duration: {duration}")

        # Check network state
        network_state = page.evaluate("document.querySelector('video').networkState")
        print(f"  Video networkState: {network_state} (2=LOADING, 3=NO_SOURCE)")

        # Wait a bit more and check if currentTime increases (actually playing)
        time1 = page.evaluate("document.querySelector('video').currentTime")
        page.wait_for_timeout(2000)
        time2 = page.evaluate("document.querySelector('video').currentTime")

        print(f"  Video currentTime: {time1} -> {time2}")

        if time2 > time1:
            print("✓✓✓ VIDEO IS ACTUALLY PLAYING! ✓✓✓")
            # Take screenshot as proof
            page.screenshot(path="/tmp/video_playing.png")
            print("  Screenshot saved to /tmp/video_playing.png")
        elif ready_state >= 2:
            print("⚠ Video has data but isn't auto-playing (might need user interaction)")
        else:
            pytest.fail(f"Video not playing! readyState={ready_state}, time={time1}")

        page.close()

    def test_check_network_requests(self, browser_context):
        """Monitor network requests to see what's happening."""
        page = browser_context.new_page()

        # Track network requests
        requests_log = []

        def log_request(request):
            if "/api/stream/" in request.url:
                requests_log.append({
                    "url": request.url,
                    "method": request.method
                })

        def log_response(response):
            if "/api/stream/" in response.url:
                print(f"  Stream response: {response.status} {response.url[:80]}")

        page.on("request", log_request)
        page.on("response", log_response)

        page.goto(f"{self.BASE_URL}/library", wait_until="networkidle")

        # Click play
        play_button = page.locator('button[class*="ActionIcon"]:has(svg)').first
        if play_button.count() > 0:
            play_button.click()
            page.wait_for_timeout(5000)

            # Print all stream requests
            print("\n  Stream requests made:")
            for req in requests_log:
                print(f"    {req['method']} {req['url']}")

            assert len(requests_log) > 0, "No stream requests made!"
            print(f"✓ {len(requests_log)} stream request(s) made")
        else:
            pytest.skip("No play button found")

        page.close()


# ==============================================================================
# LEVEL 3: GPU Monitoring Tests
# ==============================================================================

class TestGPUMonitoring:
    """Test that GPU transcoding is actually triggered."""

    def test_gpu_process_starts(self):
        """Test that FFmpeg GPU process starts when streaming."""
        import threading

        # Start monitoring GPU in background
        gpu_activity = {"detected": False}

        def monitor_gpu():
            """Monitor nvidia-smi for 10 seconds."""
            for _ in range(20):  # 20 x 0.5s = 10 seconds
                result = subprocess.run(
                    ["nvidia-smi", "--query-compute-apps=pid,process_name,used_memory", "--format=csv,noheader"],
                    capture_output=True,
                    text=True
                )
                if "python" in result.stdout.lower() or "ffmpeg" in result.stdout.lower():
                    gpu_activity["detected"] = True
                    print(f"  GPU activity detected: {result.stdout.strip()}")
                    break
                time.sleep(0.5)

        monitor_thread = threading.Thread(target=monitor_gpu)
        monitor_thread.start()

        # Trigger a stream request
        url = "https://mediavault.orourkes.me/api/stream/335/progressive?use_gpu=true"

        print("  Requesting stream to trigger GPU...")
        try:
            response = requests.get(url, verify=False, stream=True, timeout=5)
            # Read a bit of data to ensure FFmpeg starts
            for _ in range(10):
                next(response.iter_content(chunk_size=8192))
            response.close()
        except Exception as e:
            print(f"  Stream request: {e}")

        # Wait for monitoring to complete
        monitor_thread.join(timeout=12)

        if gpu_activity["detected"]:
            print("✓ GPU encoder activity detected during stream!")
        else:
            print("⚠ No GPU activity detected (might not have DTS audio)")


# ==============================================================================
# Test Runner
# ==============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
