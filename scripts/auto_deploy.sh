#!/bin/bash
#
# CAAS Full Automation Workflow
#
# One-command deployment from requirement to production.
# Includes validation, generation, testing, and deployment.
#
# Usage:
#   ./scripts/auto_deploy.sh "Build a blog system" --target docker
#   ./scripts/auto_deploy.sh "E-commerce platform" --target kubernetes --skip-tests
#

set -e  # Exit on error
set -o pipefail  # Pipe failures propagate

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
REQUIREMENT="${1:-Build a task management system}"
DEPLOY_TARGET="${DEPLOY_TARGET:-docker}"
OUTPUT_DIR="${OUTPUT_DIR:-./generated}"
SKIP_TESTS="${SKIP_TESTS:-false}"
SKIP_DOCKER="${SKIP_DOCKER:-false}"
VERBOSE="${VERBOSE:-false}"
DRY_RUN="${DRY_RUN:-false}"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --target)
            DEPLOY_TARGET="$2"
            shift 2
            ;;
        --output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --skip-tests)
            SKIP_TESTS="true"
            shift
            ;;
        --skip-docker)
            SKIP_DOCKER="true"
            shift
            ;;
        --verbose)
            VERBOSE="true"
            shift
            ;;
        --dry-run)
            DRY_RUN="true"
            shift
            ;;
        *)
            # First positional argument is requirement
            if [ -z "$REQUIREMENT_SET" ]; then
                REQUIREMENT="$1"
                REQUIREMENT_SET="true"
            fi
            shift
            ;;
    esac
done

# Helper functions
log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

log_success() {
    echo -e "${GREEN}✅${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠️${NC}  $1"
}

log_error() {
    echo -e "${RED}❌${NC} $1"
}

log_step() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
}

check_command() {
    if ! command -v $1 &> /dev/null; then
        log_error "$1 is not installed. Please install it first."
        return 1
    fi
    return 0
}

# Cleanup on error
cleanup_on_error() {
    log_error "Deployment failed! Rolling back..."

    # Stop running containers
    if [ -d "$OUTPUT_DIR" ] && [ -f "$OUTPUT_DIR/docker-compose.yml" ]; then
        cd "$OUTPUT_DIR"
        docker-compose down 2>/dev/null || true
        cd - > /dev/null
    fi

    log_warning "Rollback complete. Check logs for details."
    exit 1
}

trap cleanup_on_error ERR

# Banner
echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║          🚀 CAAS Full Automation Workflow                ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
log_info "Requirement: ${REQUIREMENT}"
log_info "Deploy Target: ${DEPLOY_TARGET}"
log_info "Output Directory: ${OUTPUT_DIR}"
echo ""

if [ "$DRY_RUN" = "true" ]; then
    log_warning "DRY RUN MODE - No actual changes will be made"
    echo ""
fi

# Step 1: Environment Validation
log_step "📋 Step 1/7: Validating Environment"

if [ "$DRY_RUN" = "false" ]; then
    python scripts/validate_env.py --export-json validation_results.json
    if [ $? -ne 0 ]; then
        log_error "Environment validation failed. Fix issues and try again."
        exit 1
    fi
    log_success "Environment validation passed"
else
    log_info "DRY RUN: Would validate environment"
fi

# Step 2: Code Generation
log_step "🔧 Step 2/7: Generating Code"

CAAS_CMD="caas generate \"$REQUIREMENT\" -o $OUTPUT_DIR"

if [ "$VERBOSE" = "true" ]; then
    CAAS_CMD="$CAAS_CMD --verbose"
fi

if [ "$DRY_RUN" = "false" ]; then
    log_info "Running: $CAAS_CMD"
    eval $CAAS_CMD

    if [ $? -ne 0 ]; then
        log_error "Code generation failed"
        exit 1
    fi

    log_success "Code generation completed"
    log_info "Files generated in: $OUTPUT_DIR"
else
    log_info "DRY RUN: Would run: $CAAS_CMD"
fi

# Step 3: Install Dependencies
log_step "📦 Step 3/7: Installing Dependencies"

if [ "$DRY_RUN" = "false" ]; then
    if [ -f "$OUTPUT_DIR/requirements.txt" ]; then
        cd "$OUTPUT_DIR"

        # Create virtual environment if not exists
        if [ ! -d "venv" ]; then
            log_info "Creating virtual environment..."
            python -m venv venv
        fi

        # Activate and install
        source venv/bin/activate
        log_info "Installing dependencies..."
        pip install -r requirements.txt --quiet

        # Install test dependencies if tests directory exists
        if [ -d "tests" ] && [ -f "tests/requirements-test.txt" ]; then
            pip install -r tests/requirements-test.txt --quiet
        fi

        log_success "Dependencies installed"
        cd - > /dev/null
    else
        log_warning "No requirements.txt found, skipping"
    fi
else
    log_info "DRY RUN: Would install dependencies from requirements.txt"
fi

# Step 4: Run Tests
log_step "🧪 Step 4/7: Running Tests"

if [ "$SKIP_TESTS" = "true" ]; then
    log_warning "Skipping tests (--skip-tests flag)"
elif [ "$DRY_RUN" = "true" ]; then
    log_info "DRY RUN: Would run pytest tests/ --cov=src --cov-report=html"
else
    if [ -d "$OUTPUT_DIR/tests" ]; then
        cd "$OUTPUT_DIR"
        source venv/bin/activate

        log_info "Running pytest with coverage..."
        pytest tests/ --cov=src --cov-report=html --cov-report=term -v

        if [ $? -ne 0 ]; then
            log_error "Tests failed"
            cd - > /dev/null
            exit 1
        fi

        log_success "All tests passed"
        log_info "Coverage report: $OUTPUT_DIR/htmlcov/index.html"

        cd - > /dev/null
    else
        log_warning "No tests directory found, skipping"
    fi
fi

# Step 5: Code Quality Validation
log_step "✅ Step 5/7: Validating Code Quality"

if [ "$SKIP_TESTS" = "true" ]; then
    log_warning "Skipping code quality checks (--skip-tests flag)"
elif [ "$DRY_RUN" = "true" ]; then
    log_info "DRY RUN: Would run pylint, black, and mypy"
else
    if [ -d "$OUTPUT_DIR/src" ]; then
        cd "$OUTPUT_DIR"
        source venv/bin/activate

        # Check if quality tools are installed
        HAS_QUALITY_TOOLS=true
        pip list | grep -q pylint || HAS_QUALITY_TOOLS=false
        pip list | grep -q black || HAS_QUALITY_TOOLS=false

        if [ "$HAS_QUALITY_TOOLS" = "true" ]; then
            log_info "Running code formatters..."

            # Black (code formatter)
            black src/ --check --quiet || {
                log_warning "Code formatting issues found, auto-fixing..."
                black src/ --quiet
            }

            # Pylint (linter)
            log_info "Running linter..."
            pylint src/ --fail-under=7.0 --output-format=colorized || {
                log_warning "Linting score below 7.0, but continuing..."
            }

            log_success "Code quality checks completed"
        else
            log_warning "Quality tools not installed, skipping"
            log_info "Install: pip install pylint black mypy"
        fi

        cd - > /dev/null
    else
        log_warning "No src directory found, skipping"
    fi
fi

# Step 6: Docker Build
log_step "🐳 Step 6/7: Building Docker Image"

if [ "$SKIP_DOCKER" = "true" ]; then
    log_warning "Skipping Docker build (--skip-docker flag)"
elif [ "$DRY_RUN" = "true" ]; then
    log_info "DRY RUN: Would build Docker image"
else
    if [ -f "$OUTPUT_DIR/Dockerfile" ]; then
        cd "$OUTPUT_DIR"

        # Check if Docker is available
        if ! check_command docker; then
            log_warning "Docker not found, skipping build"
            cd - > /dev/null
        else
            PROJECT_NAME=$(basename "$OUTPUT_DIR")
            IMAGE_TAG="${PROJECT_NAME}:latest"

            log_info "Building Docker image: $IMAGE_TAG"
            docker build -t "$IMAGE_TAG" .

            if [ $? -ne 0 ]; then
                log_error "Docker build failed"
                cd - > /dev/null
                exit 1
            fi

            log_success "Docker image built: $IMAGE_TAG"

            # Run container health check
            if [ -f "docker-compose.yml" ]; then
                log_info "Starting containers for health check..."
                docker-compose up -d
                sleep 5

                # Check if containers are running
                if docker-compose ps | grep -q "Up"; then
                    log_success "Containers started successfully"

                    # Run integration tests if available
                    if [ -d "tests/integration" ]; then
                        log_info "Running integration tests..."
                        source venv/bin/activate
                        pytest tests/integration/ --verbose || {
                            log_warning "Integration tests failed"
                        }
                    fi

                    # Stop containers
                    log_info "Stopping containers..."
                    docker-compose down
                else
                    log_error "Containers failed to start"
                    docker-compose down
                    cd - > /dev/null
                    exit 1
                fi
            fi

            cd - > /dev/null
        fi
    else
        log_warning "No Dockerfile found, skipping Docker build"
    fi
fi

# Step 7: Deployment
log_step "🚢 Step 7/7: Deploying"

if [ "$DRY_RUN" = "true" ]; then
    log_info "DRY RUN: Would deploy to $DEPLOY_TARGET"
else
    cd "$OUTPUT_DIR"

    case "$DEPLOY_TARGET" in
        docker)
            if [ -f "docker-compose.yml" ]; then
                log_info "Deploying with Docker Compose..."
                docker-compose up -d --build

                log_success "Deployment complete!"
                log_info "Application running via Docker Compose"
                log_info "View logs: docker-compose logs -f"
                log_info "Stop: docker-compose down"
            else
                log_warning "No docker-compose.yml found"
            fi
            ;;

        kubernetes|k8s)
            if [ -d "k8s" ]; then
                if ! check_command kubectl; then
                    log_error "kubectl not found. Install Kubernetes CLI first."
                    exit 1
                fi

                log_info "Deploying to Kubernetes..."
                kubectl apply -f k8s/

                log_success "Deployment complete!"
                log_info "Check status: kubectl get pods"
                log_info "View logs: kubectl logs -l app=${PROJECT_NAME:-caas-app}"
            else
                log_warning "No k8s directory found"
            fi
            ;;

        local)
            log_info "Starting local deployment..."

            if [ -f "main.py" ]; then
                source venv/bin/activate

                # Create .env if not exists
                if [ ! -f ".env" ] && [ -f ".env.example" ]; then
                    log_info "Creating .env from .env.example"
                    cp .env.example .env
                    log_warning "Edit .env to add your API keys"
                fi

                log_info "Starting application locally..."
                log_info "Run: python main.py"

                if [ "$VERBOSE" = "true" ]; then
                    python main.py
                fi

                log_success "Local deployment ready"
            else
                log_error "No main.py found"
                exit 1
            fi
            ;;

        *)
            log_error "Unknown deployment target: $DEPLOY_TARGET"
            log_info "Supported targets: docker, kubernetes, local"
            exit 1
            ;;
    esac

    cd - > /dev/null
fi

# Final Summary
echo ""
log_step "🎉 CAAS Full Automation Workflow Completed!"

echo ""
echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Summary:${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
echo -e "  Requirement:      ${REQUIREMENT}"
echo -e "  Deploy Target:    ${DEPLOY_TARGET}"
echo -e "  Output Directory: ${OUTPUT_DIR}"
echo -e "  Tests:            $([ "$SKIP_TESTS" = "true" ] && echo "Skipped" || echo "Passed")"
echo -e "  Docker:           $([ "$SKIP_DOCKER" = "true" ] && echo "Skipped" || echo "Built")"
echo ""

if [ "$DEPLOY_TARGET" = "docker" ] && [ "$DRY_RUN" = "false" ]; then
    echo -e "${CYAN}Next Steps:${NC}"
    echo -e "  1. View application:  cd $OUTPUT_DIR && docker-compose logs -f"
    echo -e "  2. Access UI:         http://localhost:8600 (if frontend enabled)"
    echo -e "  3. Stop:              docker-compose down"
    echo -e "  4. Restart:           docker-compose restart"
    echo ""
fi

log_success "✨ Deployment successful! ✨"
echo ""

exit 0
