# PLG Lead Sourcer - Setup Guide

## Overview

This guide will help you set up and run the complete PLG Lead Sourcer application.

## Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- GitHub Personal Access Token
- OpenAI API Key (optional, for AI classification)
- Serper API Key (optional, for web search)

## Quick Setup

### 1. Database Setup

```bash
# Create database
createdb plg_lead_sourcer

# Run schema
cd database
psql -d plg_lead_sourcer -f schema.sql
```

### 2. Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env with your credentials:
# - DATABASE_URL
# - SECRET_KEY (generate with: openssl rand -hex 32)
# - GITHUB_TOKEN
# - OPENAI_API_KEY (optional)
# - SERPER_API_KEY (optional)

# Start API server
uvicorn main:app --reload --port 8000
```

The API will be available at http://localhost:8000
- API Documentation: http://localhost:8000/docs

### 3. Background Jobs Setup

```bash
cd jobs
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Use same credentials as backend

# Run job processor
python job_processor.py
```

### 4. Frontend Setup

```bash
cd frontend
npm install

# Create .env file
cp .env.example .env
# Default: VITE_API_URL=http://localhost:8000

# Start development server
npm run dev
```

The frontend will be available at http://localhost:5173

## Default Credentials

- **Username**: admin
- **Password**: admin123

## Application Workflow

### 1. Login
Access the application at http://localhost:5173 and login with default credentials.

### 2. Create a Project
- Navigate to "Projects"
- Click "New Project"
- Enter project name and description
- Click "Create"

### 3. Add Repository
- Open your project
- Click "Add Repository"
- Paste GitHub repository URL (e.g., https://github.com/facebook/react)
- Set sourcing interval (daily, weekly, monthly)
- Click "Add"

### 4. Monitor Sourcing
- The system automatically creates a sourcing job
- View job progress in "Jobs" section
- Job processor will:
  - Fetch repository metadata
  - Identify contributors
  - Calculate activity statistics
  - Store normalized data

### 5. Enrich Social Profiles
- Navigate to "Contributors" or "Leads"
- Click on a contributor
- Click "Enrich Profile"
- System will:
  - Search for LinkedIn profile
  - Extract professional information
  - Classify using LLM (DECISION_MAKER, KEY_CONTRIBUTOR, HIGH_IMPACT)
  - Calculate lead scores

### 6. Review Dashboard
- Access comprehensive dashboard with:
  - Total projects, repositories, contributors
  - Qualified leads count
  - Classification breakdowns
  - Top leads by score
  - Recent activity feed

## API Endpoints

### Authentication
- `POST /api/auth/login` - Login
- `POST /api/auth/register` - Register new user
- `GET /api/auth/me` - Get current user

### Projects
- `GET /api/projects` - List projects
- `POST /api/projects` - Create project
- `GET /api/projects/{id}` - Get project details
- `PUT /api/projects/{id}` - Update project
- `DELETE /api/projects/{id}` - Delete project

### Repositories
- `GET /api/repositories` - List repositories
- `POST /api/repositories` - Add repository
- `GET /api/repositories/{id}` - Get repository details
- `POST /api/repositories/{id}/source-now` - Trigger immediate sourcing
- `PUT /api/repositories/{id}` - Update repository
- `DELETE /api/repositories/{id}` - Delete repository

### Contributors/Leads
- `GET /api/contributors` - List contributors (with filtering)
- `GET /api/contributors/{id}` - Get contributor details
- `POST /api/contributors/{id}/enrich` - Trigger social enrichment

### Jobs
- `GET /api/jobs` - List jobs
- `GET /api/jobs/{id}` - Get job details with progress
- `POST /api/jobs/{id}/cancel` - Cancel job
- `GET /api/jobs/stats/summary` - Get job statistics

### Dashboard
- `GET /api/dashboard/stats` - Get dashboard statistics
- `GET /api/dashboard/repositories/stats` - Get repository statistics
- `GET /api/dashboard/recent-activity` - Get recent activity
- `GET /api/dashboard/top-leads` - Get top leads

## Features

### Dashboard
- **Summary Cards**: Projects, repositories, contributors, qualified leads
- **Classification Breakdown**: Decision makers, key contributors, high impact
- **Job Status**: Active, pending, completed jobs
- **Top Leads**: Highest scoring leads with profiles
- **Recent Activity**: Real-time job updates
- **Repository Stats**: Lead distribution by repository

### Projects
- Create multiple sourcing projects
- Track repositories per project
- View project-level statistics
- Manage project lifecycle

### Repository Management
- Add repositories via URL
- Configure sourcing intervals (daily/weekly/monthly)
- On-demand sourcing trigger
- Automatic scheduling
- Repository metadata tracking

### Contributor Analysis
- Comprehensive GitHub profile data
- Activity statistics (commits, PRs, issues)
- Time-based metrics (3m, 6m, 12m)
- Maintainer detection
- Contribution patterns

### Social Enrichment
- LinkedIn profile discovery
- Professional information extraction
- Position classification
- Company identification
- Experience estimation

### AI-Powered Classification
- **DECISION_MAKER**: C-suite, VPs, Directors who make purchasing decisions
- **KEY_CONTRIBUTOR**: Maintainers, architects with high influence (bottom-up motion)
- **HIGH_IMPACT**: Active contributors with significant recent contributions

### Lead Scoring
- **Activity Score** (25%): Recent contributions, total commits, PRs
- **Influence Score** (20%): Followers, public repos, community presence
- **Position Score** (40%): Professional role, decision-making authority
- **Engagement Score** (15%): Issues, reviews, contribution recency

Qualified leads have scores ≥ 60/100

### Job System
- Database-backed job queue
- Progress tracking with detailed steps
- Real-time status updates
- Error handling and retry logic
- Concurrent job processing

## Environment Variables

### Backend
```env
DATABASE_URL=postgresql://user:password@localhost/plg_lead_sourcer
SECRET_KEY=your-secret-key
GITHUB_TOKEN=ghp_your_token
OPENAI_API_KEY=sk_your_key  # Optional
SERPER_API_KEY=your_key  # Optional
ALLOWED_ORIGINS=http://localhost:5173
```

### Jobs
```env
DATABASE_URL=postgresql://user:password@localhost/plg_lead_sourcer
GITHUB_TOKEN=ghp_your_token
OPENAI_API_KEY=sk_your_key  # Optional
SERPER_API_KEY=your_key  # Optional
CHECK_INTERVAL_SECONDS=30
MAX_CONCURRENT_JOBS=3
```

### Frontend
```env
VITE_API_URL=http://localhost:8000
```

## Troubleshooting

### Database Connection Issues
- Verify PostgreSQL is running: `pg_isready`
- Check DATABASE_URL format
- Ensure database exists: `psql -l`

### GitHub API Rate Limits
- Check rate limit: `curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/rate_limit`
- Use authenticated requests (provide GITHUB_TOKEN)
- Implement backoff strategy

### Job Processing Issues
- Check job processor logs
- Verify jobs table has pending jobs
- Ensure background processor is running
- Check for error messages in sourcing_jobs table

### Frontend Not Loading
- Verify backend is running (port 8000)
- Check browser console for errors
- Verify CORS settings in backend
- Clear browser cache

## Production Deployment

### Security
1. Change default admin password
2. Use strong SECRET_KEY
3. Enable HTTPS
4. Implement rate limiting
5. Use environment-specific configurations
6. Enable database SSL

### Scaling
1. Use managed PostgreSQL (AWS RDS, Google Cloud SQL)
2. Deploy API with Gunicorn/Uvicorn workers
3. Use Redis for caching
4. Implement CDN for frontend
5. Run multiple job processors
6. Add monitoring (DataDog, New Relic)

### Monitoring
1. Add application logging (ELK stack)
2. Set up alerts for failed jobs
3. Monitor GitHub API rate limits
4. Track database performance
5. Monitor job queue depth

## Support

For issues, feature requests, or questions:
- Check API documentation: http://localhost:8000/docs
- Review database schema: `database/schema.sql`
- Check logs for detailed error messages

## License

MIT License
