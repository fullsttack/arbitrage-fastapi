# Crypto Arbitrage Platform - Intelligent Makefile
# This Makefile provides simple commands to set up and run the entire project

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;34m
PURPLE := \033[0;35m
CYAN := \033[0;36m
WHITE := \033[1;37m
NC := \033[0m

# Project configuration
PROJECT_NAME := crypto-arbitrage
PYTHON_VERSION := 3.13
VENV_DIR := .venv
ENV_FILE := .env
REDIS_PORT := 6379
DJANGO_PORT := 8000

# Default target
.DEFAULT_GOAL := help

# Check if uv is installed
.PHONY: check-uv
check-uv:
	@printf "$(BLUE)📦 Checking uv installation...$(NC)\n"
	@command -v uv >/dev/null 2>&1 || { \
		printf "$(RED)❌ Error: uv is not installed!$(NC)\n"; \
		printf "$(YELLOW)💡 Install uv with: curl -LsSf https://astral.sh/uv/install.sh | sh$(NC)\n"; \
		exit 1; \
	}
	@printf "$(GREEN)✅ uv is installed$(NC)\n"

# Check if Redis is running
.PHONY: check-redis
check-redis:
	@printf "$(BLUE)🔴 Checking Redis server...$(NC)\n"
	@redis-cli -p $(REDIS_PORT) ping >/dev/null 2>&1 || { \
		printf "$(YELLOW)⚠️  Redis not running, attempting to start...$(NC)\n"; \
		(redis-server --daemonize yes --port $(REDIS_PORT) 2>/dev/null || \
		 brew services start redis 2>/dev/null || \
		 systemctl start redis 2>/dev/null || \
		 service redis-server start 2>/dev/null) && sleep 2; \
		redis-cli -p $(REDIS_PORT) ping >/dev/null 2>&1 || { \
			printf "$(RED)❌ Error: Could not start Redis!$(NC)\n"; \
			printf "$(YELLOW)💡 Please install and start Redis manually:$(NC)\n"; \
			printf "   - Ubuntu/Debian: sudo apt install redis-server && sudo service redis-server start$(NC)\n"; \
			printf "   - macOS: brew install redis && brew services start redis$(NC)\n"; \
			printf "   - Or run: redis-server$(NC)\n"; \
			exit 1; \
		}; \
	}
	@printf "$(GREEN)✅ Redis is running on port $(REDIS_PORT)$(NC)\n"

# Create .env file from example if it doesn't exist
.PHONY: setup-env
setup-env:
	@printf "$(BLUE)⚙️  Setting up environment file...$(NC)\n"
	@if [ ! -f $(ENV_FILE) ]; then \
		if [ -f env.example ]; then \
			cp env.example $(ENV_FILE); \
			printf "$(GREEN)✅ Created .env file from env.example$(NC)\n"; \
			printf "$(YELLOW)💡 Please edit .env file with your configuration$(NC)\n"; \
		else \
			printf "$(RED)❌ Error: env.example file not found!$(NC)\n"; \
			exit 1; \
		fi; \
	else \
		printf "$(GREEN)✅ .env file already exists$(NC)\n"; \
	fi

# Initialize uv project and install dependencies
.PHONY: setup-uv
setup-uv: check-uv
	@printf "$(BLUE)📦 Setting up uv environment...$(NC)\n"
	@if [ ! -d $(VENV_DIR) ]; then \
		printf "$(YELLOW)🔨 Creating virtual environment...$(NC)\n"; \
		uv venv --python $(PYTHON_VERSION) $(VENV_DIR) || { \
			printf "$(RED)❌ Error: Failed to create virtual environment!$(NC)\n"; \
			exit 1; \
		}; \
	fi
	@printf "$(YELLOW)📥 Installing dependencies...$(NC)\n"
	@uv pip install -e . || { \
		printf "$(RED)❌ Error: Failed to install dependencies!$(NC)\n"; \
		printf "$(YELLOW)💡 Trying alternative installation method...$(NC)\n"; \
		uv pip install django celery redis httpx cryptography psycopg2-binary django-ninja django-cors-headers django-celery-beat || { \
			printf "$(RED)❌ Error: Failed to install dependencies with alternative method!$(NC)\n"; \
			exit 1; \
		}; \
	}
	@printf "$(GREEN)✅ Dependencies installed successfully$(NC)\n"

# Create logs directory
.PHONY: setup-logs
setup-logs:
	@printf "$(BLUE)📝 Setting up logs directory...$(NC)\n"
	@mkdir -p logs
	@touch logs/crypto_arbitrage.log logs/security.log logs/arbitrage.log
	@printf "$(GREEN)✅ Logs directory created$(NC)\n"

# Run database migrations
.PHONY: migrate
migrate:
	@printf "$(BLUE)🗃️  Running database migrations...$(NC)\n"
	@. $(VENV_DIR)/bin/activate && python manage.py makemigrations --noinput || { \
		printf "$(RED)❌ Error: Failed to create migrations!$(NC)\n"; \
		exit 1; \
	}
	@. $(VENV_DIR)/bin/activate && python manage.py migrate --noinput || { \
		printf "$(RED)❌ Error: Failed to run migrations!$(NC)\n"; \
		exit 1; \
	}
	@printf "$(GREEN)✅ Database migrations completed$(NC)\n"

# Create superuser (only if none exists)
.PHONY: create-superuser
create-superuser:
	@printf "$(BLUE)👤 Setting up admin user...$(NC)\n"
	@. $(VENV_DIR)/bin/activate && python -c "import django; django.setup(); from django.contrib.auth import get_user_model; User = get_user_model(); print('Superuser exists') if User.objects.filter(is_superuser=True).exists() else User.objects.create_superuser('admin', 'admin@example.com', 'admin123') or print('Superuser created')" || { \
		printf "$(YELLOW)🔐 Creating superuser (admin/admin123)...$(NC)\n"; \
		. $(VENV_DIR)/bin/activate && python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('admin', 'admin@example.com', 'admin123') if not User.objects.filter(username='admin').exists() else print('Superuser already exists')"; \
	}
	@printf "$(GREEN)✅ Admin user ready (admin/admin123)$(NC)\n"

# Load initial data
.PHONY: load-fixtures
load-fixtures:
	@printf "$(BLUE)📊 Loading initial data...$(NC)\n"
	@. $(VENV_DIR)/bin/activate && python -c "\
import os; \
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings'); \
import django; django.setup(); \
from core.models import Currency, Exchange; \
from decimal import Decimal; \
\
currencies = [ \
    ('BTC', 'Bitcoin', True, 8), \
    ('ETH', 'Ethereum', True, 8), \
    ('USDT', 'Tether', True, 6), \
    ('RLS', 'Iranian Rial', False, 0), \
    ('IRT', 'Iranian Toman', False, 0), \
]; \
\
for symbol, name, is_crypto, decimals in currencies: \
    Currency.objects.get_or_create( \
        symbol=symbol, \
        defaults={'name': name, 'is_crypto': is_crypto, 'decimal_places': decimals} \
    ); \
\
exchanges = [ \
    ('nobitex', 'Nobitex', 'https://api.nobitex.ir', 300, 0.0025, 0.0025), \
    ('wallex', 'Wallex', 'https://api.wallex.ir', 60, 0.002, 0.002), \
    ('ramzinex', 'Ramzinex', 'https://publicapi.ramzinex.com', 60, 0.002, 0.002), \
]; \
\
for code, name, api_url, rate_limit, maker_fee, taker_fee in exchanges: \
    Exchange.objects.get_or_create( \
        code=code, \
        defaults={ \
            'name': name, \
            'api_url': api_url, \
            'rate_limit': rate_limit, \
            'maker_fee': Decimal(str(maker_fee)), \
            'taker_fee': Decimal(str(taker_fee)) \
        } \
    ); \
\
print('Initial data loaded successfully'); \
" || printf "$(YELLOW)⚠️  Initial data loading completed with warnings$(NC)\n"
	@printf "$(GREEN)✅ Initial data loaded$(NC)\n"

# Full setup process
.PHONY: setup
setup: check-uv setup-env setup-uv setup-logs check-redis migrate create-superuser load-fixtures
	@printf "$(GREEN)🎉 Setup completed successfully!$(NC)\n"
	@printf "$(CYAN)🚀 You can now run: make start$(NC)\n"

# Start development server
.PHONY: runserver
runserver:
	@printf "$(BLUE)🌐 Starting Django development server...$(NC)\n"
	@. $(VENV_DIR)/bin/activate && python manage.py runserver $(DJANGO_PORT) || { \
		printf "$(RED)❌ Error: Failed to start Django server!$(NC)\n"; \
		exit 1; \
	}

# Start Celery worker
.PHONY: celery-worker
celery-worker: check-redis
	@printf "$(BLUE)⚡ Starting Celery worker...$(NC)\n"
	@. $(VENV_DIR)/bin/activate && celery -A config worker --loglevel=info --concurrency=4 || { \
		printf "$(RED)❌ Error: Failed to start Celery worker!$(NC)\n"; \
		exit 1; \
	}

# Start Celery beat scheduler
.PHONY: celery-beat
celery-beat: check-redis
	@printf "$(BLUE)⏰ Starting Celery beat scheduler...$(NC)\n"
	@. $(VENV_DIR)/bin/activate && celery -A config beat --loglevel=info || { \
		printf "$(RED)❌ Error: Failed to start Celery beat!$(NC)\n"; \
		exit 1; \
	}

# Start Celery flower (monitoring)
.PHONY: celery-flower
celery-flower: check-redis
	@printf "$(BLUE)🌸 Starting Celery flower (monitoring)...$(NC)\n"
	@. $(VENV_DIR)/bin/activate && celery -A config flower --port=5555 || { \
		printf "$(RED)❌ Error: Failed to start Celery flower!$(NC)\n"; \
		printf "$(YELLOW)💡 Install flower: uv pip install flower$(NC)\n"; \
		exit 1; \
	}

# Start all services in background
.PHONY: start-services
start-services: check-redis
	@printf "$(BLUE)🚀 Starting all background services...$(NC)\n"
	@. $(VENV_DIR)/bin/activate && { \
		nohup celery -A config worker --loglevel=info --concurrency=4 > logs/celery-worker.log 2>&1 & echo $! > .celery-worker.pid; \
		nohup celery -A config beat --loglevel=info > logs/celery-beat.log 2>&1 & echo $! > .celery-beat.pid; \
		printf "$(GREEN)✅ Background services started$(NC)\n"; \
		printf "$(CYAN)📊 Worker logs: tail -f logs/celery-worker.log$(NC)\n"; \
		printf "$(CYAN)⏰ Beat logs: tail -f logs/celery-beat.log$(NC)\n"; \
	}

# Stop all background services
.PHONY: stop-services
stop-services:
	@printf "$(BLUE)🛑 Stopping background services...$(NC)\n"
	@[ -f .celery-worker.pid ] && kill `cat .celery-worker.pid` 2>/dev/null && rm .celery-worker.pid || true
	@[ -f .celery-beat.pid ] && kill `cat .celery-beat.pid` 2>/dev/null && rm .celery-beat.pid || true
	@printf "$(GREEN)✅ Background services stopped$(NC)\n"

# Start everything (main command)
.PHONY: start
start: start-services
	@printf "$(GREEN)🎉 Starting Crypto Arbitrage Platform...$(NC)\n"
	@printf "$(CYAN)📊 Admin: http://localhost:$(DJANGO_PORT)/admin (admin/admin123)$(NC)\n"
	@printf "$(CYAN)🔗 API Docs: http://localhost:$(DJANGO_PORT)/api/docs$(NC)\n"
	@printf "$(CYAN)🌸 Flower: http://localhost:5555 (if started separately)$(NC)\n"
	@printf "$(YELLOW)⏹️  Stop with: make stop$(NC)\n"
	@printf "$(WHITE)$(CYAN)🌐 Starting Django server...$(NC)\n"
	@$(MAKE) runserver

# Stop everything
.PHONY: stop
stop: stop-services
	@printf "$(GREEN)🛑 Crypto Arbitrage Platform stopped$(NC)\n"

# Development tools
.PHONY: shell
shell:
	@printf "$(BLUE)🐚 Starting Django shell...$(NC)\n"
	@. $(VENV_DIR)/bin/activate && python manage.py shell

.PHONY: test
test:
	@printf "$(BLUE)🧪 Running tests...$(NC)\n"
	@. $(VENV_DIR)/bin/activate && python manage.py test

.PHONY: lint
lint:
	@printf "$(BLUE)🔍 Running code analysis...$(NC)\n"
	@. $(VENV_DIR)/bin/activate && { \
		black --check . || printf "$(YELLOW)💡 Run: make format$(NC)\n"; \
		flake8 . || true; \
		isort --check-only . || printf "$(YELLOW)💡 Run: make format$(NC)\n"; \
	}

.PHONY: format
format:
	@printf "$(BLUE)✨ Formatting code...$(NC)\n"
	@. $(VENV_DIR)/bin/activate && { \
		black .; \
		isort .; \
		printf "$(GREEN)✅ Code formatted$(NC)\n"; \
	}

# Database operations
.PHONY: reset-db
reset-db:
	@printf "$(YELLOW)⚠️  WARNING: This will delete all data!$(NC)\n"
	@printf "$(RED)Are you sure? [y/N] $(NC)"; \
	read confirm; \
	if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then \
		rm -f db.sqlite3; \
		$(MAKE) migrate; \
		$(MAKE) create-superuser; \
		$(MAKE) load-fixtures; \
		printf "$(GREEN)✅ Database reset completed$(NC)\n"; \
	else \
		printf "$(BLUE)ℹ️  Database reset cancelled$(NC)\n"; \
	fi

.PHONY: backup-db
backup-db:
	@printf "$(BLUE)💾 Creating database backup...$(NC)\n"
	@cp db.sqlite3 "db.sqlite3.backup.$(shell date +%Y%m%d_%H%M%S)" 2>/dev/null || { \
		printf "$(YELLOW)⚠️  No database file found to backup$(NC)\n"; \
		exit 0; \
	}
	@printf "$(GREEN)✅ Database backup created$(NC)\n"

# Monitoring and logs
.PHONY: logs
logs:
	@printf "$(BLUE)📋 Showing application logs...$(NC)\n"
	@tail -f logs/crypto_arbitrage.log

.PHONY: status
status:
	@printf "$(BLUE)📊 System Status$(NC)\n"
	@printf "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)\n"
	@printf "$(GREEN)🐍 Python Environment:$(NC) "; [ -d $(VENV_DIR) ] && printf "$(GREEN)✅ Active$(NC)\n" || printf "$(RED)❌ Not found$(NC)\n"
	@printf "$(GREEN)🔴 Redis:$(NC) "; redis-cli -p $(REDIS_PORT) ping >/dev/null 2>&1 && printf "$(GREEN)✅ Running$(NC)\n" || printf "$(RED)❌ Not running$(NC)\n"
	@printf "$(GREEN)👷 Celery Worker:$(NC) "; [ -f .celery-worker.pid ] && kill -0 `cat .celery-worker.pid` 2>/dev/null && printf "$(GREEN)✅ Running$(NC)\n" || printf "$(RED)❌ Not running$(NC)\n"
	@printf "$(GREEN)⏰ Celery Beat:$(NC) "; [ -f .celery-beat.pid ] && kill -0 `cat .celery-beat.pid` 2>/dev/null && printf "$(GREEN)✅ Running$(NC)\n" || printf "$(RED)❌ Not running$(NC)\n"
	@printf "$(GREEN)🗃️  Database:$(NC) "; [ -f db.sqlite3 ] && printf "$(GREEN)✅ Ready$(NC)\n" || printf "$(RED)❌ Not found$(NC)\n"

# Cleanup
.PHONY: clean
clean: stop-services
	@printf "$(BLUE)🧹 Cleaning up...$(NC)\n"
	@find . -type f -name "*.pyc" -delete
	@find . -type d -name "__pycache__" -delete
	@rm -rf .pytest_cache
	@rm -f .celery-worker.pid .celery-beat.pid
	@printf "$(GREEN)✅ Cleanup completed$(NC)\n"

.PHONY: clean-all
clean-all: clean
	@printf "$(YELLOW)⚠️  This will remove virtual environment and database!$(NC)\n"
	@printf "$(RED)Are you sure? [y/N] $(NC)"; \
	read confirm; \
	if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then \
		rm -rf $(VENV_DIR); \
		rm -f db.sqlite3; \
		rm -rf logs/*.log; \
		printf "$(GREEN)✅ Complete cleanup done$(NC)\n"; \
	else \
		printf "$(BLUE)ℹ️  Cleanup cancelled$(NC)\n"; \
	fi

# Help
.PHONY: help
help:
	@printf "$(WHITE)🚀 Crypto Arbitrage Platform - Makefile Commands$(NC)\n"
	@printf "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)\n"
	@printf "$(GREEN)📦 Setup Commands:$(NC)\n"
	@printf "  $(YELLOW)make setup$(NC)          - 🏗️  Complete project setup (first time)\n"
	@printf "  $(YELLOW)make setup-uv$(NC)       - 📦 Setup uv environment and dependencies\n"
	@printf "  $(YELLOW)make migrate$(NC)        - 🗃️  Run database migrations\n"
	@printf "  $(YELLOW)make load-fixtures$(NC)  - 📊 Load initial data\n"
	@printf "\n$(GREEN)🚀 Start/Stop Commands:$(NC)\n"
	@printf "  $(YELLOW)make start$(NC)          - 🎉 Start the entire platform\n"
	@printf "  $(YELLOW)make stop$(NC)           - 🛑 Stop all services\n"
	@printf "  $(YELLOW)make runserver$(NC)      - 🌐 Start Django development server only\n"
	@printf "  $(YELLOW)make start-services$(NC) - ⚡ Start background services (Celery)\n"
	@printf "\n$(GREEN)🔧 Development Commands:$(NC)\n"
	@printf "  $(YELLOW)make shell$(NC)          - 🐚 Django shell\n"
	@printf "  $(YELLOW)make test$(NC)           - 🧪 Run tests\n"
	@printf "  $(YELLOW)make lint$(NC)           - 🔍 Code analysis\n"
	@printf "  $(YELLOW)make format$(NC)         - ✨ Format code\n"
	@printf "\n$(GREEN)🗃️  Database Commands:$(NC)\n"
	@printf "  $(YELLOW)make reset-db$(NC)       - ⚠️  Reset database (destructive)\n"
	@printf "  $(YELLOW)make backup-db$(NC)      - 💾 Backup database\n"
	@printf "\n$(GREEN)📊 Monitoring Commands:$(NC)\n"
	@printf "  $(YELLOW)make status$(NC)         - 📊 Show system status\n"
	@printf "  $(YELLOW)make logs$(NC)           - 📋 Show application logs\n"
	@printf "  $(YELLOW)make celery-flower$(NC)  - 🌸 Start Celery monitoring\n"
	@printf "\n$(GREEN)🧹 Cleanup Commands:$(NC)\n"
	@printf "  $(YELLOW)make clean$(NC)          - 🧹 Clean cache files\n"
	@printf "  $(YELLOW)make clean-all$(NC)      - ⚠️  Remove everything (destructive)\n"
	@printf "\n$(CYAN)💡 Quick Start:$(NC)\n"
	@printf "  1. $(YELLOW)make setup$(NC)  - First time setup\n"
	@printf "  2. $(YELLOW)make start$(NC)  - Start the platform\n"
	@printf "  3. Visit $(CYAN)http://localhost:$(DJANGO_PORT)/admin$(NC) (admin/admin123)\n"
	@printf "\n$(PURPLE)🌟 Features:$(NC)\n"
	@printf "  • 💹 Multi-exchange arbitrage detection\n"
	@printf "  • 🔐 Encrypted API credential storage\n"
	@printf "  • ⚡ Real-time market data processing\n"
	@printf "  • 📊 Advanced analytics and reporting\n"
	@printf "  • 🛡️  Comprehensive security monitoring\n"