#!/usr/bin/env python3
"""Restores Google OAuth token from GOOGLE_TOKEN_B64 environment variable."""
import base64
import os

token_b64 = os.environ.get("GOOGLE_TOKEN_B64", "")
if not token_b64:
    raise SystemExit("ERROR: GOOGLE_TOKEN_B64 environment variable is not set")

os.makedirs(".tmp", exist_ok=True)
# Add padding if it was stripped during copy-paste
token_b64 += '=' * (4 - len(token_b64) % 4)
data = base64.b64decode(token_b64)
with open(".tmp/token.pickle", "wb") as f:
    f.write(data)
print(f"Token restored — {len(data)} bytes")
