"""
LinkedIn Service - Advanced Social Engineering and Profile Analysis

This service provides comprehensive LinkedIn profile discovery and analysis
for lead qualification. It includes:
- Multi-source LinkedIn profile discovery
- Professional network mapping
- Job history and career trajectory analysis
- Skills and endorsements extraction
- Company intelligence gathering
- Contact information discovery
"""

import re
import httpx
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from tenacity import retry, stop_after_attempt, wait_exponential
from config import config


class LinkedInService:
    """
    Advanced LinkedIn intelligence gathering service.
    
    Uses multiple techniques:
    1. Google/Serper search for public profiles
    2. GitHub profile links to LinkedIn
    3. Company domain matching
    4. Email pattern analysis
    5. Social media cross-referencing
    """
    
    def __init__(self):
        self.serper_api_key = config.SERPER_API_KEY
        self.headers = {
            'X-API-KEY': self.serper_api_key,
            'Content-Type': 'application/json'
        }
        self.cache = {}
        
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def search_linkedin_profile(
        self, 
        name: str, 
        company: Optional[str] = None,
        location: Optional[str] = None,
        keywords: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Search for LinkedIn profile using multiple data points.
        
        Args:
            name: Full name of the person
            company: Current or past company name
            location: Geographic location
            keywords: Additional keywords (title, skills, etc.)
            
        Returns:
            Dict with LinkedIn profile data or None
        """
        cache_key = f"{name}_{company}_{location}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Build search query
        query_parts = [f'"{name}"', 'site:linkedin.com/in/']
        if company:
            query_parts.append(f'"{company}"')
        if location:
            query_parts.append(location)
        if keywords:
            query_parts.extend(keywords)
            
        query = ' '.join(query_parts)
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    'https://google.serper.dev/search',
                    headers=self.headers,
                    json={'q': query, 'num': 5}
                )
                response.raise_for_status()
                results = response.json()
                
                if results.get('organic'):
                    # Parse first relevant result
                    for result in results['organic'][:3]:
                        if 'linkedin.com/in/' in result.get('link', ''):
                            profile_data = await self._extract_profile_data(result)
                            if profile_data:
                                self.cache[cache_key] = profile_data
                                return profile_data
                                
            except Exception as e:
                print(f"LinkedIn search error for {name}: {e}")
                
        return None
    
    async def _extract_profile_data(self, search_result: Dict) -> Dict[str, Any]:
        """Extract structured data from search result."""
        link = search_result.get('link', '')
        snippet = search_result.get('snippet', '')
        title = search_result.get('title', '')
        
        # Extract LinkedIn username
        username_match = re.search(r'linkedin\.com/in/([^/?]+)', link)
        username = username_match.group(1) if username_match else None
        
        # Parse title for name and position
        title_parts = title.split(' - ')
        profile_name = title_parts[0].strip() if title_parts else None
        
        # Extract current position and company from snippet
        position, company = self._parse_position_company(snippet)
        
        # Extract profile photo if available in search result
        profile_photo_url = self._extract_profile_photo(search_result)
        
        return {
            'linkedin_url': link,
            'linkedin_username': username,
            'linkedin_profile_photo_url': profile_photo_url,
            'profile_name': profile_name,
            'current_position': position,
            'current_company': company,
            'snippet': snippet,
            'profile_summary': snippet[:500],
            'discovered_at': datetime.utcnow().isoformat()
        }
    
    def _extract_profile_photo(self, search_result: Dict) -> Optional[str]:
        """Extract LinkedIn profile photo URL from search result."""
        # Serper returns images in the result if available
        if 'image' in search_result:
            return search_result['image']
        
        # Sometimes in the 'sitelinks' or 'organic' result
        if 'sitelinks' in search_result:
            for sitelink in search_result['sitelinks']:
                if 'image' in sitelink:
                    return sitelink['image']
        
        # Check if there's a thumbnail
        if 'thumbnail' in search_result:
            return search_result['thumbnail']
        
        # LinkedIn profile photos often follow a pattern
        # If we have the username, we can construct a likely URL
        link = search_result.get('link', '')
        username_match = re.search(r'linkedin\.com/in/([^/?]+)', link)
        if username_match:
            username = username_match.group(1)
            # This is a fallback - actual photo will be in search results
            # but this provides a consistent fallback
            return f"https://www.linkedin.com/in/{username}/photo/"
        
        return None
    
    def _parse_position_company(self, text: str) -> tuple[Optional[str], Optional[str]]:
        """Parse position and company from text."""
        # Common patterns
        patterns = [
            r'(.+?)\s+at\s+(.+?)(?:\s*[·•|]|$)',
            r'(.+?)\s+@\s+(.+?)(?:\s*[·•|]|$)',
            r'(.+?)\s+-\s+(.+?)(?:\s*[·•|]|$)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                position = match.group(1).strip()
                company = match.group(2).strip()
                # Clean up common suffixes
                company = re.sub(r'\s*\|\s*LinkedIn.*$', '', company)
                return position, company
                
        return None, None
    
    async def enrich_from_github_profile(self, github_data: Dict) -> Dict[str, Any]:
        """
        Extract LinkedIn info from GitHub profile.
        
        Args:
            github_data: GitHub profile data including name, bio, company, blog
            
        Returns:
            Enriched data with LinkedIn profile if found
        """
        enriched = {}
        
        # Check for LinkedIn URL in bio or blog
        bio = github_data.get('bio', '') or ''
        blog = github_data.get('blog', '') or ''
        company = github_data.get('company', '') or ''
        
        combined_text = f"{bio} {blog}"
        linkedin_match = re.search(
            r'(?:https?://)?(?:www\.)?linkedin\.com/in/([^/\s]+)',
            combined_text,
            re.IGNORECASE
        )
        
        if linkedin_match:
            username = linkedin_match.group(1)
            enriched['linkedin_url'] = f"https://linkedin.com/in/{username}"
            enriched['linkedin_username'] = username
            enriched['source'] = 'github_profile'
        else:
            # Try searching
            name = github_data.get('name') or github_data.get('login')
            if name and len(name.split()) >= 2:  # Has first and last name
                # Clean company name
                clean_company = company.strip('@').strip()
                
                profile = await self.search_linkedin_profile(
                    name=name,
                    company=clean_company if clean_company else None
                )
                
                if profile:
                    enriched.update(profile)
                    enriched['source'] = 'search'
        
        return enriched
    
    async def analyze_professional_network(
        self, 
        profile_url: str
    ) -> Dict[str, Any]:
        """
        Analyze professional network and connections.
        Uses public search to find common connections, shared groups, etc.
        
        Args:
            profile_url: LinkedIn profile URL
            
        Returns:
            Network analysis data
        """
        username = self._extract_username(profile_url)
        if not username:
            return {}
        
        query = f'"{username}" site:linkedin.com connections OR network'
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    'https://google.serper.dev/search',
                    headers=self.headers,
                    json={'q': query, 'num': 10}
                )
                
                if response.status_code == 200:
                    results = response.json()
                    return self._analyze_network_results(results)
                    
            except Exception as e:
                print(f"Network analysis error: {e}")
                
        return {}
    
    def _analyze_network_results(self, results: Dict) -> Dict[str, Any]:
        """Analyze search results for network insights."""
        analysis = {
            'estimated_connections': None,
            'common_groups': [],
            'shared_interests': [],
            'network_quality_score': 0
        }
        
        # Parse organic results for insights
        for result in results.get('organic', [])[:5]:
            snippet = result.get('snippet', '').lower()
            
            # Look for connection count mentions
            conn_match = re.search(r'(\d+)\+?\s+connections?', snippet)
            if conn_match:
                analysis['estimated_connections'] = int(conn_match.group(1))
            
            # Look for groups
            if 'group' in snippet or 'member' in snippet:
                analysis['common_groups'].append(result.get('title', ''))
        
        # Calculate network quality score
        if analysis['estimated_connections']:
            if analysis['estimated_connections'] >= 500:
                analysis['network_quality_score'] = 10
            elif analysis['estimated_connections'] >= 100:
                analysis['network_quality_score'] = 7
            else:
                analysis['network_quality_score'] = 4
                
        return analysis
    
    async def find_contact_information(
        self,
        name: str,
        company: Optional[str] = None,
        linkedin_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Discover contact information through public sources.
        
        Args:
            name: Full name
            company: Company name
            linkedin_url: LinkedIn profile URL
            
        Returns:
            Contact information (email patterns, social profiles)
        """
        contacts = {
            'email_patterns': [],
            'social_profiles': {},
            'company_domain': None
        }
        
        # Search for email patterns
        if company:
            query = f'"{name}" "{company}" email'
            async with httpx.AsyncClient(timeout=30.0) as client:
                try:
                    response = await client.post(
                        'https://google.serper.dev/search',
                        headers=self.headers,
                        json={'q': query, 'num': 5}
                    )
                    
                    if response.status_code == 200:
                        results = response.json()
                        contacts['email_patterns'] = self._extract_email_patterns(
                            results, 
                            name
                        )
                        
                except Exception as e:
                    print(f"Contact search error: {e}")
        
        # Search for other social profiles
        social_platforms = ['twitter', 'github', 'medium', 'dev.to']
        for platform in social_platforms:
            query = f'"{name}" site:{platform}.com'
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        'https://google.serper.dev/search',
                        headers=self.headers,
                        json={'q': query, 'num': 3}
                    )
                    
                    if response.status_code == 200:
                        results = response.json()
                        if results.get('organic'):
                            contacts['social_profiles'][platform] = results['organic'][0]['link']
                            
            except Exception:
                continue
        
        return contacts
    
    def _extract_email_patterns(self, results: Dict, name: str) -> List[str]:
        """Extract potential email patterns from search results."""
        patterns = []
        email_regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        
        for result in results.get('organic', [])[:5]:
            snippet = result.get('snippet', '')
            emails = re.findall(email_regex, snippet)
            
            # Filter for relevant emails
            name_parts = name.lower().split()
            for email in emails:
                email_lower = email.lower()
                # Check if email contains name parts
                if any(part in email_lower for part in name_parts):
                    patterns.append(email)
        
        return list(set(patterns))  # Remove duplicates
    
    def _extract_username(self, url: str) -> Optional[str]:
        """Extract LinkedIn username from URL."""
        match = re.search(r'linkedin\.com/in/([^/?]+)', url)
        return match.group(1) if match else None
    
    async def analyze_career_trajectory(
        self,
        linkedin_url: str
    ) -> Dict[str, Any]:
        """
        Analyze career progression and trajectory.
        
        Args:
            linkedin_url: LinkedIn profile URL
            
        Returns:
            Career analysis including progression, stability, growth
        """
        username = self._extract_username(linkedin_url)
        if not username:
            return {}
        
        # Search for career history mentions
        query = f'"{username}" site:linkedin.com (promoted OR joined OR experience)'
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    'https://google.serper.dev/search',
                    headers=self.headers,
                    json={'q': query, 'num': 10}
                )
                
                if response.status_code == 200:
                    results = response.json()
                    return self._analyze_career_data(results)
                    
            except Exception as e:
                print(f"Career analysis error: {e}")
        
        return {}
    
    def _analyze_career_data(self, results: Dict) -> Dict[str, Any]:
        """Analyze career trajectory from search results."""
        analysis = {
            'seniority_level': 'unknown',
            'career_stability': 'unknown',
            'growth_trajectory': 'unknown',
            'leadership_indicators': []
        }
        
        # Analyze snippets for seniority keywords
        seniority_keywords = {
            'c-level': ['ceo', 'cto', 'cfo', 'coo', 'chief'],
            'vp': ['vice president', 'vp '],
            'director': ['director', 'head of'],
            'senior': ['senior', 'principal', 'staff'],
            'mid': ['engineer', 'manager', 'lead'],
        }
        
        combined_text = ' '.join([
            r.get('snippet', '').lower() 
            for r in results.get('organic', [])
        ])
        
        for level, keywords in seniority_keywords.items():
            if any(kw in combined_text for kw in keywords):
                analysis['seniority_level'] = level
                break
        
        # Look for leadership indicators
        leadership_terms = ['team lead', 'manage', 'built team', 'hired', 'founded']
        analysis['leadership_indicators'] = [
            term for term in leadership_terms 
            if term in combined_text
        ]
        
        return analysis
    
    async def get_company_intelligence(
        self,
        company_name: str
    ) -> Dict[str, Any]:
        """
        Gather intelligence about the company.
        
        Args:
            company_name: Name of the company
            
        Returns:
            Company intelligence data
        """
        query = f'"{company_name}" (funding OR revenue OR employees OR valuation)'
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    'https://google.serper.dev/search',
                    headers=self.headers,
                    json={'q': query, 'num': 10}
                )
                
                if response.status_code == 200:
                    results = response.json()
                    return self._parse_company_data(results, company_name)
                    
            except Exception as e:
                print(f"Company intelligence error: {e}")
        
        return {}
    
    def _parse_company_data(self, results: Dict, company_name: str) -> Dict[str, Any]:
        """Parse company information from search results."""
        intel = {
            'company_name': company_name,
            'estimated_size': None,
            'funding_info': None,
            'industry': None,
            'tech_stack': []
        }
        
        combined_text = ' '.join([
            r.get('snippet', '') 
            for r in results.get('organic', [])
        ])
        
        # Extract employee count
        employee_match = re.search(r'(\d+(?:,\d+)?)\s*employees?', combined_text, re.IGNORECASE)
        if employee_match:
            intel['estimated_size'] = employee_match.group(1)
        
        # Extract funding info
        funding_match = re.search(r'\$(\d+(?:\.\d+)?[MBK]?)\s*(?:funding|raised)', combined_text, re.IGNORECASE)
        if funding_match:
            intel['funding_info'] = f"${funding_match.group(1)}"
        
        return intel


# Global instance
linkedin_service = LinkedInService()
