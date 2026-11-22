#!/usr/bin/env python3
"""Run locally once to obtain a YouTube upload refresh token."""
import argparse
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--client-secret", default="client_secret.json", help="OAuth Desktop client JSON downloaded from Google Cloud")
    args = parser.parse_args()
    flow = InstalledAppFlow.from_client_secrets_file(args.client_secret, SCOPES)
    credentials = flow.run_local_server(port=0, access_type="offline", prompt="consent")
    if not credentials.refresh_token:
        raise SystemExit("No refresh token returned. Revoke this app's access in your Google Account and run again with prompt=consent.")
    print("\nYOUTUBE_CLIENT_ID=" + str(credentials.client_id))
    print("YOUTUBE_CLIENT_SECRET=" + str(credentials.client_secret))
    print("YOUTUBE_REFRESH_TOKEN=" + str(credentials.refresh_token))
    print("\nAdd these three values as GitHub Actions repository secrets. Do not commit this output or client_secret.json.")


if __name__ == "__main__":
    main()
