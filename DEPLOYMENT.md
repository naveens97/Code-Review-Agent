# Deploying CodeSage to the Web (24/7 Cloud Hosting)

To make your project accessible to anyone on the web at any time (without running on `localhost` or keeping your PC turned on), deploy it to a free cloud hosting provider.

Your project has already been configured with:
- **`Dockerfile`**: A multi-stage production Docker container that builds both frontend and backend.
- **`.dockerignore`**: Prevents unnecessary local files from slowing down cloud builds.
- **`render.yaml`**: A 1-click blueprint for [Render](https://render.com).

---

## Step 1: Push Your Code to GitHub

1. Go to [GitHub.com](https://github.com/new) and create a **New Repository** (e.g., `code-review-agent`). Keep it Public or Private.
2. In your terminal, run these commands (replace `<YOUR_GITHUB_USERNAME>` and `<REPO_NAME>` with your GitHub details):

```bash
git remote add origin https://github.com/<YOUR_GITHUB_USERNAME>/<REPO_NAME>.git
git branch -M main
git push -u origin main
```

---

## Step 2: Deploy for Free (Choose One Option)

### Option A: Render (Recommended — 100% Free, Easiest)

Render will build and host your complete application (both UI and Backend) under a single free HTTPS domain (e.g., `https://codesage-review-agent.onrender.com`).

1. Sign up or log in at **[render.com](https://render.com)** (sign in with your GitHub account).
2. Click the **"New +"** button at the top right and select **"Web Service"** (or **"Blueprint"**).
3. Connect your GitHub repository (`code-review-agent`).
4. Render will automatically detect the **`Dockerfile`** (or the `render.yaml` blueprint):
   - **Name**: `codesage-review-agent` (or your preferred name)
   - **Runtime**: `Docker`
   - **Instance Type**: `Free`
5. Click **"Deploy Web Service"**.
6. Render will build the Docker container in the cloud and give you a public URL (e.g. `https://codesage-review-agent.onrender.com`) that is live 24/7!

---

### Option B: Railway (Fastest Setup)

1. Go to **[railway.app](https://railway.app)** and log in with GitHub.
2. Click **"New Project"** -> **"Deploy from GitHub repo"**.
3. Select your repository.
4. Railway will automatically detect the `Dockerfile` and begin building.
5. In your project settings on Railway, go to **Networking** -> click **"Generate Domain"**.
6. Your web application is instantly online at `https://*.up.railway.app`!

---

### Option C: Koyeb (Free Nano Tier)

1. Go to **[koyeb.com](https://koyeb.com)** and create a free account.
2. Click **"Create Service"** -> select **GitHub**.
3. Select your repository.
4. Under **Builder**, select **Dockerfile**.
5. Click **Deploy**. Koyeb will assign you a live HTTPS URL.

---

## Optional: Adding AI API Keys in Production

If you want the AI-powered code explanations and smart reviews active on your live site:
1. In your cloud provider dashboard (e.g., Render or Railway), navigate to **Environment Variables**.
2. Add:
   - `GROQ_API_KEY`: Your Groq API key (optional)
   - `GEMINI_API_KEY`: Your Google Gemini API key (optional)
   - `OPENAI_API_KEY`: Your OpenAI API key (optional)
3. Redeploy or save changes.
