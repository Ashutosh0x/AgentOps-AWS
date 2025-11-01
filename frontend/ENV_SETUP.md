# Frontend Environment Setup

## Create .env File

Create a file named `.env` in the `frontend/` directory with the following content:

```
VITE_API_URL=https://7ovf2ipaywdvgp7j3r7d6mk5ca0cvfic.lambda-url.us-east-1.on.aws/
```

## Quick Setup (PowerShell)

```powershell
cd frontend
@"
VITE_API_URL=https://7ovf2ipaywdvgp7j3r7d6mk5ca0cvfic.lambda-url.us-east-1.on.aws/
"@ | Out-File -FilePath .env -Encoding utf8
```

## Quick Setup (Bash)

```bash
cd frontend
echo "VITE_API_URL=https://7ovf2ipaywdvgp7j3r7d6mk5ca0cvfic.lambda-url.us-east-1.on.aws/" > .env
```

## Verify

After creating the `.env` file, you can test locally:

```powershell
npm run dev
```

Then open `http://localhost:5173` in your browser.

## Note

The `.env` file is already in `.gitignore`, so it won't be committed to version control. This is correct behavior to keep your API URLs private.

