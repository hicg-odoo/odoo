# MCP Server Documentation for CRM AI Team

## Overview

The CRM AI Team addon includes a lightweight **Model Context Protocol (MCP) server** that exposes Odoo models and operations to external AI systems via XML-RPC. This enables AI agents, chatbots, and automation tools to interact with customer relationship data programmatically.

**Location:** `addons/crm_ai_team/tools/mcp_server.py`

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Server Configuration](#server-configuration)
3. [Running the Server](#running-the-server)
4. [Available Tools](#available-tools)
5. [Data Models](#data-models)
6. [Usage Examples](#usage-examples)
7. [Error Handling](#error-handling)
8. [Security Considerations](#security-considerations)

---

## Prerequisites

### Required Python Package

```bash
pip install mcp
```

The MCP server uses `mcp.server.fastmcp.FastMCP` for tool registration and execution.

### Odoo Requirements

- Odoo instance running with XML-RPC enabled
- `crm_ai_team` module installed and configured
- Valid Odoo user credentials with appropriate access rights

---

## Server Configuration

The MCP server requires the following environment variables:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ODOO_URL` | No | `http://localhost:8069` | Base URL of the Odoo instance |
| `ODOO_DB` | Yes | - | Database name |
| `ODOO_USERNAME` | Yes | - | Odoo username for authentication |
| `ODOO_PASSWORD` | Yes | - | User password or API key |

---

## Running the Server

### Basic Execution

```bash
ODOO_URL=http://localhost:8069 \
ODOO_DB=mydb \
ODOO_USERNAME=admin \
ODOO_PASSWORD=admin \
python3 addons/crm_ai_team/tools/mcp_server.py
```

### Using Docker (Recommended for Production)

The `deploy/` directory contains a complete containerized setup:

```bash
cd addons/crm_ai_team/deploy
./deploy.sh up-mcp
```

For Windows PowerShell:

```powershell
cd addons/crm_ai_team/deploy
.\deploy.ps1 up-mcp
```

---

## Available Tools

### 1. `list_conversation_summaries`

List recent AI conversation summaries.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `limit` | `int` | No | 20 | Maximum number of records (1-100) |

**Returns:** `list[dict]` - List of conversation summary records

**Fields Returned:**
- `name` - Summary title
- `conversation_datetime` - Date/time of conversation
- `sentiment` - Sentiment classification
- `partner_id` - Related customer
- `opportunity_id` - Linked sales opportunity

**Example:**

```python
# Tool call
list_conversation_summaries(limit=10)

# Response
[
    {
        "id": 1,
        "name": "Q4 Renewal Discussion",
        "conversation_datetime": "2024-01-15 14:30:00",
        "sentiment": "positive",
        "partner_id": [42, "Acme Corp"],
        "opportunity_id": [15, "Enterprise License Renewal"]
    },
    ...
]
```

---

### 2. `create_conversation_summary`

Create a new conversation summary record.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `title` | `str` | Yes | - | Summary title |
| `summary` | `str` | Yes | - | Conversation summary text |
| `sentiment` | `str` | No | `"neutral"` | Sentiment: `very_negative`, `negative`, `neutral`, `positive`, `very_positive` |
| `partner_id` | `int` | No | `None` | Customer partner ID |
| `team_id` | `int` | No | `None` | AI agent team ID |
| `agent_id` | `int` | No | `None` | Primary agent ID |
| `opportunity_id` | `int` | No | `None` | Related opportunity ID |
| `key_points` | `str` | No | `None` | Structured key takeaways |

**Returns:** `dict` - Created record with ID and details

**Example:**

```python
create_conversation_summary(
    title="Product Demo Follow-up",
    summary="Customer showed strong interest in the enterprise tier features...",
    sentiment="positive",
    partner_id=42,
    opportunity_id=15,
    key_points="- Interested in SSO integration\n- Budget approved for Q2\n- Decision maker: CTO"
)

# Response
{
    "id": 25,
    "record": {
        "id": 25,
        "name": "Product Demo Follow-up",
        "conversation_datetime": "2024-01-20 10:15:00",
        "sentiment": "positive",
        "partner_id": [42, "Acme Corp"],
        "opportunity_id": [15, "Enterprise License Renewal"]
    }
}
```

---

### 3. `create_relationship_signal`

Create a relationship signal for cross-sell, upsell, renewal, or churn risk workflows.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `summary_id` | `int` | Yes | - | Parent conversation summary ID |
| `signal_type` | `str` | Yes | - | Type: `cross_sell`, `upsell`, `renewal`, `churn_risk` |
| `recommendation` | `str` | Yes | - | Actionable recommendation text |
| `priority` | `str` | No | `"medium"` | Priority: `low`, `medium`, `high` |
| `confidence` | `float` | No | `0.5` | Confidence score (0.0-1.0) |
| `lead_id` | `int` | No | `None` | Related CRM lead/opportunity ID |
| `owner_id` | `int` | No | `None` | Assigned owner user ID |

**Returns:** `dict` - Created signal record

**Example:**

```python
create_relationship_signal(
    summary_id=25,
    signal_type="upsell",
    recommendation="Propose enterprise tier upgrade with SSO feature",
    priority="high",
    confidence=0.85,
    lead_id=15
)

# Response
{
    "id": 12,
    "record": {
        "id": 12,
        "summary_id": [25, "Product Demo Follow-up"],
        "signal_type": "upsell",
        "priority": "high",
        "confidence": 0.85,
        "lead_id": [15, "Enterprise License Renewal"],
        "owner_id": [3, "John Sales"]
    }
}
```

---

### 4. `list_sales_opportunities`

List CRM opportunities available for linking to AI outputs.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `partner_id` | `int` | No | `None` | Filter by customer partner ID |
| `limit` | `int` | No | 20 | Maximum records (1-100) |

**Returns:** `list[dict]` - List of opportunity records

**Fields Returned:**
- `name` - Opportunity name
- `partner_id` - Customer
- `stage_id` - Current pipeline stage
- `probability` - Win probability percentage
- `expected_revenue` - Expected revenue amount

**Example:**

```python
list_sales_opportunities(partner_id=42, limit=5)

# Response
[
    {
        "id": 15,
        "name": "Enterprise License Renewal",
        "partner_id": [42, "Acme Corp"],
        "stage_id": [4, "Negotiation"],
        "probability": 65.0,
        "expected_revenue": 50000.0
    }
]
```

---

### 5. `run_agent_team`

Execute the team orchestration pipeline on pending conversation summaries.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `team_id` | `int` | Yes | - | AI agent team ID to run |

**Returns:** `dict` - Execution result with run details

**Example:**

```python
run_agent_team(team_id=1)

# Response
{
    "team_id": 1,
    "run": {
        "id": 8,
        "name": "Sales AI Team / 2024-01-20 15:30:00",
        "team_id": [1, "Sales AI Team"],
        "status": "success",
        "start_datetime": "2024-01-20 15:30:00",
        "end_datetime": "2024-01-20 15:30:45",
        "processed_summary_count": 5,
        "success_step_count": 25,
        "failed_step_count": 0,
        "duration_seconds": 45.0
    }
}
```

**Status Values:**
- `success` - All agent steps completed successfully
- `partial` - Some steps failed, others succeeded
- `failed` - All steps failed

---

### 6. `get_observability_snapshot`

Retrieve observability metrics for agent runs and logs.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `team_id` | `int` | No | `None` | Filter by specific team (all teams if None) |

**Returns:** `dict` - Aggregated metrics and recent runs

**Example:**

```python
get_observability_snapshot(team_id=1)

# Response
{
    "team_id": 1,
    "run_count": 15,
    "failed_run_count": 2,
    "partial_run_count": 3,
    "error_log_count": 8,
    "latest_runs": [
        {
            "id": 15,
            "name": "Sales AI Team / 2024-01-20 15:30:00",
            "team_id": [1, "Sales AI Team"],
            "status": "success",
            "processed_summary_count": 5,
            "failed_step_count": 0
        },
        ...
    ]
}
```

---

### 7. `ingest_meeting_transcript`

Import a meeting transcript from Zoom, Teams, Meet, or other providers.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `title` | `str` | Yes | - | Meeting title |
| `provider` | `str` | Yes | - | Provider: `zoom`, `microsoft_teams`, `google_meet`, `other` |
| `transcript_text` | `str` | Yes | - | Raw transcript content |
| `external_ref` | `str` | No | `None` | Provider's meeting identifier |
| `partner_id` | `int` | No | `None` | Customer partner ID |
| `team_id` | `int` | No | `None` | AI agent team ID |
| `opportunity_id` | `int` | No | `None` | Related opportunity ID |
| `language` | `str` | No | `"en"` | Language code |
| `auto_process` | `bool` | No | `True` | Automatically process to summary |

**Returns:** `dict` - Created transcript record with processing status

**Example:**

```python
ingest_meeting_transcript(
    title="Q4 Strategy Review",
    provider="zoom",
    transcript_text="John: Let's discuss the renewal...\nJane: We're interested in expanding...",
    external_ref="zoom-meeting-12345",
    partner_id=42,
    auto_process=True
)

# Response
{
    "id": 30,
    "record": {
        "id": 30,
        "name": "Q4 Strategy Review",
        "provider": "zoom",
        "external_ref": "zoom-meeting-12345",
        "ingest_status": "processed",
        "summary_id": [45, "Q4 Strategy Review"]
    }
}
```

**Ingest Status Values:**
- `new` - Transcript imported, not yet processed
- `processed` - Successfully converted to summary
- `failed` - Processing encountered an error

---

### 8. `list_meeting_transcripts`

List imported meeting transcripts.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `provider` | `str` | No | `None` | Filter by provider |
| `ingest_status` | `str` | No | `None` | Filter by status: `new`, `processed`, `failed` |
| `limit` | `int` | No | 20 | Maximum records (1-100) |

**Returns:** `list[dict]` - List of transcript records

**Example:**

```python
list_meeting_transcripts(provider="zoom", ingest_status="processed", limit=10)

# Response
[
    {
        "id": 30,
        "name": "Q4 Strategy Review",
        "meeting_datetime": "2024-01-20 14:00:00",
        "provider": "zoom",
        "external_ref": "zoom-meeting-12345",
        "ingest_status": "processed",
        "summary_id": [45, "Q4 Strategy Review"]
    }
]
```

---

### 9. `create_dummy_dataset`

Generate programmatic demo data for testing and demonstrations.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `team_name` | `str` | No | `"AI Demo Team"` | Name for the demo team |
| `agent_count` | `int` | No | 5 | Number of agents to create (1-25) |
| `transcript_count` | `int` | No | 20 | Number of transcripts to create (1-200) |
| `auto_run` | `bool` | No | `True` | Automatically execute team pipeline |

**Returns:** `dict` - Summary of created records

**Example:**

```python
create_dummy_dataset(
    team_name="Demo Team Alpha",
    agent_count=4,
    transcript_count=10,
    auto_run=True
)

# Response
{
    "team_id": 5,
    "agent_count": 4,
    "transcript_count": 10,
    "summary_count": 10,
    "run_count": 1
}
```

---

## Data Models

### Model Relationship Diagram

```
┌─────────────────────┐
│ crm.ai.agent.team   │
│─────────────────────│
│ name                │
│ active              │
│ run_count           │ (computed)
│ last_run_date       │ (computed)
│ last_run_status     │ (computed)
└─────────┬───────────┘
          │
          │ 1:N
          ▼
┌─────────────────────┐     ┌─────────────────────┐
│ crm.ai.agent        │     │ crm.ai.agent.run    │
│─────────────────────│     │─────────────────────│
│ name                │     │ name                │
│ team_id (FK)        │     │ team_id (FK)        │
│ role                │     │ status              │
│ instruction         │     │ start_datetime      │
│ active              │     │ end_datetime        │
└─────────────────────┘     │ duration_seconds    │
                            │ processed_summary   │
                            │ success_step_count  │
                            │ failed_step_count   │
                            └─────────┬───────────┘
                                      │
                                      │ 1:N
                                      ▼
                            ┌─────────────────────┐
                            │ crm.ai.agent.run.log│
                            │─────────────────────│
                            │ run_id (FK)         │
                            │ team_id (FK)        │
                            │ summary_id (FK)     │
                            │ agent_id (FK)       │
                            │ log_level           │
                            │ message             │
                            └─────────────────────┘

┌─────────────────────────┐
│ crm.ai.meeting.transcript│
│─────────────────────────│
│ name                    │
│ provider                │
│ external_ref            │
│ meeting_datetime        │
│ partner_id (FK)         │
│ team_id (FK)            │
│ opportunity_id (FK)     │
│ raw_transcript          │
│ language                │
│ ingest_status           │
│ processing_error        │
│ summary_id (FK)         │──┐
└─────────────────────────┘  │
                             │ 1:1
                             ▼
┌─────────────────────────────┐
│ crm.ai.conversation.summary │
│─────────────────────────────│
│ name                        │
│ conversation_datetime       │
│ team_id (FK)                │
│ agent_id (FK)               │
│ partner_id (FK)             │
│ sentiment                   │
│ summary                     │
│ key_points                  │
│ theme_ids (M2M)             │
│ opportunity_id (FK)         │
│ case_ref (Reference)        │
│ transcript_id (FK)          │
│ processed                   │
└─────────┬───────────────────┘
          │
          │ 1:N
          ▼
┌─────────────────────────────┐
│ crm.ai.relationship.signal  │
│─────────────────────────────│
│ summary_id (FK)             │
│ partner_id (related)        │
│ signal_type                 │
│ confidence                  │
│ priority                    │
│ recommendation              │
│ owner_id (FK)               │
│ lead_id (FK)                │
│ case_ref (Reference)        │
└─────────────────────────────┘
```

### Model Details

#### `crm.ai.agent.team`

AI Agent Team configuration.

| Field | Type | Description |
|-------|------|-------------|
| `name` | `Char` | Team name (required) |
| `active` | `Boolean` | Active status (default: True) |
| `member_ids` | `One2many` | Team member agents |
| `summary_ids` | `One2many` | Associated conversation summaries |
| `run_ids` | `One2many` | Pipeline execution records |
| `run_count` | `Integer` | Total runs (computed) |
| `last_run_date` | `Datetime` | Most recent run timestamp (computed) |
| `last_run_status` | `Selection` | Most recent run status (computed) |

**Actions:**
- `action_run_agent_team()` - Execute team pipeline on pending summaries

---

#### `crm.ai.agent`

AI Agent profile with role and instructions.

| Field | Type | Description |
|-------|------|-------------|
| `name` | `Char` | Agent name (required) |
| `active` | `Boolean` | Active status (default: True) |
| `team_id` | `Many2one` | Parent team (required, cascade delete) |
| `role` | `Selection` | Agent role (required) |
| `instruction` | `Text` | Prompt/policy for orchestration |

**Role Options:**
- `relationship_manager` - Relationship Manager (default)
- `sales_specialist` - Sales Specialist
- `renewal_specialist` - Renewal Specialist
- `support_specialist` - Support Specialist
- `risk_analyst` - Risk Analyst

---

#### `crm.ai.theme`

Conversation theme classification.

| Field | Type | Description |
|-------|------|-------------|
| `name` | `Char` | Display name (required) |
| `code` | `Selection` | Theme code (required) |
| `description` | `Text` | Detailed description |

**Theme Codes:**
- `cross_sell` - Cross-sell opportunity
- `upsell` - Upsell opportunity
- `renewal` - Renewal action
- `churn_risk` - Churn risk indicator
- `support_case` - Support case
- `product_feedback` - Product feedback
- `general` - General (default)

---

#### `crm.ai.conversation.summary`

AI-processed conversation summary.

| Field | Type | Description |
|-------|------|-------------|
| `name` | `Char` | Summary title (required) |
| `conversation_datetime` | `Datetime` | Conversation timestamp (required) |
| `team_id` | `Many2one` | AI agent team |
| `agent_id` | `Many2one` | Primary agent |
| `partner_id` | `Many2one` | Customer |
| `sentiment` | `Selection` | Sentiment classification (required) |
| `summary` | `Text` | Summary text (required) |
| `key_points` | `Text` | Structured key takeaways |
| `theme_ids` | `Many2many` | Associated themes |
| `opportunity_id` | `Many2one` | Linked CRM opportunity |
| `case_ref` | `Reference` | Optional case/ticket link |
| `transcript_id` | `Many2one` | Source transcript |
| `processed` | `Boolean` | Pipeline processed flag |

**Sentiment Options:**
- `very_negative` - Very Negative
- `negative` - Negative
- `neutral` - Neutral (default)
- `positive` - Positive
- `very_positive` - Very Positive

---

#### `crm.ai.agent.run`

Pipeline execution record.

| Field | Type | Description |
|-------|------|-------------|
| `name` | `Char` | Run identifier (required) |
| `team_id` | `Many2one` | Team (required, cascade delete) |
| `start_datetime` | `Datetime` | Start timestamp (required) |
| `end_datetime` | `Datetime` | End timestamp |
| `status` | `Selection` | Execution status (required) |
| `processed_summary_count` | `Integer` | Summaries processed |
| `success_step_count` | `Integer` | Successful agent steps |
| `failed_step_count` | `Integer` | Failed agent steps |
| `duration_seconds` | `Float` | Total duration (computed) |
| `log_ids` | `One2many` | Detailed run logs |

**Status Options:**
- `success` - Success (default)
- `partial` - Partial
- `failed` - Failed

---

#### `crm.ai.agent.run.log`

Detailed step execution log.

| Field | Type | Description |
|-------|------|-------------|
| `run_id` | `Many2one` | Parent run (required, cascade delete) |
| `team_id` | `Many2one` | Team (related) |
| `summary_id` | `Many2one` | Processed summary |
| `agent_id` | `Many2one` | Executing agent |
| `log_level` | `Selection` | Log severity (required) |
| `message` | `Text` | Log message (required) |

**Log Level Options:**
- `debug` - Debug
- `info` - Info (default)
- `warning` - Warning
- `error` - Error

---

#### `crm.ai.meeting.transcript`

Imported meeting transcript.

| Field | Type | Description |
|-------|------|-------------|
| `name` | `Char` | Meeting title (required) |
| `provider` | `Selection` | Source provider (required) |
| `external_ref` | `Char` | Provider meeting ID |
| `meeting_datetime` | `Datetime` | Meeting timestamp (required) |
| `partner_id` | `Many2one` | Customer |
| `team_id` | `Many2one` | AI agent team |
| `opportunity_id` | `Many2one` | Related opportunity |
| `raw_transcript` | `Text` | Raw transcript text (required) |
| `language` | `Char` | Language code (default: "en") |
| `ingest_status` | `Selection` | Processing status (required) |
| `processing_error` | `Text` | Error message if failed |
| `summary_id` | `Many2one` | Generated summary (readonly) |

**Provider Options:**
- `zoom` - Zoom
- `microsoft_teams` - Microsoft Teams
- `google_meet` - Google Meet
- `other` - Other (default)

**SQL Constraint:**
- `provider_external_ref_uniq` - Unique combination of provider and external_ref

**Actions:**
- `action_process_transcript()` - Process transcript to summary

---

#### `crm.ai.relationship.signal`

Actionable signal from AI analysis.

| Field | Type | Description |
|-------|------|-------------|
| `summary_id` | `Many2one` | Source summary (required, cascade delete) |
| `partner_id` | `Many2one` | Customer (related) |
| `signal_type` | `Selection` | Signal type (required) |
| `confidence` | `Float` | Confidence score (0.0-1.0) |
| `priority` | `Selection` | Priority level (required) |
| `recommendation` | `Text` | Actionable recommendation (required) |
| `owner_id` | `Many2one` | Assigned user |
| `lead_id` | `Many2one` | Related opportunity |
| `case_ref` | `Reference` | Related case/ticket |

**Signal Type Options:**
- `cross_sell` - Cross-sell Opportunity
- `upsell` - Upsell Opportunity
- `renewal` - Renewal Action
- `churn_risk` - Churn Risk

**Priority Options:**
- `low` - Low
- `medium` - Medium (default)
- `high` - High

---

## Usage Examples

### Complete Workflow: Meeting to Signal

```python
# 1. Import meeting transcript
result = ingest_meeting_transcript(
    title="Q4 Renewal Discussion",
    provider="zoom",
    transcript_text="""
    John (Customer): We've been happy with the platform but noticed some downtime last month.
    Jane (Account Manager): I apologize for that. Let me look into the incident reports.
    John: We're considering our renewal options. The Enterprise tier looks interesting.
    Jane: Great! The Enterprise tier includes 99.99% SLA and dedicated support.
    John: That would address our concerns. Can we get a quote?
    """,
    partner_id=42,
    team_id=1,
    opportunity_id=15,
    auto_process=True
)

# 2. Check the generated summary
summaries = list_conversation_summaries(limit=1)
summary = summaries[0]
# summary["sentiment"] might be "positive" (interested in upgrade)
# summary["theme_ids"] might include "renewal", "upsell"

# 3. Run the agent team pipeline
run_result = run_agent_team(team_id=1)
# Agents will analyze sentiment/themes and create appropriate signals

# 4. Check observability
metrics = get_observability_snapshot(team_id=1)
print(f"Total runs: {metrics['run_count']}")
print(f"Failed runs: {metrics['failed_run_count']}")
```

### Manual Signal Creation

```python
# Create a high-priority churn risk signal
create_relationship_signal(
    summary_id=25,
    signal_type="churn_risk",
    recommendation="Escalate to Customer Success manager. Schedule executive check-in within 48 hours.",
    priority="high",
    confidence=0.92,
    lead_id=15,
    owner_id=5
)
```

### Batch Transcript Import

```python
transcripts = [
    {"title": "Sales Call - Acme", "provider": "zoom", "text": "...", "partner_id": 42},
    {"title": "Support Escalation", "provider": "microsoft_teams", "text": "...", "partner_id": 43},
    {"title": "Renewal Prep", "provider": "google_meet", "text": "...", "partner_id": 44},
]

for t in transcripts:
    ingest_meeting_transcript(
        title=t["title"],
        provider=t["provider"],
        transcript_text=t["text"],
        partner_id=t["partner_id"],
        team_id=1,
        auto_process=True
    )
```

---

## Error Handling

### Authentication Errors

```
ValueError: Failed to authenticate to Odoo. Check ODOO_* credentials.
```

**Solution:** Verify `ODOO_DB`, `ODOO_USERNAME`, and `ODOO_PASSWORD` environment variables.

### Model Access Errors

If the Odoo user lacks permissions, XML-RPC calls will return access errors.

**Solution:** Ensure the user belongs to `base.group_user` or has custom access rights configured in `security/ir.model.access.csv`.

### Transcript Processing Errors

When `ingest_meeting_transcript` with `auto_process=True` fails, check:

```python
result = list_meeting_transcripts(ingest_status="failed")
for t in result:
    print(f"Transcript {t['id']}: {t.get('processing_error')}")
```

---

## Security Considerations

### Authentication

- The MCP server authenticates to Odoo via XML-RPC using username/password
- Consider using API keys instead of passwords for production
- Store credentials in environment variables, never in code

### Network Security

- XML-RPC communicates over HTTP; use HTTPS in production
- Consider VPN or private network for MCP server communication
- The Docker deployment isolates the MCP server in a separate container

### Access Control

- All models have full CRUD access for `base.group_user`
- Extend with custom groups for finer-grained control
- The MCP server operates with the permissions of the configured Odoo user

### Data Privacy

- Meeting transcripts may contain sensitive customer information
- Implement appropriate data retention policies
- Consider encryption for transcript storage

---

## Integration with External AI Systems

### Using with Claude Desktop

Add to Claude Desktop configuration:

```json
{
  "mcpServers": {
    "crm-ai-team": {
      "command": "python",
      "args": ["addons/crm_ai_team/tools/mcp_server.py"],
      "env": {
        "ODOO_URL": "http://localhost:8069",
        "ODOO_DB": "mydb",
        "ODOO_USERNAME": "api_user",
        "ODOO_PASSWORD": "api_key_or_password"
      }
    }
  }
}
```

### Using with Custom AI Agents

The MCP server implements the standard MCP protocol. Any MCP-compatible client can connect:

```python
from mcp import Client

client = Client("crm-ai-team")
tools = await client.list_tools()

# Call tools
result = await client.call_tool("list_conversation_summaries", {"limit": 10})
```

---

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Connection refused | Odoo not running | Start Odoo or check `ODOO_URL` |
| Authentication failed | Invalid credentials | Check `ODOO_DB`, `ODOO_USERNAME`, `ODOO_PASSWORD` |
| Module not found | `crm_ai_team` not installed | Install module in Odoo |
| Tool returns empty | No matching records | Check filters and data existence |
| Processing failed | Transcript parsing error | Check `processing_error` field |

### Logs

View MCP server logs:

```bash
# Docker deployment
./deploy.sh logs mcp-server

# Direct execution
# Logs appear in stdout/stderr
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Initial | Core MCP server with 9 tools |

---

## License

LGPL-3 (same as parent module)
