# Execulytics Mushroom Consumer Chatbot

## Setup Instructions

### Step 1 - Upload to GitHub
1. Create a free GitHub account at github.com
2. Create a new repository called "mushroombot"
3. Upload all files in this folder to that repository

### Step 2 - Deploy to Render
1. Log into render.com
2. Click "New" then "Web Service"
3. Connect your GitHub account and select the mushroombot repository
4. Render will detect the settings automatically
5. Under "Environment Variables" add:
   - Key: ANTHROPIC_API_KEY
   - Value: your Anthropic API key
6. Click Deploy

### Step 3 - Upload your PDF
Once deployed, go to your Render URL and add /api/upload-pdf
Use a tool like Postman or the upload form to send your PDF

### Step 4 - Embed on WordPress
Add this code to any WordPress page using a Custom HTML block:
<iframe src="https://your-render-app.onrender.com" width="100%" height="650px" frameborder="0" style="border-radius:16px"></iframe>

### Login Credentials
No login required for users. The chatbot is open and ready to use.

### Adding Your PDF
Upload your report.pdf directly to the Render server or use the /api/upload-pdf endpoint.
