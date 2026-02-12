# PLG Lead Sourcer - Quick Start Guide

## What You've Got

A complete enterprise-grade PLG lead sourcing application with:

- **Backend API** (FastAPI + PostgreSQL)
- **Background Jobs** (Python job processor)
- **Frontend** (React + TypeScript + TailwindCSS)
- **Database** (PostgreSQL with normalized schema)

## Quick Setup (5 minutes)

### 1. Database Setup

```bash
# Create database
createdb plg_lead_sourcer

# Import schema
psql -d plg_lead_sourcer -f database/schema.sql
```

This creates all tables and the default admin user (admin/admin123).

### 2. Backend Setup

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create environment file
cp .env.example .env
```

Edit `.env` and set:
- `DATABASE_URL=postgresql://your_user:your_password@localhost/plg_lead_sourcer`
- `SECRET_KEY=$(openssl rand -hex 32)`
- `GITHUB_TOKEN=ghp_your_github_token`

```bash
# Start API
uvicorn main:app --reload --port 8000
```

API runs at: http://localhost:8000

### 3. Background Jobs Setup

```bash
cd jobs
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Use same .env as backend
cp ../backend/.env .env

# Start job processor
python job_processor.py
```

### 4. Frontend Setup

```bash
cd frontend
npm install

# Create environment file
cp .env.example .env
# Default VITE_API_URL=http://localhost:8000 should work

# Start dev server
npm run dev
```

Frontend runs at: http://localhost:5173

## First Use

1. **Login**: http://localhost:5173/login
   - Username: `admin`
   - Password: `admin123`

2. **Create Project**:
   - Click "Projects" → "New Project"
   - Name: "My First Project"
   - Click "Create"

3. **Add Repository**:
   - Open your project
   - Click "Add Repository"  
   - Paste GitHub URL: `https://github.com/facebook/react`
   - Set interval: "monthly"
   - Click "Add"

4. **Monitor Progress**:
   - Go to "Jobs" to see sourcing progress
   - Job processor will:
     - Fetch repository metadata
     - Identify contributors (top 100)
     - Calculate activity stats
     - Store in database

5. **View Results**:
   - Dashboard shows overall stats
   - Contributors page lists all leads
   - Each lead has GitHub profile data

## Key API Endpoints

```
POST   /api/auth/login          # Login
GET    /api/dashboard/stats     # Dashboard data
GET    /api/projects            # List projects
POST   /api/repositories        # Add repository
POST   /api/repositories/{id}/source-now  # Trigger sourcing
GET    /api/contributors        # List leads
GET    /api/jobs                # View jobs
```

Full API docs: http://localhost:8000/docs

## Architecture

```
┌─────────────┐
│   Browser   │
│  (React)    │
└──────┬──────┘
       │ HTTP
       ▼
┌─────────────┐      ┌──────────────┐
│   FastAPI   │◄────►│  PostgreSQL  │
│   Backend   │      │   Database   │
└──────┬──────┘      └──────────────┘
       │                     ▲
       │                     │
       ▼                     │
┌─────────────┐             │
│ Job Queue   │─────────────┘
│ (Database)  │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│Background   │
│Job Processor│
└─────────────┘
       │
       ▼
┌─────────────┐
│GitHub API   │
│LinkedIn     │
│OpenAI       │
└─────────────┘
```

## Database Schema Highlights

### Core Tables
- **users** - Authentication
- **projects** - Sourcing projects
- **repositories** - GitHub repos
- **contributors** - GitHub users
- **contributor_stats** - Activity metrics
- **social_context** - LinkedIn + AI classification
- **lead_scores** - Computed lead scores
- **sourcing_jobs** - Job tracking
- **job_progress** - Progress steps

### Lead Classification
- **DECISION_MAKER**: C-suite, VPs, Directors
- **KEY_CONTRIBUTOR**: Maintainers, architects
- **HIGH_IMPACT**: Active contributors

## Features Implemented

### ✅ Authentication
- JWT-based login
- Static credentials (SAML-ready architecture)
- Protected routes

### ✅ Dashboard
- Total projects, repos, contributors
- Qualified leads count
- Classification breakdown
- Top leads by score

### ✅ Projects
- Create/view/delete projects
- Project-level statistics
- Repository management

### ✅ Repository Sourcing
- Add repos via GitHub URL
- Configurable intervals (daily/weekly/monthly)
- On-demand sourcing
- Automatic scheduling

### ✅ Contributor Analysis
- GitHub profile data
- Commit statistics (3m, 6m, 12m)
- Maintainer detection
- Activity patterns

### ✅ Social Enrichment (Optional)
- LinkedIn profile discovery
- Professional information
- AI-powered classification
- Position analysis

### ✅ Lead Scoring
- Activity score (25%)
- Influence score (20%)
- Position score (40%)
- Engagement score (15%)
- Qualified threshold: 60/100

### ✅ Job System
- Database-backed queue
- Progress tracking
- Real-time updates
- Error handling

## Optional Enhancements

### Enable AI Classification

1. Get OpenAI API key from https://platform.openai.com/api-keys

2. Add to `.env`:
```
OPENAI_API_KEY=sk-your-openai-api-key
OPENAI_MODEL=gpt-4-turbo-preview
```

3. Restart job processor

### Enable LinkedIn Search

1. Get Serper API key from https://serper.dev/

2. Add to `.env`:
```
SERPER_API_KEY=your-serper-api-key
```

3. Restart job processor

## Troubleshooting

### TypeScript Errors in Frontend
**All TypeScript/lint errors are expected before `npm install`.**  
They resolve automatically once you run `npm install`.

### Database Connection Failed
```bash
# Check PostgreSQL is running
pg_isready

# Verify connection string in .env
DATABASE_URL=postgresql://user:password@localhost/plg_lead_sourcer
```

### GitHub API Rate Limit
- Unauthenticated: 60 requests/hour
- Authenticated: 5,000 requests/hour
- Always provide `GITHUB_TOKEN` in `.env`

### Jobs Not Processing
```bash
# Check job processor is running
ps aux | grep job_processor

# Check for pending jobs
psql plg_lead_sourcer -c "SELECT COUNT(*) FROM sourcing_jobs WHERE status='pending';"

# Check job processor logs for errors
```

### Frontend Not Loading
1. Verify backend is running (http://localhost:8000/health)
2. Check CORS settings in backend/.env
3. Clear browser cache
4. Check browser console for errors

## Next Steps

### Expand Functionality

1. **Complete Repository Page**
   - List repositories with stats
   - Edit sourcing interval
   - Trigger immediate sourcing

2. **Enhanced Contributors Page**
   - Filtering by classification
   - Sorting by score
   - Enrichment triggers
   - Export to CSV

3. **Advanced Jobs Page**
   - Real-time progress bars
   - Job cancellation
   - Job history
   - Retry failed jobs

4. **Analytics**
   - Lead conversion tracking
   - Source effectiveness
   - Time-based trends
   - Custom reports

### Production Deployment

1. **Security**
   - Change default admin password
   - Use strong SECRET_KEY
   - Enable HTTPS
   - Implement rate limiting
   - Add CSRF protection

2. **Infrastructure**
   - Managed PostgreSQL (AWS RDS, Cloud SQL)
   - Container orchestration (Docker/Kubernetes)
   - CDN for frontend
   - Load balancer for API
   - Redis for caching

3. **Monitoring**
   - Application logs (ELK stack)
   - APM (DataDog, New Relic)
   - Error tracking (Sentry)
   - Uptime monitoring
   - Alert configuration

4. **Scaling**
   - Multiple job processors
   - Database read replicas
   - API autoscaling
   - Queue optimization

## Files Structure

```
plg-lead-sourcer/
├── README.md                  # Main documentation
├── SETUP_GUIDE.md            # Detailed setup
├── QUICKSTART.md             # This file
├── FRONTEND_IMPLEMENTATION.md # Frontend details
│
├── database/
│   └── schema.sql            # Database schema
│
├── backend/                  # FastAPI application
│   ├── main.py              # API entry point
│   ├── config.py            # Configuration
│   ├── database.py          # DB connection
│   ├── models.py            # SQLAlchemy models
│   ├── schemas.py           # Pydantic schemas
│   ├── auth.py              # Authentication
│   ├── requirements.txt     # Python dependencies
│   ├── .env.example         # Environment template
│   └── routers/             # API routes
│       ├── auth.py
│       ├── projects.py
│       ├── repositories.py
│       ├── contributors.py
│       ├── jobs.py
│       └── dashboard.py
│
├── jobs/                     # Background job processor
│   ├── job_processor.py     # Main processor
│   ├── config.py            # Configuration
│   ├── database.py          # DB connection
│   ├── requirements.txt     # Python dependencies
│   ├── .env.example         # Environment template
│   └── services/            # Service layer
│       ├── github_service.py      # GitHub API
│       ├── enrichment_service.py  # Social enrichment
│       └── scoring_service.py     # Lead scoring
│
└── frontend/                 # React application
    ├── index.html           # HTML entry
    ├── package.json         # npm dependencies
    ├── vite.config.ts       # Vite config
    ├── tailwind.config.js   # Tailwind config
    ├── tsconfig.json        # TypeScript config
    ├── .env.example         # Environment template
    └── src/
        ├── main.tsx         # App entry
        ├── App.tsx          # Main app
        ├── index.css        # Global styles
        ├── lib/
        │   ├── api.ts       # API client
        │   └── utils.ts     # Utilities
        ├── contexts/
        │   └── AuthContext.tsx  # Auth state
        ├── components/
        │   └── Layout.tsx   # Main layout
        └── pages/           # Page components
            ├── Login.tsx
            ├── Dashboard.tsx
            ├── Projects.tsx
            ├── ProjectDetail.tsx
            ├── Repositories.tsx
            ├── Contributors.tsx
            └── Jobs.tsx
```

## Getting Help

- **API Documentation**: http://localhost:8000/docs
- **Database Schema**: `database/schema.sql`
- **Setup Guide**: `SETUP_GUIDE.md`
- **Frontend Details**: `FRONTEND_IMPLEMENTATION.md`

## License

MIT License - Feel free to use and modify for your needs!
