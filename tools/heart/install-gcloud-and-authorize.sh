#!/usr/bin/env bash
set -euo pipefail

# One-time interactive bootstrap for Granite. Every privileged command is here
# so the Admiral can inspect/paste this script as a unit.
sudo install -d -m 0755 /usr/share/keyrings
curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg \
  | gpg --dearmor \
  | sudo tee /usr/share/keyrings/cloud.google.gpg >/dev/null
echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" \
  | sudo tee /etc/apt/sources.list.d/google-cloud-sdk.list >/dev/null
sudo apt-get update
sudo apt-get install -y google-cloud-cli

# Opens the browser for the Admiral's Google account. Do not automate this.
gcloud auth application-default login \
  --scopes=https://www.googleapis.com/auth/drive,https://www.googleapis.com/auth/documents

echo "Authorization complete. Test with:"
echo "  python3 /home/cgl/dev/monad/tools/heart/drive_heart.py read"
