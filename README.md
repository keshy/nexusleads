# PLG Lead Sourcer

Enterprise-grade application for sourcing and qualifying leads from GitHub repositories for Product-Led Growth businesses.

## Features

- 🔐 **Authentication**: Static credential-based user management (SAML-ready architecture)
- 📊 **Dashboards**: Real-time insights into repositories, contributors, and key leads
- 🎯 **Smart Lead Scoring**: AI-powered classification (Decision Makers, Key Contributors, High Impact)
- 🔄 **Automated Sourcing**: Scheduled and on-demand GitHub repository analysis
- 🌐 **Social Profiling**: LinkedIn and web search integration for lead enrichment
- 📈 **Analytics**: Project-based insights and contributor statistics
- ⚙️ **Background Jobs**: Robust job tracking with progress metering

## Architecture

```
plg-lead-sourcer/
├── backend/          # FastAPI application
├── frontend/         # React application
├── jobs/             # Background job processors
├── database/         # Schema and migrations
└── shared/           # Shared utilities
```

## Tech Stack

- **Backend**: Python 3.11+, FastAPI
- **Frontend**: React 18, TypeScript, TailwindCSS, shadcn/ui
- **Database**: PostgreSQL 15+
- **Job Queue**: Database-backed job system
- **AI/ML**: OpenAI GPT-4 for lead classification

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- GitHub Personal Access Token
- OpenAI API Key (optional, for AI classification)

### 1. Database Setup

```bash
createdb plg_lead_sourcer
cd database
psql -d plg_lead_sourcer -f schema.sql
```

### 2. Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Run migrations
alembic upgrade head

# Start API server
uvicorn main:app --reload --port 8000
```

### 3. Frontend Setup

```bash
cd frontend
npm install

# Configure environment
cp .env.example .env
# Edit .env with API endpoint

# Start development server
npm run dev
```

### 4. Background Jobs

```bash
cd jobs
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run job processor
python job_processor.py
```

## Configuration

### Environment Variables

#### Backend (`backend/.env`)
```
DATABASE_URL=postgresql://user:password@localhost/plg_lead_sourcer
SECRET_KEY=your-secret-key-here
GITHUB_TOKEN=ghp_your_github_token
OPENAI_API_KEY=sk-your-openai-key  # Optional
SERPER_API_KEY=your-serper-key  # For web search
```

#### Frontend (`frontend/.env`)
```
VITE_API_URL=http://localhost:8000
```

## Usage

### 1. Login
Default credentials:
- Username: `admin`
- Password: `admin123`

### 2. Create a Project
Navigate to Projects → New Project and give it a name and description.

### 3. Add Repository
- Paste a GitHub repository URL
- Configure sourcing interval (default: monthly)
- Start sourcing process

### 4. Monitor Progress
Watch the sourcing job progress in real-time with detailed status updates.

### 5. Analyze Leads
Review classified leads by category:
- **Decision Makers**: C-suite, VPs, Directors
- **Key Contributors**: Maintainers, Core team members
- **High Impact**: Active contributors with significant commits

## API Documentation

Once the backend is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Database Schema

### Core Tables
- `users`: System users (authentication)
- `projects`: Lead sourcing projects
- `repositories`: GitHub repositories
- `contributors`: GitHub contributors/users
- `contributor_stats`: Activity metrics
- `social_context`: Enriched social profiles
- `sourcing_jobs`: Background job tracking
- `job_progress`: Job progress metering

## Development

### Running Tests

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

### Database Migrations

```bash
cd backend
alembic revision --autogenerate -m "Description"
alembic upgrade head
```

## Deployment

### Production Considerations

1. **Environment Variables**: Use secrets management (AWS Secrets Manager, HashiCorp Vault)
2. **Database**: Use managed PostgreSQL (AWS RDS, Google Cloud SQL)
3. **API**: Deploy with Gunicorn/Uvicorn behind Nginx
4. **Frontend**: Build and serve static files via CDN
5. **Jobs**: Run as systemd service or Kubernetes CronJob
6. **Rate Limiting**: Configure GitHub API rate limits appropriately
7. **Monitoring**: Add APM (DataDog, New Relic) and logging (ELK stack)

### Docker Deployment

```bash
docker-compose up -d
```

## Roadmap

- [ ] SAML/SSO authentication
- [ ] Advanced analytics and custom reports
- [ ] Email notifications for completed jobs
- [ ] Webhook integrations (Slack, Teams)
- [ ] Export functionality (CSV, PDF)
- [ ] Multi-tenancy support
- [ ] Advanced filtering and search
- [ ] API rate limiting and quotas

## License

MIT License

## Support

For issues and feature requests, please create an issue in the repository.
