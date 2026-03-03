# 006 — Dynamic Classification & User-Defined Scoring

> Replace the hard-coded DECISION_MAKER / KEY_CONTRIBUTOR / HIGH_IMPACT taxonomy with a flexible, user-driven classification system where the project's sourcing context becomes the LLM prompt for classification.

## Problem Statement

Today, classification is fixed to three labels (`DECISION_MAKER`, `KEY_CONTRIBUTOR`, `HIGH_IMPACT`) with hard-coded rules in both the LLM prompt (`enrichment_service.py`) and the rule-based fallback. The scoring weights in `scoring_service.py` are also static (position 40%, activity 25%, influence 20%, engagement 15%).

This doesn't work when:
- A user is sourcing from a **Discord server** — "commits" and "maintainer status" don't exist
- A user cares about **different personas** — e.g. "Enterprise Buyer", "Technical Evaluator", "Community Champion"
- A user wants to weight **engagement** higher than position for a developer-tools product
- Classification criteria should reflect what the user describes in their **sourcing context**

## Design

### 1. Project-Level Classification Schema

When creating a project, the user already provides `sourcing_context` (free-text). We enhance this:

```
Project:
  sourcing_context: str          # Existing — user describes what they're looking for
  classification_labels: list    # NEW — user-defined labels (or use defaults)
  scoring_weights: dict          # NEW — user-defined score weights (or use defaults)
```

#### Default Classification Labels

If the user doesn't define custom labels, the platform provides sensible defaults:

```json
[
  {"key": "DECISION_MAKER", "label": "Decision Maker", "description": "C-suite, VPs, Directors who can make purchasing decisions"},
  {"key": "KEY_CONTRIBUTOR", "label": "Key Contributor", "description": "Core team members, maintainers, architects with high influence"},
  {"key": "HIGH_IMPACT", "label": "High Impact", "description": "Active participants with significant recent activity"}
]
```

#### Custom Classification Labels (User-Defined)

Users can override with their own:

```json
[
  {"key": "ENTERPRISE_BUYER", "label": "Enterprise Buyer", "description": "Senior leaders at companies >500 employees who control budget"},
  {"key": "TECHNICAL_EVALUATOR", "label": "Technical Evaluator", "description": "Engineers and architects who evaluate tools and recommend to leadership"},
  {"key": "COMMUNITY_CHAMPION", "label": "Community Champion", "description": "Highly active community members who influence adoption through content and advocacy"}
]
```

### 2. Sourcing Context as LLM Classification Prompt

The `sourcing_context` field becomes the **primary prompt context** for the LLM classifier. Today's hard-coded prompt in `enrichment_service.classify_contributor()` becomes dynamic:

```python
async def classify_member(self, project, member_data, activity_data, social_data):
    """Classify a member using the project's sourcing context as the LLM prompt."""

    labels_block = "\n".join(
        f"- {l['key']}: {l['description']}"
        for l in project.classification_labels
    )

    prompt = f"""
    You are classifying a community member for a lead sourcing project.

    PROJECT CONTEXT:
    {project.sourcing_context}

    CLASSIFICATION LABELS (pick exactly one):
    {labels_block}

    MEMBER PROFILE:
    - Name: {member_data.get('full_name')}
    - Platform handles: {member_data.get('platform_identities')}
    - Company: {member_data.get('company')}
    - Bio: {member_data.get('bio')}

    COMMUNITY ACTIVITY:
    {format_activity(activity_data)}

    PROFESSIONAL PROFILE:
    - Position: {social_data.get('current_position')}
    - Company: {social_data.get('current_company')}
    - LinkedIn: {social_data.get('linkedin_headline')}

    Return JSON:
    {{
        "classification": "<one of the label keys above>",
        "confidence": 0.0-1.0,
        "reasoning": "Brief explanation",
        "organization": "Inferred employer or null",
        "industry": "Industry sector or null"
    }}
    """
```

Key insight: The `sourcing_context` gives the LLM the **business context** — what the user is trying to find and why. This naturally adapts classification to the user's actual intent.

### 3. User-Defined Scoring Weights

Replace the hard-coded weights in `ScoringService.calculate_overall_score()`:

```python
# Current (hard-coded):
weights = {'position': 0.4, 'activity': 0.25, 'influence': 0.20, 'engagement': 0.15}

# New (project-level, with defaults):
weights = project.scoring_weights or DEFAULT_SCORING_WEIGHTS
```

#### Default Weights

```json
{
  "position": 0.35,
  "activity": 0.25,
  "influence": 0.20,
  "engagement": 0.20
}
```

#### UI for Custom Weights

In the Project settings, sliders for each weight dimension that must sum to 1.0:

```
Score Weights               [Use defaults]

Position / Seniority  ████████░░  0.35
Community Activity    █████░░░░░  0.25
Influence / Reach     ████░░░░░░  0.20
Engagement / Recency  ████░░░░░░  0.20
                              Total: 1.00
```

### 4. Platform-Agnostic Scoring

The current `ScoringService` uses GitHub-specific metrics (commits, PRs, followers, public_repos). With community generalization, scoring must work across platforms.

#### Activity Score — Generalized

| Signal | GitHub | Discord | Reddit | X |
|--------|--------|---------|--------|---|
| Recent activity count | commits_last_3_months | messages_last_3_months | posts_last_3_months | tweets_last_3_months |
| Total activity | total_commits | total_messages | total_posts | total_tweets |
| Quality interactions | pull_requests | thread_starts | top_level_posts | original_tweets |
| Maintainer/Mod status | is_maintainer | has_mod_role | is_moderator | — |

The scoring service reads from `MemberActivity` which is already normalized by the connector. Thresholds can be tuned per source type or kept generic.

#### Influence Score — Generalized

| Signal | GitHub | Discord | Reddit | X |
|--------|--------|---------|--------|---|
| Follower/member reach | followers | mutual_servers | karma | followers |
| Content volume | public_repos | — | total_posts | tweet_count |
| Has org/company | company field | server roles | flair | bio |

#### Engagement Score — Generalized

| Signal | Description |
|--------|-------------|
| Recency ratio | (activity in last 3 months) / (total activity) |
| Interaction depth | Replies, reviews, threads vs. drive-by posts |
| Multi-source presence | Member appears in multiple community sources within the project |

### 5. Database Changes

#### `projects` table additions

| Column | Type | Notes |
|--------|------|-------|
| `classification_labels` | JSONB | Array of `{key, label, description}` or NULL for defaults |
| `scoring_weights` | JSONB | `{position, activity, influence, engagement}` or NULL for defaults |

#### `social_context` table changes

| Column | Change |
|--------|--------|
| `classification` | No longer constrained to 3 values — stores whatever key the project defines |

### 6. Schema Changes (backend/schemas.py)

```python
class ClassificationLabel(BaseModel):
    key: str = Field(..., pattern="^[A-Z_]+$", max_length=50)
    label: str = Field(..., max_length=100)
    description: str = Field(..., max_length=500)

class ScoringWeights(BaseModel):
    position: float = Field(0.35, ge=0, le=1)
    activity: float = Field(0.25, ge=0, le=1)
    influence: float = Field(0.20, ge=0, le=1)
    engagement: float = Field(0.20, ge=0, le=1)

    @validator('engagement')
    def weights_must_sum_to_one(cls, v, values):
        total = values.get('position', 0) + values.get('activity', 0) + values.get('influence', 0) + v
        if abs(total - 1.0) > 0.01:
            raise ValueError('Scoring weights must sum to 1.0')
        return v

class ProjectCreate(ProjectBase):
    classification_labels: list[ClassificationLabel] | None = None
    scoring_weights: ScoringWeights | None = None

class ProjectUpdate(BaseModel):
    # ... existing fields ...
    classification_labels: list[ClassificationLabel] | None = None
    scoring_weights: ScoringWeights | None = None
```

### 7. Frontend Changes

#### Project Create/Edit Modal

New sections:

1. **Classification Labels** — editable list with key, label, description per row. "Reset to defaults" button.
2. **Scoring Weights** — 4 sliders that auto-balance to 1.0.
3. **Sourcing Context** — enhanced with a hint: "Describe what you're looking for. This text is used to guide AI classification of community members."

#### Leads Page

- Classification badge colors dynamically mapped from label keys (hash-based color or user picks color)
- Filter dropdown populated from `project.classification_labels` instead of hard-coded 3 values
- Dashboard stats use dynamic label names

#### Dashboard

- Classification breakdown chart labels come from the project's labels, not hard-coded

### 8. Rule-Based Fallback

The `_rule_based_classification` fallback in `enrichment_service.py` currently hard-codes position title matching. With dynamic labels, the fallback becomes:

1. If project has only default labels → use existing rule-based logic
2. If project has custom labels → skip rule-based, require LLM (or return the first label with low confidence as a best-effort)

### 9. Re-Classification

When a user updates `classification_labels` or `sourcing_context`, they should be able to trigger re-classification of existing members:

- New API endpoint: `POST /api/projects/{id}/reclassify`
- Creates enrichment jobs for all members in the project
- UI: "Re-classify All Members" button in project settings with a confirm dialog

## Migration

- Add `classification_labels` and `scoring_weights` columns to `projects` (nullable JSONB, NULL = use defaults)
- No data migration needed — existing classifications remain valid; they match the default labels
- Existing scoring weights continue to work (code falls back to defaults when NULL)

## Success Criteria

- Users can define custom classification labels per project
- Sourcing context is used as the LLM prompt for classification
- Scoring weights are configurable per project
- All existing projects continue to work identically (defaults match current behavior)
- Re-classification works when labels or context change
- Works across all community source types (not just GitHub)
