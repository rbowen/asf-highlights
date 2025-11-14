# Mastodon CLI Poster

A minimal Python script to post to Mastodon from the command line using a virtual environment.

## Setup

1. **Install dependencies:**
   ```bash
   ./setup_mastodon.sh
   ```

2. **Activate the virtual environment:**
   ```bash
   source mastodon_venv/bin/activate
   ```

3. **Authenticate with Mastodon (one-time setup):**
   ```bash
   python3 mastodon_post.py --setup
   ```
   
   This will:
   - Register the app with mastodon.social
   - Give you an authorization URL to visit
   - Prompt you to enter the authorization code
   - Save your credentials for future use

## Usage

Once set up, post messages like this:

```bash
# Activate virtual environment
source mastodon_venv/bin/activate

# Post a message
python3 mastodon_post.py "Hello from the command line!"

# Post multi-word messages
python3 mastodon_post.py "This is a longer message with multiple words"
```

## Files Created

The script creates two credential files:
- `mastodon_clientcred.secret` - App credentials
- `mastodon_usercred.secret` - Your access token

Keep these files secure and don't commit them to version control.
