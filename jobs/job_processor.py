"""Background job processor."""
import logging
import time
import asyncio
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session

from database import SessionLocal
from config import config
from services.github_service import GitHubService
from services.enrichment_service import EnrichmentService
from services.scoring_service import ScoringService
from models import (
    SourcingJob, JobProgress, Repository, Contributor,
    ContributorStats, SocialContext, LeadScore,
    RepositoryContributor, OrgMember
)
import billing_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class JobCancelledError(Exception):
    """Raised when a job is cancelled while processing."""


class JobProcessor:
    """Processes sourcing jobs from the database."""
    
    def __init__(self):
        """Initialize job processor."""
        self.scoring_service = ScoringService()
        self.running_jobs = set()

    def _init_services(self, db: Session, user_id=None):
        """Re-initialize services reading latest settings from DB."""
        self.github_service = GitHubService(db=db, user_id=user_id)
        self.enrichment_service = EnrichmentService(db=db, user_id=user_id)
    
    def claim_pending_jobs(self, db: Session) -> List[SourcingJob]:
        """Claim pending jobs for processing with row-level locking."""
        available = max(0, config.MAX_CONCURRENT_JOBS - len(self.running_jobs))
        if available == 0:
            return []

        pending_jobs = db.query(SourcingJob).filter(
            SourcingJob.status == 'pending'
        ).order_by(SourcingJob.created_at).with_for_update(skip_locked=True).limit(available).all()

        if not pending_jobs:
            return []

        now = datetime.utcnow()
        for job in pending_jobs:
            job.status = 'running'
            if not job.started_at:
                job.started_at = now
        db.commit()

        return pending_jobs
    
    def create_progress_step(
        self,
        db: Session,
        job_id: str,
        step_number: int,
        step_name: str,
        status: str = 'pending'
    ) -> JobProgress:
        """Create a progress step."""
        progress = JobProgress(
            job_id=job_id,
            step_number=step_number,
            step_name=step_name,
            status=status
        )
        db.add(progress)
        db.commit()
        db.refresh(progress)
        return progress
    
    def update_progress_step(
        self,
        db: Session,
        progress: JobProgress,
        status: str,
        message: str = None,
        details: dict = None
    ):
        """Update a progress step."""
        progress.status = status
        if message:
            progress.message = message
            if status == 'failed':
                progress.error_message = message
        if details:
            progress.details = details
        
        if status == 'running':
            progress.started_at = datetime.utcnow()
        elif status in ['completed', 'failed']:
            progress.completed_at = datetime.utcnow()
        
        db.commit()
    
    def update_job_progress(
        self,
        db: Session,
        job: SourcingJob,
        current_step: int,
        total_steps: int
    ):
        """Update job progress percentage."""
        job.current_step = current_step
        job.total_steps = total_steps
        job.progress_percentage = (current_step / total_steps * 100) if total_steps > 0 else 0
        db.commit()

    def ensure_job_active(self, db: Session, job_id: str):
        """Ensure the job has not been cancelled."""
        status = db.query(SourcingJob.status).filter(SourcingJob.id == job_id).scalar()
        if status == 'cancelled':
            raise JobCancelledError()

    def mark_job_cancelled(self, db: Session, job_id: str):
        """Mark any running/pending steps as failed due to cancellation."""
        steps = db.query(JobProgress).filter(
            JobProgress.job_id == job_id,
            JobProgress.status.in_(['pending', 'running'])
        ).all()
        now = datetime.utcnow()
        for step in steps:
            step.status = 'failed'
            step.message = "Cancelled by user"
            step.error_message = "Cancelled by user"
            step.completed_at = now
        db.commit()

    def build_stats_payload(self, stats_data: dict) -> dict:
        """Normalize stats data for lead scoring."""
        return {
            "total_commits": stats_data.get("total_commits", 0),
            "commits_last_3_months": stats_data.get("commits_last_3_months", 0),
            "pull_requests": stats_data.get("pull_requests", 0),
            "issues_opened": stats_data.get("issues_opened", 0),
            "code_reviews": stats_data.get("code_reviews", 0),
            "is_maintainer": stats_data.get("is_maintainer", False)
        }

    def aggregate_stats(self, stats_rows: List[ContributorStats]) -> dict:
        """Aggregate contributor stats across repositories."""
        if not stats_rows:
            return {}

        aggregated = {
            "total_commits": 0,
            "commits_last_3_months": 0,
            "pull_requests": 0,
            "issues_opened": 0,
            "code_reviews": 0,
            "is_maintainer": False
        }

        for stats in stats_rows:
            aggregated["total_commits"] += stats.total_commits or 0
            aggregated["commits_last_3_months"] += stats.commits_last_3_months or 0
            aggregated["pull_requests"] += stats.pull_requests or 0
            aggregated["issues_opened"] += stats.issues_opened or 0
            aggregated["code_reviews"] += stats.code_reviews or 0
            aggregated["is_maintainer"] = aggregated["is_maintainer"] or bool(stats.is_maintainer)

        return aggregated

    def upsert_lead_score(
        self,
        db: Session,
        project_id: str,
        contributor: Contributor,
        stats_data: dict
    ):
        """Create or update lead scores for a contributor in a project."""
        social_context = db.query(SocialContext).filter(
            SocialContext.contributor_id == contributor.id
        ).first()

        social_context_data = {
            "classification": social_context.classification if social_context else None,
            "position_level": social_context.position_level if social_context else None
        }

        contributor_data = {
            "followers": contributor.followers or 0,
            "public_repos": contributor.public_repos or 0,
            "company": contributor.company
        }

        score_data = self.scoring_service.calculate_overall_score(
            contributor_data,
            stats_data,
            social_context_data
        )

        lead_score = db.query(LeadScore).filter(
            LeadScore.project_id == project_id,
            LeadScore.contributor_id == contributor.id
        ).first()

        if not lead_score:
            lead_score = LeadScore(
                project_id=project_id,
                contributor_id=contributor.id
            )
            db.add(lead_score)

        lead_score.overall_score = score_data["overall_score"]
        lead_score.activity_score = score_data["activity_score"]
        lead_score.influence_score = score_data["influence_score"]
        lead_score.position_score = score_data["position_score"]
        lead_score.engagement_score = score_data["engagement_score"]
        lead_score.is_qualified_lead = score_data["is_qualified_lead"]
        lead_score.priority = score_data["priority"]
        lead_score.calculated_at = datetime.utcnow()
    
    async def process_repository_sourcing(self, db: Session, job: SourcingJob):
        """Process repository sourcing job."""
        logger.info(f"Processing repository sourcing job {job.id}")
        
        try:
            self.ensure_job_active(db, job.id)
            # Get repository
            repository = db.query(Repository).filter(
                Repository.id == job.repository_id
            ).first()
            
            if not repository:
                raise Exception("Repository not found")
            
            # Initialize job
            if job.status != 'running':
                job.status = 'running'
            if not job.started_at:
                job.started_at = datetime.utcnow()
            if not job.total_steps:
                job.total_steps = 4
            db.commit()
            
            # Step 1: Fetch repository metadata
            self.ensure_job_active(db, job.id)
            step1 = self.create_progress_step(db, job.id, 1, "Fetching repository metadata")
            self.update_progress_step(db, step1, 'running')
            
            try:
                repo_data = await asyncio.to_thread(
                    self.github_service.get_repository,
                    repository.owner,
                    repository.repo_name
                )
                
                # Update repository
                repository.description = repo_data['description']
                repository.stars = repo_data['stars']
                repository.forks = repo_data['forks']
                repository.open_issues = repo_data['open_issues']
                repository.language = repo_data['language']
                repository.topics = repo_data['topics']
                repository.last_sourced_at = datetime.utcnow()
                db.commit()
                
                self.update_progress_step(db, step1, 'completed', f"Fetched metadata for {repository.full_name}")
            except Exception as e:
                self.update_progress_step(db, step1, 'failed', str(e))
                raise
            
            self.update_job_progress(db, job, 1, 4)
            
            # Step 2: Fetch contributors
            self.ensure_job_active(db, job.id)
            step2 = self.create_progress_step(db, job.id, 2, "Fetching contributors")
            self.update_progress_step(db, step2, 'running')
            
            try:
                contributors_data = await asyncio.to_thread(
                    self.github_service.get_contributors,
                    repository.owner,
                    repository.repo_name,
                    100
                )

                bulk_stats = {}
                if config.USE_BULK_CONTRIBUTOR_STATS:
                    bulk_stats = await asyncio.to_thread(
                        self.github_service.get_contributor_stats_bulk,
                        repository.owner,
                        repository.repo_name
                    )
                
                self.update_progress_step(
                    db, step2, 'completed',
                    f"Found {len(contributors_data)} contributors"
                )
            except Exception as e:
                self.update_progress_step(db, step2, 'failed', str(e))
                raise
            
            self.update_job_progress(db, job, 2, 4)
            
            # Step 3: Process contributors and stats
            self.ensure_job_active(db, job.id)
            step3 = self.create_progress_step(db, job.id, 3, "Processing contributor statistics")
            self.update_progress_step(db, step3, 'running')
            
            try:
                processed_count = 0
                batch_size = 25
                for contrib_data in contributors_data:
                    if processed_count % 10 == 0:
                        self.ensure_job_active(db, job.id)
                    # Create or update contributor
                    contributor = db.query(Contributor).filter(
                        Contributor.github_id == contrib_data['github_id']
                    ).first()
                    
                    if not contributor:
                        contributor = Contributor(
                            github_id=contrib_data['github_id'],
                            username=contrib_data['username'],
                            full_name=contrib_data['full_name'],
                            email=contrib_data['email'],
                            company=contrib_data['company'],
                            location=contrib_data['location'],
                            bio=contrib_data['bio'],
                            blog=contrib_data['blog'],
                            twitter_username=contrib_data['twitter_username'],
                            avatar_url=contrib_data['avatar_url'],
                            github_url=contrib_data['github_url'],
                            public_repos=contrib_data['public_repos'],
                            followers=contrib_data['followers'],
                            following=contrib_data['following']
                        )
                        db.add(contributor)
                        db.flush()
                    else:
                        # Update existing contributor
                        contributor.full_name = contrib_data['full_name'] or contributor.full_name
                        contributor.email = contrib_data['email'] or contributor.email
                        contributor.company = contrib_data['company'] or contributor.company
                        contributor.location = contrib_data['location'] or contributor.location
                        contributor.bio = contrib_data['bio'] or contributor.bio
                        contributor.followers = contrib_data['followers']
                        contributor.public_repos = contrib_data['public_repos']
                    
                    # Create repository-contributor relationship
                    repo_contrib = db.query(RepositoryContributor).filter(
                        RepositoryContributor.repository_id == repository.id,
                        RepositoryContributor.contributor_id == contributor.id
                    ).first()
                    
                    if not repo_contrib:
                        repo_contrib = RepositoryContributor(
                            repository_id=repository.id,
                            contributor_id=contributor.id
                        )
                        db.add(repo_contrib)
                    
                    # Get detailed stats
                    if config.USE_BULK_CONTRIBUTOR_STATS:
                        stats_data = self.github_service.build_stats_from_bulk(
                            contrib_data['username'],
                            contrib_data.get('contributions'),
                            bulk_stats
                        )
                    else:
                        stats_data = await asyncio.to_thread(
                            self.github_service.get_contributor_stats,
                            repository.owner,
                            repository.repo_name,
                            contrib_data['username']
                        )

                    if config.FETCH_PR_ISSUE_COUNTS:
                        prs, issues = await asyncio.to_thread(
                            self.github_service.get_pr_issue_counts,
                            repository.owner,
                            repository.repo_name,
                            contrib_data['username']
                        )
                        stats_data["pull_requests"] = prs
                        stats_data["issues_opened"] = issues
                    
                    # Create or update contributor stats
                    stats = db.query(ContributorStats).filter(
                        ContributorStats.repository_id == repository.id,
                        ContributorStats.contributor_id == contributor.id
                    ).first()
                    
                    if not stats:
                        stats = ContributorStats(
                            repository_id=repository.id,
                            contributor_id=contributor.id
                        )
                        db.add(stats)
                    
                    stats.total_commits = stats_data['total_commits']
                    stats.commits_last_3_months = stats_data['commits_last_3_months']
                    stats.commits_last_6_months = stats_data['commits_last_6_months']
                    stats.commits_last_year = stats_data['commits_last_year']
                    stats.first_commit_date = stats_data['first_commit_date']
                    stats.last_commit_date = stats_data['last_commit_date']
                    stats.pull_requests = stats_data['pull_requests']
                    stats.issues_opened = stats_data['issues_opened']
                    stats.is_maintainer = stats_data['is_maintainer']
                    stats.calculated_at = datetime.utcnow()

                    stats_payload = self.build_stats_payload(stats_data)
                    self.upsert_lead_score(db, repository.project_id, contributor, stats_payload)

                    processed_count += 1
                    
                    # Update progress
                    if processed_count % 10 == 0:
                        self.update_progress_step(
                            db, step3, 'running',
                            f"Processed {processed_count}/{len(contributors_data)} contributors"
                        )
                    if processed_count % batch_size == 0:
                        db.commit()
                
                db.commit()
                self.update_progress_step(
                    db, step3, 'completed',
                    f"Processed {processed_count} contributors"
                )
            except Exception as e:
                self.update_progress_step(db, step3, 'failed', str(e))
                raise
            
            self.update_job_progress(db, job, 3, 4)
            
            # Step 4: Auto-enrich contributors
            self.ensure_job_active(db, job.id)
            step4 = self.create_progress_step(db, job.id, 4, "Queuing social enrichment for contributors")
            self.update_progress_step(db, step4, 'running')

            try:
                # Find all contributors linked to this repository that don't have social context yet
                enriched_ids = {sc.contributor_id for sc in db.query(SocialContext.contributor_id).all()}
                repo_contributors = db.query(RepositoryContributor).filter(
                    RepositoryContributor.repository_id == repository.id
                ).all()

                enrich_count = 0
                for rc in repo_contributors:
                    if rc.contributor_id in enriched_ids:
                        continue
                    enrich_job = SourcingJob(
                        project_id=repository.project_id,
                        repository_id=repository.id,
                        job_type='social_enrichment',
                        status='pending',
                        job_metadata={'contributor_id': str(rc.contributor_id)},
                        created_by=job.created_by
                    )
                    db.add(enrich_job)
                    enrich_count += 1

                db.commit()
                self.update_progress_step(
                    db, step4, 'completed',
                    f"Queued enrichment for {enrich_count} contributors ({len(repo_contributors) - enrich_count} already enriched)"
                )
                logger.info(f"Queued {enrich_count} enrichment jobs for repo {repository.full_name}")
            except Exception as e:
                self.update_progress_step(db, step4, 'failed', str(e))
                logger.warning(f"Failed to queue enrichment jobs: {e}")

            self.update_job_progress(db, job, 4, 4)

            # Finalize
            job.status = 'completed'
            job.completed_at = datetime.utcnow()
            job.progress_percentage = 100
            db.commit()
            
            logger.info(f"Completed repository sourcing job {job.id}")

            # Auto-export to Clay if configured
            self._check_auto_export(db, job)
        except JobCancelledError:
            logger.info(f"Job {job.id} cancelled")
            self.mark_job_cancelled(db, job.id)
            return
        except Exception as e:
            logger.error(f"Error processing job {job.id}: {e}")
            job.status = 'failed'
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            db.commit()
    
    async def process_social_enrichment(self, db: Session, job: SourcingJob):
        """Process social enrichment job."""
        logger.info(f"Processing social enrichment job {job.id}")
        
        try:
            self.ensure_job_active(db, job.id)
            contributor_id = job.job_metadata.get('contributor_id') if job.job_metadata else None
            
            if not contributor_id:
                raise Exception("No contributor ID specified")
            
            contributor = db.query(Contributor).filter(
                Contributor.id == contributor_id
            ).first()
            
            if not contributor:
                raise Exception("Contributor not found")
            
            # ── Metering: check credits before enrichment ──
            org_id = billing_service.get_user_org_id(db, job.created_by)
            if org_id:
                ok, remaining = billing_service.check_and_deduct(
                    db, org_id, job.id, contributor.id
                )
                if not ok:
                    logger.warning(f"Job {job.id} out of credits (org {org_id}, balance {remaining})")
                    job.status = 'out_of_credits'
                    job.error_message = 'Insufficient credits. Add credits to continue.'
                    job.completed_at = datetime.utcnow()
                    db.commit()
                    return
            
            # Initialize job
            if job.status != 'running':
                job.status = 'running'
            if not job.started_at:
                job.started_at = datetime.utcnow()
            if not job.total_steps:
                job.total_steps = 3
            db.commit()
            
            # Step 1: Search for person
            self.ensure_job_active(db, job.id)
            step1 = self.create_progress_step(db, job.id, 1, "Searching for social profiles")
            self.update_progress_step(db, step1, 'running')
            
            try:
                search_results = await self.enrichment_service.search_person(
                    contributor.full_name or contributor.username,
                    contributor.company,
                    contributor.username
                )
                
                self.update_progress_step(db, step1, 'completed', "Search completed")
            except Exception as e:
                self.update_progress_step(db, step1, 'failed', str(e))
                search_results = {}
            
            self.update_job_progress(db, job, 1, 3)
            
            # Step 2: Extract LinkedIn info
            self.ensure_job_active(db, job.id)
            step2 = self.create_progress_step(db, job.id, 2, "Extracting professional information")
            self.update_progress_step(db, step2, 'running')
            
            try:
                linkedin_info = self.enrichment_service.extract_linkedin_info(search_results)
                position_level = self.enrichment_service.classify_position_level(
                    linkedin_info.get('current_position')
                )
                
                # Get contributor stats for classification
                stats = db.query(ContributorStats).filter(
                    ContributorStats.contributor_id == contributor.id
                ).first()
                
                stats_dict = {
                    'total_commits': stats.total_commits if stats else 0,
                    'commits_last_3_months': stats.commits_last_3_months if stats else 0,
                    'pull_requests': stats.pull_requests if stats else 0,
                    'is_maintainer': stats.is_maintainer if stats else False
                } if stats else {}
                
                # Classify contributor
                classification = await self.enrichment_service.classify_contributor(
                    {
                        'full_name': contributor.full_name,
                        'username': contributor.username,
                        'company': contributor.company,
                        'bio': contributor.bio,
                        'followers': contributor.followers
                    },
                    stats_dict,
                    linkedin_info
                )
                
                # Create or update social context
                social_context = db.query(SocialContext).filter(
                    SocialContext.contributor_id == contributor.id
                ).first()
                
                if not social_context:
                    social_context = SocialContext(contributor_id=contributor.id)
                    db.add(social_context)
                
                social_context.linkedin_url = linkedin_info.get('linkedin_url')
                social_context.linkedin_profile_photo_url = linkedin_info.get('linkedin_profile_photo_url')
                social_context.linkedin_headline = linkedin_info.get('linkedin_headline')
                social_context.current_company = classification.get('organization') or linkedin_info.get('current_company')
                social_context.current_position = linkedin_info.get('current_position')
                social_context.position_level = position_level
                social_context.industry = classification.get('industry')
                social_context.search_results = search_results
                social_context.classification = classification['classification']
                social_context.classification_confidence = classification['classification_confidence']
                social_context.classification_reasoning = classification['classification_reasoning']
                social_context.last_enriched_at = datetime.utcnow()

                project_ids = db.query(Repository.project_id).join(
                    RepositoryContributor, RepositoryContributor.repository_id == Repository.id
                ).filter(
                    RepositoryContributor.contributor_id == contributor.id
                ).distinct().all()

                for (project_id,) in project_ids:
                    stats_rows = db.query(ContributorStats).join(Repository).filter(
                        Repository.project_id == project_id,
                        ContributorStats.contributor_id == contributor.id
                    ).all()
                    stats_payload = self.aggregate_stats(stats_rows)
                    self.upsert_lead_score(db, project_id, contributor, stats_payload)

                db.commit()

                self.update_progress_step(db, step2, 'completed', f"Classified as {classification['classification']}")
            except Exception as e:
                self.update_progress_step(db, step2, 'failed', str(e))
                raise
            
            self.update_job_progress(db, job, 2, 3)
            
            # Step 3: Complete
            self.ensure_job_active(db, job.id)
            step3 = self.create_progress_step(db, job.id, 3, "Finalizing")
            self.update_progress_step(db, step3, 'running')
            
            job.status = 'completed'
            job.completed_at = datetime.utcnow()
            job.progress_percentage = 100
            db.commit()
            
            self.update_progress_step(db, step3, 'completed', "Enrichment completed")
            
            logger.info(f"Completed social enrichment job {job.id}")
        except JobCancelledError:
            logger.info(f"Job {job.id} cancelled")
            self.mark_job_cancelled(db, job.id)
            return
        except Exception as e:
            logger.error(f"Error processing job {job.id}: {e}")
            job.status = 'failed'
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            db.commit()
    
    async def process_stargazer_analysis(self, db: Session, job: SourcingJob):
        """Process stargazer analysis job — fetch stargazers, create contributors, enrich."""
        logger.info(f"Processing stargazer analysis job {job.id}")

        try:
            self.ensure_job_active(db, job.id)
            repository = db.query(Repository).filter(
                Repository.id == job.repository_id
            ).first()

            if not repository:
                raise Exception("Repository not found")

            if job.status != 'running':
                job.status = 'running'
            if not job.started_at:
                job.started_at = datetime.utcnow()
            if not job.total_steps:
                job.total_steps = 3
            db.commit()

            # Step 1: Fetch stargazers
            self.ensure_job_active(db, job.id)
            step1 = self.create_progress_step(db, job.id, 1, "Fetching stargazers")
            self.update_progress_step(db, step1, 'running')

            try:
                stargazers_data = await asyncio.to_thread(
                    self.github_service.get_stargazers,
                    repository.owner,
                    repository.repo_name,
                    200
                )
                self.update_progress_step(
                    db, step1, 'completed',
                    f"Found {len(stargazers_data)} stargazers"
                )
            except Exception as e:
                self.update_progress_step(db, step1, 'failed', str(e))
                raise

            self.update_job_progress(db, job, 1, 3)

            # Step 2: Process stargazers as contributors
            self.ensure_job_active(db, job.id)
            step2 = self.create_progress_step(db, job.id, 2, "Processing stargazer profiles")
            self.update_progress_step(db, step2, 'running')

            try:
                processed_count = 0
                for sg_data in stargazers_data:
                    if processed_count % 10 == 0:
                        self.ensure_job_active(db, job.id)

                    contributor = db.query(Contributor).filter(
                        Contributor.github_id == sg_data['github_id']
                    ).first()

                    if not contributor:
                        contributor = Contributor(
                            github_id=sg_data['github_id'],
                            username=sg_data['username'],
                            full_name=sg_data['full_name'],
                            email=sg_data['email'],
                            company=sg_data['company'],
                            location=sg_data['location'],
                            bio=sg_data['bio'],
                            blog=sg_data['blog'],
                            twitter_username=sg_data['twitter_username'],
                            avatar_url=sg_data['avatar_url'],
                            github_url=sg_data['github_url'],
                            public_repos=sg_data['public_repos'],
                            followers=sg_data['followers'],
                            following=sg_data['following']
                        )
                        db.add(contributor)
                        db.flush()
                    else:
                        contributor.full_name = sg_data['full_name'] or contributor.full_name
                        contributor.email = sg_data['email'] or contributor.email
                        contributor.company = sg_data['company'] or contributor.company
                        contributor.bio = sg_data['bio'] or contributor.bio
                        contributor.followers = sg_data['followers']
                        contributor.public_repos = sg_data['public_repos']

                    # Create repo-contributor relationship
                    repo_contrib = db.query(RepositoryContributor).filter(
                        RepositoryContributor.repository_id == repository.id,
                        RepositoryContributor.contributor_id == contributor.id
                    ).first()

                    if not repo_contrib:
                        repo_contrib = RepositoryContributor(
                            repository_id=repository.id,
                            contributor_id=contributor.id
                        )
                        db.add(repo_contrib)

                    # Create contributor_stats with source='stargazer'
                    stats = db.query(ContributorStats).filter(
                        ContributorStats.repository_id == repository.id,
                        ContributorStats.contributor_id == contributor.id
                    ).first()

                    if not stats:
                        stats = ContributorStats(
                            repository_id=repository.id,
                            contributor_id=contributor.id,
                            source='stargazer'
                        )
                        db.add(stats)
                    elif stats.source != 'commit':
                        stats.source = 'stargazer'

                    stats.calculated_at = datetime.utcnow()

                    # Score stargazers — they have no commit activity, so score is influence-heavy
                    stats_payload = {
                        "total_commits": 0,
                        "commits_last_3_months": 0,
                        "pull_requests": 0,
                        "issues_opened": 0,
                        "code_reviews": 0,
                        "is_maintainer": False
                    }
                    self.upsert_lead_score(db, repository.project_id, contributor, stats_payload)

                    processed_count += 1
                    if processed_count % 25 == 0:
                        self.update_progress_step(
                            db, step2, 'running',
                            f"Processed {processed_count}/{len(stargazers_data)} stargazers"
                        )
                        db.commit()

                db.commit()
                self.update_progress_step(
                    db, step2, 'completed',
                    f"Processed {processed_count} stargazers"
                )
            except Exception as e:
                self.update_progress_step(db, step2, 'failed', str(e))
                raise

            self.update_job_progress(db, job, 2, 3)

            # Step 3: Queue enrichment for stargazers
            self.ensure_job_active(db, job.id)
            step3 = self.create_progress_step(db, job.id, 3, "Queuing social enrichment")
            self.update_progress_step(db, step3, 'running')

            try:
                enriched_ids = {sc.contributor_id for sc in db.query(SocialContext.contributor_id).all()}
                repo_contributors = db.query(RepositoryContributor).filter(
                    RepositoryContributor.repository_id == repository.id
                ).all()

                enrich_count = 0
                for rc in repo_contributors:
                    if rc.contributor_id in enriched_ids:
                        continue
                    enrich_job = SourcingJob(
                        project_id=repository.project_id,
                        repository_id=repository.id,
                        job_type='social_enrichment',
                        status='pending',
                        job_metadata={'contributor_id': str(rc.contributor_id)},
                        created_by=job.created_by
                    )
                    db.add(enrich_job)
                    enrich_count += 1

                db.commit()
                self.update_progress_step(
                    db, step3, 'completed',
                    f"Queued enrichment for {enrich_count} stargazers"
                )
                logger.info(f"Queued {enrich_count} enrichment jobs for stargazers of {repository.full_name}")
            except Exception as e:
                self.update_progress_step(db, step3, 'failed', str(e))
                logger.warning(f"Failed to queue enrichment jobs: {e}")

            self.update_job_progress(db, job, 3, 3)

            job.status = 'completed'
            job.completed_at = datetime.utcnow()
            job.progress_percentage = 100
            db.commit()

            logger.info(f"Completed stargazer analysis job {job.id}")

            # Auto-export to Clay if configured
            self._check_auto_export(db, job)
        except JobCancelledError:
            logger.info(f"Job {job.id} cancelled")
            self.mark_job_cancelled(db, job.id)
            return
        except Exception as e:
            logger.error(f"Error processing stargazer job {job.id}: {e}")
            job.status = 'failed'
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            db.commit()

    def _check_auto_export(self, db: Session, job: SourcingJob):
        """After a sourcing/stargazer job completes, check if auto-export to Clay is enabled
        and queue a clay_push job for new leads that haven't been pushed yet."""
        from models import ClayPushLog, OrgMember
        from settings_service import get_setting
        from decimal import Decimal

        try:
            project = db.query(Project).filter(Project.id == job.project_id).first()
            if not project or not project.auto_export_clay_enabled:
                return

            # Resolve org
            org_id = None
            if job.created_by:
                member = db.query(OrgMember).filter(OrgMember.user_id == job.created_by).first()
                if member:
                    org_id = member.org_id

            # Check Clay is configured
            webhook_url = get_setting(db, 'CLAY_WEBHOOK_URL', org_id=org_id, user_id=job.created_by)
            if not webhook_url:
                logger.info(f"Auto-export skipped for project {project.name}: Clay webhook not configured")
                return

            # Get all contributor IDs in this project
            project_contributor_ids = db.query(RepositoryContributor.contributor_id).join(
                Repository, Repository.id == RepositoryContributor.repository_id
            ).filter(Repository.project_id == project.id).distinct().all()
            all_ids = {str(row[0]) for row in project_contributor_ids}

            if not all_ids:
                return

            # Exclude already-pushed contributors
            already_pushed = set()
            if org_id:
                pushed_rows = db.query(ClayPushLog.contributor_id).filter(
                    ClayPushLog.org_id == org_id,
                    ClayPushLog.project_id == project.id,
                    ClayPushLog.status == 'success',
                ).all()
                already_pushed = {str(row[0]) for row in pushed_rows}

            new_ids = all_ids - already_pushed
            if not new_ids:
                logger.info(f"Auto-export: no new leads for project {project.name}")
                return

            # Apply filters
            if project.auto_export_clay_min_score or project.auto_export_clay_classifications:
                filtered_ids = set()
                for cid in new_ids:
                    score = db.query(LeadScore).filter(
                        LeadScore.project_id == project.id,
                        LeadScore.contributor_id == cid,
                    ).first()
                    if not score:
                        continue
                    if project.auto_export_clay_min_score and (score.overall_score or 0) < Decimal(str(project.auto_export_clay_min_score)):
                        continue
                    if project.auto_export_clay_classifications:
                        social = db.query(SocialContext.classification).filter(
                            SocialContext.contributor_id == cid
                        ).first()
                        if not social or social.classification not in project.auto_export_clay_classifications:
                            continue
                    filtered_ids.add(cid)
                new_ids = filtered_ids

            if not new_ids:
                logger.info(f"Auto-export: no leads pass filters for project {project.name}")
                return

            # Queue clay_push job
            auto_job = SourcingJob(
                project_id=project.id,
                job_type='clay_push',
                status='pending',
                job_metadata={
                    'lead_ids': list(new_ids),
                    'project_id': str(project.id),
                    'org_id': str(org_id) if org_id else None,
                    'clay_webhook_url': webhook_url,
                    'push_mode': 'auto',
                },
                created_by=job.created_by,
            )
            db.add(auto_job)
            db.commit()
            logger.info(f"Auto-export: queued clay_push for {len(new_ids)} leads in project {project.name}")

        except Exception as e:
            logger.warning(f"Auto-export check failed for job {job.id}: {e}")

    async def process_clay_push(self, db: Session, job: SourcingJob):
        """Process clay_push job — push leads to Clay via webhook."""
        from services.clay_service import build_lead_payload, push_lead_to_clay
        from models import ClayPushLog, OrgMember
        from settings_service import get_setting

        logger.info(f"Processing clay_push job {job.id}")

        try:
            self.ensure_job_active(db, job.id)

            metadata = job.job_metadata or {}
            lead_ids = metadata.get('lead_ids', [])
            project_id = metadata.get('project_id')

            if not lead_ids:
                raise Exception("No lead IDs specified")
            if not project_id:
                raise Exception("No project ID specified")

            # Resolve org
            org_id = None
            if job.created_by:
                member = db.query(OrgMember).filter(OrgMember.user_id == job.created_by).first()
                if member:
                    org_id = member.org_id

            # Get Clay webhook URL
            webhook_url = get_setting(db, 'CLAY_WEBHOOK_URL', org_id=org_id, user_id=job.created_by)
            if not webhook_url:
                raise Exception("Clay webhook URL not configured")

            rate_limit_ms = int(get_setting(db, 'CLAY_RATE_LIMIT_MS', default='200', org_id=org_id, user_id=job.created_by))

            project = db.query(Project).filter(Project.id == project_id).first()
            if not project:
                raise Exception("Project not found")

            # Initialize job
            if job.status != 'running':
                job.status = 'running'
            if not job.started_at:
                job.started_at = datetime.utcnow()
            job.total_steps = 2
            db.commit()

            # Step 1: Prepare leads
            self.ensure_job_active(db, job.id)
            step1 = self.create_progress_step(db, job.id, 1, "Preparing leads")
            self.update_progress_step(db, step1, 'running')

            contributors = db.query(Contributor).filter(
                Contributor.id.in_(lead_ids)
            ).all()

            if not contributors:
                self.update_progress_step(db, step1, 'failed', "No valid leads found")
                raise Exception("No valid leads found for the given IDs")

            self.update_progress_step(db, step1, 'completed', f"Found {len(contributors)} leads to push")
            self.update_job_progress(db, job, 1, 2)

            # Step 2: Push to Clay
            self.ensure_job_active(db, job.id)
            step2 = self.create_progress_step(db, job.id, 2, "Pushing leads to Clay")
            self.update_progress_step(db, step2, 'running')

            success_count = 0
            fail_count = 0
            skip_count = 0

            for i, contributor in enumerate(contributors):
                if i % 5 == 0:
                    self.ensure_job_active(db, job.id)

                # Build payload
                payload = build_lead_payload(db, contributor, project)

                # Push
                ok, status_code, error = await asyncio.to_thread(
                    push_lead_to_clay, webhook_url, payload, rate_limit_ms
                )

                # Log the push
                log_entry = ClayPushLog(
                    org_id=org_id,
                    job_id=job.id,
                    contributor_id=contributor.id,
                    project_id=project_id,
                    status='success' if ok else 'failed',
                    error_message=error,
                    clay_response_status=status_code,
                )
                db.add(log_entry)

                if ok:
                    success_count += 1
                else:
                    fail_count += 1
                    logger.warning(f"Clay push failed for contributor {contributor.username}: {error}")

                # Update progress
                if (i + 1) % 5 == 0 or i == len(contributors) - 1:
                    self.update_progress_step(
                        db, step2, 'running',
                        f"Pushed {i + 1}/{len(contributors)} leads ({success_count} ok, {fail_count} failed)"
                    )
                    db.commit()

                # Rate limit
                if rate_limit_ms > 0 and i < len(contributors) - 1:
                    await asyncio.sleep(rate_limit_ms / 1000.0)

            db.commit()

            summary = f"Pushed {success_count} leads to Clay"
            if fail_count:
                summary += f" ({fail_count} failed)"
            if skip_count:
                summary += f" ({skip_count} skipped)"

            self.update_progress_step(db, step2, 'completed', summary)
            self.update_job_progress(db, job, 2, 2)

            job.status = 'completed'
            job.completed_at = datetime.utcnow()
            job.progress_percentage = 100
            db.commit()

            logger.info(f"Completed clay_push job {job.id}: {summary}")

        except JobCancelledError:
            logger.info(f"Job {job.id} cancelled")
            self.mark_job_cancelled(db, job.id)
            return
        except Exception as e:
            logger.error(f"Error processing clay_push job {job.id}: {e}")
            job.status = 'failed'
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            db.commit()

    def recover_orphaned_jobs(self, db: Session):
        """Reset any 'running' jobs back to 'pending' on startup (handles container restarts).
        Note: out_of_credits jobs are NOT recovered — they wait for credits to be added."""
        orphaned = db.query(SourcingJob).filter(SourcingJob.status == 'running').all()
        if orphaned:
            logger.info(f"Recovering {len(orphaned)} orphaned running jobs")
            for job in orphaned:
                job.status = 'pending'
                job.started_at = None
                job.progress_percentage = 0
                job.current_step = 0
                # Clean up old progress steps
                db.query(JobProgress).filter(JobProgress.job_id == job.id).delete()
            db.commit()

    async def process_job(self, job: SourcingJob):
        """Process a single job."""
        db = SessionLocal()
        try:
            self.running_jobs.add(str(job.id))

            # Re-read settings from DB so UI changes take effect
            # Pass the job creator's user_id so org-specific API keys are resolved
            self._init_services(db, user_id=job.created_by)

            db_job = db.query(SourcingJob).filter(SourcingJob.id == job.id).first()
            if not db_job:
                logger.warning(f"Job {job.id} not found, skipping")
                return
            if db_job.status == 'cancelled':
                logger.info(f"Job {job.id} already cancelled, skipping")
                return

            if db_job.job_type == 'repository_sourcing':
                await self.process_repository_sourcing(db, db_job)
            elif db_job.job_type == 'social_enrichment':
                await self.process_social_enrichment(db, db_job)
            elif db_job.job_type == 'stargazer_analysis':
                await self.process_stargazer_analysis(db, db_job)
            elif db_job.job_type == 'clay_push':
                await self.process_clay_push(db, db_job)
            else:
                logger.warning(f"Unknown job type: {db_job.job_type}")

        except Exception as e:
            logger.error(f"Error processing job {job.id}: {e}", exc_info=True)
            try:
                db_job = db.query(SourcingJob).filter(SourcingJob.id == job.id).first()
                if db_job and db_job.status == 'running':
                    db_job.status = 'failed'
                    db_job.error_message = str(e)[:500]
                    db_job.completed_at = datetime.utcnow()
                    db.commit()
            except Exception:
                logger.error(f"Failed to mark job {job.id} as failed", exc_info=True)

        finally:
            self.running_jobs.discard(str(job.id))
            db.close()
    
    async def run(self):
        """Main processing loop."""
        logger.info("Job processor started")

        # Recover any jobs left in 'running' state from a previous crash/restart
        try:
            db = SessionLocal()
            self.recover_orphaned_jobs(db)
            db.close()
        except Exception as e:
            logger.error(f"Failed to recover orphaned jobs: {e}")

        while True:
            try:
                db = SessionLocal()
                
                # Get pending jobs
                pending_jobs = self.claim_pending_jobs(db)
                
                if pending_jobs:
                    logger.info(f"Found {len(pending_jobs)} pending jobs")
                    
                    # Process jobs concurrently
                    tasks = [self.process_job(job) for job in pending_jobs]
                    await asyncio.gather(*tasks, return_exceptions=True)
                
                db.close()
                
                # Wait before next check
                await asyncio.sleep(config.CHECK_INTERVAL_SECONDS)
            
            except KeyboardInterrupt:
                logger.info("Shutting down...")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(config.CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    processor = JobProcessor()
    asyncio.run(processor.run())
