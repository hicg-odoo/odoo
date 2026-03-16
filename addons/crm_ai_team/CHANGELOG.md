# CRM AI Agent Team - Changelog

## Version 2.0.0 - Major Update

### Summary

This release transforms the CRM AI Team addon into a truly **plug-and-play AI CRM platform** with:

- **LLM Provider Configuration**: Full support for OpenAI, Anthropic, Google AI, Azure OpenAI, and local models
- **CRM Decoupling**: Works without CRM module installed - optional integration when CRM is available
- **Vector Embeddings**: Foundation for semantic search and RAG implementations
- **Configurable Signal Rules**: No more hardcoded logic - customize rules via UI
- **Enhanced MCP Server**: Pagination, error handling, resources, and prompts

---

## Breaking Changes

### Model Field Changes

| Model | Old Field | New Field | Notes |
|-------|-----------|-----------|-------|
| `crm.ai.conversation.summary` | `opportunity_id` (Many2one) | `opportunity_ref` (Reference) | CRM decoupling - works without CRM module |
| `crm.ai.meeting.transcript` | `opportunity_id` (Many2one) | `opportunity_ref` (Reference) | CRM decoupling |
| `crm.ai.relationship.signal` | `lead_id` (Many2one) | `lead_ref` (Reference) | CRM decoupling |

**Migration Notes:**
- Legacy `opportunity_id` and `lead_id` fields are maintained as computed fields for backward compatibility
- New code should use `opportunity_ref` and `lead_ref` fields

### New Models

| Model | Description |
|-------|-------------|
| `crm.ai.signal.rule` | Configurable signal generation rules |

---

## New Features

### 1. LLM Provider Configuration

Teams and agents can now configure which LLM provider to use:

**Team-level settings:**
- `llm_provider`: openai, anthropic, google, azure, local, none
- `llm_model`: Model name (e.g., gpt-4, claude-3-opus)
- `llm_api_endpoint`: Custom API endpoint
- `llm_temperature`: Sampling temperature (0.0-2.0)
- `llm_max_tokens`: Maximum response tokens
- `llm_system_prompt`: Team-wide system prompt

**Agent-level overrides:**
- `llm_provider`: Can override team setting or inherit
- `llm_model`, `llm_temperature`, `llm_max_tokens`: Per-agent overrides
- `system_prompt`: Agent-specific prompts with placeholders
- `response_format`: text, json, markdown
- `tool_definitions`: JSON tool schemas for function calling

### 2. Vector Embeddings

Conversation summaries now support embedding storage:

- `embedding_vector`: Binary storage for embedding vectors
- `embedding_model`: Model used (e.g., text-embedding-3-small)
- `embedding_dimension`: Vector dimension (e.g., 1536)
- `embedding_timestamp`: When embedding was generated

### 3. AI Processing Metadata

Track AI enhancement on summaries:

- `ai_processed`: Whether AI has enhanced the summary
- `ai_model_version`: Version of AI model used

### 4. Signal Lifecycle Management

Signals now have a complete lifecycle:

**States:**
- `new` → `acknowledged` → `in_progress` → `resolved`
- Can be `dismissed` from any early state

**New fields:**
- `state`: Signal lifecycle state
- `resolution_notes`: Notes when resolving

### 5. Configurable Signal Rules

Replace hardcoded signal generation with configurable rules:

**Rule fields:**
- `condition_sentiment`: Filter by sentiment
- `condition_theme_ids`: Filter by themes (OR logic)
- `condition_agent_role`: Filter by agent role
- `condition_expression`: Custom Python expression
- `action_signal_type`: Type of signal to create
- `action_priority`: Priority level
- `action_confidence`: Confidence score
- `action_recommendation`: Template with placeholders

### 6. mail.thread Inheritance

All models now inherit from `mail.thread` for full chatter support:

| Model | Inheritance |
|-------|-------------|
| `crm.ai.agent.team` | mail.thread, mail.activity.mixin |
| `crm.ai.agent` | mail.thread, mail.activity.mixin |
| `crm.ai.theme` | mail.thread |
| `crm.ai.conversation.summary` | mail.thread, mail.activity.mixin (existing) |
| `crm.ai.meeting.transcript` | mail.thread, mail.activity.mixin (existing) |
| `crm.ai.relationship.signal` | mail.thread, mail.activity.mixin |
| `crm.ai.signal.rule` | mail.thread |
| `crm.ai.agent.run` | mail.thread |

### 7. MCP Server Enhancements

**New features:**
- **Pagination**: All list tools now support `limit` and `offset` with `total` and `has_more`
- **Error handling**: Sanitized errors with custom exception classes
- **Resources**: Model discovery, health checks, field introspection
- **Prompts**: Pre-built prompt templates for common tasks
- **New tools**: `list_signal_rules`, `get_agent_team_config`, `get_agent_config`

**New resources:**
- `odoo://health` - Health and connection status
- `odoo://models` - List all AI CRM models
- `odoo://{model}/fields` - Field definitions for a model
- `odoo://{model}/record/{id}` - Read a specific record
- `odoo://signal-types` - Available signal types
- `odoo://sentiment-options` - Available sentiment classifications

**New prompts:**
- `analyze_customer_relationship` - Analyze relationship from summary
- `configure_agent_team` - Configure team LLM settings

---

## Model Changes Detail

### CrmAiAgentTeam

**New fields:**
- `llm_provider` (Selection): LLM provider selection
- `llm_model` (Char): Model name
- `llm_api_endpoint` (Char): Custom API endpoint
- `llm_temperature` (Float): Sampling temperature
- `llm_max_tokens` (Integer): Maximum response tokens
- `llm_system_prompt` (Text): Team-wide system prompt

**New inheritance:**
- `mail.thread`, `mail.activity.mixin`

### CrmAiAgent

**New fields:**
- `llm_provider` (Selection): Override or inherit from team
- `llm_model` (Char): Override model name
- `llm_temperature` (Float): Override temperature
- `llm_max_tokens` (Integer): Override max tokens
- `system_prompt` (Text): Agent-specific prompt
- `response_format` (Selection): text, json, markdown
- `tool_definitions` (Text): JSON tool schemas

**New inheritance:**
- `mail.thread`, `mail.activity.mixin`

### CrmAiTheme

**New fields:**
- `priority_weight` (Float): Weight for signal priority calculation

**New inheritance:**
- `mail.thread`

### CrmAiConversationSummary

**New fields:**
- `opportunity_ref` (Reference): CRM-agnostic opportunity reference
- `embedding_vector` (Binary): Embedding vector storage
- `embedding_model` (Char): Model used for embeddings
- `embedding_dimension` (Integer): Vector dimension
- `embedding_timestamp` (Datetime): When embedding was generated
- `ai_processed` (Boolean): AI enhancement flag
- `ai_model_version` (Char): AI model version used

**Computed fields (backward compatibility):**
- `opportunity_id` (Many2one): Computed from `opportunity_ref`

**New methods:**
- `action_generate_embedding()`: Trigger embedding generation
- `action_reprocess_with_ai()`: Reprocess with AI

### CrmAiMeetingTranscript

**New fields:**
- `opportunity_ref` (Reference): CRM-agnostic opportunity reference
- `embedding_vector` (Binary): Embedding vector for transcript

**Computed fields (backward compatibility):**
- `opportunity_id` (Many2one): Computed from `opportunity_ref`

### CrmAiRelationshipSignal

**New fields:**
- `lead_ref` (Reference): CRM-agnostic lead reference
- `state` (Selection): Signal lifecycle state
- `resolution_notes` (Text): Resolution notes

**Computed fields (backward compatibility):**
- `lead_id` (Many2one): Computed from `lead_ref`

**New methods:**
- `action_acknowledge()`: Acknowledge signal
- `action_start_progress()`: Start working on signal
- `action_resolve()`: Mark as resolved
- `action_dismiss()`: Dismiss signal

**New inheritance:**
- `mail.thread`, `mail.activity.mixin`

### CrmAiAgentRun

**New inheritance:**
- `mail.thread`

### CrmAiAgentRunLog

**New fields:**
- `extra_data` (Text): Additional structured data in JSON

### CrmAiSignalRule (New Model)

Configurable signal generation rules:

- `name` (Char): Rule name
- `active` (Boolean): Active status
- `sequence` (Integer): Execution order
- `description` (Text): Description
- `condition_sentiment` (Selection): Sentiment filter
- `condition_theme_ids` (Many2many): Theme filter
- `condition_agent_role` (Selection): Agent role filter
- `condition_expression` (Text): Custom Python expression
- `action_signal_type` (Selection): Signal type to create
- `action_priority` (Selection): Priority level
- `action_confidence` (Float): Confidence score
- `action_recommendation` (Text): Recommendation template

---

## CRM Decoupling

The addon now works **without the CRM module installed**:

1. **Opportunity references** use Reference fields that work with any model
2. **create_dummy_dataset** checks if CRM is installed before creating opportunities
3. **Views** handle both CRM and non-CRM scenarios
4. **Menu** is parented under CRM menu but gracefully handles CRM absence

### How it works:

```python
# Old (CRM-dependent)
opportunity_id = fields.Many2one('crm.lead')

# New (CRM-agnostic)
opportunity_ref = fields.Reference(
    selection='_get_opportunity_models',
    help='Works with CRM or other sales modules'
)

@api.model
def _get_opportunity_models(self):
    models = []
    if self.env.registry.get('crm.lead') is not None:
        models.append(('crm.lead', 'CRM Opportunity'))
    return models
```

---

## Migration Guide

### From v1.0 to v2.0

1. **Update module**: Standard Odoo module update
2. **No data migration needed**: Legacy fields are computed from new Reference fields
3. **Update custom code**: Use `opportunity_ref` and `lead_ref` instead of `opportunity_id` and `lead_id`
4. **Configure signal rules**: Create rules in UI to replace hardcoded logic

### Recommended post-update steps:

1. Configure LLM providers for teams
2. Create signal rules to replace hardcoded logic
3. Review and update any custom integrations

---

## File Changes

| File | Changes |
|------|---------|
| `models/crm_ai_team.py` | Complete rewrite with new models and fields |
| `tools/mcp_server.py` | Enhanced with pagination, resources, prompts |
| `views/crm_ai_team_views.xml` | Updated views for new fields |
| `security/ir.model.access.csv` | Added signal rule access |
| `tests/test_agent_loops.py` | New tests for LLM config, embeddings, rules |
| `MCP_SERVER_DOCUMENTATION.md` | Updated with new tools and features |
| `CHANGELOG.md` | This file |

---

## Upgrade Path

1. Backup database
2. Stop Odoo services
3. Update module files
4. Start Odoo
5. Update module in Apps
6. Verify functionality

---

## Support

For issues or questions:
- Check MCP_SERVER_DOCUMENTATION.md for MCP server details
- Review tests in `tests/test_agent_loops.py` for usage examples
- Consult README.rst for general module information
