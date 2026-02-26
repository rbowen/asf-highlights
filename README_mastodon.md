# Mastodon CLI Poster

A minimal Python script to post to Mastodon from the command line using uv.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) - Fast Python package installer and resolver
  - Install: `curl -LsSf https://astral.sh/uv/install.sh | sh`

## Setup

**Authenticate with Mastodon (one-time setup):**
```bash
./mastodon_post.py --setup
```

This will:
- Automatically install dependencies via uv
- Register the app with mastodon.social
- Give you an authorization URL to visit
- Prompt you to enter the authorization code
- Save your credentials for future use

## Usage

Once set up, post messages like this:

```bash
# Post a message
./mastodon_post.py "Hello from the command line!"

# Post multi-word messages
./mastodon_post.py "This is a longer message with multiple words"
```

No virtual environment activation needed - uv handles dependencies automatically.

## Files Created

The script creates two credential files:
- `mastodon_clientcred.secret` - App credentials
- `mastodon_usercred.secret` - Your access token

Keep these files secure and don't commit them to version control.
