# Automated Iterative Test-Fix Loop

## What It Does

Removes you from the manual test-restart-test cycle! This script:

1. **Forcefully restarts backend** (stops service + kills workers + starts fresh)
2. **Runs full test suite** automatically (~90 seconds)
3. **Shows results** (passed/failed with details)
4. **Waits 5 minutes** for AI to review results and make fixes
5. **Repeats** for 5 iterations (or until all tests pass)

## Usage

```bash
./iterative_fix_loop.sh
```

**That's it!** The script handles everything.

**Timing:**
- ~90 seconds for tests to run
- 5 minutes for AI to review and make fixes
- Automatic restart and re-test

## What You'll See

### Each Iteration Shows:

```
════════════════════════════════════════
  ITERATION 2 of 5
════════════════════════════════════════

⏳ Restarting backend (forceful - killing all workers)...
✓ Backend restarted successfully

⏳ Running test suite...
✓ Tests completed

════════════════════════════════════════
  ITERATION 2 RESULTS
════════════════════════════════════════

Results: 9 passed, 2 failed (Total: 11)

FAILED TESTS:
  ✗ TestStreamAPIValidation::test_response_headers
    → AssertionError: Wrong Content-Type: application/json

  ✗ TestBrowserPlayback::test_video_actually_plays
    → Video readyState: 0 (HAVE_NOTHING)

Full output: test_results/iteration_2_20251109_180422.txt

⏰ Waiting 5 minutes for AI to review results and make fixes...
   AI will make fixes during this time
   [███████████████████████░░░] 180s remaining
   Press Enter to skip wait, or Ctrl+C to exit
```

### During the 5 Minute Wait:

1. **AI reads the failure details** from test output
2. **AI makes code changes** to fix the issues
3. **Script auto-continues** - tests run again automatically
4. OR **Press Enter** to skip the wait and test immediately
5. OR **Press Ctrl+C** to exit the loop

### When All Tests Pass:

```
════════════════════════════════════════
  ✓✓✓ ALL TESTS PASSING! ✓✓✓
════════════════════════════════════════

Video streaming is now working!
Check /tmp/video_playing.png for proof.
```

**The loop exits automatically when all tests pass!**

## Features

### Forceful Backend Restart
- Stops systemd service
- Kills all uvicorn workers (fixes stale code issue)
- Starts fresh
- Waits 5 seconds for startup
- Verifies service is running

### Timestamped Results
All test outputs saved to `test_results/`:
```
test_results/
├── iteration_1_20251109_180305.txt
├── iteration_2_20251109_180422.txt
├── iteration_3_20251109_180539.txt
└── ...
```

You can compare results across iterations to see progress.

### Final Summary
At the end, shows side-by-side comparison:

```
════════════════════════════════════════
  FINAL SUMMARY
════════════════════════════════════════

Iteration | Passed | Failed | Total | Output File
----------|--------|--------|-------|-------------
    1     |      8 |      3 |    11 | ✗ iteration_1_20251109_180305.txt
    2     |      9 |      2 |    11 | ✗ iteration_2_20251109_180422.txt
    3     |     11 |      0 |    11 | ✓ iteration_3_20251109_180539.txt
```

## Configuration

Edit the script to customize:

```bash
ITERATIONS=5        # Number of iterations (default: 5)
WAIT_SECONDS=300    # Wait time between iterations (default: 300 = 5 minutes)
```

## Why This Helps

### Before (Manual Process):
1. Make code change
2. Run `sudo systemctl restart mediavault-backend`
3. Wait 5 seconds
4. Run `./test_streaming_automated.sh`
5. Wait 60 seconds for tests
6. Read results
7. Repeat from step 1
8. **You're the bottleneck!**

### After (Automated Loop):
1. Run `./iterative_fix_loop.sh` once
2. AI makes code changes during 5-minute waits
3. Script handles all restarts and testing
4. **Complete automation - no manual intervention needed**

## Exit Options

- **Auto-exit**: Loop exits when all tests pass
- **Manual exit**: Press Ctrl+C anytime
- **Skip wait**: Press Enter during countdown

## Root Cause Fixed

The original issue was **uvicorn multi-worker stale code**:
- HEAD handlers were in code but workers didn't reload
- Regular `systemctl restart` didn't kill all workers
- Some workers served old code → HTTP 405

This script does a **forceful restart** that fixes the issue:
```bash
sudo systemctl stop mediavault-backend
sudo pkill -9 -f "uvicorn app.main:app"  # Kill stale workers!
sleep 2
sudo systemctl start mediavault-backend
```

## Expected Outcome

After first iteration with forceful restart:
- ✅ HEAD handlers work (`Content-Type: video/mp4`)
- ✅ Video readyState goes from 0 → 2+
- ✅ Screenshot shows video playing
- ✅ **Video actually works!**

## Files Created

- `iterative_fix_loop.sh` - Main script
- `test_results/` - All test outputs (gitignored)
- This README

## Next Steps

Just run it:
```bash
./iterative_fix_loop.sh
```

Watch the magic happen! 🎉
