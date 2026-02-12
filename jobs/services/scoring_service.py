"""Lead scoring service."""
import logging
from typing import Dict, Any
from decimal import Decimal

logger = logging.getLogger(__name__)


class ScoringService:
    """Service for calculating lead scores."""
    
    def calculate_activity_score(self, stats: Dict[str, Any]) -> Decimal:
        """Calculate activity score based on contribution stats."""
        score = 0.0
        
        # Recent activity (40 points)
        commits_3m = stats.get('commits_last_3_months', 0)
        if commits_3m >= 50:
            score += 40
        elif commits_3m >= 20:
            score += 30
        elif commits_3m >= 10:
            score += 20
        elif commits_3m >= 5:
            score += 10
        
        # Total commits (30 points)
        total_commits = stats.get('total_commits', 0)
        if total_commits >= 500:
            score += 30
        elif total_commits >= 200:
            score += 25
        elif total_commits >= 100:
            score += 20
        elif total_commits >= 50:
            score += 15
        elif total_commits >= 10:
            score += 10
        
        # Pull requests (20 points)
        prs = stats.get('pull_requests', 0)
        if prs >= 50:
            score += 20
        elif prs >= 20:
            score += 15
        elif prs >= 10:
            score += 10
        elif prs >= 5:
            score += 5
        
        # Maintainer status (10 points)
        if stats.get('is_maintainer', False):
            score += 10
        
        return Decimal(str(min(score, 100.0)))
    
    def calculate_influence_score(self, contributor: Dict[str, Any]) -> Decimal:
        """Calculate influence score based on GitHub profile."""
        score = 0.0
        
        # Followers (50 points)
        followers = contributor.get('followers', 0)
        if followers >= 1000:
            score += 50
        elif followers >= 500:
            score += 40
        elif followers >= 100:
            score += 30
        elif followers >= 50:
            score += 20
        elif followers >= 10:
            score += 10
        
        # Public repos (30 points)
        repos = contributor.get('public_repos', 0)
        if repos >= 50:
            score += 30
        elif repos >= 20:
            score += 20
        elif repos >= 10:
            score += 15
        elif repos >= 5:
            score += 10
        
        # Has company (20 points)
        if contributor.get('company'):
            score += 20
        
        return Decimal(str(min(score, 100.0)))
    
    def calculate_position_score(self, social_context: Dict[str, Any]) -> Decimal:
        """Calculate position score based on professional role."""
        score = 0.0
        
        classification = social_context.get('classification', '')
        position_level = social_context.get('position_level', '')
        
        # Classification score (60 points)
        if classification == 'DECISION_MAKER':
            score += 60
        elif classification == 'KEY_CONTRIBUTOR':
            score += 40
        elif classification == 'HIGH_IMPACT':
            score += 20
        
        # Position level score (40 points)
        position_scores = {
            'C-Suite': 40,
            'Director': 35,
            'Manager': 25,
            'Lead': 20,
            'Senior': 15,
            'Mid': 10,
            'Entry': 5
        }
        score += position_scores.get(position_level, 0)
        
        return Decimal(str(min(score, 100.0)))
    
    def calculate_engagement_score(self, stats: Dict[str, Any]) -> Decimal:
        """Calculate engagement score based on interaction patterns."""
        score = 0.0
        
        # Issues opened (30 points)
        issues = stats.get('issues_opened', 0)
        if issues >= 20:
            score += 30
        elif issues >= 10:
            score += 20
        elif issues >= 5:
            score += 10
        
        # Code reviews (30 points)
        reviews = stats.get('code_reviews', 0)
        if reviews >= 50:
            score += 30
        elif reviews >= 20:
            score += 20
        elif reviews >= 10:
            score += 10
        
        # Recency (40 points)
        commits_3m = stats.get('commits_last_3_months', 0)
        commits_total = stats.get('total_commits', 1)  # Avoid division by zero
        
        recency_ratio = commits_3m / commits_total if commits_total > 0 else 0
        
        if recency_ratio >= 0.5:
            score += 40
        elif recency_ratio >= 0.3:
            score += 30
        elif recency_ratio >= 0.2:
            score += 20
        elif recency_ratio >= 0.1:
            score += 10
        
        return Decimal(str(min(score, 100.0)))
    
    def calculate_overall_score(
        self,
        contributor: Dict[str, Any],
        stats: Dict[str, Any],
        social_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate overall lead score."""
        
        # Calculate individual scores
        activity_score = self.calculate_activity_score(stats)
        influence_score = self.calculate_influence_score(contributor)
        position_score = self.calculate_position_score(social_context)
        engagement_score = self.calculate_engagement_score(stats)
        
        # Weighted average (position is most important for PLG)
        weights = {
            'position': 0.4,
            'activity': 0.25,
            'influence': 0.20,
            'engagement': 0.15
        }
        
        overall_score = (
            float(position_score) * weights['position'] +
            float(activity_score) * weights['activity'] +
            float(influence_score) * weights['influence'] +
            float(engagement_score) * weights['engagement']
        )
        
        overall_score = Decimal(str(overall_score))
        
        # Determine if qualified lead (score >= 60)
        is_qualified_lead = overall_score >= Decimal('60.0')
        
        # Determine priority
        if overall_score >= Decimal('80.0'):
            priority = 'high'
        elif overall_score >= Decimal('60.0'):
            priority = 'medium'
        else:
            priority = 'low'
        
        return {
            'overall_score': overall_score,
            'activity_score': activity_score,
            'influence_score': influence_score,
            'position_score': position_score,
            'engagement_score': engagement_score,
            'is_qualified_lead': is_qualified_lead,
            'priority': priority
        }
