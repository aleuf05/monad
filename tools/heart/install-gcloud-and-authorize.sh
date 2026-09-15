#!/usr/bin/env bash
set -euo pipefail

# One-time interactive bootstrap for Granite. Every privileged command is here
# so the Admiral can inspect/paste this script as a unit.
client_json="${1:-${GOOGLE_OAUTH_CLIENT_JSON:-}}"
if [[ -z "${client_json}" || ! -f "${client_json}" ]]; then
  echo "Usage: $0 /path/to/oauth-client-secret.json" >&2
  echo "Create a Google Cloud OAuth client of type Desktop app and download its JSON first." >&2
  exit 2
fi
sudo install -d -m 0755 /usr/share/keyrings
curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg \
  | gpg --dearmor \
  | sudo tee /usr/share/keyrings/cloud.google.gpg >/dev/null
echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" \
  | sudo tee /etc/apt/sources.list.d/google-cloud-sdk.list >/dev/null
sudo apt-get update
sudo apt-get install -y google-cloud-cli

# Opens the browser for the Admiral's Google account. Do not automate this.
# cloud-platform is required by gcloud ADC; Drive/Docs are the additional
# scopes, authorized through the Admiral's own OAuth client ID.
gcloud auth application-default login \
  --client-id-file="${client_json}" \
  --scopes=https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/drive,https://www.googleapis.com/auth/documents

echo "Authorization complete. Test with:"
echo "  python3 /home/cgl/dev/monad/tools/heart/drive_heart.py read"
