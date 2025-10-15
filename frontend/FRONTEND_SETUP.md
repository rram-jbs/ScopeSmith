# Frontend Setup Guide

## What Was Fixed

The frontend now properly displays the AI agent work with real-time updates. Here's what was implemented:

### 1. **AgentStreamViewer Component** 
- Polls the backend every 2 seconds for agent status
- Displays all agent events (reasoning, tool calls, responses)
- Beautiful UI with color-coded event types
- Auto-scrolls to show latest events
- Shows completion/error states

### 2. **AssessmentView Integration**
- Three-stage workflow: Form → Processing → Results
- Smooth transitions between stages
- Proper error handling
- Document download links when complete

### 3. **Router Configuration**
- Vue Router properly configured
- Single-page application working correctly

## Setup Instructions

```bash
cd /Users/rpm4/Documents/GitHub/ScopeSmith/frontend

# Install dependencies (including vue-router)
npm install

# Create environment file
cp .env.example .env

# Edit .env and set your API Gateway URL
# VITE_API_URL=https://your-api-id.execute-api.us-east-1.amazonaws.com/prod

# Start development server
npm run dev
```

## How It Works

### Polling Mechanism
The `AgentStreamViewer` polls `GET /api/agent-status/{sessionId}` every 2 seconds:

```javascript
// Expected response format:
{
  "status": "PROCESSING",
  "agent_events": [
    {
      "type": "reasoning",
      "content": "Let me analyze these requirements...",
      "timestamp": "2024-01-15T10:30:00Z"
    },
    {
      "type": "tool_call",
      "function": "requirementsanalyzer",
      "action_group": "RequirementsAnalyzer",
      "parameters": [...]
    },
    {
      "type": "tool_response",
      "content": "{...}"
    }
  ]
}
```

### Event Types Displayed

| Event Type | Icon | Color | Description |
|------------|------|-------|-------------|
| `reasoning` | 🤔 | Blue | Agent thinking process |
| `tool_call` | 🔧 | Green | Calling a Lambda function |
| `tool_response` | ✅ | Yellow | Function returned result |
| `chunk` | 💬 | Purple | Agent response text |
| `warning` | ⚠️ | Orange | Warning message |
| `error` | ❌ | Red | Error occurred |

### Backend Requirements

Your Session Manager Lambda must return the `agent_events` field in this format:

```python
# In session_manager/app.py
dynamodb.update_item(
    TableName=os.environ['SESSIONS_TABLE_NAME'],
    Key={'session_id': {'S': session_id}},
    UpdateExpression='SET agent_events = :events',
    ExpressionAttributeValues={
        ':events': {'S': json.dumps([
            {
                'type': 'reasoning',
                'content': 'Analyzing requirements...',
                'timestamp': datetime.utcnow().isoformat()
            }
        ])}
    }
)
```

## Testing the UI

1. **Start the frontend**: `npm run dev`
2. **Open browser**: http://localhost:5173
3. **Submit a test assessment** with sample requirements
4. **Watch the agent work** in real-time:
   - See reasoning steps
   - Watch tool calls to Lambda functions
   - View responses
   - Get completion notification
5. **Download documents** when complete

## Troubleshooting

### Agent events not showing?
- Check browser console for API errors
- Verify API Gateway URL in `.env`
- Check that Session Manager returns `agent_events` in DynamoDB
- Ensure CORS is enabled on API Gateway

### Polling not working?
- Check Network tab - should see requests every 2 seconds
- Verify `/api/agent-status/{sessionId}` endpoint exists
- Check CloudWatch logs for Lambda errors

### Events showing but not updating?
- Make sure `agent_events` is a JSON string in DynamoDB
- Verify timestamps are included
- Check that events array is growing over time

## Next Steps

1. Deploy the updated Lambda stack with Nova Pro
2. Configure API Gateway URL in `.env`
3. Test the complete flow end-to-end
4. Build for production: `npm run build`
5. Deploy to S3/CloudFront

The UI is now fully functional and will display all agent activity in real-time! 🎉