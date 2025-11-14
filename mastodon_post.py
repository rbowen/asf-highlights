#!/usr/bin/env python3

import sys
import os
from mastodon import Mastodon

def setup_mastodon():
    """Register app and get access token (run once)"""
    
    # Register app
    Mastodon.create_app(
        'CLI Poster',
        api_base_url='https://mastodon.social',
        to_file='mastodon_clientcred.secret',
        scopes=['write']
    )
    
    # Get access token
    mastodon = Mastodon(client_id='mastodon_clientcred.secret')
    
    print("Visit this URL to authorize the app:")
    print("https://mastodon.social/oauth/authorize?client_id=" + 
          mastodon.client_id + "&scope=write&redirect_uri=urn:ietf:wg:oauth:2.0:oob&response_type=code")
    
    auth_code = input("Enter the authorization code: ")
    
    # Use the scopes that were actually granted
    granted_scopes = ['write', 'write:accounts', 'write:blocks', 'write:favourites', 
                     'write:filters', 'write:follows', 'write:lists', 'write:media', 
                     'write:mutes', 'write:notifications', 'write:reports', 
                     'write:statuses', 'write:bookmarks']
    
    access_token = mastodon.log_in(code=auth_code, scopes=granted_scopes, to_file='mastodon_usercred.secret')
    print("Setup complete! You can now post to Mastodon.")

def post_to_mastodon(message):
    """Post message to Mastodon"""
    
    if not os.path.exists('mastodon_usercred.secret'):
        print("Error: Not authenticated. Run with --setup first.")
        return False
    
    mastodon = Mastodon(access_token='mastodon_usercred.secret')
    
    try:
        mastodon.toot(message)
        print("Posted successfully!")
        return True
    except Exception as e:
        print(f"Error posting: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 mastodon_post.py --setup")
        print("  python3 mastodon_post.py 'Your message here'")
        sys.exit(1)
    
    if sys.argv[1] == "--setup":
        setup_mastodon()
    else:
        message = " ".join(sys.argv[1:])
        post_to_mastodon(message)
