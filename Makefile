# =============================================================================
# CRYPTO ARBITRAGE TRADING SYSTEM - MAKEFILE
# =============================================================================
# Comprehensive development and production management commands
# Run 'make help' to see all available commands

.PHONY: help setup install start stop restart status logs health test clean docker-build docker-up docker-down backup

# Default target
.DEFAULT_GOAL := help

# =============================================================================
# CONFIGURATION
# =============================================================================
PROJECT_NAME := crypto-arbitrage
PYTHON := python3
PIP := pip3
VENV := .venv
DJANGO_SETTINGS := config.settings.base
COMPOSE_FILE := docker-compose.yml

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[0;33m
BLUE := \033[0;34m
PURPLE := \033[0;35m
CYAN := \033[0;36m
WHITE := \033[0;37m
RESET := \033[0m

# =============================================================================
# HELP & INFORMATION
# =============================================================================
help: ## Show this help message
	@echo "$(CYAN)===============================================================================$(RESET)"
	@echo "$(CYAN)  CRYPTO ARBITRAGE TRADING SYSTEM - MAKEFILE COMMANDS$(RESET)"
	@echo "$(CYAN)===============================================================================$(RESET)"
	@echo ""
	@echo "$(GREEN)🚀 QUICK START:$(RESET)"
	@echo "  $(YELLOW)make setup$(RESET)     - Complete project setup"
	@echo "  $(YELLOW)make start$(RESET)     - Start all services"
	@echo "  $(YELLOW)make health$(RESET)    - Check system health"
	@echo ""
	@echo "$(GREEN)📋 AVAILABLE COMMANDS:$(RESET)"
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*##/ { printf "  $(YELLOW)%-15s$(RESET) %s\n", $$1, $$2 }' $(MAKEFILE_LIST)
	@echo ""
	@echo "$(GREEN)🔧 DOCKER COMMANDS:$(RESET)"
	@echo "  $(YELLOW)make docker-build$(RESET) - Build Docker images"
	@echo "  $(YELLOW)make docker-up$(RESET)    - Start with Docker Compose"
	@echo "  $(YELLOW)make docker-down$(RESET)  - Stop Docker services"
	@echo ""

# =============================================================================
# ENVIRONMENT SETUP
# =============================================================================
check-env: ## Check if .env file exists
	@echo "$(BLUE)Checking environment configuration...$(RESET)"
	@if [ ! -f .env ]; then \
		echo "$(RED)❌ .env file not found!$(RESET)"; \
		echo "$(YELLOW)Creating .env from template...$(RESET)"; \
		cp env .env; \
		echo "$(GREEN)✅ .env file created. Please edit it with your settings.$(RESET)"; \
		exit 1; \
	else \
		echo "$(GREEN)✅ .env file found$(RESET)"; \
	fi

generate-secrets: ## Generate Django secret key and encryption key
	@echo "$(BLUE)Generating secure keys...$(RESET)"
	@python3 -c "from django.core.management.utils import get_random_secret_key; print('SECRET_KEY=' + get_random_secret_key())"
	@python3 -c "from cryptography.fernet import Fernet; print('ENCRYPTION_KEY=' + Fernet.generate_key().decode())"

check-python: ## Check Python version and virtual environment
	@echo "$(BLUE)Checking Python environment...$(RESET)"
	@if ! command -v uv &> /dev/null; then \
		echo "$(RED)❌ uv not found. Please install uv first$(RESET)"; \
		echo "$(YELLOW)💡 Install with: curl -LsSf https://astral.sh/uv/install.sh | sh$(RESET)"; \
		exit 1; \
	fi
	@echo "$(GREEN)✅ uv version: $$(uv --version)$(RESET)"
	@if [ ! -d "$(VENV)" ]; then \
		echo "$(YELLOW)Creating virtual environment with uv...$(RESET)"; \
		uv venv; \
		echo "$(GREEN)✅ Virtual environment created$(RESET)"; \
	else \
		echo "$(GREEN)✅ Virtual environment exists$(RESET)"; \
	fi

install: check-python ## Install Python dependencies
	@echo "$(BLUE)Installing Python dependencies...$(RESET)"
	@uv sync
	@echo "$(GREEN)✅ Dependencies installed$(RESET)"

check-services: ## Check if required services are running
	@echo "$(BLUE)Checking required services...$(RESET)"
	@echo "$(YELLOW)Using SQLite database - no PostgreSQL check needed$(RESET)"
	@echo "$(YELLOW)Checking Redis...$(RESET)"
	@if ! redis-cli -h localhost -p 6379 ping &> /dev/null; then \
		echo "$(RED)❌ Redis not running on localhost:6379$(RESET)"; \
		echo "$(YELLOW)💡 Try: brew services start redis (macOS) or sudo systemctl start redis (Linux)$(RESET)"; \
	else \
		echo "$(GREEN)✅ Redis is running$(RESET)"; \
	fi

create-logs: ## Create log directories
	@echo "$(BLUE)Creating log directories...$(RESET)"
	@mkdir -p logs
	@echo "$(GREEN)✅ Log directories created$(RESET)"

migrate: ## Run database migrations
	@echo "$(BLUE)Running database migrations...$(RESET)"
	@uv run python manage.py makemigrations
	@uv run python manage.py migrate
	@echo "$(GREEN)✅ Database migrations completed$(RESET)"

create-superuser: ## Create Django superuser (interactive)
	@echo "$(BLUE)Creating Django superuser...$(RESET)"
	@uv run python manage.py createsuperuser

setup: check-env check-python install create-logs check-services migrate ## Complete project setup
	@echo ""
	@echo "$(GREEN)===============================================================================$(RESET)"
	@echo "$(GREEN)  🎉 PROJECT SETUP COMPLETED SUCCESSFULLY!$(RESET)"
	@echo "$(GREEN)===============================================================================$(RESET)"
	@echo ""
	@echo "$(YELLOW)Next steps:$(RESET)"
	@echo "  1. Edit .env file with your exchange API keys"
	@echo "  2. Run '$(CYAN)make create-superuser$(RESET)' to create admin user"
	@echo "  3. Run '$(CYAN)make start$(RESET)' to start all services"
	@echo "  4. Visit http://localhost:8000/admin/ for admin panel"
	@echo "  5. Visit http://localhost:8000/api/docs/ for API documentation"
	@echo ""

# =============================================================================
# DEVELOPMENT SERVER MANAGEMENT
# =============================================================================
runserver: ## Start Django development server
	@echo "$(BLUE)Starting Django development server...$(RESET)"
	@uv run python manage.py runserver 0.0.0.0:8000

celery-worker: ## Start Celery worker
	@echo "$(BLUE)Starting Celery worker...$(RESET)"
	@uv run celery -A config worker -l info --concurrency=4

celery-beat: ## Start Celery beat scheduler
	@echo "$(BLUE)Starting Celery beat scheduler...$(RESET)"
	@uv run celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler

celery-flower: ## Start Celery Flower monitoring
	@echo "$(BLUE)Starting Celery Flower...$(RESET)"
	@uv run celery -A config flower --port=5555

start-dev: ## Start all development services in background
	@echo "$(BLUE)Starting all development services...$(RESET)"
	@echo "$(YELLOW)Starting Django server...$(RESET)"
	@uv run python manage.py runserver 0.0.0.0:8000 &
	@echo "$(YELLOW)Starting Celery worker...$(RESET)"
	@uv run celery -A config worker -l info --concurrency=4 &
	@echo "$(YELLOW)Starting Celery beat...$(RESET)"
	@uv run celery -A config beat -l info &
	@echo "$(YELLOW)Starting Celery flower...$(RESET)"
	@uv run celery -A config flower --port=5555 &
	@echo "$(GREEN)✅ All services started!$(RESET)"
	@echo ""
	@echo "$(CYAN)Services running at:$(RESET)"
	@echo "  🌐 Django: http://localhost:8000"
	@echo "  🌸 Flower: http://localhost:5555"
	@echo "  📊 Admin: http://localhost:8000/admin/"
	@echo "  📚 API Docs: http://localhost:8000/api/docs/"

start: start-dev ## Alias for start-dev

stop: ## Stop all development services
	@echo "$(BLUE)Stopping all services...$(RESET)"
	@pkill -f "manage.py runserver" || true
	@pkill -f "celery worker" || true
	@pkill -f "celery beat" || true
	@pkill -f "celery flower" || true
	@echo "$(GREEN)✅ All services stopped$(RESET)"

restart: stop start ## Restart all services

status: ## Check status of all services
	@echo "$(BLUE)Checking service status...$(RESET)"
	@echo "$(YELLOW)Django processes:$(RESET)"
	@pgrep -fl "manage.py runserver" || echo "  No Django server running"
	@echo "$(YELLOW)Celery processes:$(RESET)"
	@pgrep -fl "celery" || echo "  No Celery processes running"
	@echo "$(YELLOW)Database connections:$(RESET)"
	@uv run python manage.py shell -c "from django.db import connection; connection.cursor().execute('SELECT 1'); print('✅ Database connected')" 2>/dev/null || echo "❌ Database connection failed"

# =============================================================================
# HEALTH CHECKS & MONITORING
# =============================================================================
health: ## Comprehensive system health check
	@echo "$(BLUE)Running comprehensive health check...$(RESET)"
	@echo ""
	@echo "$(CYAN)1. Environment Check:$(RESET)"
	@$(MAKE) check-env
	@echo ""
	@echo "$(CYAN)2. Services Check:$(RESET)"
	@$(MAKE) check-services
	@echo ""
	@echo "$(CYAN)3. Application Health:$(RESET)"
	@. $(VENV)/bin/activate && python manage.py check
	@echo "$(GREEN)✅ Django check passed$(RESET)"
	@echo ""
	@echo "$(CYAN)4. Database Health:$(RESET)"
	@. $(VENV)/bin/activate && python manage.py shell -c "from django.db import connection; connection.cursor().execute('SELECT COUNT(*) FROM django_migrations'); print('✅ Database is healthy')"
	@echo ""
	@echo "$(CYAN)5. Cache Health:$(RESET)"
	@. $(VENV)/bin/activate && python manage.py shell -c "from django.core.cache import cache; cache.set('test', 'ok', 10); result = cache.get('test'); print('✅ Cache is working' if result == 'ok' else '❌ Cache failed')"
	@echo ""
	@echo "$(GREEN)🏥 Health check completed!$(RESET)"

test-exchanges: ## Test exchange connectivity
	@echo "$(BLUE)Testing exchange connectivity...$(RESET)"
	@. $(VENV)/bin/activate && python manage.py shell -c "from exchanges.tasks import check_exchange_health; check_exchange_health(); print('✅ Exchange connectivity test completed')"

logs: ## Show recent logs
	@echo "$(BLUE)Showing recent logs...$(RESET)"
	@if [ -f logs/crypto_arbitrage.log ]; then \
		tail -n 50 logs/crypto_arbitrage.log; \
	else \
		echo "$(YELLOW)No log file found. Run the application first.$(RESET)"; \
	fi

logs-follow: ## Follow logs in real-time
	@echo "$(BLUE)Following logs in real-time (Ctrl+C to stop)...$(RESET)"
	@if [ -f logs/crypto_arbitrage.log ]; then \
		tail -f logs/crypto_arbitrage.log; \
	else \
		echo "$(YELLOW)No log file found. Run the application first.$(RESET)"; \
	fi

logs-error: ## Show error logs
	@echo "$(BLUE)Showing error logs...$(RESET)"
	@if [ -f logs/crypto_arbitrage.log ]; then \
		grep -i error logs/crypto_arbitrage.log | tail -n 20; \
	else \
		echo "$(YELLOW)No log file found.$(RESET)"; \
	fi

# =============================================================================
# TESTING
# =============================================================================
test: ## Run all tests
	@echo "$(BLUE)Running tests...$(RESET)"
	@. $(VENV)/bin/activate && python manage.py test
	@echo "$(GREEN)✅ Tests completed$(RESET)"

test-coverage: ## Run tests with coverage
	@echo "$(BLUE)Running tests with coverage...$(RESET)"
	@. $(VENV)/bin/activate && coverage run manage.py test
	@. $(VENV)/bin/activate && coverage report
	@. $(VENV)/bin/activate && coverage html
	@echo "$(GREEN)✅ Coverage report generated in htmlcov/$(RESET)"

lint: ## Run code linting
	@echo "$(BLUE)Running code linting...$(RESET)"
	@. $(VENV)/bin/activate && flake8 .
	@. $(VENV)/bin/activate && black --check .
	@. $(VENV)/bin/activate && isort --check-only .
	@echo "$(GREEN)✅ Linting completed$(RESET)"

format: ## Format code
	@echo "$(BLUE)Formatting code...$(RESET)"
	@. $(VENV)/bin/activate && black .
	@. $(VENV)/bin/activate && isort .
	@echo "$(GREEN)✅ Code formatted$(RESET)"

# =============================================================================
# DATABASE MANAGEMENT
# =============================================================================
db-reset: ## Reset database (WARNING: Destructive!)
	@echo "$(RED)⚠️  WARNING: This will DELETE all data!$(RESET)"
	@read -p "Are you sure? Type 'yes' to continue: " confirm && [ "$$confirm" = "yes" ] || exit 1
	@. $(VENV)/bin/activate && python manage.py flush --noinput
	@. $(VENV)/bin/activate && python manage.py migrate
	@echo "$(GREEN)✅ Database reset completed$(RESET)"

db-backup: ## Backup database
	@echo "$(BLUE)Creating database backup...$(RESET)"
	@mkdir -p backups
	@pg_dump crypto_arbitrage > backups/backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "$(GREEN)✅ Database backup created in backups/$(RESET)"

db-shell: ## Open database shell
	@echo "$(BLUE)Opening database shell...$(RESET)"
	@. $(VENV)/bin/activate && python manage.py dbshell

# =============================================================================
# DOCKER OPERATIONS
# =============================================================================
docker-build: ## Build Docker images
	@echo "$(BLUE)Building Docker images...$(RESET)"
	@docker-compose build
	@echo "$(GREEN)✅ Docker images built$(RESET)"

docker-up: ## Start services with Docker Compose
	@echo "$(BLUE)Starting services with Docker Compose...$(RESET)"
	@docker-compose up -d
	@echo "$(GREEN)✅ Docker services started$(RESET)"
	@echo ""
	@echo "$(CYAN)Services running at:$(RESET)"
	@echo "  🌐 Django: http://localhost:8000"
	@echo "  🌸 Flower: http://localhost:5555"
	@echo "  📊 Admin: http://localhost:8000/admin/"
	@echo "  🗄️  Redis Commander: http://localhost:8081 (debug profile)"
	@echo "  🐘 pgAdmin: http://localhost:8080 (debug profile)"

docker-up-debug: ## Start with debugging services
	@echo "$(BLUE)Starting with debugging services...$(RESET)"
	@docker-compose --profile debug up -d
	@echo "$(GREEN)✅ Docker services with debugging tools started$(RESET)"

docker-down: ## Stop Docker services
	@echo "$(BLUE)Stopping Docker services...$(RESET)"
	@docker-compose down
	@echo "$(GREEN)✅ Docker services stopped$(RESET)"

docker-logs: ## Show Docker logs
	@echo "$(BLUE)Showing Docker logs...$(RESET)"
	@docker-compose logs -f

docker-health: ## Check Docker services health
	@echo "$(BLUE)Checking Docker services health...$(RESET)"
	@docker-compose ps

# =============================================================================
# UTILITY COMMANDS
# =============================================================================
shell: ## Open Django shell
	@echo "$(BLUE)Opening Django shell...$(RESET)"
	@. $(VENV)/bin/activate && python manage.py shell

collectstatic: ## Collect static files
	@echo "$(BLUE)Collecting static files...$(RESET)"
	@. $(VENV)/bin/activate && python manage.py collectstatic --noinput
	@echo "$(GREEN)✅ Static files collected$(RESET)"

clean: ## Clean up temporary files
	@echo "$(BLUE)Cleaning up temporary files...$(RESET)"
	@find . -type f -name "*.pyc" -delete
	@find . -type d -name "__pycache__" -delete
	@find . -type f -name "*.log" -delete
	@find . -type f -name ".coverage" -delete
	@rm -rf htmlcov/
	@rm -rf .pytest_cache/
	@echo "$(GREEN)✅ Cleanup completed$(RESET)"

requirements: ## Generate requirements.txt
	@echo "$(BLUE)Generating requirements.txt...$(RESET)"
	@. $(VENV)/bin/activate && pip freeze > requirements.txt
	@echo "$(GREEN)✅ requirements.txt generated$(RESET)"

# =============================================================================
# PRODUCTION COMMANDS
# =============================================================================
deploy-check: ## Check if ready for deployment
	@echo "$(BLUE)Checking deployment readiness...$(RESET)"
	@. $(VENV)/bin/activate && python manage.py check --deploy
	@echo "$(GREEN)✅ Deployment check completed$(RESET)"

# =============================================================================
# QUICK TROUBLESHOOTING
# =============================================================================
troubleshoot: ## Run troubleshooting diagnostics
	@echo "$(BLUE)Running troubleshooting diagnostics...$(RESET)"
	@echo ""
	@echo "$(CYAN)🔍 System Information:$(RESET)"
	@echo "Python version: $$(python3 --version 2>/dev/null || echo 'Not found')"
	@echo "Pip version: $$(pip3 --version 2>/dev/null || echo 'Not found')"
	@echo "Virtual env: $$(if [ -d '$(VENV)' ]; then echo 'Exists'; else echo 'Missing'; fi)"
	@echo ""
	@echo "$(CYAN)🔍 File Permissions:$(RESET)"
	@ls -la manage.py 2>/dev/null || echo "manage.py not found"
	@echo ""
	@echo "$(CYAN)🔍 Port Availability:$(RESET)"
	@echo "Port 8000: $$(if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null; then echo 'In use'; else echo 'Available'; fi)"
	@echo "Port 5432: $$(if lsof -Pi :5432 -sTCP:LISTEN -t >/dev/null; then echo 'In use'; else echo 'Available'; fi)"
	@echo "Port 6379: $$(if lsof -Pi :6379 -sTCP:LISTEN -t >/dev/null; then echo 'In use'; else echo 'Available'; fi)"
	@echo ""
	@$(MAKE) health

# =============================================================================
# DEVELOPMENT SHORTCUTS
# =============================================================================
dev: setup start ## Quick development setup and start
	@echo "$(GREEN)🚀 Development environment ready!$(RESET)"

quick-start: check-services migrate start ## Quick start (skip full setup)
	@echo "$(GREEN)🚀 Quick start completed!$(RESET)"