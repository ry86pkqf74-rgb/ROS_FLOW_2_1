# Production Docker Compose Makefile
# Convenience commands for Docker operations

.PHONY: help build up down logs shell db-shell clean prune dev prod

# Default target
help:
	@echo "Production Docker Compose Commands"
	@echo "==================================="
	@echo ""
	@echo "Development:"
	@echo "  make dev           - Start development environment"
	@echo "  make dev-down      - Stop development environment"
	@echo ""
	@echo "Production:"
	@echo "  make build         - Build production Docker images"
	@echo "  make up            - Start production services"
	@echo "  make down          - Stop production services"
	@echo "  make logs          - View all service logs"
	@echo "  make logs-app      - View application logs"
	@echo "  make logs-db       - View database logs"
	@echo ""
	@echo "With Nginx (SSL/Load Balancing):"
	@echo "  make up-nginx      - Start with nginx reverse proxy"
	@echo "  make down-nginx    - Stop all services including nginx"
	@echo ""
	@echo "Database:"
	@echo "  make db-shell      - Access PostgreSQL shell"
	@echo "  make db-backup     - Backup database"
	@echo "  make db-restore    - Restore database from backup"
	@echo ""
	@echo "Maintenance:"
	@echo "  make shell         - Access application shell"
	@echo "  make clean         - Remove containers and volumes"
	@echo "  make prune         - Remove all unused Docker resources"
	@echo "  make health        - Check service health status"

# Development
dev:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

dev-down:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml down

# Production build
build:
	docker compose build --no-cache

# Start production services
up:
	docker compose up -d

# Start with nginx reverse proxy
up-nginx:
	docker compose --profile with-nginx up -d

# Stop services
down:
	docker compose down

down-nginx:
	docker compose --profile with-nginx down

# View logs
logs:
	docker compose logs -f

logs-app:
	docker compose logs -f app

logs-db:
	docker compose logs -f db

# Access shells
shell:
	docker compose exec app sh

db-shell:
	docker compose exec db psql -U $${POSTGRES_USER:-postgres} -d $${POSTGRES_DB:-appdb}

# Database backup/restore
db-backup:
	@mkdir -p backups
	docker compose exec db pg_dump -U $${POSTGRES_USER:-postgres} $${POSTGRES_DB:-appdb} > backups/backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "Backup created in backups/"

db-restore:
	@if [ -z "$(FILE)" ]; then \
		echo "Usage: make db-restore FILE=backups/backup_file.sql"; \
		exit 1; \
	fi
	docker compose exec -T db psql -U $${POSTGRES_USER:-postgres} -d $${POSTGRES_DB:-appdb} < $(FILE)
	@echo "Database restored from $(FILE)"

# Health check
health:
	@echo "Checking service health..."
	@docker compose ps
	@echo ""
	@echo "Application health:"
	@curl -s http://localhost:$${APP_PORT:-5000}/api/health | jq . || echo "Application not responding"

# Cleanup
clean:
	docker compose down -v --remove-orphans
	docker compose --profile with-nginx down -v --remove-orphans

prune:
	docker system prune -af
	docker volume prune -f

# Restart services
restart:
	docker compose restart

restart-app:
	docker compose restart app
