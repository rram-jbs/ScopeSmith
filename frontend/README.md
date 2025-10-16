# ScopeSmith Frontend

Vue.js 3 frontend for the ScopeSmith AI Proposal Generator with real-time agent workflow monitoring.

## Overview

The frontend provides a modern, responsive interface for:
- Submitting project assessment requests
- Real-time monitoring of Bedrock Agent workflow execution
- Live event streaming from AI agent (reasoning, tool calls, responses)
- Progress tracking with 8-step workflow visualization
- Document download and results display

## Architecture

### Asynchronous Pattern
The frontend implements a polling-based architecture to handle long-running agent workflows:
- **Immediate Response**: API returns session ID in <500ms
- **Status Polling**: Polls `/api/agent-status/{sessionId}` every 2 seconds
- **Real-time Updates**: Displays agent events, progress (0-100%), and current stage
- **No Timeouts**: Works seamlessly with 3-5 minute backend workflows

### Key Components

#### AgentStreamViewer.vue
Real-time agent orchestration viewer with:
- Event type visualization (reasoning, tool calls, responses, chunks, warnings)
- Color-coded event display with icons
- Auto-scrolling to latest events
- Progress bar with percentage tracking
- Stage-based progress indicators

#### AssessmentView.vue
Three-stage workflow management:
1. **Form Stage**: Collect client information and requirements
2. **Processing Stage**: Show real-time agent progress
3. **Results Stage**: Display generated documents and cost data

#### usePolling.js Composable
Reusable polling logic for status updates:
- 2-second polling interval
- Automatic cleanup on unmount
- Error handling and retry logic

## Setup

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Environment Variables

Create `.env.local` to override environment variables:

```bash
# API Configuration (required)
VITE_API_BASE_URL=https://xxx.execute-api.us-east-1.amazonaws.com/prod

# Feature Flags (optional)
VITE_ENABLE_TEMPLATE_UPLOAD=false
```

### Getting the API URL
After deploying the CDK infrastructure:
```bash
cd ../cdk
cdk deploy ScopeSmithApi
# Look for output: ScopeSmithApi.ApiUrl = https://xxx.execute-api.us-east-1.amazonaws.com/prod
```

## Project Structure

```
src/
├── assets/              # Static assets and global styles
│   ├── tailwind.css    # Tailwind CSS configuration
│   └── vue.svg         # Vue logo
├── components/          # Vue components
│   ├── AgentStreamViewer.vue      # Real-time agent progress viewer
│   ├── AgentStatus.vue            # Status badge component
│   ├── AppHeader.vue              # Application header
│   ├── AssessmentForm.vue         # Project intake form
│   ├── ErrorMessage.vue           # Error display component
│   ├── LoadingSpinner.vue         # Loading animation
│   └── ResultsDisplay.vue         # Documents and cost display
├── composables/         # Reusable composition functions
│   ├── useApi.js       # API client wrapper
│   └── usePolling.js   # Status polling logic
├── lib/
│   └── api.ts          # TypeScript API definitions
├── router/
│   └── index.js        # Vue Router configuration
├── utils/
│   └── constants.js    # Status constants (synced with backend)
├── views/
│   └── AssessmentView.vue         # Main assessment workflow view
├── App.vue              # Root component
├── main.js              # Application entry point
└── style.css            # Global styles
```

## Technology Stack

### Core
- **Vue.js 3** with Composition API
- **Vite** for build tooling and dev server
- **Vue Router** for navigation

### Styling
- **Tailwind CSS** for utility-first styling
- **PostCSS** for CSS processing
- Glassmorphic design system
- Responsive design for all devices

### HTTP & Data
- **Axios** for HTTP requests
- Real-time polling with composables
- JSON API communication

## Status Constants (Synchronized with Backend)

The frontend maintains synchronized status constants with the backend:

```javascript
// utils/constants.js
export const STATUS = {
  PENDING: 'PENDING',              // Session created, workflow queued
  PROCESSING: 'PROCESSING',         // Agent actively running
  COMPLETED: 'COMPLETED',           // All documents generated
  ERROR: 'ERROR',                   // Workflow failed
  CONFIGURATION_ERROR: 'CONFIGURATION_ERROR'  // Agent not configured
}

export const WORKFLOW_STAGES = [
  { id: 1, name: 'Initializing', key: 'Initializing' },
  { id: 2, name: 'Analyzing Requirements', key: 'RequirementsAnalyzer' },
  { id: 3, name: 'Calculating Costs', key: 'CostCalculator' },
  { id: 4, name: 'Selecting Templates', key: 'TemplateRetriever' },
  { id: 5, name: 'Generating PowerPoint', key: 'PowerPointGenerator' },
  { id: 6, name: 'Generating SOW', key: 'SOWGenerator' },
  { id: 7, name: 'Finalizing', key: 'Finalizing' },
  { id: 8, name: 'Complete', key: 'Complete' }
]
```

## Agent Event Types

The AgentStreamViewer displays various event types from the Bedrock Agent:

| Event Type | Icon | Color | Description |
|------------|------|-------|-------------|
| `reasoning` | 🤔 | Blue | Agent's thought process (ReAct pattern) |
| `tool_call` | 🔧 | Green | Lambda function invocation |
| `tool_response` | ✅ | Yellow | Function response |
| `chunk` | 💬 | Purple | Streaming text from agent |
| `warning` | ⚠️ | Orange | Rate limiting or throttling |
| `error` | ❌ | Red | Error occurred |
| `final_response` | 🎯 | Green | Agent's final output |

## API Integration

### Submit Assessment
```javascript
POST /api/submit-assessment
Request:
{
  client_name: "Acme Corp",
  project_name: "E-commerce Platform",
  industry: "Retail",
  requirements: "Build a modern e-commerce platform...",
  duration: "6 months",
  team_size: 5
}

Response (< 500ms):
{
  session_id: "uuid",
  status: "PENDING",
  message: "Assessment request received. Processing in background.",
  poll_url: "/api/agent-status/{session_id}"
}
```

### Poll Status (Every 2 seconds)
```javascript
GET /api/agent-status/{session_id}
Response:
{
  session_id: "uuid",
  status: "PROCESSING",
  current_stage: "Running CostCalculator",
  progress: 50,
  client_name: "Acme Corp",
  project_name: "E-commerce Platform",
  agent_events: "[{...}]",  // JSON string of events
  created_at: "ISO 8601",
  updated_at: "ISO 8601"
}
```

### Fetch Results
```javascript
GET /api/results/{session_id}
Response:
{
  powerpoint_url: "https://s3.../presentation.pptx",
  sow_url: "https://s3.../sow.docx",
  cost_data: {
    total_cost: 150000,
    total_hours: 1200,
    complexity_level: "High",
    cost_breakdown: {...},
    ai_insights: {...}
  }
}
```

## Development

### Running Locally

1. **Install dependencies**:
   ```bash
   npm install
   ```

2. **Configure API URL**:
   ```bash
   echo "VITE_API_BASE_URL=https://xxx.execute-api.us-east-1.amazonaws.com/prod" > .env.local
   ```

3. **Start dev server**:
   ```bash
   npm run dev
   # Visit http://localhost:5173
   ```

### Building for Production

```bash
# Build production bundle
npm run build

# Preview production build locally
npm run preview

# Deploy to S3 (done via CDK)
cd ../cdk
cdk deploy ScopeSmithFrontend
```

## Production Deployment

The frontend is automatically deployed via GitHub Actions and CDK:

### GitHub Actions Workflow
The `deploy-frontend.yml` workflow:
1. Builds Vue application with environment variables
2. Sets `VITE_API_BASE_URL` from CDK outputs
3. Syncs to S3 bucket
4. Invalidates CloudFront cache

### Manual Deployment
```bash
# Build the production bundle
npm run build

# Deploy manually (if needed)
aws s3 sync dist/ s3://scopesmith-frontend-bucket --delete
aws cloudfront create-invalidation --distribution-id <DIST_ID> --paths "/*"
```

### CDK Deployment
```bash
cd ../cdk
cdk deploy ScopeSmithFrontend
```

## Features

- 🎨 **Modern UI**: Glassmorphic design with Tailwind CSS
- ⚡ **Real-time Updates**: 2-second polling for live progress
- 🤖 **Agent Monitoring**: View AI agent reasoning and tool calls
- 📊 **Progress Tracking**: 0-100% progress with 8-step workflow
- 📱 **Responsive Design**: Works on desktop, tablet, and mobile
- 🔄 **Automatic Retry**: Error handling with retry logic
- 📥 **Document Downloads**: One-click document access
- 🎯 **Stage Indicators**: Visual workflow stage tracking

## Performance Characteristics

- **Initial Load**: < 1 second
- **Form Submission**: < 500ms response
- **Polling Frequency**: Every 2 seconds
- **Event Updates**: Real-time as they occur
- **Bundle Size**: Optimized with Vite tree-shaking

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Mobile browsers (iOS Safari, Chrome Mobile)

## Troubleshooting

### API Not Responding
1. Check `VITE_API_BASE_URL` in `.env.local`
2. Verify API Gateway is deployed and accessible
3. Check CORS configuration in API Gateway
4. Look at browser Network tab for errors

### Events Not Showing
1. Verify DynamoDB `agent_events` field exists
2. Check that events are stored as JSON string
3. Ensure polling is working (check Network tab)
4. Verify session_id is correct

### Styling Issues
1. Run `npm run build` to ensure Tailwind is processing
2. Check PostCSS configuration
3. Clear browser cache
4. Verify Tailwind CSS is imported in main.js

### Polling Not Working
1. Check browser console for errors
2. Verify composable is properly mounted
3. Ensure cleanup is happening on unmount
4. Check API endpoint is returning valid JSON

## Contributing

1. Follow Vue 3 Composition API best practices
2. Use Tailwind CSS for styling (avoid custom CSS)
3. Ensure status constants match backend
4. Test polling behavior thoroughly
5. Maintain accessibility standards
6. Add comments for complex logic

## Related Documentation

- [Main README](../README.md) - Project overview and architecture
- [Frontend Setup Guide](./FRONTEND_SETUP.md) - Detailed setup instructions
- [API Documentation](../README.md#api-reference) - Backend API reference

## License

This project is licensed under the MIT License - see the LICENSE file for details.
