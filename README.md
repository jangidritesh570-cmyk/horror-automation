# Telegram → n8n Cloud → 2D Hindi Horror → YouTube

This is a starter implementation, not a pre-connected bot. It contains an importable n8n workflow and a GitHub Actions video-rendering worker. You connect your own Telegram, Gemini, GitHub and YouTube credentials during setup.

## What the free MVP does

1. You send `/start` to your Telegram bot. You can add an idea, e.g. `/start sunsaan haveli ka raaz`.
2. n8n Cloud asks Gemini for an original Hindi horror story, eight scenes, narration, YouTube title/description/tags and thumbnail text.
3. GitHub Actions runs the rendering worker. It creates original dark 2D vector-style scene illustrations, Hindi narration through `edge-tts`, slow camera zoom, synthetic ambient sound and subtitles, then exports a 16:9 MP4 plus thumbnail.
4. The worker uploads the video and thumbnail to the YouTube channel authorized by your OAuth account.
5. The bot sends the YouTube link to your Telegram chat.

**Honest free-tier limitation:** this MVP does not create cinematic AI image-to-video footage. It creates illustrated 2D scenes with camera motion (an animated-story/slideshow style). Genuine AI image/video generation usually needs a separate service and may incur charges. `edge-tts` uses Microsoft's online Edge speech service through a community client; it is not an official, guaranteed production TTS API, so availability/rate limits can change.

## Files

- `n8n_telegram_horror_workflow.json` — import this into n8n Cloud.
- `.github/workflows/horror-pipeline.yml` — GitHub Actions job that accepts a story JSON payload.
- `render_and_upload.py` — creates 2D art, narration, MP4, subtitles, thumbnail and uploads to YouTube.
- `authorize_youtube.py` — one-time local helper to obtain a YouTube OAuth refresh token.
- `requirements.txt` — Python packages used by the GitHub video renderer.
- `requirements-auth.txt` — small dependency set for the one-time YouTube OAuth authorization on your laptop.
- `sample_story.json` — an example of the story JSON schema (not an actual generated episode).

## Setup part A — GitHub renderer (free runner)

1. Create a GitHub repository named `horror-automation` (private is fine for a small personal project).
2. Important: after extracting this ZIP, upload **all files and folders visible at the extracted top level** into the GitHub repository root. Do not create another enclosing project folder. The repository root must contain `render_and_upload.py`, `requirements.txt`, `n8n_telegram_horror_workflow.json`, and `.github/workflows/horror-pipeline.yml` directly. Keep the hidden `.github/workflows/` folder and the workflow filename `horror-pipeline.yml` unchanged. Use the default branch `main` (or change the branch in the n8n workflow URL/body if you use another branch).
3. Open **Settings → Secrets and variables → Actions → New repository secret** and add:

   - `TELEGRAM_BOT_TOKEN` — token from @BotFather.
   - `YOUTUBE_CLIENT_ID` — from Google Cloud OAuth Desktop client.
   - `YOUTUBE_CLIENT_SECRET` — from that same OAuth client.
   - `YOUTUBE_REFRESH_TOKEN` — created by `authorize_youtube.py` in part C.

4. Under **Settings → Secrets and variables → Actions → Variables**, optionally add:

   - `YOUTUBE_PRIVACY_STATUS` = `unlisted` for initial tests. Change to `public` only when you are happy with the output. If missing or invalid, the renderer defaults to `unlisted`.
   - `YOUTUBE_MADE_FOR_KIDS` = `true` only if the video is actually directed to children; otherwise leave it unset/`false`. Set this accurately for every upload.
   - `TTS_VOICE` = `hi-IN-MadhurNeural` (male narration) or `hi-IN-SwaraNeural` (female narration).

5. Open **Actions** and make sure the repository allows GitHub Actions to run. The workflow should appear as **2D Hindi Horror Video Pipeline**.

## Setup part B — YouTube OAuth (one-time setup on your Windows laptop)

1. In [Google Cloud Console](https://console.cloud.google.com/), create a project and enable **YouTube Data API v3**.
2. Configure the OAuth consent screen. Add your own Google account as a test user while setting it up.
3. Create an OAuth Client ID with application type **Desktop app** and download the JSON file. Save it beside `authorize_youtube.py` as `client_secret.json`. Do not upload it to GitHub or share it in chat.
4. Open PowerShell in the extracted project folder and run:

   ```powershell
   py -3.11 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip
   pip install -r requirements-auth.txt
   python authorize_youtube.py --client-secret client_secret.json
   ```

5. A browser opens. Sign in with the Google account that owns/manages the YouTube channel and approve the `youtube.upload` permission.
6. Copy the three printed values into the matching GitHub Actions repository secrets above. Never paste tokens in Telegram, n8n chat messages, source code, or a public repository.

**OAuth testing warning:** Google's OAuth documentation says refresh tokens for an External app left in `Testing` expire after 7 days when scopes such as YouTube upload are requested. For long-running automation, review the OAuth consent screen's publishing status and any verification requirements; otherwise you may need to authorize again after the test token expires. Source: https://developers.google.com/identity/protocols/oauth2

## Setup part C — Telegram bot + n8n Cloud

1. In Telegram, open [@BotFather](https://t.me/BotFather), send `/newbot`, follow the prompts, and copy the bot token.
2. In n8n Cloud, create a workflow and choose **Import from File**. Import `n8n_telegram_horror_workflow.json`.
3. Open the **Telegram Trigger** node, create/select a Telegram API credential, and paste the BotFather token.
4. Assign that same Telegram credential to all three Telegram send nodes:
   - `Telegram - Start Acknowledgement`
   - `Telegram - Render Queued`
   - `Telegram - Help Reply`
5. Open `Gemini - Story + SEO Generator`:
   - Create a new **Header Auth** credential.
   - Header name: `x-goog-api-key`
   - Header value: your key from [Google AI Studio](https://aistudio.google.com/apikey)
   - Select that credential on this HTTP Request node.
   - The workflow is configured for `gemini-3.8-flash`, the current stable Flash model. It uses the Gemini Developer API `generateContent` endpoint and expects a free-tier API key from AI Studio.
6. Open `GitHub - Start Free Render Job`:
   - The imported n8n workflow is already configured for `jangidritesh570-cmyk/horror-automation`; no URL change is needed unless you move the project to another repository.
   - Create a **fine-grained GitHub Personal Access Token**, limited to this repository. Give it **Actions: Read and write** permission (and Contents: Read if GitHub's setup asks for it).
   - Create/select a **Header Auth** credential: header name `Authorization`; header value `Bearer YOUR_GITHUB_TOKEN`.
   - Select that credential on the GitHub HTTP Request node.
   - Ensure the URL ends with `/actions/workflows/horror-pipeline.yml/dispatches` and the workflow's branch is `main`.
7. Save the workflow and activate it. Send `/start` to your bot once. The first reply includes your Telegram Chat ID because the owner lock is not configured yet.
8. Copy that Chat ID. Open the **Parse Telegram Command** Code node and replace `PASTE_YOUR_TELEGRAM_CHAT_ID_HERE` in `OWNER_CHAT_ID` with your numeric Chat ID (keep the quotes). Save and activate the workflow again. This prevents other Telegram users from triggering uploads to your channel.
9. Send `/start` again. You can pass a story idea too, e.g. `/start ek purane railway station ka bhoot`.

## First test and publishing

- Keep `YOUTUBE_PRIVACY_STATUS` set to `unlisted` for the first run. Check the audio, subtitles, thumbnail and story, then change the repository variable to `public` when ready for automatic public publishing.
- The first complete run may take several minutes. Watch the GitHub repository's **Actions** tab if you need detailed logs.
- YouTube uploads use the channel associated with the Google account that approved OAuth. No channel is selected by name in the script; double-check the Google account during the consent flow.
- The YouTube Data API upload method has a daily quota limit; the default quota currently lists 100 `videos.insert` calls per day. Source: https://developers.google.com/youtube/data/determine_quota_cost

## Telegram commands

- `/start` — create a fresh story.
- `/start <idea>` — create a story around your idea.
- Any other message receives setup/help instructions.

## Important limitations and safe use

- This is an MVP: one job at a time is recommended. Do not spam `/start`; free API rate limits and GitHub runner quotas apply. GitHub Free currently includes 2,000 standard-runner minutes/month for private repositories; standard runner use is free for public repositories. A public repo exposes the workflow source, so never commit API keys or OAuth files.
- The video worker uses vector-style generated artwork, not a dedicated AI video model. Visual prompts guide scene categories and mood, rather than generating photorealistic footage.
- Review all stories before changing the privacy variable to `public`. The workflow publishes directly once configured for public uploads.
- Use original stories and licensed music/assets. This starter makes its own ambient noise bed instead of downloading copyrighted tracks.
- YouTube upload credentials authorize publishing to your own channel. Keep the GitHub repository and its Actions secrets secure.
- If you use the bot for videos actually directed at children, set the Made for Kids variable correctly; animation alone does not decide the audience setting.
