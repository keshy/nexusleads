"""Service for reading app settings from DB with env var fallback."""
import os
from typing import Optional, Dict, List
from sqlalchemy.orm import Session
from models import AppSetting


# Defines which settings are manageable via UI
MANAGED_SETTINGS = [
    {
        "key": "GITHUB_TOKEN",
        "description": "GitHub Personal Access Token for fetching repository data, contributors, and stargazers.",
        "is_secret": True,
        "hint": "Create at github.com/settings/tokens. Required scopes: public_repo, read:user. Classic tokens recommended.",
        "help_url": "https://github.com/settings/tokens",
        "required": True,
        "placeholder": "ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    },
    {
        "key": "AZURE_OPENAI_ENDPOINT",
        "description": "Your Azure OpenAI resource endpoint URL for AI-powered lead classification and enrichment.",
        "is_secret": False,
        "hint": "Found in Azure Portal > Your OpenAI Resource > Keys and Endpoint. Format: https://<resource-name>.openai.azure.com/",
        "help_url": "https://portal.azure.com/#view/Microsoft_Azure_ProjectOxford/CognitiveServicesHub/~/OpenAI",
        "required": False,
        "placeholder": "https://your-resource.openai.azure.com/",
    },
    {
        "key": "AZURE_OPENAI_API_KEY",
        "description": "API key for your Azure OpenAI resource.",
        "is_secret": True,
        "hint": "Found in Azure Portal > Your OpenAI Resource > Keys and Endpoint. Either Key 1 or Key 2 works.",
        "help_url": "https://portal.azure.com/#view/Microsoft_Azure_ProjectOxford/CognitiveServicesHub/~/OpenAI",
        "required": False,
        "placeholder": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    },
    {
        "key": "AZURE_OPENAI_DEPLOYMENT",
        "description": "The deployment name of your Azure OpenAI model (e.g. gpt-4o-mini).",
        "is_secret": False,
        "hint": "Found in Azure OpenAI Studio > Deployments. This is the name you gave your model deployment, not the model name itself.",
        "help_url": "https://oai.azure.com/portal/deployment",
        "required": False,
        "placeholder": "gpt-4o-mini",
    },
    {
        "key": "AZURE_OPENAI_API_VERSION",
        "description": "Azure OpenAI API version string.",
        "is_secret": False,
        "hint": "Usually '2024-02-15-preview' or newer. Check Azure docs for latest stable version.",
        "help_url": "https://learn.microsoft.com/en-us/azure/ai-services/openai/reference",
        "required": False,
        "placeholder": "2024-02-15-preview",
    },
    {
        "key": "OPENAI_API_KEY",
        "description": "Standard OpenAI API key. Used as fallback if Azure OpenAI is not configured.",
        "is_secret": True,
        "hint": "Create at platform.openai.com/api-keys. Requires a paid OpenAI account with API access.",
        "help_url": "https://platform.openai.com/api-keys",
        "required": False,
        "placeholder": "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    },
    {
        "key": "OPENAI_MODEL",
        "description": "OpenAI model to use for classification (non-Azure).",
        "is_secret": False,
        "hint": "Recommended: gpt-4o-mini (fast & cheap) or gpt-4-turbo-preview (higher quality). See OpenAI pricing page.",
        "help_url": "https://platform.openai.com/docs/models",
        "required": False,
        "placeholder": "gpt-4o-mini",
    },
    {
        "key": "SERPER_API_KEY",
        "description": "Serper.dev API key for web search to find LinkedIn profiles and professional context.",
        "is_secret": True,
        "hint": "Sign up at serper.dev for 2,500 free searches/month. Used for LinkedIn profile discovery and social enrichment.",
        "help_url": "https://serper.dev/",
        "required": True,
        "placeholder": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    },
    {
        "key": "CLAY_WEBHOOK_URL",
        "description": "Clay table webhook URL for pushing enriched leads.",
        "is_secret": False,
        "hint": "Find this in your Clay table settings under 'Webhooks'. Format: https://hooks.clay.com/...",
        "help_url": "https://university.clay.com/docs/http-api-integration-overview",
        "required": False,
        "placeholder": "https://hooks.clay.com/...",
    },
    {
        "key": "CLAY_TABLE_NAME",
        "description": "Display name for your Clay table (for your reference only).",
        "is_secret": False,
        "hint": "Optional — helps you identify which Clay table leads are pushed to.",
        "help_url": "",
        "required": False,
        "placeholder": "NexusLeads Inbound",
    },
    {
        "key": "CLAY_RATE_LIMIT_MS",
        "description": "Delay between Clay webhook pushes in milliseconds.",
        "is_secret": False,
        "hint": "Default: 200ms. Increase if you hit Clay rate limits.",
        "help_url": "",
        "required": False,
        "placeholder": "200",
    },
]

MANAGED_KEYS = {s["key"] for s in MANAGED_SETTINGS}


def _is_default_org(db: Session, org_id) -> bool:
    """Check if an org is the default org (env var fallback allowed)."""
    from models import Organization
    org = db.query(Organization).filter(Organization.id == org_id).first()
    return org is not None and org.slug == 'default'


def get_setting(db: Session, key: str, default: str = "", org_id=None) -> str:
    """Get a setting value. Org DB → (env var only for default org) → default."""
    if org_id:
        from models import OrgSetting
        row = db.query(OrgSetting).filter(
            OrgSetting.org_id == org_id,
            OrgSetting.key == key,
        ).first()
        if row and row.value:
            return row.value
        # Only fall back to env vars for the default org
        if _is_default_org(db, org_id):
            return os.getenv(key, default)
        return default
    return os.getenv(key, default)


def get_org_settings(db: Session, org_id) -> List[Dict]:
    """Get all managed settings for an organization (secrets masked)."""
    from models import OrgSetting
    db_settings = {
        s.key: s for s in db.query(OrgSetting).filter(
            OrgSetting.org_id == org_id,
            OrgSetting.key.in_(MANAGED_KEYS),
        ).all()
    }

    is_default = _is_default_org(db, org_id)
    result = []
    for defn in MANAGED_SETTINGS:
        key = defn["key"]
        row = db_settings.get(key)
        raw_value = ""
        source = "not_set"

        if row and row.value:
            raw_value = row.value
            source = "database"
        elif is_default and os.getenv(key):
            raw_value = os.getenv(key, "")
            source = "environment"

        is_set = bool(raw_value)
        display_value = ""
        if is_set and defn["is_secret"]:
            display_value = raw_value[:4] + "****" + raw_value[-4:] if len(raw_value) > 8 else "****"
        elif is_set:
            display_value = raw_value

        result.append({
            "key": key,
            "value": display_value,
            "description": defn["description"],
            "is_secret": defn["is_secret"],
            "is_set": is_set,
            "source": source,
            "hint": defn.get("hint", ""),
            "help_url": defn.get("help_url", ""),
            "required": defn.get("required", False),
            "placeholder": defn.get("placeholder", ""),
        })

    return result


def upsert_org_setting(db: Session, org_id, key: str, value: str):
    """Create or update an org setting."""
    from models import OrgSetting
    defn = next((s for s in MANAGED_SETTINGS if s["key"] == key), None)
    if not defn:
        raise ValueError(f"Unknown setting key: {key}")

    row = db.query(OrgSetting).filter(
        OrgSetting.org_id == org_id,
        OrgSetting.key == key,
    ).first()
    if not row:
        row = OrgSetting(
            org_id=org_id,
            key=key,
            value=value,
            is_secret=defn["is_secret"],
        )
        db.add(row)
    else:
        row.value = value
    db.commit()
    db.refresh(row)
    return row


def delete_org_setting(db: Session, org_id, key: str):
    """Delete an org setting (reverts to env var fallback)."""
    from models import OrgSetting
    db.query(OrgSetting).filter(
        OrgSetting.org_id == org_id,
        OrgSetting.key == key,
    ).delete()
    db.commit()


def get_user_org_id(db: Session, user_id):
    """Get the org_id for a user (returns first org they belong to, or None)."""
    from models import OrgMember
    member = db.query(OrgMember).filter(OrgMember.user_id == user_id).first()
    return member.org_id if member else None
