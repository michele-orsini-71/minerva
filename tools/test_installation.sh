#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TEST_DIR="/tmp/minerva-install-test-$$"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

cleanup() {
    log_info "Cleaning up test directory: $TEST_DIR"
    rm -rf "$TEST_DIR"
}

trap cleanup EXIT

test_pipx_installation() {
    log_info "========================================="
    log_info "Testing pipx installation method"
    log_info "========================================="

    if ! command -v pipx &> /dev/null; then
        log_error "pipx is not installed. Install it with: pip install pipx"
        return 1
    fi

    log_info "Creating test directory: $TEST_DIR/pipx-test"
    mkdir -p "$TEST_DIR/pipx-test"
    cd "$TEST_DIR/pipx-test"

    log_info "Installing minerva with pipx..."
    PIPX_HOME="$TEST_DIR/pipx-test/.pipx" PIPX_BIN_DIR="$TEST_DIR/pipx-test/bin" \
        pipx install "$PROJECT_ROOT"

    export PATH="$TEST_DIR/pipx-test/bin:$PATH"

    log_info "Verifying minerva command is available..."
    if ! command -v minerva &> /dev/null; then
        log_error "minerva command not found after pipx install"
        return 1
    fi

    log_info "Testing minerva --version..."
    minerva --version

    log_info "Testing minerva --help..."
    minerva --help > /dev/null

    log_info "Testing all four commands help text..."
    minerva index --help > /dev/null
    minerva serve --help > /dev/null
    minerva peek --help > /dev/null
    minerva validate --help > /dev/null

    log_info "✅ pipx installation test PASSED"

    log_info "Uninstalling minerva..."
    PIPX_HOME="$TEST_DIR/pipx-test/.pipx" PIPX_BIN_DIR="$TEST_DIR/pipx-test/bin" \
        pipx uninstall minerva

    return 0
}

test_pip_alias_installation() {
    log_info "========================================="
    log_info "Testing pip+alias installation method"
    log_info "========================================="

    log_info "Creating test directory: $TEST_DIR/pip-test"
    mkdir -p "$TEST_DIR/pip-test"
    cd "$TEST_DIR/pip-test"

    log_info "Creating virtual environment..."
    python3 -m venv .venv

    log_info "Activating virtual environment..."
    source .venv/bin/activate

    log_info "Installing minerva with pip..."
    pip install -e "$PROJECT_ROOT" > /dev/null 2>&1

    log_info "Creating shell alias..."
    MINERVIUM_BIN="$(pwd)/.venv/bin/minerva"

    if [ ! -f "$MINERVIUM_BIN" ]; then
        log_error "minerva binary not found at $MINERVIUM_BIN"
        deactivate
        return 1
    fi

    log_info "Testing minerva command (via direct path)..."
    "$MINERVIUM_BIN" --version

    log_info "Testing minerva --help..."
    "$MINERVIUM_BIN" --help > /dev/null

    log_info "Testing all four commands help text..."
    "$MINERVIUM_BIN" index --help > /dev/null
    "$MINERVIUM_BIN" serve --help > /dev/null
    "$MINERVIUM_BIN" peek --help > /dev/null
    "$MINERVIUM_BIN" validate --help > /dev/null

    log_info "✅ pip+alias installation test PASSED"

    log_info "Deactivating virtual environment..."
    deactivate

    return 0
}

test_extractors() {
    log_info "========================================="
    log_info "Testing extractor installations"
    log_info "========================================="

    log_info "Creating test directory: $TEST_DIR/extractors-test"
    mkdir -p "$TEST_DIR/extractors-test"
    cd "$TEST_DIR/extractors-test"

    log_info "Creating virtual environment..."
    python3 -m venv .venv
    source .venv/bin/activate

    log_info "Installing bear-notes-extractor..."
    pip install -e "$PROJECT_ROOT/extractors/bear-notes-extractor" > /dev/null 2>&1

    log_info "Testing bear-extractor command..."
    bear-extractor --help > /dev/null

    log_info "Installing zim-extractor..."
    pip install -e "$PROJECT_ROOT/extractors/zim-extractor" > /dev/null 2>&1

    log_info "Testing zim-extractor command..."
    zim-extractor --help > /dev/null

    log_info "Installing markdown-books-extractor..."
    pip install -e "$PROJECT_ROOT/extractors/markdown-books-extractor" > /dev/null 2>&1

    log_info "Testing markdown-books-extractor command..."
    markdown-books-extractor --help > /dev/null

    log_info "✅ All extractors installation test PASSED"

    deactivate
    return 0
}

main() {
    log_info "Starting Minervium installation tests..."
    log_info "Project root: $PROJECT_ROOT"
    log_info "Test directory: $TEST_DIR"
    echo ""

    FAILED=0

    if test_pipx_installation; then
        log_info "✅ pipx installation: SUCCESS"
    else
        log_error "❌ pipx installation: FAILED"
        FAILED=$((FAILED + 1))
    fi
    echo ""

    if test_pip_alias_installation; then
        log_info "✅ pip+alias installation: SUCCESS"
    else
        log_error "❌ pip+alias installation: FAILED"
        FAILED=$((FAILED + 1))
    fi
    echo ""

    if test_extractors; then
        log_info "✅ extractors installation: SUCCESS"
    else
        log_error "❌ extractors installation: FAILED"
        FAILED=$((FAILED + 1))
    fi
    echo ""

    log_info "========================================="
    log_info "Installation Test Summary"
    log_info "========================================="

    if [ $FAILED -eq 0 ]; then
        log_info "✅ ALL TESTS PASSED"
        return 0
    else
        log_error "❌ $FAILED TEST(S) FAILED"
        return 1
    fi
}

main "$@"
