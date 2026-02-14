# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SIGRP (Sistema Integrado de Gestión de Recursos y Proyectos) is a Django-based monolithic system for integrated management of human resources, projects, and predictive analytics with a **dual-cost architecture** (Estimation vs. Execution).

**Core Concept**: Separation between role-based estimation/billing (using `Role.standard_rate`) and resource-based actual costs (using `Resource.internal_cost`). This enables accurate profit margin calculation and variance analysis.

## Technology Stack

- **Framework**: Django 5.x + HTMX
- **Database**: PostgreSQL 15+ (JSONB for skills_vector)
- **Vector Store**: Qdrant (for skill embeddings)
- **Cache & Queue**: Redis + Celery
- **NLP**: spaCy (sentiment analysis in standups)
- **Server**: Gunicorn
- **Package Manager**: uv (Astral) - **Always use `uv run` prefix for all Python commands**

## Essential Commands

### Development Server
```bash
# Start Django development server
uv run python manage.py runserver

# Start Celery worker (Windows)
uv run celery -A config worker -l info --pool=solo

# Start Celery worker (Linux/macOS)
uv run celery -A config worker -l info

# Start Celery beat (periodic tasks)
uv run celery -A config beat -l info
```

### Database Management
```bash
# Create migrations
uv run python manage.py makemigrations

# Apply migrations
uv run python manage.py migrate

# Create superuser
uv run python manage.py createsuperuser

# Django database shell
uv run python manage.py dbshell
```

### Testing
```bash
# Run all tests
uv run pytest

# Run tests with coverage report
uv run pytest --cov=apps --cov-report=html

# Run specific test file
uv run pytest apps/projects/tests/test_models.py

# Run specific test
uv run pytest apps/projects/tests/test_models.py::TestTaskModel::test_dual_cost_logic
```

### Code Quality
```bash
# Format code with black
uv run black .

# Lint code with ruff
uv run ruff check .

# Type checking with mypy
uv run mypy apps/
```

### Docker Services
```bash
# Start all services (PostgreSQL, Redis, Qdrant)
docker-compose up -d

# View service logs
docker-compose logs -f db

# Stop services
docker-compose down

# Stop and remove volumes (WARNING: deletes data)
docker-compose down -v
```

### Other Useful Commands
```bash
# Django shell with IPython
uv run python manage.py shell

# Collect static files
uv run python manage.py collectstatic

# Check Django configuration
uv run python manage.py check

# Show applied migrations
uv run python manage.py showmigrations

# Download spaCy Spanish model
uv run python -m spacy download es_core_news_sm
```

## Architecture

### App Structure
```
apps/
├── core/           # Base abstract models (TimeStampedModel, AuditableModel)
├── resources/      # Human resources: Role and Resource models
├── projects/       # Projects: Project, Stage, Task, TimeLog, TimeEntry, Allocation
├── standups/       # Daily standups with NLP analysis
└── analytics/      # Dashboards and reports
```

### Dual-Cost Architecture

**Critical Design Pattern**: All financial calculations follow dual-cost logic:

1. **Estimation/Billing Layer (Role-based)**:
   - `Role.standard_rate` → Used for project estimation and client billing
   - `Task.required_role` + `Task.estimated_hours` → `Task.planned_value`
   - `TimeLog.billable_amount` = hours × role.standard_rate

2. **Execution/Cost Layer (Resource-based)**:
   - `Resource.internal_cost` → Actual hourly cost to company
   - `Task.assigned_resource` + `Task.logged_hours` → `Task.actual_cost_projection`
   - `TimeLog.cost` = hours × resource.internal_cost

3. **Profit Analysis**:
   - Margin = (billable - cost) / billable × 100
   - Variance = actual_cost - planned_value
   - Project-level metrics aggregate from TimeLog and TimeEntry

### Key Models

**Base Models** (apps/core/models.py):
- `TimeStampedModel`: Adds created_at, updated_at
- `AuditableModel`: Extends TimeStampedModel with created_by, updated_by

**Resources** (apps/resources/models.py):
- `Role`: Professional roles with standard_rate for billing (e.g., "Senior Developer @ $150/h")
- `Resource`: Real people with internal_cost for actual expenses (e.g., "Juan @ $80/h")

**Projects** (apps/projects/models.py):
- `Project`: Fixed Price or Time & Materials, tracks total_cost, total_billable, profit_margin
- `Stage`: Logical grouping of tasks (Sprint, Phase)
- `Task`: Individual work items with dual-cost tracking
- `TimeLog`: Time entries for specific tasks (auto-calculates cost and billable_amount)
- `TimeEntry`: Time entries at project level (meetings, overhead)
- `Allocation`: Resource assignment with burnout/context-switching validation (RF-11)

### Auto-Calculation Rules

**TimeLog.save() and TimeEntry.save()**:
- Automatically calculate `cost` = hours × resource.internal_cost
- Automatically calculate `billable_amount` = hours × role.standard_rate (if billable)
- Update Task.logged_hours via Django signals

**Task Properties** (@property methods):
- `planned_value`: estimated_hours × required_role.standard_rate
- `actual_cost_projection`: logged_hours × assigned_resource.internal_cost
- `cost_variance`: actual_cost_projection - planned_value
- `hours_variance`: logged_hours - estimated_hours

**Project Properties**:
- `total_logged_hours`: Sum from TimeLog + TimeEntry
- `total_cost`: Sum of all internal costs
- `total_billable`: Sum of all billable amounts
- `profit_margin`: ((total_billable - total_cost) / total_billable) × 100

### Resource Allocation Validation (RF-11)

The `Allocation` model implements mathematical validation to prevent:
1. **Burnout (Hard Block)**: Total hours_per_week across overlapping allocations cannot exceed resource capacity (default 40h/week)
2. **Context Switching (Soft Warning)**: Warns when a resource is assigned to 3+ concurrent projects (can reduce efficiency by 40%)

When creating/editing allocations, the `clean()` method validates against overlapping assignments and raises `ValidationError` if capacity is exceeded.

## Development Guidelines

### When Working with Financial Models
- **Never** manually set `cost` or `billable_amount` on TimeLog/TimeEntry - these are auto-calculated
- Always consider both estimation (Role-based) and execution (Resource-based) layers
- Use `@property` methods for calculated fields instead of stored fields
- Ensure all decimal fields use `Decimal` type, not float

### When Creating Migrations
- Run `uv run python manage.py makemigrations` after model changes
- Review generated migrations before applying
- For data migrations, create empty migration: `uv run python manage.py makemigrations --empty app_name`

### When Writing Tests
- Use pytest fixtures for common test data
- Test both happy path and validation errors
- For financial models, test decimal precision and auto-calculations
- Example location: `apps/projects/tests/`

### When Adding New Apps
```bash
uv run python manage.py startapp app_name apps/app_name
```
Then:
1. Add to `INSTALLED_APPS` in config/settings.py
2. Inherit from `AuditableModel` or `TimeStampedModel` for automatic audit fields
3. Register in Django admin if needed

### Environment Variables
Copy `.env.example` to `.env` and configure:
- `SECRET_KEY`: Django secret (change in production)
- `DEBUG`: Set to False in production
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`: PostgreSQL credentials (docker-compose uses sigrp/sigrp/sigrp_db)
- `DB_HOST`: localhost (default)
- `DB_PORT`: 5433 (docker-compose maps to 5433, not 5432)
- `REDIS_URL`: redis://localhost:6379/0

### Database Port Configuration
**Important**: The docker-compose.yml maps PostgreSQL to port **5433** (not 5432) to avoid conflicts. Ensure `.env` uses:
```
DB_PORT=5433
```

### Celery on Windows
Always use `--pool=solo` flag on Windows:
```bash
uv run celery -A config worker -l info --pool=solo
```

### Code Style
- Line length: 100 characters (configured in pyproject.toml)
- Use Black for formatting
- Follow Django naming conventions (models: PascalCase, functions: snake_case)
- Add docstrings to complex business logic methods

## Common Patterns

### Creating a Task with Dual-Cost Logic
```python
# 1. Define estimation (Role-based)
task = Task.objects.create(
    project=project,
    title="Implement auth",
    required_role=Role.objects.get(code="SBE"),  # Senior Backend Engineer
    estimated_hours=Decimal("40.00"),
    # planned_value auto-calculated: 40h × $150/h = $6,000
)

# 2. Assign execution (Resource-based)
task.assigned_resource = Resource.objects.get(employee_id="EMP001")
task.save()

# 3. Log time (auto-calculates cost and billable_amount)
TimeLog.objects.create(
    task=task,
    resource=task.assigned_resource,
    date=date.today(),
    hours=Decimal("8.00"),
    description="Implemented JWT authentication",
    # cost auto-calculated: 8h × resource.internal_cost
    # billable_amount auto-calculated: 8h × role.standard_rate
)
```

### Checking Project Profitability
```python
project = Project.objects.get(code="PRJ-2026-001")

# All properties are auto-calculated via aggregation
print(f"Total Hours: {project.total_logged_hours}")
print(f"Total Cost: ${project.total_cost}")
print(f"Total Billable: ${project.total_billable}")
print(f"Profit Margin: {project.profit_margin}%")
print(f"Over Budget: {project.is_over_budget}")
```

## Documentation References

- [ESPEC.md](ESPEC.md) - Full requirements specification (SRS)
- [ARCHITECTURE.md](ARCHITECTURE.md) - Data architecture and models
- [SETUP.md](SETUP.md) - Detailed installation guide
- [UV_REFERENCE.md](UV_REFERENCE.md) - uv quick reference
- [RF-11_IMPLEMENTATION_SUMMARY.md](RF-11_IMPLEMENTATION_SUMMARY.md) - Resource leveling implementation
- [docs/MODELOS_IMPLEMENTADOS.md](docs/MODELOS_IMPLEMENTADOS.md) - Detailed model documentation

## Ports and Services

- **Django**: http://localhost:8000
- **Django Admin**: http://localhost:8000/admin
- **PostgreSQL**: localhost:5433 (mapped from container's 5432)
- **Redis**: localhost:6379
- **Qdrant HTTP**: http://localhost:6333
- **Qdrant gRPC**: localhost:6334
- **Qdrant Dashboard**: http://localhost:6333/dashboard
