# ScopeSmith Frontend

Vue.js 3 frontend for the ScopeSmith AI Proposal Generator.

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
# API Configuration
VITE_API_BASE_URL=http://localhost:3000

# Feature Flags
VITE_ENABLE_TEMPLATE_UPLOAD=false
```

## Project Structure

```
src/
├── assets/          # Static assets and global styles
├── components/      # Vue components
├── composables/     # Reusable composition functions
└── utils/          # Utility functions and constants
```

## Technology Stack

- Vue.js 3 with Composition API
- Tailwind CSS for styling
- Axios for HTTP requests
- Vite for build tooling

## Development

1. Run `npm install` to install dependencies
2. Start the development server with `npm run dev`
3. Visit `http://localhost:3000` in your browser

## Production Deployment

The frontend is automatically deployed to AWS S3 + CloudFront through the CDK frontend stack.

```bash
# Build the production bundle
npm run build

# Deploy manually (if needed)
aws s3 sync dist/ s3://scopesmith-frontend --delete
aws cloudfront create-invalidation --distribution-id <DIST_ID> --paths "/*"
```

## Features

- Real-time proposal generation status tracking
- Document download capabilities
- Cost breakdown visualization
- Responsive design for all devices
- Animated transitions between views
