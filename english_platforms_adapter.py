#!/usr/bin/env python3
"""
English News Platforms Adapter

Supports fetching trending news from:
1. Reddit (free, no API key)
2. Hacker News (free, no API key)
3. News API (requires API key, 100 requests/day free)
"""

import requests
import time
from typing import Dict, List, Optional
from datetime import datetime


class EnglishPlatformsAdapter:
    """Adapter for fetching from English news platforms"""

    def __init__(self, newsapi_key: Optional[str] = None, proxy_url: Optional[str] = None):
        """
        Initialize the adapter

        Args:
            newsapi_key: API key for News API (optional)
            proxy_url: Proxy URL if needed (optional)
        """
        self.newsapi_key = newsapi_key
        self.proxy_url = proxy_url
        self.proxies = {'http': proxy_url, 'https': proxy_url} if proxy_url else None

    def fetch(self, platform_config: Dict) -> Dict:
        """
        Fetch from specified platform

        Args:
            platform_config: Platform configuration dict with 'id', 'api', and optional 'subreddit'

        Returns:
            Dict with platform data in TrendRadar format
        """
        api_type = platform_config.get('api', 'unknown')
        platform_id = platform_config['id']

        if api_type == 'reddit':
            subreddit = platform_config.get('subreddit', platform_id)
            return self.fetch_from_reddit(subreddit)
        elif api_type == 'hackernews':
            return self.fetch_from_hackernews()
        elif api_type == 'newsapi':
            source_id = platform_config.get('source_id', platform_id)
            return self.fetch_from_newsapi(source_id)
        else:
            raise ValueError(f"Unknown API type: {api_type}")

    def fetch_from_reddit(self, subreddit: str) -> Dict:
        """
        Fetch trending posts from Reddit via Arctic Shift (free archive API, no auth).

        Why not reddit.com directly: reddit.com/hot.json blocks server/datacenter IPs
        ("whoa there, pardner!" / IncompleteRead) from this VM and from GitHub Actions,
        so the original direct-JSON fetch returns 0 items. Arctic Shift
        (https://arctic-shift.photon-reddit.com) mirrors Reddit posts with ~2 min lag
        and works from server IPs. Verified 2026-11-07: r/gaming 24h window returns
        real scores (max 13284); r/SideProject 7-day window max 86.

        Strategy: pull the last 24h (newest first, limit 100), then rank locally by
        score and keep the top 50. Scores on fresh low-volume posts are still 1, so
        discovery value comes from the titles themselves, not the ranking.
        """
        import time as _time

        now = int(_time.time())
        url = "https://arctic-shift.photon-reddit.com/api/posts/search"
        params = {
            "subreddit": subreddit,
            "sort": "desc",          # newest first; we re-rank by score locally
            "limit": 100,
            "after": now - 24 * 3600,
        }
        headers = {"User-Agent": "MajiaTools-TrendRadar/1.0 (Arctic Shift Reddit mirror)"}

        try:
            response = requests.get(url, params=params, headers=headers,
                                    proxies=self.proxies, timeout=30)
            response.raise_for_status()
            posts = response.json().get("data", [])
            print(f"  Arctic Shift r/{subreddit}: {len(posts)} posts in last 24h")

            items = []
            for post in posts:
                if post.get("stickied"):
                    continue
                if post.get("removed_by") is not None:
                    continue
                title = (post.get("title") or "").strip()
                if not title:
                    continue
                permalink = post.get("permalink") or ""
                link = f"https://www.reddit.com{permalink}" if permalink else (post.get("url") or "")
                items.append({
                    "rank": 0,  # set after sorting by score
                    "title": title,
                    "url": link,
                    "mobileUrl": link,
                    "score": post.get("score", 0) or 0,
                    "comments": post.get("num_comments", 0) or 0,
                    "created": post.get("created_utc", 0) or 0,
                    "author": post.get("author", "unknown"),
                    "is_video": bool(post.get("is_video", False)),
                    "is_self": bool(post.get("is_self", False)),
                })

            items.sort(key=lambda x: x["score"], reverse=True)
            items = items[:50]
            for idx, it in enumerate(items, 1):
                it["rank"] = idx

            if items:
                print(f"  Top r/{subreddit}: score={items[0]['score']}, comments={items[0]['comments']}")
            return {
                "id": f"reddit-{subreddit}",
                "name": f"Reddit r/{subreddit}",
                "items": items,
            }

        except Exception as e:
            print(f"Error fetching from Reddit r/{subreddit} via Arctic Shift: {e}")
            return {
                "id": f"reddit-{subreddit}",
                "name": f"Reddit r/{subreddit}",
                "items": [],
                "error": str(e),
            }

    def fetch_from_hackernews(self) -> Dict:
        """
        Fetch top stories from Hacker News

        Returns:
            Dict with format: {'id': str, 'name': str, 'items': List[Dict]}
        """
        try:
            # Get top story IDs
            ids_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
            ids_response = requests.get(ids_url, proxies=self.proxies, timeout=10)
            ids_response.raise_for_status()
            story_ids = ids_response.json()[:50]  # Get top 50 IDs

            items = []
            for idx, story_id in enumerate(story_ids, 1):
                try:
                    # Fetch individual story
                    item_url = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
                    story_response = requests.get(item_url, proxies=self.proxies, timeout=5)
                    story_response.raise_for_status()
                    story = story_response.json()

                    if story and story.get('title'):
                        # Use story URL if available, otherwise link to HN discussion
                        story_url = story.get('url', f"https://news.ycombinator.com/item?id={story_id}")
                        
                        items.append({
                            'rank': idx,
                            'title': story['title'],
                            'url': story_url,
                            'mobileUrl': story_url,
                            'score': story.get('score', 0),
                            'comments': story.get('descendants', 0),
                            'by': story.get('by', 'unknown'),
                            'time': story.get('time', 0)
                        })

                    # Rate limiting - be nice to HN API
                    if idx % 10 == 0:
                        time.sleep(0.5)

                except Exception as e:
                    print(f"Error fetching HN story {story_id}: {e}")
                    continue

            return {
                'id': 'hackernews',
                'name': 'Hacker News',
                'items': items
            }

        except Exception as e:
            print(f"Error fetching from Hacker News: {e}")
            return {
                'id': 'hackernews',
                'name': 'Hacker News',
                'items': [],
                'error': str(e)
            }

    def fetch_from_newsapi(self, source_id: str) -> Dict:
        """
        Fetch top headlines from News API

        Args:
            source_id: News API source ID (e.g., 'techcrunch', 'bbc-news')

        Returns:
            Dict with format: {'id': str, 'name': str, 'items': List[Dict]}
        """
        if not self.newsapi_key:
            return {
                'id': source_id,
                'name': source_id,
                'items': [],
                'error': 'News API key not configured'
            }

        url = "https://newsapi.org/v2/top-headlines"
        params = {
            'sources': source_id,
            'apiKey': self.newsapi_key,
            'pageSize': 100,
            'language': 'en'
        }

        try:
            response = requests.get(
                url,
                params=params,
                proxies=self.proxies,
                timeout=15
            )
            response.raise_for_status()
            data = response.json()

            if data.get('status') != 'ok':
                error_msg = data.get('message', 'Unknown error')
                print(f"News API error for {source_id}: {error_msg}")
                return {
                    'id': source_id,
                    'name': source_id,
                    'items': [],
                    'error': error_msg
                }

            items = []
            for idx, article in enumerate(data.get('articles', []), 1):
                items.append({
                    'rank': idx,
                    'title': article['title'],
                    'url': article['url'],
                    'mobileUrl': article['url'],
                    'description': article.get('description', ''),
                    'author': article.get('author', ''),
                    'publishedAt': article.get('publishedAt', ''),
                    'source': article.get('source', {}).get('name', source_id)
                })

            # Get source name from first article if available
            source_name = data['articles'][0]['source']['name'] if data.get('articles') else source_id

            return {
                'id': source_id,
                'name': source_name,
                'items': items
            }

        except Exception as e:
            print(f"Error fetching from News API ({source_id}): {e}")
            return {
                'id': source_id,
                'name': source_id,
                'items': [],
                'error': str(e)
            }


# Standalone test function
def test_adapter():
    """Test the adapter with sample requests"""
    print("=" * 60)
    print("Testing English Platforms Adapter")
    print("=" * 60)

    adapter = EnglishPlatformsAdapter()

    # Test Reddit
    print("\n1. Testing Reddit (r/worldnews)...")
    reddit_config = {'id': 'worldnews', 'api': 'reddit', 'subreddit': 'worldnews'}
    reddit_data = adapter.fetch(reddit_config)
    print(f"   Found {len(reddit_data['items'])} posts")
    if reddit_data['items']:
        print(f"   Top post: {reddit_data['items'][0]['title'][:80]}...")

    # Test Hacker News
    print("\n2. Testing Hacker News...")
    hn_config = {'id': 'hackernews', 'api': 'hackernews'}
    hn_data = adapter.fetch(hn_config)
    print(f"   Found {len(hn_data['items'])} stories")
    if hn_data['items']:
        print(f"   Top story: {hn_data['items'][0]['title'][:80]}...")

    # Test News API (will fail without key, which is expected)
    print("\n3. Testing News API (requires key)...")
    newsapi_config = {'id': 'techcrunch', 'api': 'newsapi', 'source_id': 'techcrunch'}
    newsapi_data = adapter.fetch(newsapi_config)
    if 'error' in newsapi_data:
        print(f"   ⚠️  {newsapi_data['error']} (expected without API key)")
    else:
        print(f"   Found {len(newsapi_data['items'])} articles")

    print("\n" + "=" * 60)
    print("Test complete!")
    print("=" * 60)


if __name__ == "__main__":
    test_adapter()
