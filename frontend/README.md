# AgentOps Dashboard

Modern React dashboard for the AgentOps autonomous model deployment orchestrator.

## Features

- **Real-time KPI Metrics**: Active deployments, pending approvals, monthly GPU spend
- **Deployment Table**: Comprehensive view of all deployment plans with status tracking
- **Natural Language Command Interface**: Deploy models using natural language commands
- **Auto-refresh**: Polls backend every 60 seconds for fresh data

## Setup

1. Install dependencies:
```bash
npm install
```

2. Configure API endpoint:
```bash
cp .env.example .env
# Edit .env and set VITE_API_URL to your Lambda function URL
```

3. Start development server:
```bash
npm run dev
```

4. Build for production:
```bash
npm run build
```

## Deployment

The frontend is designed to be deployed to AWS S3 + CloudFront. See `deploy/terraform/frontend.tf` for infrastructure setup.

