"""Background job processor."""
import logging
import random
import time
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session

from database import SessionLocal
from config import config
from services.github_service import GitHubService
from services.enrichment_service import EnrichmentService
from services.scoring_service import ScoringService
from models import (
    SourcingJob, JobProgress, CommunitySource, Member,
    MemberActivity, SocialContext, LeadScore,
    CommunityMember, OrgMember, Project
)
import billing_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Max members to enrich per scan — random sample for broader coverage across runs
ENRICHMENT_SAMPLE_SIZE = 100


class JobCancelledError(Exception):
    """Raised when a job is cancelled while processing."""


class JobProcessor:
    """Processes sourcing jobs from the database."""
    
    def __init__(self):
        """Initialize job processor."""
        self.scoring_service = ScoringService()
        self.running_jobs = set()

    def _init_services(self, db: Session, user_id=None):
        """Re-initialize services reading latest settings from DB.

        GitHub service is lazily initialized — it is only created when a
        GitHub-specific job actually needs it, so a missing token won't
        crash unrelated jobs.
        """
        self._db = db
        self._user_id = user_id
        self._github_service = None
        self.enrichment_service = EnrichmentService(db=db, user_id=user_id)

    @property
    def github_service(self) -> GitHubService:
        """Lazy-init GitHub service; raises ValueError if token missing."""
        if self._github_service is None:
            self._github_service = GitHubService(db=self._db, user_id=self._user_id)
        return self._github_service
    
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

    def aggregate_stats(self, stats_rows: List[MemberActivity]) -> dict:
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
        member: Member,
        stats_data: dict
    ):
        """Create or update lead scores for a member in a project."""
        social_context = db.query(SocialContext).filter(
            SocialContext.member_id == member.id
        ).first()

        social_context_data = {
            "classification": social_context.classification if social_context else None,
            "position_level": social_context.position_level if social_context else None
        }

        member_data = {
            "followers": member.followers or 0,
            "public_repos": member.public_repos or 0,
            "company": member.company
        }

        # Get project-specific scoring weights if available
        project = db.query(Project).filter(Project.id == project_id).first()
        scoring_weights = project.scoring_weights if project else None

        score_data = self.scoring_service.calculate_overall_score(
            member_data,
            stats_data,
            social_context_data,
            scoring_weights=scoring_weights
        )

        lead_score = db.query(LeadScore).filter(
            LeadScore.project_id == project_id,
            LeadScore.member_id == member.id
        ).first()

        if not lead_score:
            lead_score = LeadScore(
                project_id=project_id,
                member_id=member.id
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
            # Get source
            repository = db.query(CommunitySource).filter(
                CommunitySource.id == job.source_id
            ).first()
            
            if not repository:
                raise Exception("Community source not found")
            
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
                sample_size = (job.job_metadata or {}).get('sample_size')
                if sample_size:
                    fetch_limit = int(sample_size)
                else:
                    from settings_service import get_setting
                    project = db.query(Project).filter(Project.id == job.project_id).first()
                    org_id = project.org_id if project else None
                    fetch_limit = int(get_setting(db, 'CONTRIBUTOR_SCAN_LIMIT', '100', org_id=org_id))
                logger.info(f"Contributor limit for job {job.id}: {fetch_limit} (sample_size={sample_size})")
                contributors_data = await asyncio.to_thread(
                    self.github_service.get_contributors,
                    repository.owner,
                    repository.repo_name,
                    fetch_limit
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
                    # Create or update member
                    member = db.query(Member).filter(
                        Member.github_id == contrib_data['github_id']
                    ).first()
                    
                    if not member:
                        member = Member(
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
                            following=contrib_data['following'],
                            platform_identities={'github': {'id': contrib_data['github_id'], 'url': contrib_data['github_url'], 'username': contrib_data['username']}}
                        )
                        db.add(member)
                        db.flush()
                    else:
                        # Update existing member
                        member.full_name = contrib_data['full_name'] or member.full_name
                        member.email = contrib_data['email'] or member.email
                        member.company = contrib_data['company'] or member.company
                        member.location = contrib_data['location'] or member.location
                        member.bio = contrib_data['bio'] or member.bio
                        member.followers = contrib_data['followers']
                        member.public_repos = contrib_data['public_repos']
                    
                    # Create source-member relationship
                    community_member = db.query(CommunityMember).filter(
                        CommunityMember.source_id == repository.id,
                        CommunityMember.member_id == member.id
                    ).first()
                    
                    if not community_member:
                        community_member = CommunityMember(
                            source_id=repository.id,
                            member_id=member.id
                        )
                        db.add(community_member)
                    
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
                    
                    # Create or update member activity
                    stats = db.query(MemberActivity).filter(
                        MemberActivity.source_id == repository.id,
                        MemberActivity.member_id == member.id
                    ).first()
                    
                    if not stats:
                        stats = MemberActivity(
                            source_id=repository.id,
                            member_id=member.id
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
                    self.upsert_lead_score(db, repository.project_id, member, stats_payload)

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
                # Find all members linked to this source that don't have social context yet
                enriched_ids = {sc.member_id for sc in db.query(SocialContext.member_id).all()}
                source_members = db.query(CommunityMember).filter(
                    CommunityMember.source_id == repository.id
                ).all()

                unenriched = [cm for cm in source_members if cm.member_id not in enriched_ids]
                # Random sample for broader coverage across multiple scans
                if len(unenriched) > ENRICHMENT_SAMPLE_SIZE:
                    sample = random.sample(unenriched, ENRICHMENT_SAMPLE_SIZE)
                    logger.info(f"Sampling {ENRICHMENT_SAMPLE_SIZE} of {len(unenriched)} unenriched members for enrichment")
                else:
                    sample = unenriched

                member_ids = [cm.member_id for cm in sample]
                member_map = {m.id: m.username for m in db.query(Member).filter(Member.id.in_(member_ids)).all()} if member_ids else {}

                enrich_count = 0
                for cm in sample:
                    enrich_job = SourcingJob(
                        project_id=repository.project_id,
                        source_id=repository.id,
                        job_type='social_enrichment',
                        status='pending',
                        job_metadata={'contributor_id': str(cm.member_id), 'username': member_map.get(cm.member_id, 'unknown')},
                        created_by=job.created_by
                    )
                    db.add(enrich_job)
                    enrich_count += 1

                db.commit()
                already_enriched = len(source_members) - len(unenriched)
                remaining = len(unenriched) - enrich_count
                self.update_progress_step(
                    db, step4, 'completed',
                    f"Queued enrichment for {enrich_count} members ({already_enriched} already enriched, {remaining} remaining for next scan)"
                )
                logger.info(f"Queued {enrich_count} enrichment jobs for source {repository.full_name}")
            except Exception as e:
                self.update_progress_step(db, step4, 'failed', str(e))
                logger.warning(f"Failed to queue enrichment jobs: {e}")

            self.update_job_progress(db, job, 4, 4)

            # Finalize
            job.status = 'completed'
            job.completed_at = datetime.utcnow()
            job.progress_percentage = 100
            db.commit()

            # Advance next_sourcing_at for periodic scheduling
            self._advance_next_sourcing(db, repository)
            
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
                raise Exception("No member ID specified")
            
            contributor = db.query(Member).filter(
                Member.id == contributor_id
            ).first()
            
            if not contributor:
                raise Exception("Member not found")
            
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
                
                # Get member activity for classification
                stats = db.query(MemberActivity).filter(
                    MemberActivity.member_id == contributor.id
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
                    SocialContext.member_id == contributor.id
                ).first()
                
                if not social_context:
                    social_context = SocialContext(member_id=contributor.id)
                    db.add(social_context)
                
                social_context.linkedin_url = linkedin_info.get('linkedin_url')
                social_context.linkedin_profile_photo_url = linkedin_info.get('linkedin_profile_photo_url')
                social_context.linkedin_headline = linkedin_info.get('linkedin_headline')
                social_context.current_company = classification.get('organization') or linkedin_info.get('current_company')
                social_context.current_position = linkedin_info.get('current_position')

                # Update member full_name from LinkedIn if we found a better name
                linkedin_name = linkedin_info.get('linkedin_name')
                if linkedin_name and len(linkedin_name.split()) >= 2:
                    contributor.full_name = linkedin_name
                social_context.position_level = position_level
                social_context.industry = classification.get('industry')
                social_context.search_results = search_results
                social_context.classification = classification['classification']
                social_context.classification_confidence = classification['classification_confidence']
                social_context.classification_reasoning = classification['classification_reasoning']
                social_context.last_enriched_at = datetime.utcnow()

                project_ids = db.query(CommunitySource.project_id).join(
                    CommunityMember, CommunityMember.source_id == CommunitySource.id
                ).filter(
                    CommunityMember.member_id == contributor.id
                ).distinct().all()

                for (project_id,) in project_ids:
                    stats_rows = db.query(MemberActivity).join(
                        CommunitySource, MemberActivity.source_id == CommunitySource.id
                    ).filter(
                        CommunitySource.project_id == project_id,
                        MemberActivity.member_id == contributor.id
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
        """Process stargazer analysis job — fetch stargazers, create members, enrich."""
        logger.info(f"Processing stargazer analysis job {job.id}")

        try:
            self.ensure_job_active(db, job.id)
            repository = db.query(CommunitySource).filter(
                CommunitySource.id == job.source_id
            ).first()

            if not repository:
                raise Exception("Community source not found")

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
                sample_size = (job.job_metadata or {}).get('sample_size')
                if sample_size:
                    sg_limit = int(sample_size)
                else:
                    from settings_service import get_setting
                    project = db.query(Project).filter(Project.id == job.project_id).first()
                    org_id = project.org_id if project else None
                    sg_limit = int(get_setting(db, 'STARGAZER_SCAN_LIMIT', '200', org_id=org_id))
                logger.info(f"Stargazer limit for job {job.id}: {sg_limit} (sample_size={sample_size})")
                stargazers_data = await asyncio.to_thread(
                    self.github_service.get_stargazers,
                    repository.owner,
                    repository.repo_name,
                    sg_limit
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

                    member = db.query(Member).filter(
                        Member.github_id == sg_data['github_id']
                    ).first()

                    if not member:
                        member = Member(
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
                            following=sg_data['following'],
                            platform_identities={'github': {'id': sg_data['github_id'], 'url': sg_data['github_url'], 'username': sg_data['username']}}
                        )
                        db.add(member)
                        db.flush()
                    else:
                        member.full_name = sg_data['full_name'] or member.full_name
                        member.email = sg_data['email'] or member.email
                        member.company = sg_data['company'] or member.company
                        member.bio = sg_data['bio'] or member.bio
                        member.followers = sg_data['followers']
                        member.public_repos = sg_data['public_repos']

                    # Create source-member relationship
                    community_member = db.query(CommunityMember).filter(
                        CommunityMember.source_id == repository.id,
                        CommunityMember.member_id == member.id
                    ).first()

                    if not community_member:
                        community_member = CommunityMember(
                            source_id=repository.id,
                            member_id=member.id
                        )
                        db.add(community_member)

                    # Create member_activity with source='stargazer'
                    stats = db.query(MemberActivity).filter(
                        MemberActivity.source_id == repository.id,
                        MemberActivity.member_id == member.id
                    ).first()

                    if not stats:
                        stats = MemberActivity(
                            source_id=repository.id,
                            member_id=member.id,
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
                    self.upsert_lead_score(db, repository.project_id, member, stats_payload)

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
                enriched_ids = {sc.member_id for sc in db.query(SocialContext.member_id).all()}
                source_members = db.query(CommunityMember).filter(
                    CommunityMember.source_id == repository.id
                ).all()

                unenriched = [cm for cm in source_members if cm.member_id not in enriched_ids]
                # Random sample for broader coverage across multiple scans
                if len(unenriched) > ENRICHMENT_SAMPLE_SIZE:
                    sample = random.sample(unenriched, ENRICHMENT_SAMPLE_SIZE)
                    logger.info(f"Sampling {ENRICHMENT_SAMPLE_SIZE} of {len(unenriched)} unenriched stargazers for enrichment")
                else:
                    sample = unenriched

                member_ids = [cm.member_id for cm in sample]
                member_map = {m.id: m.username for m in db.query(Member).filter(Member.id.in_(member_ids)).all()} if member_ids else {}

                enrich_count = 0
                for cm in sample:
                    enrich_job = SourcingJob(
                        project_id=repository.project_id,
                        source_id=repository.id,
                        job_type='social_enrichment',
                        status='pending',
                        job_metadata={'contributor_id': str(cm.member_id), 'username': member_map.get(cm.member_id, 'unknown')},
                        created_by=job.created_by
                    )
                    db.add(enrich_job)
                    enrich_count += 1

                remaining = len(unenriched) - enrich_count
                db.commit()
                self.update_progress_step(
                    db, step3, 'completed',
                    f"Queued enrichment for {enrich_count} stargazers ({remaining} remaining for next scan)"
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

    # ── Token / config requirement map for each source type ────────────
    _SOURCE_TOKEN_HINTS: dict = {
        'github_repo': 'GITHUB_TOKEN',
        'discord_server': 'DISCORD_BOT_TOKEN',
        'reddit_subreddit': 'REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET',
        'x_account': 'X_BEARER_TOKEN',
        'stock_forum': 'STOCKTWITS_TOKEN',
    }

    async def process_source_ingestion(self, db: Session, job: SourcingJob):
        """Process a generic source ingestion job.

        For source types that don't yet have a connector implementation,
        the job fails immediately with a descriptive error — exactly the
        same pattern used when a GitHub token is missing.
        """
        logger.info(f"Processing source_ingestion job {job.id}")

        try:
            self.ensure_job_active(db, job.id)

            source = db.query(CommunitySource).filter(
                CommunitySource.id == job.source_id
            ).first()

            if not source:
                raise Exception("Community source not found")

            # Initialize job
            if job.status != 'running':
                job.status = 'running'
            if not job.started_at:
                job.started_at = datetime.utcnow()
            job.total_steps = 1
            db.commit()

            step1 = self.create_progress_step(
                db, job.id, 1, f"Connecting to {source.source_type} source"
            )
            self.update_progress_step(db, step1, 'running')

            # Try to get a connector from the registry
            try:
                from connectors.registry import ConnectorRegistry
                connector_cls = ConnectorRegistry.get(source.source_type)
            except Exception:
                connector_cls = None

            if connector_cls is None:
                hint = self._SOURCE_TOKEN_HINTS.get(source.source_type, '')
                msg = (
                    f"No connector available for source type '{source.source_type}'. "
                    f"This community type is not yet supported for automatic ingestion."
                )
                if hint:
                    msg += f" When available, it will require: {hint} (set in Settings > API Keys)."
                self.update_progress_step(db, step1, 'failed', msg)
                raise Exception(msg)

            # Connector exists — check if it can actually connect
            # (e.g. token might be missing even though connector code exists)
            try:
                from settings_service import get_setting, get_user_org_id
                org_id = get_user_org_id(db, job.created_by) if job.created_by else None
                source_config = dict(source.source_config or {})
                connector = connector_cls(
                    db=db, user_id=job.created_by, source_config=source_config
                )
            except (ValueError, Exception) as e:
                hint = self._SOURCE_TOKEN_HINTS.get(source.source_type, '')
                msg = str(e)
                if hint and 'token' in msg.lower():
                    msg += f" Configure {hint} in Settings > API Keys."
                self.update_progress_step(db, step1, 'failed', msg)
                raise Exception(msg)

            # If we reach here the connector initialized — attempt fetch
            try:
                members_data = await connector.fetch_members(source, limit=100)
                self.update_progress_step(
                    db, step1, 'completed',
                    f"Fetched {len(members_data)} members from {source.full_name}"
                )
            except Exception as e:
                self.update_progress_step(db, step1, 'failed', str(e))
                raise

            self.update_job_progress(db, job, 1, 1)

            # Process fetched members (same pattern as GitHub contributors)
            platform_key = source.source_type.split('_')[0]  # github, discord, reddit, x, stock
            processed_count = 0
            for m_data in members_data:
                platform_id = m_data.get('platform_id')
                username = m_data.get('username', '')

                # Try to find existing member by platform identity or username
                member = None
                if platform_id:
                    if source.source_type == 'github_repo':
                        member = db.query(Member).filter(
                            Member.github_id == platform_id
                        ).first()
                    if not member:
                        # Search in platform_identities JSONB
                        member = db.query(Member).filter(
                            Member.platform_identities[platform_key]['id'].astext == str(platform_id)
                        ).first()
                if not member and username:
                    member = db.query(Member).filter(
                        Member.username == username
                    ).first()

                if not member:
                    member = Member(
                        username=username,
                        full_name=m_data.get('full_name'),
                        email=m_data.get('email'),
                        company=m_data.get('company'),
                        location=m_data.get('location'),
                        bio=m_data.get('bio'),
                        avatar_url=m_data.get('avatar_url'),
                        github_url=m_data.get('profile_url') if source.source_type == 'github_repo' else None,
                        public_repos=m_data.get('public_repos', 0),
                        followers=m_data.get('followers', 0),
                        following=m_data.get('following', 0),
                        platform_identities={
                            platform_key: {
                                'id': str(platform_id) if platform_id else username,
                                'username': username,
                            }
                        },
                    )
                    if source.source_type == 'github_repo' and platform_id:
                        member.github_id = platform_id
                    db.add(member)
                    db.flush()
                else:
                    # Update fields if newer data available
                    member.full_name = m_data.get('full_name') or member.full_name
                    member.email = m_data.get('email') or member.email
                    member.company = m_data.get('company') or member.company
                    member.bio = m_data.get('bio') or member.bio
                    member.avatar_url = m_data.get('avatar_url') or member.avatar_url
                    member.followers = m_data.get('followers') or member.followers
                    # Merge platform identity
                    identities = dict(member.platform_identities or {})
                    if platform_key not in identities:
                        identities[platform_key] = {
                            'id': str(platform_id) if platform_id else username,
                            'username': username,
                        }
                        member.platform_identities = identities

                # Create source-member link
                cm = db.query(CommunityMember).filter(
                    CommunityMember.source_id == source.id,
                    CommunityMember.member_id == member.id,
                ).first()
                if not cm:
                    cm = CommunityMember(source_id=source.id, member_id=member.id)
                    db.add(cm)

                # Create/update activity stub
                activity = db.query(MemberActivity).filter(
                    MemberActivity.source_id == source.id,
                    MemberActivity.member_id == member.id,
                ).first()
                if not activity:
                    activity = MemberActivity(
                        source_id=source.id, member_id=member.id
                    )
                    db.add(activity)
                activity.calculated_at = datetime.utcnow()

                # Score
                stats_payload = self.build_stats_payload({})
                self.upsert_lead_score(db, source.project_id, member, stats_payload)

                processed_count += 1
                if processed_count % 25 == 0:
                    db.commit()

            source.last_sourced_at = datetime.utcnow()
            db.commit()

            # Queue enrichment for new members (random sample for broader coverage)
            enriched_ids = {sc.member_id for sc in db.query(SocialContext.member_id).all()}
            source_members = db.query(CommunityMember).filter(
                CommunityMember.source_id == source.id
            ).all()
            unenriched = [cm for cm in source_members if cm.member_id not in enriched_ids]
            if len(unenriched) > ENRICHMENT_SAMPLE_SIZE:
                sample = random.sample(unenriched, ENRICHMENT_SAMPLE_SIZE)
                logger.info(f"Sampling {ENRICHMENT_SAMPLE_SIZE} of {len(unenriched)} unenriched members for enrichment")
            else:
                sample = unenriched

            member_ids = [cm.member_id for cm in sample]
            member_map = {m.id: m.username for m in db.query(Member).filter(Member.id.in_(member_ids)).all()} if member_ids else {}

            enrich_count = 0
            for cm in sample:
                enrich_job = SourcingJob(
                    project_id=source.project_id,
                    source_id=source.id,
                    job_type='social_enrichment',
                    status='pending',
                    job_metadata={'contributor_id': str(cm.member_id), 'username': member_map.get(cm.member_id, 'unknown')},
                    created_by=job.created_by,
                )
                db.add(enrich_job)
                enrich_count += 1
            remaining = len(unenriched) - enrich_count
            db.commit()
            logger.info(f"Queued {enrich_count} enrichment jobs for source {source.full_name} ({remaining} remaining for next scan)")

            # Finalize
            job.status = 'completed'
            job.completed_at = datetime.utcnow()
            job.progress_percentage = 100
            db.commit()

            # Advance next_sourcing_at for periodic scheduling
            self._advance_next_sourcing(db, source)

            logger.info(f"Completed source_ingestion job {job.id}: {processed_count} members")

            self._check_auto_export(db, job)

        except JobCancelledError:
            logger.info(f"Job {job.id} cancelled")
            self.mark_job_cancelled(db, job.id)
            return
        except Exception as e:
            logger.error(f"Error processing source_ingestion job {job.id}: {e}")
            job.status = 'failed'
            job.error_message = str(e)[:500]
            job.completed_at = datetime.utcnow()
            db.commit()

    def _check_auto_export(self, db: Session, job: SourcingJob):
        """After a sourcing/stargazer job completes, check if auto-export to Clay is enabled
        and queue a clay_push job for new leads that haven't been pushed yet."""
        from models import ClayPushLog
        from settings_service import get_setting
        from decimal import Decimal

        try:
            project = db.query(Project).filter(Project.id == job.project_id).first()
            if not project or not project.auto_export_clay_enabled:
                return

            # Resolve org
            org_id = None
            if job.created_by:
                org_member = db.query(OrgMember).filter(OrgMember.user_id == job.created_by).first()
                if org_member:
                    org_id = org_member.org_id

            # Check Clay is configured
            webhook_url = get_setting(db, 'CLAY_WEBHOOK_URL', org_id=org_id, user_id=job.created_by)
            if not webhook_url:
                logger.info(f"Auto-export skipped for project {project.name}: Clay webhook not configured")
                return

            # Get all member IDs in this project
            project_member_ids = db.query(CommunityMember.member_id).join(
                CommunitySource, CommunitySource.id == CommunityMember.source_id
            ).filter(CommunitySource.project_id == project.id).distinct().all()
            all_ids = {str(row[0]) for row in project_member_ids}

            if not all_ids:
                return

            # Exclude already-pushed members
            already_pushed = set()
            if org_id:
                pushed_rows = db.query(ClayPushLog.member_id).filter(
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
                        LeadScore.member_id == cid,
                    ).first()
                    if not score:
                        continue
                    if project.auto_export_clay_min_score and (score.overall_score or 0) < Decimal(str(project.auto_export_clay_min_score)):
                        continue
                    if project.auto_export_clay_classifications:
                        social = db.query(SocialContext.classification).filter(
                            SocialContext.member_id == cid
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
        from models import ClayPushLog
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
                org_member = db.query(OrgMember).filter(OrgMember.user_id == job.created_by).first()
                if org_member:
                    org_id = org_member.org_id

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

            contributors = db.query(Member).filter(
                Member.id.in_(lead_ids)
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
                    member_id=contributor.id,
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

    INTERVAL_DAYS = {'daily': 1, 'weekly': 7, 'monthly': 30}

    def _advance_next_sourcing(self, db: Session, source: CommunitySource):
        """Advance next_sourcing_at based on the source's interval after a scan completes."""
        days = self.INTERVAL_DAYS.get(source.sourcing_interval, 30)
        source.next_sourcing_at = datetime.utcnow() + timedelta(days=days)
        db.commit()
        logger.info(f"Next scan for source {source.full_name} scheduled at {source.next_sourcing_at}")

    def check_scheduled_sources(self, db: Session):
        """Create jobs for active sources whose next_sourcing_at is due.
        Idempotent: skips sources that already have a pending or running job."""
        from sqlalchemy import and_, exists

        now = datetime.utcnow()
        due_sources = db.query(CommunitySource).filter(
            CommunitySource.is_active == True,
            CommunitySource.next_sourcing_at != None,
            CommunitySource.next_sourcing_at <= now,
        ).all()

        created = 0
        for source in due_sources:
            # Skip if there's already a pending/running job for this source
            has_active_job = db.query(SourcingJob).filter(
                SourcingJob.source_id == source.id,
                SourcingJob.status.in_(['pending', 'running']),
            ).first()
            if has_active_job:
                continue

            # Determine job type based on source_type
            job_type = 'source_ingestion' if source.source_type != 'github_repo' else 'repository_sourcing'

            job = SourcingJob(
                project_id=source.project_id,
                source_id=source.id,
                job_type=job_type,
                status='pending',
                job_metadata={'triggered_by': 'scheduler'},
            )
            db.add(job)
            created += 1
            logger.info(f"Scheduled {job_type} job for source {source.full_name} (due: {source.next_sourcing_at})")

        if created:
            db.commit()
            logger.info(f"Created {created} scheduled sourcing jobs")

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
            elif db_job.job_type == 'source_ingestion':
                await self.process_source_ingestion(db, db_job)
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

                # Check for sources due for periodic re-scan
                try:
                    self.check_scheduled_sources(db)
                except Exception as e:
                    logger.error(f"Error checking scheduled sources: {e}")
                
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
