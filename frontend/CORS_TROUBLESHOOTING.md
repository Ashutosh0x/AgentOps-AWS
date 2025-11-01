# CORS Troubleshooting Guide

## Current Status

✅ Lambda Function URL CORS is correctly configured:
- `AllowOrigins: ["*"]`
- `AllowMethods: ["*"]`
- `AllowHeaders: ["*"]`
- `AllowCredentials: true`

✅ FastAPI CORS middleware is configured:
- `allow_origins=["*"]`
- `allow_methods=["*"]`
- `allow_headers=["*"]`

## Known Issue

When running the frontend from `http://localhost:5173`, browsers enforce strict CORS policies. The network errors you're seeing are likely due to:

1. **Browser CORS preflight checks** - Browsers send OPTIONS requests before actual requests
2. **Mixed content warnings** - HTTPS API with HTTP localhost
3. **Browser security policies** - Some browsers block cross-origin requests even with CORS headers

## Solutions

### Option 1: Use a Proxy (Recommended for Local Development)

Add a Vite proxy to bypass CORS issues locally:

1. Update `frontend/vite.config.ts`:

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'https://7ovf2ipaywdvgp7j3r7d6mk5ca0cvfic.lambda-url.us-east-1.on.aws',
        changeOrigin: true,
        secure: true,
      }
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: false
  }
})
```

2. Update `frontend/src/lib/api.ts` to use relative URLs in development:

```typescript
const isDevelopment = import.meta.env.DEV
const API_BASE_URL = isDevelopment 
  ? '' // Use proxy in development
  : (import.meta.env.VITE_API_URL || 'https://7ovf2ipaywdvgp7j3r7d6mk5ca0cvfic.lambda-url.us-east-1.on.aws')
```

3. Restart the dev server

### Option 2: Disable Browser CORS (Not Recommended)

Only for local testing - disable CORS in Chrome:
```
chrome.exe --user-data-dir="C:/Chrome dev session" --disable-web-security
```

### Option 3: Deploy Frontend to AWS

Deploy the frontend to S3 + CloudFront. Since both frontend and API are on HTTPS and same origin, CORS won't be an issue.

## Testing

After implementing Option 1, test:

```powershell
cd frontend
npm run dev
```

The proxy will forward `/api/*` requests to the Lambda Function URL, bypassing CORS.

## Verify Lambda is Working

Test directly:
```powershell
Invoke-WebRequest -Uri "https://7ovf2ipaywdvgp7j3r7d6mk5ca0cvfic.lambda-url.us-east-1.on.aws/api/deployments" -Method GET
```

Should return: `{"deployments":[],"count":0}`

