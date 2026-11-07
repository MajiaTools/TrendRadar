# MajiaTools patches (vs joaomps/TrendRadar)

Applied 2026-11-07 for lynsea's X/Reddit breakout-term monitoring.

1. `english_platforms_adapter.py` — `fetch_from_reddit()` now uses the Arctic Shift
   API (`arctic-shift.photon-reddit.com/api/posts/search`) instead of
   `reddit.com/r/{sub}/hot.json`. Reason: reddit.com blocks server/datacenter IPs
   (GitHub Actions + this VM return "whoa there, pardner!" / IncompleteRead, 0 items).
   Arctic Shift verified 2026-11-07: ~2 min ingestion lag, real scores.
   Fetches last 24h (limit 100), ranks locally by score, keeps top 50.
2. `config/config.yaml` — platforms replaced with 8 Reddit subs (SideProject,
   InternetIsBeautiful, webdev, SaaS, selfhosted, artificial, LocalLLaMA, gamedev)
   + Hacker News. All NewsAPI sources removed (no key, not needed).
3. `config/frequency_words.txt` — replaced news/company watchlist with site-fit
   discovery groups (maker posts / game codes-wiki-guide / tool generator-calculator /
   AI / tutorial), plus crypto/stock/giveaway excludes.
4. `.github/workflows/crawler.yml` — NOT changed: the GitHub App cannot update workflow
   files (403, missing workflows permission), so the unused NEWSAPI_KEY env line stays.
   Harmless: no newsapi sources remain, the variable is never read. Schedule unchanged:
   every 4 hours, commits output back to the repo.
