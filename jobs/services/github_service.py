"""GitHub API service."""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from github import Github, GithubException
from tenacity import retry, stop_after_attempt, wait_exponential
from config import config

logger = logging.getLogger(__name__)


class GitHubService:
    """Service for interacting with GitHub API."""
    
    def __init__(self, token: str = None, db=None, user_id=None):
        """Initialize GitHub service."""
        if not token and db:
            from settings_service import get_setting, get_user_org_id
            org_id = get_user_org_id(db, user_id) if user_id else None
            token = get_setting(db, 'GITHUB_TOKEN', org_id=org_id)
        self.token = token or config.GITHUB_TOKEN
        if not self.token:
            raise ValueError("GitHub token is required")
        
        self.client = Github(self.token)
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def get_repository(self, owner: str, repo: str) -> Dict[str, Any]:
        """Get repository information."""
        try:
            repo_obj = self.client.get_repo(f"{owner}/{repo}")
            
            return {
                "full_name": repo_obj.full_name,
                "owner": owner,
                "repo_name": repo,
                "description": repo_obj.description,
                "stars": repo_obj.stargazers_count,
                "forks": repo_obj.forks_count,
                "open_issues": repo_obj.open_issues_count,
                "language": repo_obj.language,
                "topics": repo_obj.get_topics(),
                "url": repo_obj.html_url
            }
        except GithubException as e:
            logger.error(f"Error fetching repository {owner}/{repo}: {e}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def get_contributors(self, owner: str, repo: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get repository contributors."""
        try:
            repo_obj = self.client.get_repo(f"{owner}/{repo}")
            contributors = []

            detailed_limit = limit if config.FETCH_DETAILED_CONTRIBUTOR_PROFILES else config.DETAILED_PROFILE_LIMIT

            for idx, contributor in enumerate(repo_obj.get_contributors()[:limit]):
                try:
                    base = {
                        "github_id": contributor.id,
                        "username": contributor.login,
                        "full_name": None,
                        "email": None,
                        "company": None,
                        "location": None,
                        "bio": None,
                        "blog": None,
                        "twitter_username": None,
                        "avatar_url": contributor.avatar_url,
                        "github_url": contributor.html_url,
                        "public_repos": 0,
                        "followers": 0,
                        "following": 0,
                        "contributions": contributor.contributions
                    }

                    fetch_details = config.FETCH_DETAILED_CONTRIBUTOR_PROFILES or (
                        detailed_limit > 0 and idx < detailed_limit
                    )

                    if fetch_details:
                        # Get detailed user information
                        user = self.client.get_user(contributor.login)
                        base.update({
                            "github_id": user.id,
                            "username": user.login,
                            "full_name": user.name,
                            "email": user.email,
                            "company": user.company,
                            "location": user.location,
                            "bio": user.bio,
                            "blog": user.blog,
                            "twitter_username": user.twitter_username,
                            "avatar_url": user.avatar_url,
                            "github_url": user.html_url,
                            "public_repos": user.public_repos,
                            "followers": user.followers,
                            "following": user.following,
                        })

                    contributors.append(base)
                except Exception as e:
                    logger.warning(f"Error fetching contributor {contributor.login}: {e}")
                    continue
            
            return contributors
        except GithubException as e:
            logger.error(f"Error fetching contributors for {owner}/{repo}: {e}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def get_contributor_stats(self, owner: str, repo: str, username: str) -> Dict[str, Any]:
        """Get detailed contributor statistics."""
        try:
            repo_obj = self.client.get_repo(f"{owner}/{repo}")

            stats = None
            if config.USE_BULK_CONTRIBUTOR_STATS:
                stats = self._get_stats_for_user_from_bulk(repo_obj, username)
            if stats:
                commits_last_3_months = stats.get("commits_last_3_months", 0)
                commits_last_6_months = stats.get("commits_last_6_months", 0)
                commits_last_year = stats.get("commits_last_year", 0)
                total_commits = stats.get("total_commits", commits_last_year)
                first_commit_date = stats.get("first_commit_date")
                last_commit_date = stats.get("last_commit_date")
            else:
                now = datetime.utcnow()
                one_year_ago = now - timedelta(days=365)
                commits = list(repo_obj.get_commits(author=username, since=one_year_ago))
                total_commits = len(commits)
                commits_last_year = total_commits
                commits_last_6_months = 0
                commits_last_3_months = 0
                first_commit_date = None
                last_commit_date = None

                three_months_ago = now - timedelta(days=90)
                six_months_ago = now - timedelta(days=180)
                for commit in commits:
                    commit_date = commit.commit.author.date
                    if not first_commit_date or commit_date < first_commit_date:
                        first_commit_date = commit_date
                    if not last_commit_date or commit_date > last_commit_date:
                        last_commit_date = commit_date
                    if commit_date >= three_months_ago:
                        commits_last_3_months += 1
                    if commit_date >= six_months_ago:
                        commits_last_6_months += 1

            pulls_count = 0
            issues_opened = 0
            if config.FETCH_PR_ISSUE_COUNTS:
                pulls_count, issues_opened = self.get_pr_issue_counts(owner, repo, username)

            is_maintainer = False
            
            return {
                "total_commits": total_commits,
                "commits_last_3_months": commits_last_3_months,
                "commits_last_6_months": commits_last_6_months,
                "commits_last_year": commits_last_year,
                "first_commit_date": first_commit_date,
                "last_commit_date": last_commit_date,
                "pull_requests": pulls_count,
                "issues_opened": issues_opened,
                "is_maintainer": is_maintainer
            }
        except Exception as e:
            logger.error(f"Error fetching stats for {username} in {owner}/{repo}: {e}")
            # Return minimal stats on error
            return {
                "total_commits": 0,
                "commits_last_3_months": 0,
                "commits_last_6_months": 0,
                "commits_last_year": 0,
                "first_commit_date": None,
                "last_commit_date": None,
                "pull_requests": 0,
                "issues_opened": 0,
                "is_maintainer": False
            }

    def get_pr_issue_counts(self, owner: str, repo: str, username: str) -> tuple[int, int]:
        """Get PR and issue counts using GitHub search API."""
        try:
            pr_query = f"repo:{owner}/{repo} type:pr author:{username}"
            issue_query = f"repo:{owner}/{repo} type:issue author:{username}"
            prs = self.client.search_issues(query=pr_query).totalCount
            issues = self.client.search_issues(query=issue_query).totalCount
            return prs, issues
        except Exception as e:
            logger.warning(f"Error fetching PR/issue counts for {username}: {e}")
            return 0, 0

    def get_contributor_stats_bulk(self, owner: str, repo: str) -> Dict[str, Dict[str, Any]]:
        """Get contributor stats for a repository in a single call."""
        try:
            repo_obj = self.client.get_repo(f"{owner}/{repo}")
            stats = repo_obj.get_stats_contributors()
            if not stats:
                logger.info(f"Bulk stats not available yet for {owner}/{repo}")
                return {}

            now = datetime.utcnow()
            three_months_ago = int((now - timedelta(days=90)).timestamp())
            six_months_ago = int((now - timedelta(days=180)).timestamp())
            one_year_ago = int((now - timedelta(days=365)).timestamp())

            by_login: Dict[str, Dict[str, Any]] = {}
            for stat in stats:
                if not stat.author:
                    continue
                login = stat.author.login.lower()
                commits_last_3_months = 0
                commits_last_6_months = 0
                commits_last_year = 0
                first_commit_date = None
                last_commit_date = None

                for week in stat.weeks or []:
                    if not week.c:
                        continue
                    commits_last_year += week.c
                    week_ts = int(week.w.timestamp()) if isinstance(week.w, datetime) else int(week.w)
                    if week_ts >= three_months_ago:
                        commits_last_3_months += week.c
                    if week_ts >= six_months_ago:
                        commits_last_6_months += week.c
                    if week_ts >= one_year_ago:
                        if not first_commit_date:
                            first_commit_date = datetime.utcfromtimestamp(week_ts)
                        last_commit_date = datetime.utcfromtimestamp(week_ts)

                by_login[login] = {
                    "commits_last_3_months": commits_last_3_months,
                    "commits_last_6_months": commits_last_6_months,
                    "commits_last_year": commits_last_year,
                    "total_commits": stat.total,
                    "first_commit_date": first_commit_date,
                    "last_commit_date": last_commit_date,
                }

            return by_login
        except GithubException as e:
            logger.error(f"Error fetching bulk stats for {owner}/{repo}: {e}")
            return {}

    def build_stats_from_bulk(
        self,
        username: str,
        contributions: Optional[int],
        bulk_stats: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build stats data for a contributor from bulk stats and contributions."""
        stats = bulk_stats.get(username.lower(), {})
        total_commits = contributions if contributions is not None else stats.get("total_commits", 0)

        return {
            "total_commits": total_commits or 0,
            "commits_last_3_months": stats.get("commits_last_3_months", 0),
            "commits_last_6_months": stats.get("commits_last_6_months", 0),
            "commits_last_year": stats.get("commits_last_year", 0),
            "first_commit_date": stats.get("first_commit_date"),
            "last_commit_date": stats.get("last_commit_date"),
            "pull_requests": 0,
            "issues_opened": 0,
            "is_maintainer": False,
        }

    def _get_stats_for_user_from_bulk(self, repo_obj, username: str) -> Optional[Dict[str, Any]]:
        """Try to get stats for a single user using the bulk stats endpoint."""
        try:
            stats = repo_obj.get_stats_contributors()
            if not stats:
                return None
            lookup = username.lower()
            now = datetime.utcnow()
            three_months_ago = int((now - timedelta(days=90)).timestamp())
            six_months_ago = int((now - timedelta(days=180)).timestamp())
            one_year_ago = int((now - timedelta(days=365)).timestamp())

            for stat in stats:
                if not stat.author or stat.author.login.lower() != lookup:
                    continue
                commits_last_3_months = 0
                commits_last_6_months = 0
                commits_last_year = 0
                first_commit_date = None
                last_commit_date = None
                for week in stat.weeks or []:
                    if not week.c:
                        continue
                    commits_last_year += week.c
                    week_ts = int(week.w)
                    if week_ts >= three_months_ago:
                        commits_last_3_months += week.c
                    if week_ts >= six_months_ago:
                        commits_last_6_months += week.c
                    if week_ts >= one_year_ago:
                        if not first_commit_date:
                            first_commit_date = datetime.utcfromtimestamp(week_ts)
                        last_commit_date = datetime.utcfromtimestamp(week_ts)
                return {
                    "commits_last_3_months": commits_last_3_months,
                    "commits_last_6_months": commits_last_6_months,
                    "commits_last_year": commits_last_year,
                    "total_commits": stat.total,
                    "first_commit_date": first_commit_date,
                    "last_commit_date": last_commit_date,
                }
            return None
        except Exception:
            return None
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def get_stargazers(self, owner: str, repo: str, limit: int = 200) -> List[Dict[str, Any]]:
        """Get users who starred a repository with detailed profiles."""
        try:
            repo_obj = self.client.get_repo(f"{owner}/{repo}")
            stargazers = []

            for idx, user in enumerate(repo_obj.get_stargazers()):
                if idx >= limit:
                    break
                try:
                    # Fetch detailed profile for richer data
                    detailed = self.client.get_user(user.login)
                    stargazers.append({
                        "github_id": detailed.id,
                        "username": detailed.login,
                        "full_name": detailed.name,
                        "email": detailed.email,
                        "company": detailed.company,
                        "location": detailed.location,
                        "bio": detailed.bio,
                        "blog": detailed.blog,
                        "twitter_username": detailed.twitter_username,
                        "avatar_url": detailed.avatar_url,
                        "github_url": detailed.html_url,
                        "public_repos": detailed.public_repos,
                        "followers": detailed.followers,
                        "following": detailed.following,
                        "contributions": 0
                    })
                except Exception as e:
                    logger.warning(f"Error fetching stargazer {user.login}: {e}")
                    continue

            return stargazers
        except GithubException as e:
            logger.error(f"Error fetching stargazers for {owner}/{repo}: {e}")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def search_repositories(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for similar repositories."""
        try:
            repositories = []
            for repo in self.client.search_repositories(query=query, sort='stars', order='desc')[:limit]:
                repositories.append({
                    "full_name": repo.full_name,
                    "owner": repo.owner.login,
                    "repo_name": repo.name,
                    "description": repo.description,
                    "stars": repo.stargazers_count,
                    "forks": repo.forks_count,
                    "language": repo.language,
                    "topics": repo.get_topics(),
                    "url": repo.html_url
                })
            
            return repositories
        except GithubException as e:
            logger.error(f"Error searching repositories: {e}")
            raise
    
    def get_rate_limit(self) -> Dict[str, Any]:
        """Get current rate limit status."""
        rate_limit = self.client.get_rate_limit()
        return {
            "core": {
                "limit": rate_limit.core.limit,
                "remaining": rate_limit.core.remaining,
                "reset": rate_limit.core.reset
            },
            "search": {
                "limit": rate_limit.search.limit,
                "remaining": rate_limit.search.remaining,
                "reset": rate_limit.search.reset
            }
        }
