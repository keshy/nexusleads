# Docker & LinkedIn Intelligence Guide

## Quick Start with Docker

### 1. One-Command Setup

```bash
# Setup environment files
make setup-dev

# Edit .env files with your credentials
# backend/.env - Add your GITHUB_TOKEN, OPENAI_API_KEY, SERPER_API_KEY
# jobs/.env - Same as backend
# frontend/.env - Leave default or customize API URL

# Start everything
make up-dev
```

That's it! The application is running:
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **PostgreSQL**: localhost:5432 (database + job queue)

### 2. Docker Services

The `docker-compose.yml` includes:

#### Core Services
- **postgres** - PostgreSQL 15 database (also handles job queue)
- **backend** - FastAPI application
- **jobs** - Background job processor

#### Development Profile
- **frontend-dev** - Vite dev server with hot reload

#### Production Profile
- **frontend** - Production build with Nginx
- **nginx** - Reverse proxy with SSL support

### 3. Makefile Commands

```bash
# Development
make up-dev          # Start dev environment
make down            # Stop services
make logs            # View all logs
make logs-backend    # Backend logs only
make restart-dev     # Quick restart

# Database
make db-init         # Initialize schema
make db-backup       # Backup database
make db-reset        # Reset database (destroys data)

# Code Quality
make test            # Run tests
make lint            # Run linters
make format          # Format code

# Production
make up              # Start production
make build           # Build all images
make deploy          # Build and deploy

# Utilities
make health          # Check service health
make monitor         # Resource usage
make secrets         # Generate secure keys
```

## LinkedIn Intelligence System

### Overview

The application includes a comprehensive LinkedIn intelligence gathering system for social engineering and lead qualification. It's powered by:

1. **Multi-source Discovery** - Find profiles via GitHub, search, company domains
2. **Network Analysis** - Map professional connections and influence
3. **Career Trajectory** - Analyze progression and seniority
4. **Contact Discovery** - Find email patterns and social profiles
5. **Company Intelligence** - Gather firmographic data

### Key Features

#### 1. LinkedIn Profile Discovery

The system finds LinkedIn profiles using multiple methods:

```python
# From GitHub profile (bio, website, company)
linkedin_data = await linkedin_service.enrich_from_github_profile(github_profile)

# Direct search with multiple data points
profile = await linkedin_service.search_linkedin_profile(
    name="John Doe",
    company="Acme Corp",
    location="San Francisco",
    keywords=["CTO", "engineering"]
)
```

**What it finds:**
- LinkedIn URL and username
- Current position and company
- Profile summary
- Professional headline

#### 2. Professional Network Analysis

Analyzes the person's professional network:

```python
network = await linkedin_service.analyze_professional_network(profile_url)
```

**Returns:**
- Estimated connection count (500+, 100-500, <100)
- Common groups and communities
- Shared interests
- Network quality score (0-10)

**Use case:** Higher connection counts and quality scores indicate:
- Industry influence
- Thought leadership
- Easier to reach via mutual connections

#### 3. Career Trajectory Analysis

Understands career progression:

```python
career = await linkedin_service.analyze_career_trajectory(profile_url)
```

**Returns:**
- Seniority level (C-level, VP, Director, Senior, Mid)
- Career stability indicators
- Growth trajectory
- Leadership indicators (team management, hiring, founding)

**Use case:** Identify:
- Decision makers vs. influencers
- Fast-track executives (high growth potential)
- Stable vs. job-hopping professionals

#### 4. Contact Information Discovery

Finds contact details through public sources:

```python
contacts = await linkedin_service.find_contact_information(
    name="John Doe",
    company="Acme Corp",
    linkedin_url="https://linkedin.com/in/johndoe"
)
```

**Returns:**
- Email patterns (firstname.lastname@company.com)
- Social media profiles (Twitter, GitHub, Medium, Dev.to)
- Company domain

**Use case:** Enable multi-channel outreach:
- Email campaigns
- Social media engagement
- Content marketing targeting

#### 5. Company Intelligence

Gathers firmographic data:

```python
intel = await linkedin_service.get_company_intelligence("Acme Corp")
```

**Returns:**
- Estimated employee count
- Funding information
- Industry classification
- Technology stack

**Use case:** Qualify accounts:
- Target companies by size
- Prioritize funded startups
- Understand tech landscape

### Deep Enrichment Workflow

The `deep_enrich_profile()` method combines all capabilities:

```python
enriched = await enrichment_service.deep_enrich_profile(
    contributor_data=contributor,
    github_profile=github_data
)
```

**Returns comprehensive profile with:**
- LinkedIn data
- Network analysis
- Career trajectory
- Contact information
- Company intelligence
- Enrichment quality score (0-100%)

### Enrichment Quality Scoring

The system calculates an enrichment quality score:

| Component | Points | What It Means |
|-----------|--------|---------------|
| LinkedIn Profile Found | 30 | Basic identity verification |
| Network Analysis | 20 | Influence and reach data |
| Career Analysis | 20 | Seniority and role clarity |
| Contact Info | 15 | Reachability |
| Company Intel | 15 | Account qualification |

**Quality Tiers:**
- **90-100%**: Comprehensive intelligence, high confidence
- **70-89%**: Good data, ready for outreach
- **50-69%**: Partial data, needs manual review
- **<50%**: Limited data, low priority

### Configuration

Add to your `.env` files:

```bash
# Required for LinkedIn features
SERPER_API_KEY=your_serper_api_key

# Optional for AI classification
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4-turbo-preview
```

### API Keys

#### Serper API (Required for LinkedIn)
1. Go to https://serper.dev/
2. Sign up for free tier (2,500 searches/month)
3. Get API key from dashboard
4. Add to `.env`: `SERPER_API_KEY=xxx`

#### OpenAI API (Optional)
1. Go to https://platform.openai.com/
2. Create API key
3. Add to `.env`: `OPENAI_API_KEY=sk-xxx`

### Usage in Application

#### Via API

```bash
# Trigger enrichment for a contributor
curl -X POST http://localhost:8000/api/contributors/{id}/enrich \
  -H "Authorization: Bearer $TOKEN"
```

#### Via Job Processor

The background job processor automatically enriches contributors:

```python
# In job_processor.py
async def process_social_enrichment(self, job):
    # Fetch contributors needing enrichment
    contributors = self.get_unenriched_contributors(job.project_id)
    
    for contributor in contributors:
        # Get GitHub profile
        github_data = await github_service.get_contributor_details(...)
        
        # Deep enrich with LinkedIn intelligence
        enriched = await enrichment_service.deep_enrich_profile(
            contributor_data=contributor,
            github_profile=github_data
        )
        
        # Store in social_context table
        self.save_enrichment_data(contributor.id, enriched)
```

### Database Storage

Enriched data is stored in the `social_context` table:

```sql
CREATE TABLE social_context (
    id UUID PRIMARY KEY,
    contributor_id UUID REFERENCES contributors(id),
    linkedin_url VARCHAR(500),
    current_position VARCHAR(200),
    current_company VARCHAR(200),
    linkedin_headline TEXT,
    classification VARCHAR(50),  -- DECISION_MAKER, KEY_CONTRIBUTOR, HIGH_IMPACT
    classification_confidence NUMERIC(3,2),
    classification_reasoning TEXT,
    raw_data JSONB,  -- Full enriched data including network, career, contacts
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### Social Engineering Use Cases

#### 1. Executive Mapping

Find decision makers in target companies:

```sql
SELECT DISTINCT
    c.full_name,
    sc.current_position,
    sc.current_company,
    sc.linkedin_url,
    ls.overall_score
FROM contributors c
JOIN social_context sc ON c.id = sc.contributor_id
JOIN lead_scores ls ON c.id = ls.contributor_id
WHERE sc.classification = 'DECISION_MAKER'
    AND ls.position_score > 80
ORDER BY ls.overall_score DESC
LIMIT 50;
```

#### 2. Influencer Identification

Find thought leaders and advocates:

```sql
-- High network quality + active contribution
SELECT 
    c.full_name,
    sc.linkedin_url,
    (sc.raw_data->'network_analysis'->>'network_quality_score')::int as network_score,
    ls.influence_score
FROM contributors c
JOIN social_context sc ON c.id = sc.contributor_id
JOIN lead_scores ls ON c.id = ls.contributor_id
WHERE (sc.raw_data->'network_analysis'->>'network_quality_score')::int >= 8
    AND ls.influence_score > 70
ORDER BY network_score DESC, ls.influence_score DESC;
```

#### 3. Multi-Touch Outreach Planning

Get all contact points for top leads:

```sql
SELECT 
    c.full_name,
    c.email,
    sc.linkedin_url,
    sc.raw_data->'contact_info'->'email_patterns' as email_patterns,
    sc.raw_data->'contact_info'->'social_profiles' as social_profiles,
    ls.overall_score
FROM contributors c
JOIN social_context sc ON c.id = sc.contributor_id
JOIN lead_scores ls ON c.id = ls.contributor_id
WHERE ls.is_qualified = true
ORDER BY ls.overall_score DESC;
```

#### 4. Account-Based Marketing (ABM)

Group leads by company for coordinated campaigns:

```sql
SELECT 
    sc.current_company,
    COUNT(*) as lead_count,
    COUNT(*) FILTER (WHERE sc.classification = 'DECISION_MAKER') as decision_makers,
    COUNT(*) FILTER (WHERE sc.classification = 'KEY_CONTRIBUTOR') as key_contributors,
    AVG(ls.overall_score) as avg_score,
    (SELECT raw_data->'company_intelligence' 
     FROM social_context 
     WHERE current_company = sc.current_company 
     LIMIT 1) as company_intel
FROM social_context sc
JOIN lead_scores ls ON sc.contributor_id = ls.contributor_id
WHERE ls.is_qualified = true
GROUP BY sc.current_company
HAVING COUNT(*) >= 3  -- At least 3 leads per company
ORDER BY decision_makers DESC, avg_score DESC;
```

### Best Practices

#### 1. Rate Limiting

The LinkedIn service includes built-in retry logic and respects rate limits:
- Serper: 100 searches/hour (free tier)
- Built-in exponential backoff
- Automatic caching of results

#### 2. Data Privacy

- Only uses publicly available information
- No web scraping or ToS violations
- All data from authorized APIs
- GDPR-compliant storage

#### 3. Enrichment Strategy

**Prioritize enrichment:**
1. High-value contributors (maintainers, frequent committers)
2. Contributors with complete GitHub profiles
3. Users at target companies
4. Recent activity (last 3 months)

**Skip enrichment:**
- Obvious spam accounts
- Bots and automated users
- Very low activity (<5 commits)
- Incomplete profiles (no name, no company)

#### 4. Quality Control

Monitor enrichment quality:

```sql
-- Enrichment quality dashboard
SELECT 
    COUNT(*) as total_enriched,
    AVG((raw_data->'enrichment_quality'->>'percentage')::numeric) as avg_quality,
    COUNT(*) FILTER (
        WHERE (raw_data->'enrichment_quality'->>'percentage')::numeric >= 70
    ) as high_quality_count,
    COUNT(*) FILTER (
        WHERE raw_data->'linkedin_data'->>'linkedin_url' IS NOT NULL
    ) as linkedin_found_count
FROM social_context
WHERE created_at > NOW() - INTERVAL '30 days';
```

### Troubleshooting

#### Serper API Errors

```bash
# Check API key
curl -X POST https://google.serper.dev/search \
  -H "X-API-KEY: your_key" \
  -H "Content-Type: application/json" \
  -d '{"q":"test"}'

# Should return search results, not 401
```

#### No LinkedIn Profiles Found

- Verify contributor has a complete GitHub profile (name, company)
- Check if name is a real name vs. username
- Try manual search to verify profile exists
- Check Serper API quota (2,500/month free)

#### Low Enrichment Quality

Common causes:
- GitHub profile incomplete (no name, company)
- Common names without company context
- Privacy-conscious users (minimal public data)
- Non-Western names (search relevance issues)

**Solutions:**
- Prioritize contributors with complete profiles
- Use company/location filters in search
- Manual review for high-priority leads

## Docker Compose Profiles

### Development Profile

```bash
make up-dev
# or
docker-compose --profile dev up
```

Includes:
- All core services
- Frontend dev server with hot reload
- Volume mounts for live code updates
- Debug logging enabled

### Production Profile

```bash
make up
# or
docker-compose --profile prod up
```

Includes:
- All core services
- Production frontend build
- Nginx reverse proxy
- SSL support ready
- Optimized for performance

## Environment Variables

### Backend/Jobs

```bash
# Database
DATABASE_URL=postgresql://plg_user:plg_password@postgres:5432/plg_lead_sourcer

# Security
SECRET_KEY=your-secret-key-here

# APIs (Required)
GITHUB_TOKEN=ghp_your_github_token

# APIs (Optional for enrichment)
OPENAI_API_KEY=sk-your-openai-key
OPENAI_MODEL=gpt-4-turbo-preview
SERPER_API_KEY=your-serper-key

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# Job Processor
CHECK_INTERVAL_SECONDS=30
MAX_CONCURRENT_JOBS=3
```

### Frontend

```bash
VITE_API_URL=http://localhost:8000
```

## Deployment

### Using Docker Compose

```bash
# Build images
make build

# Deploy
make deploy

# Check health
make health
```

### Using CI/CD

The GitHub Actions workflow automatically:
1. Runs tests
2. Builds Docker images
3. Pushes to GitHub Container Registry
4. Deploys to staging
5. Deploys to production (with approval)

Configure these secrets in GitHub:
- `GITHUB_TOKEN` (auto-provided)
- `STAGING_SSH_KEY`, `STAGING_HOST`, `STAGING_USER`
- `PRODUCTION_SSH_KEY`, `PRODUCTION_HOST`, `PRODUCTION_USER`
- `SLACK_WEBHOOK` (optional for notifications)

### Manual Deployment

```bash
# On server
git clone repo
cd plg-lead-sourcer

# Setup environment
make setup-dev
# Edit .env files

# Start services
make up

# Initialize database
make db-init
```

## Monitoring & Maintenance

```bash
# View logs
make logs

# Check resource usage
make monitor

# Backup database
make db-backup

# Health check
make health

# Restart services
make restart
```

## Scaling

### Horizontal Scaling

Scale individual services:

```bash
# Multiple job processors
docker-compose up -d --scale jobs=3

# Multiple backend instances (with load balancer)
docker-compose up -d --scale backend=3
```

### Vertical Scaling

Edit `docker-compose.yml`:

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

## Security Considerations

1. **Change default credentials** in `.env` files
2. **Use strong SECRET_KEY**: `make secrets`
3. **Enable SSL** in nginx.conf (production profile)
4. **Restrict database access** to internal network
5. **Rotate API keys** regularly
6. **Monitor API usage** to detect abuse
7. **Review logs** for suspicious activity

## Cost Optimization

### API Usage

- **Serper**: Free tier 2,500 searches/month
  - ~83 searches/day
  - Optimize with caching
  - Prioritize high-value leads

- **OpenAI**: Pay-per-use
  - GPT-4 Turbo: ~$0.01-0.03 per classification
  - Optional: Use rule-based fallback
  - Batch processing for efficiency

### Infrastructure

- **PostgreSQL**: 500MB-1GB for 10K contributors (includes job queue)
- **Backend**: 256MB-512MB per instance
- **Jobs**: 256MB-512MB per instance
- **Frontend**: Static files (50-100MB)

**Estimated cloud costs:**
- Development: $20-40/month (smallest instances)
- Production: $100-200/month (HA setup)
- Enterprise: $500+/month (autoscaling, multi-region)
