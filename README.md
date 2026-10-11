# Finance

A personal finance web application for tracking income, expenses, savings, and recurring payments. A dashboard brings together transaction history, category breakdowns, cash flow, and spending activity.

Built with **Python, FastAPI, and PostgreSQL**, with a JavaScript frontend served by the same application. The project includes JWT authentication, versioned database migrations, integration tests against PostgreSQL, and a GitHub Actions CI workflow.

## Features

- **Transaction management** — create, edit, and delete transactions; browse a paginated history.
- **Custom categories** — organize income, expenses, and savings with named, color-coded categories.
- **Savings tracking** — move funds between available money and a savings vault while preserving total net worth.
- **Recurring payments** — define monthly income or expenses, catch up on missed dates, and prevent duplicate entries.
- **Financial analytics** — view balances, cash flow for a selected period, expense breakdowns, and an activity heatmap.
- **User accounts** — JWT authentication, bcrypt password hashing, and ownership checks for financial records.

## Engineering details

- Monetary amounts are stored as **integer cents** in PostgreSQL `BIGINT` columns. The UI displays EUR.
- Pydantic validates API inputs; database constraints enforce nonzero amounts and valid recurring-payment settings.
- Recurring-payment processing uses PostgreSQL row locks and a persistent record of each scheduled occurrence to prevent duplicate entries, including after a generated transaction is deleted.
- Alembic migrations manage schema changes independently of application startup.
- Tests exercise the API against a real PostgreSQL database, with data changes rolled back after each test.

## Technology stack

| Area | Technologies |
| --- | --- |
| Backend | Python 3.13 / 3.14, FastAPI, Uvicorn |
| Database | PostgreSQL, SQLModel, SQLAlchemy, psycopg2 |
| Validation and authentication | Pydantic, JWT via python-jose, bcrypt |
| Schema migrations | Alembic |
| Frontend | Jinja2, HTML, CSS, JavaScript modules, Chart.js |
| Testing and CI | pytest, HTTPX, GitHub Actions |

## Architecture

```text
Browser: HTML / CSS / JavaScript
                |
                | HTTP requests and JSON responses
                v
FastAPI: authentication, validation, routes, financial calculations
                |
                | SQLModel / SQLAlchemy
                v
           PostgreSQL
```

FastAPI serves both the frontend and the API. There is no separate frontend build step. Database migrations and account administration run as explicit commands.

```text
app/
├── main.py           # Application setup, routes, static files, health checks
├── cli.py            # User administration and recurring-payment processing
├── core/             # Configuration, database connection, models, authentication
├── api/              # Endpoints, request/response schemas, analytics, payment logic
├── templates/        # Main HTML page
└── static/           # JavaScript modules and CSS
migrations/           # Alembic configuration code and schema revisions
tests/                # PostgreSQL fixtures and API integration tests
scripts/              # Legacy data checks, seeding tools, query benchmarks
.github/workflows/    # CI workflow
run.py                # Local development server entry point
```

## Getting started

### Prerequisites

- Python 3.13 or 3.14.
- A running PostgreSQL instance; CI is configured to use PostgreSQL 17.
- A database and a database user that owns it.

Run the following commands from the repository root. Shell examples use Bash.

### 1. Install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### 2. Configure the application

```bash
cp .env.example .env
python -c 'import secrets; print(secrets.token_urlsafe(48))'
```

Copy the generated value into `SECRET_KEY` in `.env` and set `DATABASE_URL` to your database connection string:

```dotenv
DATABASE_URL=postgresql+psycopg2://finance:replace_db_password@127.0.0.1:5432/finance
SECRET_KEY=replace_with_the_generated_value
ACCESS_TOKEN_EXPIRE_MINUTES=30
APP_TIMEZONE=Europe/Berlin
```

`SECRET_KEY` must contain at least 32 characters. Environment variables take precedence over values in `.env`. Keep `.env` out of version control.

If you need to create a database, connect to PostgreSQL as an administrator and run the following SQL, replacing the example password:

```sql
CREATE USER finance WITH PASSWORD 'replace_db_password';
CREATE DATABASE finance OWNER finance;
```

The `POSTGRES_*` entries in `.env.example` do not provision a database. The application connects using `DATABASE_URL`.

### 3. Initialize a new database and create an account

For a **new, empty database**:

```bash
python -m alembic upgrade head
python -m app.cli create-user alice
```

The account command prompts for a password and creates starter categories. There is no public registration endpoint or automatically created default account.

### 4. Start the application

```bash
python run.py
```

- Application: [http://127.0.0.1:8080](http://127.0.0.1:8080)
- Interactive API documentation: [http://127.0.0.1:8080/docs](http://127.0.0.1:8080/docs)
- Liveness check: `/health`
- Database readiness check: `/health/ready`

The development server binds to localhost and reloads when source files change. Chart.js is loaded from a CDN, so charts require network access.

## Database migrations

Application startup does not create or update tables. After pulling changes that include new migrations, apply them before starting the application:

```bash
python -m alembic upgrade head
```

The current migration chain contains:

| Revision | Changes |
| --- | --- |
| `0001` | Original users, categories, transactions, and recurring-payment tables |
| `0002` | `BIGINT` amounts, validation constraints, query indexes, recurring-payment creation dates, and occurrence records |

For an existing database created before Alembic was introduced, make a backup and run `python -m scripts.preflight`. After separately confirming that its schema matches revision `0001`, use `python -m alembic stamp 0001`, then `python -m alembic upgrade head`. Stamping records a version; it does not validate or modify the existing schema. Revision `0002` assigns the migration date as the creation date of legacy recurring payments.

## Account and payment administration

```bash
python -m app.cli set-password alice
python -m app.cli process-recurring
```

Recurring payments are processed when the dashboard loads or when the CLI command runs. There is no background scheduler. Dates such as the 31st fall on the last available day in shorter months.

## Testing

Create a separate PostgreSQL database owned by your test user. Its name must end in `_test`; for example, run `CREATE DATABASE finance_test OWNER finance;` as a database administrator.

```bash
python -m pip install -r requirements-dev.txt
export TEST_DATABASE_URL='postgresql+psycopg2://finance:replace_db_password@127.0.0.1:5432/finance_test'
python -m pytest
```

The test suite requires an explicit `TEST_DATABASE_URL`, applies migrations, and uses a test JWT key. It does not use the application database URL from `.env`. Each test rolls back its data changes; the migrated schema remains in the test database.

Coverage includes authentication and expired tokens, user data isolation, transaction CRUD and pagination, amount validation, category conflicts, balances, cash flow, and recurring-payment deduplication.

## Continuous integration

The [GitHub Actions workflow](.github/workflows/ci.yml) runs on pushes, pull requests, and manual dispatch. For both Python 3.13 and 3.14, it:

1. Starts an isolated PostgreSQL 17 service and installs dependencies.
2. Checks package compatibility with `pip check`.
3. Applies migrations and checks that the schema matches the models.
4. Runs the integration tests.
5. Rolls back and reapplies migrations in the disposable test database.
6. Checks the syntax of the frontend JavaScript modules.

CI uses disposable credentials and requires no repository secrets. It does not deploy the application.

## Current scope and limitations

- Profile editing is not implemented in the backend.
- Tests cover the API and business logic; browser end-to-end tests are not included.
- Migration rollback is checked on an empty test dataset, not on a copy of historical user data.
- The Alembic template currently contains a stray Markdown fence that must be removed before generating new migration files; applying the existing revisions is unaffected.
- Legacy seeding and benchmark scripts are outside the CI checks and are not part of the application startup flow.
