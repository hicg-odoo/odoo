# User Acceptance Testing (UAT) Plans

## Overview

This document provides comprehensive testing plans for all features in the CRM AI Team addon. Each feature includes test scenarios, expected results, and step-by-step instructions for manual verification.

---

## Table of Contents

1. [Understanding Observability](#understanding-observability)
2. [Feature 1: LLM Configuration](#feature-1-llm-configuration)
3. [Feature 2: Natural Language Queries](#feature-2-natural-language-queries)
4. [Feature 3: Email Intelligence](#feature-3-email-intelligence)
5. [Feature 4: Customer Health Scoring](#feature-4-customer-health-scoring)
6. [Feature 5: Signal Rules Configuration](#feature-5-signal-rules-configuration)
7. [Feature 6: Signal Lifecycle Management](#feature-6-signal-lifecycle-management)
8. [Feature 7: Observability Dashboard](#feature-7-observability-dashboard)
9. [Feature 8: Human-in-the-Loop Approvals](#feature-8-human-in-the-loop-approvals)
10. [Feature 9: MCP Server Integration](#feature-9-mcp-server-integration)
11. [Feature 10: Vector Embeddings](#feature-10-vector-embeddings)

---

## Understanding Observability

### What is Observability?

**Observability** is the ability to understand the internal state of a system by examining its external outputs. In the context of AI CRM, it means being able to see exactly what the AI is doing, why it made certain decisions, and how long each step took.

### Why Observability Matters

| Without Observability | With Observability |
|----------------------|-------------------|
| "The AI made a mistake" | "The AI's sentiment analysis step failed due to empty input at 14:32:05" |
| "It's slow" | "The LLM call took 4.2 seconds, 3x longer than average" |
| "I don't trust the results" | "Here's the complete reasoning chain with confidence scores" |
| "How much is this costing?" | "This query used 1,234 tokens at $0.002/1K tokens = $0.0025" |

### Observability Components

1. **Run Logs**: Every AI tool execution is recorded with:
   - Start/end timestamps
   - Duration in milliseconds
   - Input/output data (JSON)
   - Success/failure status
   - Error details if failed

2. **Step-by-Step Reasoning Chain**:
   ```
   Step 1: Received query "What's the revenue for Acme Corp?"
   Step 2: Identified customer: Acme Corp (partner_id: 42)
   Step 3: Searched opportunities - found 3 active deals
   Step 4: Calculated total: $125,000
   Step 5: Generated response
   ```

3. **Performance Metrics**:
   - **TTFB** (Time to First Byte): How fast the first response appears
   - **Total Duration**: End-to-end execution time
   - **Token Usage**: Input + output tokens
   - **Cost**: Estimated cost based on model pricing

4. **Action Summary**: A human-readable narrative of what happened:
   > "Analyzed email from john@acme.com, detected negative sentiment, identified 2 action items, and created a churn_risk signal."

### How to Use Observability

1. **Navigate to**: AI Relationship Ops → Observability → Tool Runs
2. **Filter by**: Status (failed), Team, Date range, Duration > 5s
3. **Click on a run** to see:
   - Full reasoning chain
   - Each step's input/output
   - Where it failed (if applicable)
   - Token usage and cost

---

## Feature 1: LLM Configuration

### Description
Configure which LLM provider and model each team uses for AI processing.

### Test Plan

#### Test 1.1: Create Team with LLM Configuration

**Prerequisites:**
- User has access to CRM AI module
- User is logged into Odoo

**Steps:**
1. Navigate to: AI Relationship Ops → Agent Teams
2. Click "Create"
3. Enter Team Name: "Sales AI Team"
4. Set LLM Provider: "OpenAI"
5. Set Model Name: "gpt-4"
6. Set Temperature: 0.7
7. Set Max Tokens: 2048
8. Set System Prompt: "You are a helpful sales assistant..."
9. Click "Save"

**Expected Results:**
- ✓ Team is created successfully
- ✓ All LLM fields are saved
- ✓ Form shows the configured values

**Verification:**
```sql
-- Verify in database
SELECT name, llm_provider, llm_model, llm_temperature, llm_max_tokens 
FROM crm_ai_agent_team 
WHERE name = 'Sales AI Team';
```

---

#### Test 1.2: Agent LLM Override

**Steps:**
1. Open the created team
2. In "Agents" tab, add a new agent
3. Set Name: "Senior Sales Agent"
4. Set Role: "sales_specialist"
5. Set LLM Provider: "anthropic" (override)
6. Set Model: "claude-3-opus"
7. Save

**Expected Results:**
- ✓ Agent is created with override settings
- ✓ Agent uses Anthropic while team uses OpenAI
- ✓ Override badge/indicator shows in UI

---

## Feature 2: Natural Language Queries

### Description
Ask questions about CRM data using natural language and receive AI-generated responses.

### Test Plan

#### Test 2.1: Submit Basic Query

**Prerequisites:**
- At least 5 customers exist in system
- At least 3 opportunities exist

**Steps:**
1. Navigate to: AI Relationship Ops → Natural Language Queries
2. Click "Create"
3. Enter query: "What are my top 3 opportunities by expected revenue?"
4. Set Team: "Sales AI Team"
5. Click "Submit"

**Expected Results:**
- ✓ Query state changes to "Processing"
- ✓ After processing, state is "Completed"
- ✓ Response contains list of opportunities
- ✓ Response format matches selected format (markdown/json/text)

---

#### Test 2.2: Query with Customer Context

**Steps:**
1. Create new query
2. Enter: "What's the latest activity for Acme Corporation?"
3. Link to partner: Acme Corporation
4. Submit

**Expected Results:**
- ✓ AI uses partner context in analysis
- ✓ Response references specific partner data
- ✓ Partner is linked to query record

---

#### Test 2.3: Failed Query Retry

**Steps:**
1. Find a query with state "Failed"
2. Click "Retry" button
3. Observe state changes

**Expected Results:**
- ✓ Retry count increments
- ✓ State changes to "Processing"
- ✓ Error message is cleared

---

## Feature 3: Email Intelligence

### Description
Automatically analyze customer emails for sentiment, action items, and signals.

### Test Plan

#### Test 3.1: Process Support Email

**Steps:**
1. Navigate to: AI Relationship Ops → Email Intelligence
2. Click "Create"
3. Enter Subject: "Issue with product login"
4. Set From: "john@customer.com"
5. Set Body: "I've been trying to login for 2 hours and it keeps failing. This is very frustrating and I'm considering switching to your competitor."
6. Click "Process"

**Expected Results:**
- ✓ Processing status changes to "Processed"
- ✓ Sentiment is "Negative" or "Very Negative"
- ✓ Urgency is "High" or "Critical"
- ✓ Category is "Complaint" or "Support Request"
- ✓ Churn risk signal is created

---

#### Test 3.2: Process Sales Inquiry

**Steps:**
1. Create new email
2. Subject: "Interested in Enterprise Plan"
3. Body: "Hi, we're a team of 50 and interested in your enterprise offering. Can you send pricing?"
4. Link to partner
5. Process

**Expected Results:**
- ✓ Sentiment is "Positive" or "Neutral"
- ✓ Category is "Sales Inquiry" or "Upsell Opportunity"
- ✓ Upsell signal is created
- ✓ Partner is linked

---

#### Test 3.3: Action Items Extraction

**Steps:**
1. Create email with clear action items:
   "Please send me: 1. The contract renewal document 2. Updated pricing 3. Case study for similar companies"
2. Process
3. Check "Action Items" field

**Expected Results:**
- ✓ Action items are extracted as JSON array
- ✓ All 3 items are captured
- ✓ Items are linked to original request

---

## Feature 4: Customer Health Scoring

### Description
Aggregate multiple signals to provide a holistic view of customer health.

### Test Plan

#### Test 4.1: Create Health Score for New Customer

**Steps:**
1. Navigate to: AI Relationship Ops → Customer Health
2. Click "Create"
3. Select Customer: [existing partner]
4. Set initial scores:
   - Engagement: 70
   - Product Usage: 80
   - Support: 90
   - Payment: 100
   - Sentiment: 75
5. Click "Recalculate"

**Expected Results:**
- ✓ Health score is calculated (weighted average)
- ✓ Health category is set correctly (e.g., "Healthy" for score >= 80)
- ✓ Churn risk level is determined
- ✓ History record is created

---

#### Test 4.2: Health Score Trend Detection

**Steps:**
1. Open existing health score
2. Change engagement score from 80 to 50
3. Change sentiment score from 75 to 40
4. Recalculate
5. Check trend

**Expected Results:**
- ✓ Health score decreases
- ✓ Trend changes to "Declining"
- ✓ Previous score is stored
- ✓ Score change is visible

---

#### Test 4.3: Critical Health Alert

**Steps:**
1. Create health score with:
   - Engagement: 20
   - Product Usage: 15
   - Support: 30
   - Payment: 10
   - Sentiment: 25
2. Recalculate

**Expected Results:**
- ✓ Health score is < 40
- ✓ Health category is "Critical"
- ✓ Churn risk is "Critical" or "High"
- ✓ Recommended actions are generated

---

## Feature 5: Signal Rules Configuration

### Description
Configure rules that determine when and what signals are created.

### Test Plan

#### Test 5.1: Create Sentiment-Based Rule

**Steps:**
1. Navigate to: AI Relationship Ops → Signal Rules
2. Click "Create"
3. Set Name: "Negative Sentiment Alert"
4. Set Sequence: 10
5. Set Condition Sentiment: "very_negative"
6. Set Action Signal Type: "churn_risk"
7. Set Action Priority: "high"
8. Set Action Confidence: 0.9
9. Set Recommendation: "Escalate to retention team immediately"
10. Save

**Expected Results:**
- ✓ Rule is created and active
- ✓ Rule appears in list with correct sequence
- ✓ Conditions are saved correctly

---

#### Test 5.2: Create Theme-Based Rule

**Steps:**
1. Create new rule
2. Set Name: "Renewal Theme Detection"
3. Set Condition Theme: Select "Renewal"
4. Set Action Signal Type: "renewal"
5. Set Recommendation: "Prepare renewal documents"
6. Save

**Expected Results:**
- ✓ Rule triggers when summary has renewal theme
- ✓ Signal is created with configured parameters

---

#### Test 5.3: Rule Priority Order

**Steps:**
1. Create multiple rules with different sequences
2. Run agent team pipeline on test summary
3. Verify order of rule evaluation

**Expected Results:**
- ✓ Rules evaluated in sequence order
- ✓ First matching rule determines signal
- ✓ Later rules are skipped after match

---

## Feature 6: Signal Lifecycle Management

### Description
Track signals through their complete lifecycle from creation to resolution.

### Test Plan

#### Test 6.1: Signal State Transitions

**Steps:**
1. Find or create a signal with state "new"
2. Click "Acknowledge"
3. Verify state is "acknowledged"
4. Click "Start Progress"
5. Verify state is "in_progress"
6. Click "Resolve"
7. Verify state is "resolved"

**Expected Results:**
- ✓ Each transition updates state correctly
- ✓ Status bar shows current state
- ✓ Transition timestamps are recorded
- ✓ Chatter messages are posted

---

#### Test 6.2: Signal Dismissal

**Steps:**
1. Create signal with state "new"
2. Click "Dismiss"
3. Enter dismissal reason
4. Confirm

**Expected Results:**
- ✓ State changes to "dismissed"
- ✓ Dismissal reason is saved
- ✓ Signal no longer appears in active lists

---

#### Test 6.3: Bulk Signal Management

**Steps:**
1. Select multiple signals in list view
2. Click "Action: Acknowledge"
3. Verify all selected signals are updated

**Expected Results:**
- ✓ Bulk action updates all selected records
- ✓ States are all updated to "acknowledged"
- ✓ Activity is logged for each

---

## Feature 7: Observability Dashboard

### Description
View detailed execution logs and performance metrics for AI operations.

### Test Plan

#### Test 7.1: View Run Details

**Steps:**
1. Navigate to: AI Relationship Ops → Observability → Tool Runs
2. Click on any run record
3. Examine:
   - Start/End timestamps
   - Duration
   - Token usage
   - Cost estimate
   - State

**Expected Results:**
- ✓ All timing information is accurate
- ✓ Duration is calculated correctly
- ✓ Token counts match actual usage
- ✓ Cost is estimated reasonably

---

#### Test 7.2: Examine Reasoning Chain

**Steps:**
1. Open a run with steps
2. Navigate to "Reasoning Steps" tab
3. Expand each step
4. Check:
   - Step name and type
   - Input/Output data
   - Duration per step

**Expected Results:**
- ✓ Steps are in correct sequence
- ✓ Each step shows its type
- ✓ JSON data is properly formatted
- ✓ Durations are displayed

---

#### Test 7.3: Filter and Search Runs

**Steps:**
1. Go to Tool Runs list view
2. Apply filters:
   - State = "failed"
   - Date range: Last 7 days
   - Duration > 5000ms
3. Check results

**Expected Results:**
- ✓ Only matching runs are shown
- ✓ Filters work correctly
- ✓ Count matches actual results

---

#### Test 7.4: Performance Metrics

**Steps:**
1. Open "Agent Runs" view
2. Switch to Graph view
3. Verify metrics:
   - Total runs
   - Failed runs
   - Average duration
4. Switch to Pivot view

**Expected Results:**
- ✓ Graph shows distribution correctly
- ✓ Pivot allows drill-down
- ✓ Metrics are accurate

---

## Feature 8: Human-in-the-Loop Approvals

### Description
Require human approval before executing high-stakes AI actions.

### Test Plan

#### Test 8.1: Query Requiring Approval

**Steps:**
1. Create query that would modify data (e.g., "Update deal amount to $50,000")
2. Set to require approval
3. Submit
4. Verify state is "Requires Approval"
5. As approver, click "Approve"
6. Verify execution continues

**Expected Results:**
- ✓ Query enters "requires_approval" state
- ✓ Non-approver cannot execute
- ✓ Approver sees pending items
- ✓ After approval, execution proceeds

---

#### Test 8.2: Reject Approval Request

**Steps:**
1. Create query requiring approval
2. As approver, click "Reject"
3. Enter rejection reason
4. Confirm

**Expected Results:**
- ✓ State changes to "rejected"
- ✓ Rejection reason is saved
- ✓ Query is not executed
- ✓ Notification sent to requester

---

#### Test 8.3: Edit Before Approval

**Steps:**
1. Create query with parameters
2. Enter "requires_approval" state
3. Approver clicks "Edit" 
4. Modify parameters
5. Approve modified version

**Expected Results:**
- ✓ Parameters can be edited
- ✓ Original values are preserved in history
- ✓ Modified values are used for execution

---

## Feature 9: MCP Server Integration

### Description
Connect external AI tools to Odoo via Model Context Protocol.

### Test Plan

#### Test 9.1: Health Check Resource

**Steps:**
1. Start MCP server:
   ```bash
   ODOO_URL=http://localhost:8069 \
   ODOO_DB=mydb \
   ODOO_USERNAME=admin \
   ODOO_PASSWORD=admin \
   python3 addons/crm_ai_team/tools/mcp_server.py
   ```
2. Access resource: `odoo://health`
3. Verify response

**Expected Results:**
- ✓ Connection status: "healthy"
- ✓ Database name shown
- ✓ Statistics are accurate
- ✓ User ID is correct

---

#### Test 9.2: List Conversation Summaries Tool

**Steps:**
1. Call tool: `list_conversation_summaries(limit=10)`
2. Verify pagination response

**Expected Results:**
- ✓ Response has "records" array
- ✓ Response has "total" count
- ✓ Response has "has_more" boolean
- ✓ Limit is respected

---

#### Test 9.3: Create Signal via MCP

**Steps:**
1. Call: `create_relationship_signal`
2. Parameters:
   ```json
   {
     "summary_id": 1,
     "signal_type": "churn_risk",
     "recommendation": "Test signal via MCP",
     "priority": "high"
   }
   ```
3. Verify creation

**Expected Results:**
- ✓ Signal is created in Odoo
- ✓ All fields are set correctly
- ✓ Response includes signal ID and details

---

## Feature 10: Vector Embeddings

### Description
Store and use vector embeddings for semantic search and similarity matching.

### Test Plan

#### Test 10.1: Generate Embedding

**Steps:**
1. Open a conversation summary
2. Click "Generate Embedding"
3. Wait for processing
4. Check embedding fields

**Expected Results:**
- ✓ Embedding model is set
- ✓ Embedding dimension is set
- ✓ Embedding timestamp is current
- ✓ Processing completes without error

---

#### Test 10.2: Embedding Metadata

**Steps:**
1. Open summary with embedding
2. Check fields:
   - embedding_model
   - embedding_dimension
   - embedding_timestamp

**Expected Results:**
- ✓ Model name is correct (e.g., "text-embedding-3-small")
- ✓ Dimension matches model (e.g., 1536)
- ✓ Timestamp reflects when embedding was created

---

## Test Environment Setup

### Prerequisites

1. **Odoo Instance**: Running Odoo 17+ with crm_ai_team installed
2. **Database**: Clean database or test database
3. **Users**:
   - Admin user (full access)
   - Sales user (limited access)
   - Approver user (approval rights)
4. **Sample Data**: Run `create_dummy_dataset` to generate test data

### Setup Commands

```python
# In Odoo shell
env['crm.ai.agent.team'].create_dummy_dataset(
    team_name='Test Team',
    agent_count=3,
    transcript_count=10,
    auto_run=True
)
```

---

## Reporting Issues

When a test fails, include:

1. **Test Case ID** (e.g., Test 3.1)
2. **Steps to Reproduce**
3. **Expected Result**
4. **Actual Result**
5. **Screenshots** if applicable
6. **Error Messages** (full text)
7. **Environment Details**

---

## Sign-off Template

| Feature | Tester | Date | Status | Notes |
|---------|--------|------|--------|-------|
| LLM Configuration | | | | |
| Natural Language Queries | | | | |
| Email Intelligence | | | | |
| Customer Health Scoring | | | | |
| Signal Rules | | | | |
| Signal Lifecycle | | | | |
| Observability Dashboard | | | | |
| Human-in-the-Loop | | | | |
| MCP Server | | | | |
| Vector Embeddings | | | | |

**Sign-off Criteria:**
- All test cases pass
- No critical defects remain
- Documentation is complete
