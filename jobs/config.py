"""Job processor configuration."""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Configuration settings."""
    
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/plg_lead_sourcer')
    
    # GitHub
    GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', '')
    
    # Azure OpenAI
    AZURE_OPENAI_ENDPOINT = os.getenv('AZURE_OPENAI_ENDPOINT', '')
    AZURE_OPENAI_API_KEY = os.getenv('AZURE_OPENAI_API_KEY', '')
    AZURE_OPENAI_DEPLOYMENT = os.getenv('AZURE_OPENAI_DEPLOYMENT', 'gpt-4o-mini')
    AZURE_OPENAI_API_VERSION = os.getenv('AZURE_OPENAI_API_VERSION', '2024-02-15-preview')

    # OpenAI (non-Azure) fallback
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4-turbo-preview')
    
    # Serper
    SERPER_API_KEY = os.getenv('SERPER_API_KEY', '')
    
    # Job Processing
    CHECK_INTERVAL_SECONDS = int(os.getenv('CHECK_INTERVAL_SECONDS', '30'))
    MAX_CONCURRENT_JOBS = int(os.getenv('MAX_CONCURRENT_JOBS', '3'))

    # GitHub data collection controls
    USE_BULK_CONTRIBUTOR_STATS = os.getenv('USE_BULK_CONTRIBUTOR_STATS', 'true').lower() == 'true'
    FETCH_PR_ISSUE_COUNTS = os.getenv('FETCH_PR_ISSUE_COUNTS', 'false').lower() == 'true'
    FETCH_DETAILED_CONTRIBUTOR_PROFILES = os.getenv('FETCH_DETAILED_CONTRIBUTOR_PROFILES', 'false').lower() == 'true'
    DETAILED_PROFILE_LIMIT = int(os.getenv('DETAILED_PROFILE_LIMIT', '20'))


config = Config()
