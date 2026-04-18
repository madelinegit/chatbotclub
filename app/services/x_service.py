"""
X (Twitter) automation service for Maya's social presence.
Posts as Maya on a schedule. Uses OAuth 1.0a for posting
(the only auth type that works with free-tier X API write access).

Requirements:
    pip install tweepy

Access tokens (X_ACCESS_TOKEN / X_ACCESS_TOKEN_SECRET) are generated
once via the X Developer Portal → your app → "Keys and Tokens".
You need "Read and Write" permissions enabled on your app before
generating them — if you generated tokens before enabling write,
regenerate them.
"""
from app.config import (
    X_API_KEY, X_API_SECRET,
    X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET,
)


def _client():
    import tweepy
    return tweepy.Client(
        consumer_key=X_API_KEY,
        consumer_secret=X_API_SECRET,
        access_token=X_ACCESS_TOKEN,
        access_token_secret=X_ACCESS_TOKEN_SECRET,
    )


def post_tweet(text: str) -> dict:
    """
    Post a tweet as Maya. Returns the tweet ID and text on success.
    Raises on failure.
    """
    client   = _client()
    response = client.create_tweet(text=text)
    tweet_id = response.data["id"]
    print(f"X: posted tweet {tweet_id}")
    return {"id": tweet_id, "text": text}


def post_reply(text: str, reply_to_id: str) -> dict:
    """Reply to an existing tweet."""
    client   = _client()
    response = client.create_tweet(
        text=text,
        in_reply_to_tweet_id=reply_to_id,
    )
    tweet_id = response.data["id"]
    print(f"X: replied to {reply_to_id} with tweet {tweet_id}")
    return {"id": tweet_id, "text": text}


def delete_tweet(tweet_id: str) -> bool:
    """Delete a tweet by ID."""
    client = _client()
    client.delete_tweet(tweet_id)
    return True


def get_mentions(since_id: str = None) -> list:
    """
    Fetch recent mentions of Maya's account.
    Pass since_id to only get mentions newer than a known tweet.
    """
    client = _client()
    me     = client.get_me()
    kwargs = {"id": me.data.id, "max_results": 10}
    if since_id:
        kwargs["since_id"] = since_id
    response = client.get_users_mentions(**kwargs)
    if not response.data:
        return []
    return [{"id": t.id, "text": t.text} for t in response.data]
