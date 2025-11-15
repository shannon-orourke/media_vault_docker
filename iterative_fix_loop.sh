#!/bin/bash
# ========================================================================
# MediaVault - Automated Test-Fix Loop
# ========================================================================
# Runs tests, shows results, waits for AI to make fixes, repeats
# Test time: ~90 seconds | AI fix time: 5 minutes between iterations
# ========================================================================

set -e

# ========================================================================
# Configuration
# ========================================================================
ITERATIONS=5
WAIT_SECONDS=300  # 5 minutes for AI to review and make fixes
PROJECT_DIR="/home/mercury/projects/mediavault"
RESULTS_DIR="${PROJECT_DIR}/test_results"
TEST_FILE="tests/test_streaming_e2e.py"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ========================================================================
# Setup
# ========================================================================
cd "$PROJECT_DIR"
mkdir -p "$RESULTS_DIR"

# ========================================================================
# Function: Restart Backend
# ========================================================================
restart_backend() {
    echo -e "${BLUE}Restarting backend (forceful - killing all workers)...${NC}"

    # Stop service quietly
    sudo systemctl stop mediavault-backend 2>/dev/null || true

    # Kill any remaining uvicorn workers quietly
    pkill -9 -f "uvicorn app.main:app" 2>/dev/null || true
    sleep 2

    # Start service
    sudo systemctl start mediavault-backend 2>/dev/null

    # Wait for startup
    sleep 5

    # Check if running
    if sudo systemctl is-active --quiet mediavault-backend; then
        echo -e "${GREEN}[OK] Backend restarted successfully${NC}"
        return 0
    else
        echo -e "${RED}[FAIL] Backend failed to start${NC}"
        return 1
    fi
}

# ========================================================================
# Function: Run Tests
# ========================================================================
run_tests() {
    local iteration=$1
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local output_file="${RESULTS_DIR}/iteration_${iteration}_${timestamp}.txt"

    # Echo to stderr so it doesn't interfere with the return value
    echo -e "${BLUE}Running test suite...${NC}" >&2

    # Run tests from backend directory
    cd "${PROJECT_DIR}/backend"

    # Run tests and capture ALL output
    if python -m pytest "$TEST_FILE" -v --tb=short > "$output_file" 2>&1; then
        test_exit_code=0
    else
        test_exit_code=$?
    fi

    cd "$PROJECT_DIR"

    # Check if output file has content
    if [ ! -s "$output_file" ]; then
        echo "0|0|0|$output_file"
        return
    fi

    # Parse results with safer regex
    local passed=$(grep -oP '\d+(?= passed)' "$output_file" 2>/dev/null | head -1)
    local failed=$(grep -oP '\d+(?= failed)' "$output_file" 2>/dev/null | head -1)

    # Default to 0 if not found
    passed=${passed:-0}
    failed=${failed:-0}
    local total=$((passed + failed))

    # Use pipe delimiter to avoid space issues (output to stdout ONLY)
    echo "$passed|$failed|$total|$output_file"
}

# ========================================================================
# Function: Extract Failure Details
# ========================================================================
extract_failures() {
    local output_file=$1

    if [ ! -f "$output_file" ] || [ ! -s "$output_file" ]; then
        echo "No output file or file is empty"
        return
    fi

    # Extract failed test names and reasons
    grep -A 1 "FAILED.*test_streaming_e2e.py" "$output_file" 2>/dev/null | \
        sed 's/tests\/test_streaming_e2e.py:://' | \
        grep -v "^--$" || echo "No failures found in output"
}

# ========================================================================
# Function: Countdown Timer with Progress Bar
# ========================================================================
countdown() {
    local seconds=$1
    local message=$2

    echo ""
    echo -e "${YELLOW}${message}${NC}"
    echo -e "${CYAN}AI will make fixes during this time${NC}"
    echo -e "${CYAN}Press Enter to skip wait, or Ctrl+C to exit${NC}"
    echo ""

    for ((i=seconds; i>0; i--)); do
        # Calculate progress bar
        local progress=$((100 - (i * 100 / seconds)))
        local filled=$((progress / 2))
        local empty=$((50 - filled))

        # Build progress bar (ASCII only)
        local bar="["
        for ((j=0; j<filled; j++)); do bar+="="; done
        for ((j=0; j<empty; j++)); do bar+=" "; done
        bar+="]"

        # Print progress
        printf "\r   ${bar} ${i}s remaining   "

        # Check if user pressed Enter (with 1 second timeout)
        read -t 1 -n 1 && break
    done

    echo ""
    echo ""
}

# ========================================================================
# Main Loop
# ========================================================================
echo ""
echo -e "${GREEN}========================================"
echo -e "  MediaVault Automated Fix Loop"
echo -e "========================================${NC}"
echo ""
echo "Iterations: $ITERATIONS"
echo "Test time: ~90 seconds"
echo "AI fix time: ${WAIT_SECONDS}s (5 minutes)"
echo "Results: $RESULTS_DIR/"
echo ""

# Track results across iterations
declare -a iteration_results

for iteration in $(seq 1 $ITERATIONS); do
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  ITERATION $iteration of $ITERATIONS${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""

    # Restart backend
    if ! restart_backend; then
        echo -e "${RED}Failed to restart backend, aborting${NC}"
        exit 1
    fi

    echo ""

    # Run tests and parse results with pipe delimiter
    result=$(run_tests $iteration)
    IFS='|' read -r passed failed total output_file <<< "$result"

    # Store results
    iteration_results+=("$iteration:$passed:$failed:$total:$output_file")

    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  ITERATION $iteration RESULTS${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""

    # Validate numeric values before comparison
    if ! [[ "$failed" =~ ^[0-9]+$ ]] || ! [[ "$passed" =~ ^[0-9]+$ ]]; then
        echo -e "${RED}ERROR: Test parsing failed${NC}"
        echo -e "${YELLOW}Output file: $output_file${NC}"
        echo ""
        echo -e "${YELLOW}First 20 lines of output:${NC}"
        head -20 "$output_file" 2>/dev/null || echo "Could not read output file"
        echo ""

        # Wait before retrying if not last iteration
        if [ $iteration -lt $ITERATIONS ]; then
            countdown $WAIT_SECONDS "Waiting 5 minutes before retry..."
        fi
        continue
    fi

    # Show summary
    if [ "$failed" -eq 0 ] && [ "$total" -gt 0 ]; then
        echo -e "${GREEN}*** ALL TESTS PASSED! ***${NC}"
        echo -e "${GREEN}$passed/$total tests passing${NC}"
        echo ""
        echo -e "${GREEN}SUCCESS! All tests pass. Exiting loop.${NC}"
        echo ""
        break
    elif [ "$total" -eq 0 ]; then
        echo -e "${RED}ERROR: No tests found or tests did not run${NC}"
        echo -e "${YELLOW}Output file: $output_file${NC}"
        echo ""

        # Wait before retrying if not last iteration
        if [ $iteration -lt $ITERATIONS ]; then
            countdown $WAIT_SECONDS "Waiting 5 minutes before retry..."
        fi
    else
        echo -e "Results: ${GREEN}$passed passed${NC}, ${RED}$failed failed${NC} (Total: $total)"
        echo ""

        echo -e "${RED}FAILED TESTS:${NC}"
        extract_failures "$output_file" | while read -r line; do
            if [[ $line == *"::"* ]]; then
                # Test name
                echo -e "  [X] $line"
            elif [[ -n "$line" ]]; then
                # Error message
                echo -e "      -> $line"
            fi
        done
        echo ""

        echo -e "${BLUE}Full output:${NC} $output_file"
        echo ""

        # Only wait if not last iteration
        if [ $iteration -lt $ITERATIONS ]; then
            countdown $WAIT_SECONDS "Waiting 5 minutes for AI to review and make fixes..."
        fi
    fi
done

# ========================================================================
# Final Summary
# ========================================================================
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  FINAL SUMMARY${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

echo "Iteration | Passed | Failed | Total | Status | Output File"
echo "----------|--------|--------|-------|--------|------------------"

for result in "${iteration_results[@]}"; do
    IFS=':' read -r iter passed failed total file <<< "$result"

    # Validate before comparison
    if [[ "$failed" =~ ^[0-9]+$ ]] && [ "$failed" -eq 0 ] && [ "$total" -gt 0 ]; then
        status="${GREEN}  OK  ${NC}"
    else
        status="${RED} FAIL ${NC}"
    fi

    printf "    %-2s    | %6s | %6s | %5s | %b | %s\n" \
        "$iter" "$passed" "$failed" "$total" "$status" "$(basename "$file")"
done

echo ""

# Check if we ended with all passing
if [ ${#iteration_results[@]} -gt 0 ]; then
    last_result="${iteration_results[-1]}"
    IFS=':' read -r iter passed failed total file <<< "$last_result"

    if [[ "$failed" =~ ^[0-9]+$ ]] && [ "$failed" -eq 0 ] && [ "$total" -gt 0 ]; then
        echo -e "${GREEN}========================================"
        echo -e "  *** ALL TESTS PASSING! ***"
        echo -e "========================================${NC}"
        echo ""
        echo -e "${GREEN}Video streaming is now working!${NC}"
        echo -e "${GREEN}Check /tmp/video_playing.png for proof.${NC}"
        echo ""
    else
        echo -e "${YELLOW}========================================"
        echo -e "  Tests completed - some still failing"
        echo -e "========================================${NC}"
        echo ""
        echo -e "${YELLOW}Review the output files above for details.${NC}"
        echo ""
    fi
fi
