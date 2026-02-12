"""Social enrichment service for contributors."""
import logging
import json
from typing import Dict, Any, Optional
import httpx
from openai import AzureOpenAI, OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential
from config import config
from services.linkedin_service import linkedin_service

logger = logging.getLogger(__name__)


class EnrichmentService:
    """Service for enriching contributor profiles with social data."""
    
    def __init__(self, db=None, user_id=None):
        """Initialize enrichment service."""
        if db:
            from settings_service import get_setting, get_user_org_id
            org_id = get_user_org_id(db, user_id) if user_id else None
            serper_key = get_setting(db, 'SERPER_API_KEY', org_id=org_id)
            azure_key = get_setting(db, 'AZURE_OPENAI_API_KEY', org_id=org_id)
            azure_endpoint = get_setting(db, 'AZURE_OPENAI_ENDPOINT', org_id=org_id)
            azure_deployment = get_setting(db, 'AZURE_OPENAI_DEPLOYMENT', 'gpt-4o-mini', org_id=org_id)
            azure_api_version = get_setting(db, 'AZURE_OPENAI_API_VERSION', '2024-02-15-preview', org_id=org_id)
            openai_key = get_setting(db, 'OPENAI_API_KEY', org_id=org_id)
            openai_model = get_setting(db, 'OPENAI_MODEL', 'gpt-4-turbo-preview', org_id=org_id)
        else:
            serper_key = config.SERPER_API_KEY
            azure_key = config.AZURE_OPENAI_API_KEY
            azure_endpoint = config.AZURE_OPENAI_ENDPOINT
            azure_deployment = config.AZURE_OPENAI_DEPLOYMENT
            azure_api_version = config.AZURE_OPENAI_API_VERSION
            openai_key = config.OPENAI_API_KEY
            openai_model = config.OPENAI_MODEL

        self.serpapi_key = serper_key
        
        # Initialize OpenAI client (Azure preferred if configured)
        if azure_key and azure_endpoint:
            self.openai_client = AzureOpenAI(
                api_key=azure_key,
                api_version=azure_api_version,
                azure_endpoint=azure_endpoint
            )
            self.openai_model = azure_deployment
        elif openai_key:
            self.openai_client = OpenAI(
                api_key=openai_key
            )
            self.openai_model = openai_model
        else:
            self.openai_client = None
            self.openai_model = None
            
        self.linkedin_service = linkedin_service
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def search_person(self, name: str, company: Optional[str] = None, username: Optional[str] = None) -> Dict[str, Any]:
        """Search for a person on the web (LinkedIn, etc.) using SerpAPI."""
        if not self.serpapi_key:
            logger.warning("SerpAPI key not configured")
            return {"results": []}
        
        # Build search query
        query_parts = [name]
        if company:
            query_parts.append(company)
        if username:
            query_parts.append(username)
        query_parts.append("LinkedIn")
        
        query = " ".join(query_parts)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://serpapi.com/search",
                    params={
                        "q": query,
                        "api_key": self.serpapi_key,
                        "engine": "google",
                        "num": 5
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                # Normalize SerpAPI response to match the format extract_linkedin_info expects
                # SerpAPI uses "organic_results" with "title", "link", "snippet", "thumbnail"
                normalized = {
                    "organic": [
                        {
                            "title": r.get("title", ""),
                            "link": r.get("link", ""),
                            "snippet": r.get("snippet", ""),
                            "image": r.get("thumbnail")
                        }
                        for r in data.get("organic_results", [])
                    ]
                }
                return normalized
        except Exception as e:
            logger.error(f"Error searching for {name}: {e}")
            return {"results": []}
    
    def extract_linkedin_info(self, search_results: Dict[str, Any]) -> Dict[str, Any]:
        """Extract LinkedIn information from search results."""
        linkedin_info = {
            "linkedin_url": None,
            "linkedin_profile_photo_url": None,
            "linkedin_headline": None,
            "current_company": None,
            "current_position": None
        }
        
        if not search_results.get("organic"):
            return linkedin_info
        
        for result in search_results.get("organic", []):
            link = result.get("link", "")
            if "linkedin.com/in/" in link:
                linkedin_info["linkedin_url"] = link
                linkedin_info["linkedin_profile_photo_url"] = result.get("image") or result.get("thumbnail")
                
                # Try to extract info from snippet
                snippet = result.get("snippet", "")
                title = result.get("title", "")
                
                # Parse title (usually contains name and position)
                if " - " in title:
                    parts = title.split(" - ")
                    if len(parts) >= 2:
                        linkedin_info["current_position"] = parts[0].strip()
                        linkedin_info["current_company"] = parts[1].strip()
                
                # Use snippet as headline
                linkedin_info["linkedin_headline"] = snippet[:200] if snippet else None
                
                break  # Use first LinkedIn result
        
        return linkedin_info
    
    def classify_position_level(self, position: Optional[str]) -> str:
        """Classify position level based on title."""
        if not position:
            return "Unknown"
        
        position_lower = position.lower()
        
        # C-Suite
        if any(term in position_lower for term in ['ceo', 'cto', 'cfo', 'coo', 'cmo', 'chief', 'president', 'founder']):
            return "C-Suite"
        
        # VP/Director
        if any(term in position_lower for term in ['vp', 'vice president', 'director', 'head of']):
            return "Director"
        
        # Manager
        if any(term in position_lower for term in ['manager', 'lead', 'principal']):
            return "Manager"
        
        # Senior
        if any(term in position_lower for term in ['senior', 'sr.', 'staff']):
            return "Senior"
        
        # Mid-level
        if any(term in position_lower for term in ['engineer', 'developer', 'architect', 'analyst']):
            return "Mid"
        
        return "Entry"
    
    async def classify_contributor(
        self,
        contributor_data: Dict[str, Any],
        stats_data: Dict[str, Any],
        linkedin_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Classify contributor using LLM."""
        if not self.openai_client:
            # Fallback to rule-based classification
            return self._rule_based_classification(contributor_data, stats_data, linkedin_data)
        
        try:
            # Build context for LLM
            context = f"""
            Contributor Information:
            - Name: {contributor_data.get('full_name', 'Unknown')}
            - Username: {contributor_data.get('username')}
            - Company: {contributor_data.get('company', 'Unknown')}
            - Bio: {contributor_data.get('bio', 'N/A')}
            - GitHub Followers: {contributor_data.get('followers', 0)}
            
            Activity Stats:
            - Total Commits: {stats_data.get('total_commits', 0)}
            - Commits (Last 3 months): {stats_data.get('commits_last_3_months', 0)}
            - Pull Requests: {stats_data.get('pull_requests', 0)}
            - Is Maintainer: {stats_data.get('is_maintainer', False)}
            
            Professional Profile:
            - Current Position: {linkedin_data.get('current_position', 'Unknown')}
            - Current Company: {linkedin_data.get('current_company', 'Unknown')}
            - LinkedIn Headline: {linkedin_data.get('linkedin_headline', 'N/A')}
            
            Based on this information:
            
            1. Classify this contributor into one of these categories:
               - DECISION_MAKER: C-suite, VPs, Directors who can make purchasing decisions
               - KEY_CONTRIBUTOR: Maintainers, core team members, architects with high influence
               - HIGH_IMPACT: Active contributors with significant recent activity
            
            2. Infer their organization and industry from all available signals (company field, bio, repos, LinkedIn).
            
            Return ONLY a JSON object with these fields:
            {{
                "classification": "DECISION_MAKER|KEY_CONTRIBUTOR|HIGH_IMPACT",
                "confidence": 0.0-1.0,
                "reasoning": "Brief explanation of why this classification was chosen",
                "organization": "Best guess at current employer/org or null",
                "industry": "Industry sector (e.g. Cybersecurity, Cloud Infrastructure, FinTech, Healthcare, etc.) or null"
            }}
            """
            
            response = self.openai_client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at analyzing professional profiles and classifying leads for B2B sales. Return only valid JSON."
                    },
                    {
                        "role": "user",
                        "content": context
                    }
                ],
                temperature=0.3,
                max_tokens=200
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Parse JSON response
            # Remove markdown code blocks if present
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
            
            result = json.loads(result_text)
            
            return {
                "classification": result.get("classification", "HIGH_IMPACT"),
                "classification_confidence": min(max(result.get("confidence", 0.5), 0.0), 1.0),
                "classification_reasoning": result.get("reasoning", ""),
                "organization": result.get("organization"),
                "industry": result.get("industry")
            }
        
        except Exception as e:
            logger.error(f"Error in LLM classification: {e}")
            return self._rule_based_classification(contributor_data, stats_data, linkedin_data)
    
    def _rule_based_classification(
        self,
        contributor_data: Dict[str, Any],
        stats_data: Dict[str, Any],
        linkedin_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Rule-based fallback classification."""
        position = linkedin_data.get('current_position', '') or ''
        position_lower = position.lower()
        
        # Check for decision maker indicators
        decision_maker_terms = ['ceo', 'cto', 'cfo', 'coo', 'vp', 'vice president', 'director', 'head of', 'chief']
        if any(term in position_lower for term in decision_maker_terms):
            return {
                "classification": "DECISION_MAKER",
                "classification_confidence": 0.8,
                "classification_reasoning": "Senior leadership position"
            }
        
        # Check for key contributor indicators
        is_maintainer = stats_data.get('is_maintainer', False)
        total_commits = stats_data.get('total_commits', 0)
        
        if is_maintainer or total_commits > 100:
            return {
                "classification": "KEY_CONTRIBUTOR",
                "classification_confidence": 0.7,
                "classification_reasoning": "High contribution level and maintainer status"
            }
        
        # Check for high impact
        commits_last_3_months = stats_data.get('commits_last_3_months', 0)
        if commits_last_3_months >= 10:
            return {
                "classification": "HIGH_IMPACT",
                "classification_confidence": 0.6,
                "classification_reasoning": "Recent active contributions"
            }
        
        # Default
        return {
            "classification": "HIGH_IMPACT",
            "classification_confidence": 0.4,
            "classification_reasoning": "Active contributor"
        }
    
    async def deep_enrich_profile(
        self,
        contributor_data: Dict[str, Any],
        github_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Perform deep enrichment using advanced LinkedIn intelligence.
        
        This method combines:
        - LinkedIn profile discovery from multiple sources
        - Professional network analysis
        - Contact information discovery
        - Career trajectory analysis
        - Company intelligence
        
        Args:
            contributor_data: Basic contributor data from database
            github_profile: Full GitHub profile data
            
        Returns:
            Comprehensive enriched profile data
        """
        enriched = {}
        
        # Step 1: Find LinkedIn profile
        linkedin_data = await self.linkedin_service.enrich_from_github_profile(github_profile)
        
        if not linkedin_data.get('linkedin_url'):
            # Try direct search if not found in GitHub
            name = contributor_data.get('full_name')
            company = github_profile.get('company', '').strip('@').strip()
            
            if name and len(name.split()) >= 2:
                profile = await self.linkedin_service.search_linkedin_profile(
                    name=name,
                    company=company if company else None
                )
                if profile:
                    linkedin_data.update(profile)
        
        enriched['linkedin_data'] = linkedin_data
        
        # Step 2: Analyze professional network (if LinkedIn found)
        if linkedin_data.get('linkedin_url'):
            network_analysis = await self.linkedin_service.analyze_professional_network(
                linkedin_data['linkedin_url']
            )
            enriched['network_analysis'] = network_analysis
            
            # Step 3: Career trajectory analysis
            career_analysis = await self.linkedin_service.analyze_career_trajectory(
                linkedin_data['linkedin_url']
            )
            enriched['career_analysis'] = career_analysis
        
        # Step 4: Find contact information
        if contributor_data.get('full_name'):
            contacts = await self.linkedin_service.find_contact_information(
                name=contributor_data['full_name'],
                company=linkedin_data.get('current_company'),
                linkedin_url=linkedin_data.get('linkedin_url')
            )
            enriched['contact_info'] = contacts
        
        # Step 5: Company intelligence
        if linkedin_data.get('current_company'):
            company_intel = await self.linkedin_service.get_company_intelligence(
                linkedin_data['current_company']
            )
            enriched['company_intelligence'] = company_intel
        
        # Step 6: Calculate enrichment quality score
        enriched['enrichment_quality'] = self._calculate_enrichment_quality(enriched)
        
        return enriched
    
    def _calculate_enrichment_quality(self, enriched_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate quality score for enriched data."""
        score = 0
        max_score = 100
        details = {}
        
        # LinkedIn profile found (30 points)
        if enriched_data.get('linkedin_data', {}).get('linkedin_url'):
            score += 30
            details['linkedin_profile'] = True
        
        # Network analysis (20 points)
        network = enriched_data.get('network_analysis', {})
        if network.get('estimated_connections'):
            score += 20
            details['network_analysis'] = True
        
        # Career analysis (20 points)
        career = enriched_data.get('career_analysis', {})
        if career.get('seniority_level') and career['seniority_level'] != 'unknown':
            score += 20
            details['career_analysis'] = True
        
        # Contact information (15 points)
        contacts = enriched_data.get('contact_info', {})
        if contacts.get('email_patterns') or contacts.get('social_profiles'):
            score += 15
            details['contact_info'] = True
        
        # Company intelligence (15 points)
        company = enriched_data.get('company_intelligence', {})
        if company.get('estimated_size') or company.get('funding_info'):
            score += 15
            details['company_intelligence'] = True
        
        return {
            'score': score,
            'max_score': max_score,
            'percentage': round((score / max_score) * 100, 2),
            'details': details
        }
