.PHONY: help install setup-dev setup-prod up up-dev up-dev-assistant-docker assistant-local down logs clean test lint db-init db-migrate db-reset build install-git-hooks

# Default target
help:
	@echo "PLG Lead Sourcer - Available Commands"
	@echo ""
	@echo "Development:"
	@echo "  make setup-dev     - Setup development environment"
	@echo "  make up-dev        - Start development services"
	@echo "  make up-dev-assistant-docker - Start dev services with assistant in Docker"
	@echo "  make assistant-local - Run assistant on host (recommended on macOS)"
	@echo "  make up            - Start production services"
	@echo "  make down          - Stop all services"
	@echo "  make logs          - View logs"
	@echo "  make install-git-hooks - Enable pre-commit gitleaks secret scanning"
	@echo "  make shell-backend - Shell into backend container"
	@echo "  make shell-jobs    - Shell into jobs container"
	@echo ""
	@echo "Database:"
	@echo "  make db-init       - Initialize database schema"
	@echo "  make db-migrate    - Run database migrations"
	@echo "  make db-reset      - Reset database (WARNING: destroys data)"
	@echo "  make db-backup     - Backup database"
	@echo ""
	@echo "Code Quality:"
	@echo "  make test          - Run all tests"
	@echo "  make lint          - Run linters"
	@echo "  make format        - Format code"
	@echo ""
	@echo "Build & Deploy:"
	@echo "  make build         - Build all Docker images"
	@echo "  make build-prod    - Build production Docker images"
	@echo "  make up-prod       - Start production services locally"
	@echo "  make down-prod     - Stop production services"
	@echo "  make deploy-ec2    - Deploy to EC2 (EC2_HOST=... PEM_FILE=...)"
	@echo "  make push          - Push images to registry"
	@echo "  make clean         - Clean up containers and volumes"

# Development setup
setup-dev:
	@echo "Setting up development environment..."
	cp -n backend/.env.example backend/.env || true
	cp -n jobs/.env.example jobs/.env || true
	cp -n frontend/.env.example frontend/.env || true
	@echo "✓ Environment files created"
	@echo "⚠ Please edit .env files with your credentials"

# Start development services
up-dev:
	docker-compose --profile dev up -d
	@echo "✓ Development services started"
	@echo "Frontend: http://localhost:5173"
	@echo "Backend: http://localhost:8000"
	@echo "API Docs: http://localhost:8000/docs"
	@echo "Chat assistant: run 'make assistant-local' (recommended on macOS)"

# Start development services including assistant container
up-dev-assistant-docker:
	docker-compose --profile dev --profile assistant-docker up -d
	@echo "✓ Development services started (assistant in Docker)"
	@echo "Frontend: http://localhost:5173"
	@echo "Backend: http://localhost:8000"
	@echo "Assistant WS: ws://localhost:3001/ws/codex"

# Run assistant on host machine (recommended on macOS)
assistant-local:
	cd assistant && ./start-local.sh

# Start production services
up:
	docker-compose --profile prod up -d
	@echo "✓ Production services started"
	@echo "Application: http://localhost:80"
	@echo "API: http://localhost:80/api"

# Stop all services
down:
	docker-compose --profile dev --profile prod down
	@echo "✓ Services stopped"

# View logs
logs:
	docker-compose logs -f

# View specific service logs
logs-backend:
	docker-compose logs -f backend

logs-jobs:
	docker-compose logs -f jobs

logs-frontend:
	docker-compose logs -f frontend-dev frontend

# Shell access
shell-backend:
	docker-compose exec backend /bin/bash

shell-jobs:
	docker-compose exec jobs /bin/bash

shell-db:
	docker-compose exec postgres psql -U plg_user -d plg_lead_sourcer

# Database operations
db-init:
	@echo "Initializing database schema..."
	docker-compose exec -T postgres psql -U plg_user -d plg_lead_sourcer < database/schema.sql
	@echo "✓ Database initialized"

db-migrate:
	@echo "Running database migrations..."
	@for f in $$(ls database/migrations/*.sql | sort); do \
		echo "  → $$f"; \
		docker-compose exec -T postgres psql -U plg_user -d plg_lead_sourcer < $$f; \
	done
	@echo "✓ Migrations complete"

db-reset:
	@echo "⚠ WARNING: This will destroy all data!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose exec -T postgres psql -U plg_user -c "DROP DATABASE IF EXISTS plg_lead_sourcer;"; \
		docker-compose exec -T postgres psql -U plg_user -c "CREATE DATABASE plg_lead_sourcer;"; \
		docker-compose exec -T postgres psql -U plg_user -d plg_lead_sourcer < database/schema.sql; \
		echo "✓ Database reset complete"; \
	fi

db-backup:
	@echo "Backing up database..."
	@mkdir -p backups
	docker-compose exec -T postgres pg_dump -U plg_user plg_lead_sourcer > backups/backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "✓ Backup created in backups/"

db-restore:
	@echo "Available backups:"
	@ls -1 backups/*.sql
	@read -p "Enter backup filename: " backup; \
	docker-compose exec -T postgres psql -U plg_user -d plg_lead_sourcer < backups/$$backup; \
	echo "✓ Database restored"

# Testing
test:
	@echo "Running backend tests..."
	cd backend && python -m pytest
	@echo "Running frontend tests..."
	cd frontend && npm test

test-backend:
	cd backend && python -m pytest -v

test-frontend:
	cd frontend && npm test

# Code quality
lint:
	@echo "Linting backend..."
	cd backend && flake8 .
	@echo "Linting frontend..."
	cd frontend && npm run lint

format:
	@echo "Formatting backend..."
	cd backend && black .
	@echo "Formatting frontend..."
	cd frontend && npm run format || true

# Build operations
build:
	@echo "Building all Docker images..."
	docker-compose build
	@echo "✓ Build complete"

build-backend:
	docker-compose build backend

build-jobs:
	docker-compose build jobs

build-frontend:
	docker-compose build frontend

# Push to registry
push:
	@echo "Pushing images to registry..."
	docker-compose push
	@echo "✓ Images pushed"

# Clean up
clean:
	@echo "Cleaning up containers and volumes..."
	docker-compose --profile dev --profile prod down -v
	@echo "✓ Cleanup complete"

clean-all: clean
	@echo "Removing images..."
	docker rmi $$(docker images -q 'plg-lead-sourcer*') || true
	@echo "✓ Full cleanup complete"

# Install dependencies locally (without Docker)
install:
	@echo "Installing backend dependencies..."
	cd backend && pip install -r requirements.txt
	@echo "Installing jobs dependencies..."
	cd jobs && pip install -r requirements.txt
	@echo "Installing frontend dependencies..."
	cd frontend && npm install
	@echo "✓ Dependencies installed"

# Install repo-managed git hooks
install-git-hooks:
	@chmod +x .githooks/pre-commit
	@git config core.hooksPath .githooks
	@echo "✓ Enabled git hooks from .githooks"
	@if ! command -v gitleaks >/dev/null 2>&1; then \
		echo "⚠ gitleaks is not installed. Install with: brew install gitleaks"; \
	fi

# Health checks
health:
	@echo "Checking service health..."
	@curl -f http://localhost:8000/health && echo "✓ Backend healthy" || echo "✗ Backend unhealthy"
	@curl -f http://localhost:5173/ && echo "✓ Frontend healthy" || echo "✗ Frontend unhealthy"

# Development workflow
dev: setup-dev up-dev logs

# Production deployment (local)
deploy: build up
	@echo "✓ Deployment complete"
	@echo "Checking health..."
	@sleep 5
	@make health

# Deploy to EC2
deploy-ec2:
	@if [ -z "$(EC2_HOST)" ] || [ -z "$(PEM_FILE)" ]; then \
		echo "Usage: make deploy-ec2 EC2_HOST=user@host PEM_FILE=~/.ssh/key.pem [ENV_FILE=.env.production]"; \
		exit 1; \
	fi
	./deploy.sh $(EC2_HOST) $(PEM_FILE) $(if $(ENV_FILE),--env $(ENV_FILE),)

# Build production images locally
build-prod:
	docker-compose -f docker-compose.prod.yml build --parallel
	@echo "✓ Production build complete"

# Start production services locally
up-prod:
	docker-compose -f docker-compose.prod.yml up -d
	@echo "✓ Production services started"
	@echo "Application: http://localhost:80"

# Stop production services
down-prod:
	docker-compose -f docker-compose.prod.yml down
	@echo "✓ Production services stopped"

# Quick restart
restart: down up

restart-dev: down up-dev

# Monitor
monitor:
	@echo "Service Status:"
	@docker-compose ps
	@echo ""
	@echo "Resource Usage:"
	@docker stats --no-stream

# Generate secrets
secrets:
	@echo "Generating secrets..."
	@echo "SECRET_KEY=$$(openssl rand -hex 32)"
	@echo ""
	@echo "Add these to your .env files"
