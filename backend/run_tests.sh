#!/bin/bash
# Test runner for CloudAgentPR backend services
# Usage: ./run_tests.sh [service_name] [--integration]

set -e

cd "$(dirname "$0")"

# Activate venv if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

show_help() {
    echo "Usage: ./run_tests.sh [options] [service]"
    echo ""
    echo "Services:"
    echo "  ai          Test AI service (OpenRouter integration)"
    echo "  code        Test code execution service"
    echo "  docker      Test Docker detection"
    echo "  stack       Test stack detector"
    echo "  all         Run all tests (default)"
    echo ""
    echo "Options:"
    echo "  --integration   Include integration tests (requires OPENROUTER_API_KEY)"
    echo "  --verbose, -v   Verbose output"
    echo "  --help, -h      Show this help"
    echo ""
    echo "Examples:"
    echo "  ./run_tests.sh                      # Run all unit tests"
    echo "  ./run_tests.sh ai                   # Test only AI service"
    echo "  ./run_tests.sh ai --integration     # Test AI with real API calls"
    echo "  ./run_tests.sh all -v               # All tests, verbose"
}

# Parse arguments
SERVICE="all"
INTEGRATION=""
VERBOSE=""

for arg in "$@"; do
    case $arg in
        --integration)
            INTEGRATION="1"
            ;;
        --verbose|-v)
            VERBOSE="-v"
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        ai|code|docker|stack|all)
            SERVICE="$arg"
            ;;
        *)
            echo -e "${RED}Unknown argument: $arg${NC}"
            show_help
            exit 1
            ;;
    esac
done

# Map service names to test files
get_test_file() {
    case $1 in
        ai)     echo "tests/test_ai_service.py" ;;
        code)   echo "tests/test_code_execution.py" ;;
        docker) echo "tests/test_docker_detection.py" ;;
        stack)  echo "tests/test_stack_detector.py" ;;
        all)    echo "tests/" ;;
    esac
}

# Check for integration test requirements
if [ -n "$INTEGRATION" ]; then
    if [ -z "$OPENROUTER_API_KEY" ]; then
        echo -e "${YELLOW}Warning: OPENROUTER_API_KEY not set${NC}"
        echo "Integration tests will be skipped."
        echo "Set it with: export OPENROUTER_API_KEY=your-key"
        echo ""
    fi
fi

TEST_PATH=$(get_test_file "$SERVICE")

echo -e "${GREEN}Running tests for: ${SERVICE}${NC}"
echo "Test path: $TEST_PATH"
echo ""

# Build pytest command
PYTEST_CMD="python3 -m pytest $TEST_PATH $VERBOSE"

if [ -z "$INTEGRATION" ]; then
    # Skip integration tests by default
    PYTEST_CMD="$PYTEST_CMD -k 'not Integration'"
fi

# Run tests
echo -e "${YELLOW}$ $PYTEST_CMD${NC}"
echo ""

eval $PYTEST_CMD

echo ""
echo -e "${GREEN}✓ Tests completed${NC}"
