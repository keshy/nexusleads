# Interview Loop Proposal: AI-First Engineering

## Alignment To Hiring Philosophy
This loop is designed to hire AI-first engineers who build quickly without sacrificing rigor. Each round reinforces one or more principles from the hiring philosophy: AI as an amplifier, speed with correctness, strong initial direction, systems thinking, evals and data discipline, and clear communication.

## Goals
- Test AI leverage, engineering rigor, and communication together, not separately.
- Ensure candidates can start in the right direction and build correctly under constraints.
- Validate production readiness, evaluation thinking, and system design ability.

## Roles
- HM: Hiring Manager, final decision owner.
- REC: Recruiter or coordinator, candidate experience owner.
- IL: Interview Lead or bar raiser, rubric and calibration owner.
- PI: Panel Interviewer, round owner for technical depth.
- XS: Executive Sponsor, informed on finalists only.

## RACI Definitions
- Responsible (R): Executes the round and writes the assessment.
- Accountable (A): Owns final decision quality and consistency.
- Consulted (C): Provides input or calibration where needed.
- Informed (I): Receives updates for final decision context.

## RACI Matrix By Round
| Round | Responsible | Accountable | Consulted | Informed | Primary Output |
| --- | --- | --- | --- | --- | --- |
| 1. Async Build | PI | HM | IL | REC | Code, tests, AI usage log |
| 2. Live AI Pairing | PI | HM | IL | REC | Live build changes, reasoning notes |
| 3. Production Engineering | PI | HM | IL | REC | Reliability and ops plan |
| 4. Evals and Data Quality | PI | HM | IL | REC | Eval plan, dataset design |
| 5. AI-Mediated System Design | PI | HM | IL | REC | Architecture and tradeoff notes |
| 6. Communication and Execution | PI | HM | IL | REC, XS | Narrative, risk summary |

## Loop Structure Options

### Single-Threaded Problem Across Rounds
This approach uses one product scenario that evolves over the loop.

Why it works:
- Tests start-right thinking and sustained ownership.
- Shows ability to iterate with AI while preserving quality.
- Reveals whether candidates can carry context and handle compounding constraints.

Risks:
- Early mistakes can bias later rounds.
- Interviewers may over-index on artifacts rather than reasoning.

Mitigations:
- Provide a short reset summary at the start of each round.
- Allow candidates to restate assumptions and fix early choices.
- Score each round independently on its intended signals.

Recommended use:
- Strongly recommended for rounds 1-4.
- Round 5 can reuse the same scenario for continuity or introduce a fresh design prompt if needed.
- Round 6 should summarize the same scenario for real communication signal.

### Multi-Problem Variant
Use when hiring across multiple domains or when you want to reduce compounding effects. Keep it to two scenarios max to preserve signal clarity.

## Round Details

### 1. Async Build
Focus: deliver a real feature end-to-end with AI assistance.
Why: confirms AI as an amplifier plus baseline engineering fundamentals.
Measure: correctness, test coverage, AI usage quality, and design clarity.
Observe: problem framing, edge cases, and verification discipline.
Example prompt: implement a lead ingestion flow that supports CSV upload and a Clay integration, with deduping and basic enrichment.

Core questions to ask:
- What problem are you solving and how will you validate success?
- What are the first three risks or unknowns you addressed?
- How did you use AI and where did you override it?
- What tests did you choose and why?
- What would you harden next if this went to production?
- Where did you trade off speed vs rigor and why?

### 2. Live AI Pairing
Focus: fast iteration under new constraints while explaining decisions.
Why: tests real-time AI orchestration and problem-solving under pressure.
Measure: prompt quality, error correction, speed with rigor, and tradeoff clarity.
Observe: ability to steer AI, validate outputs, and maintain composure.
Example prompt: add a new enrichment provider with rate limits, retries, and an audit trail.

Core questions to ask:
- What assumptions changed and how did you adapt?
- Show the prompt you would use and explain why.
- How do you validate that the AI output is correct?
- What are the failure modes introduced by this change?
- If you had 30 more minutes, what would you improve?
- What instrumentation would you add to confirm reliability?

### 3. Production Engineering
Focus: production readiness and operational maturity.
Why: speed alone is not enough; we need durable systems.
Measure: reliability strategy, observability plan, rate limits, security, and failure handling.
Observe: depth of systems thinking and risk prioritization.
Example prompt: add billing metering for lead enrichment calls and define SLOs, alerts, and rollback strategy.

Core questions to ask:
- Which metrics indicate this system is healthy?
- How do you handle upstream provider outages?
- What would you log and what would you avoid logging?
- What is your rollback or kill switch plan?
- How would you handle per-tenant quotas and overages?
- Where do you expect the system to break first?

### 4. Evals and Data Quality
Focus: evaluation design and data discipline for AI-dependent features.
Why: evals are first-class and required for AI products.
Measure: dataset coverage, metric design, reproducibility, and monitoring.
Observe: ability to detect hallucinations, drift, and regressions.
Example prompt: design an eval harness for lead quality scoring or company enrichment accuracy.

Core questions to ask:
- What are the ground-truth sources and how do you trust them?
- What metrics matter most and why?
- What does a high-risk false positive look like?
- How do you prevent regressions when models change?
- How will you monitor drift in production?
- What is your plan for human review and feedback loops?

### 5. AI-Mediated System Design
Focus: how candidates clarify requirements and use AI to refine design.
Why: the real signal is interpretation, not a generic design diagram.
Measure: quality of clarifying questions, architectural tradeoffs, and constraints.
Observe: ability to direct AI rather than accept generic designs.
Example prompt: design a multi-tenant integrations hub for lead data providers with data residency, SOC2, and per-tenant permissions.

Core questions to ask:
- What clarifying questions do you ask before you open AI?
- What constraints drive the architecture most?
- How do you model provider auth and token storage?
- Where do you place dedupe, scoring, and enrichment in the pipeline?
- How do you isolate tenant data and limit blast radius?
- If cost doubles, what do you change first?

### 6. Communication and Execution
Focus: technical storytelling and stakeholder alignment.
Why: communication is a technical skill and a differentiator.
Measure: clarity, concision, risk articulation, and decision rationale.
Observe: ability to switch between technical and executive contexts.
Example prompt: present a 5-minute exec summary of the integration hub plan, then a 5-minute technical deep dive.

Core questions to ask:
- What is the single most important risk and how will you manage it?
- What tradeoff did you make that you would revisit later?
- If leadership pushes for speed, what do you refuse to cut?
- How do you explain model uncertainty to a non-technical stakeholder?
- What is your rollout plan and what data would change your mind?
- What do you need from other teams to succeed?

## Scoring Rubric
- Strong Hire: exceptional AI orchestration, engineering rigor, and communication.
- Hire: clear strength in AI leverage with solid engineering fundamentals.
- Mixed: promising but missing a critical dimension or consistency.
- No Hire: weak AI leverage, poor rigor, or unclear communication.

## Notes On Candidate AI Usage
Candidates may use their preferred AI tools in all technical rounds. We require an AI usage log that captures prompts, corrections, and verification steps to evaluate AI orchestration skill.

## Appendix: Remote-First Variant

### Rationale
This loop is artifact-driven and adapts well to remote hiring. Remote execution can improve signal on AI orchestration and communication if we require structured outputs, time boxes, and standardized scoring.

### Remote Loop Structure
- Async Build: submission, AI usage log, and a 5-minute walkthrough video.
- Live AI Pairing: 45-60 minutes live with screen share.
- Production Engineering: async write-up plus a 20-minute live review.
- Evals and Data Quality: async plan plus a 20-minute live review.
- AI-Mediated System Design: 45-60 minutes live.
- Communication and Execution: 30 minutes live (exec summary plus technical deep dive).

### Remote Evidence Requirements
- AI usage log with prompts, corrections, and verification steps.
- Decision log with key tradeoffs and why they were made.
- Short walkthrough video or annotated README that explains approach and architecture.
- Clear time-boxed scope to prevent over-polish.

### Remote Scoring Adjustments
- Place higher weight on clarity of written artifacts and ability to self-correct.
- Explicitly score verification habits and evidence of validation.
- Calibrate interviewers using 2-3 example submissions to reduce bias.

### Remote Risks And Mitigations
- Risk: over-polished submissions. Mitigation: short time boxes and live follow-ups.
- Risk: weak collaboration signal. Mitigation: dedicated live pairing round.
- Risk: inconsistent scoring. Mitigation: shared rubric plus calibration examples.
