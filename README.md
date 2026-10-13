# Reddit Scraper (Python)

[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![Last verified](https://img.shields.io/badge/last%20verified-2026--10--13-brightgreen.svg)](#how-we-keep-it-working)

Scrape public Reddit subreddits, posts, comments, search results and user posts with Python. No login, no API key, one file.

> **Need this at scale?** The script is for learning and small jobs. The [ToolzerHub Reddit API](https://toolzerhub.com/apis/reddit?utm_source=github&utm_medium=readme&utm_campaign=reddit-scraper) returns the same data and more (full comment trees, user profiles with karma, user comments, r/popular) as JSON from any server, with no blocks to handle. 100 free credits a month, no card needed.

## What it scrapes

| Command | What you get |
|---|---|
| `subreddit <name>` | Posts from a subreddit, sorted `hot`, `new`, `top`, `rising` or `controversial`, with score, comments, author, flair, link and text |
| `about <name>...` | Subreddit description, weekly visitors, weekly contributions, creation date and rules |
| `post <url>` | One post with its text, link and score, plus the first comments with author, score and reply depth |
| `search <query>` | Posts that match a search, with subreddit, author, score and comment count |
| `user <username>` | A user's most recent posts |

## Quick start

```bash
git clone https://github.com/toolzerhub/reddit-scraper.git
cd reddit-scraper
pip install -r requirements.txt
python reddit_scraper.py subreddit python
```

More examples:

```bash
python reddit_scraper.py subreddit space --sort top --time week --limit 50 -o space.json
python reddit_scraper.py about nasa dataisbeautiful -o about.json
python reddit_scraper.py post https://www.reddit.com/r/Python/comments/1x1t161/python_315_released/ --comments 20
python reddit_scraper.py search "web scraping" --limit 25 -o search.json
python reddit_scraper.py user nasa --limit 10
```

Every command takes `-o file.json` to save the result and `--proxy URL` to route through a proxy. The script also reads `HTTPS_PROXY`. A subreddit or user can be a name (`python`, `r/python`, `u/nasa`) or a URL.

## Example output

`python reddit_scraper.py subreddit space --sort top --time week --limit 5` (one post shown)

```json
[
  {
    "id": "1x4gwt8",
    "title": "Moonlight reflecting off the Amazon river, seen from the International Space Station",
    "url": "https://www.reddit.com/r/space/comments/1x4gwt8/moonlight_reflecting_off_the_amazon_river_seen/",
    "subreddit": "space",
    "author": "astro_pettit",
    "created_at": "2026-10-12T23:12:45+00:00",
    "score": 9465,
    "upvote_ratio": 0.9878943506969919,
    "comment_count": 58,
    "post_type": "image",
    "flair": "image/gif",
    "content_url": "https://i.redd.it/57ee6os2c4vh1.jpeg",
    "domain": "i.redd.it",
    "text": null,
    "is_pinned": false,
    "is_locked": false,
    "is_spoiler": false
  }
]
```

`python reddit_scraper.py post https://www.reddit.com/r/Python/comments/1x1t161/python_315_released/ --comments 4` (two comments shown, text trimmed)

```json
{
  "id": "1x1t161",
  "title": "Python 3.15 Released",
  "url": "https://www.reddit.com/r/Python/comments/1x1t161/python_315_released/",
  "subreddit": "Python",
  "author": "treyhunner",
  "created_at": "2026-10-09T18:29:03+00:00",
  "score": 525,
  "upvote_ratio": 0.9906542056074766,
  "comment_count": 70,
  "post_type": "multi_media",
  "flair": "News",
  "content_url": null,
  "domain": "self.Python",
  "text": "https://www.python.org/downloads/release/python-3150/\n\nRelease announcement: https://discuss.python.org/t/pyth...",
  "is_pinned": false,
  "is_locked": false,
  "is_spoiler": false,
  "comments": [
    {
      "id": "pewn5rx",
      "parent_id": null,
      "depth": 0,
      "author": "treyhunner",
      "created_at": "2026-10-09T19:04:34+00:00",
      "score": 60,
      "text": "A few of my personal favorites from this release:\n\n- UTF-8 as the default encoding (so confusing utf-8 & cp-12...",
      "is_op": true,
      "url": "https://www.reddit.com/r/Python/comments/1x1t161/comment/pewn5rx/"
    },
    {
      "id": "pexkth3",
      "parent_id": "pewn5rx",
      "depth": 1,
      "author": "ashvy",
      "created_at": "2026-10-09T21:34:10+00:00",
      "score": 3,
      "text": "Just want to ask, is there a comparison between tachyon/profiling and Scalene profiler?",
      "is_op": false,
      "url": "https://www.reddit.com/r/Python/comments/1x1t161/comment/pexkth3/"
    }
  ]
}
```

`python reddit_scraper.py about nasa` (two rules shown)

```json
{
  "id": "2qk6m",
  "name": "nasa",
  "url": "https://www.reddit.com/r/nasa/",
  "description": "r/NASA is for anything related to the National Aeronautics and Space Administration; the latest news, events,...",
  "weekly_visitors": 45980,
  "weekly_contributions": 346,
  "created_at": "2008-07-17T00:46:50+00:00",
  "rules": [
    {
      "number": 1,
      "title": "All submissions must be related to NASA",
      "description": "The focus of r/NASA is primarily around NASA itself and the work it does. Submissions and comments should refl..."
    },
    {
      "number": 2,
      "title": "Image Content and Sourcing",
      "description": "All images must be directly related to NASA. Prohibited: Drawings, memes, screenshots, Legos, non-NASA astroph..."
    }
  ]
}
```

Full outputs for every command are in [examples/](examples).

## Fields

### subreddit, user and post

`subreddit` and `user` return a list of posts. `post` returns one post with a `comments` list.

| Field | Description |
|---|---|
| id | Post id (the code in the post URL) |
| title | Post title |
| url | Link to the post on Reddit |
| subreddit | Subreddit name. A user's own page shows as `u_<name>` |
| author | Username |
| created_at | Post time, ISO 8601 UTC |
| score | Net upvotes (live; it changes between runs) |
| upvote_ratio | Share of votes that are upvotes, 0 to 1 |
| comment_count | Number of comments |
| post_type | `text`, `multi_media` (a text post that can hold images or links), `link`, `image`, `gallery`, `video` or `crosspost` |
| flair | Post flair label, if any |
| content_url | The outbound link, or the image or video, for non-text posts. `null` for text posts |
| domain | Site of the link, or `self.<subreddit>` for text posts |
| text | Post body text. `null` when the post has none |
| is_pinned, is_locked, is_spoiler | Flags |
| comments | `post` only. Comments in Reddit's order, replies included (see below) |

### comments (inside `post`)

| Field | Description |
|---|---|
| id | Comment id |
| parent_id | Id of the comment replied to. `null` for a top-level comment |
| depth | `0` for top-level, `1` for a reply, and so on |
| author | Username |
| created_at | Time, ISO 8601 UTC |
| score | Net upvotes |
| text | Comment text. `null` if the comment was deleted |
| is_op | `true` if the author wrote the post |
| url | Link to the comment |

### about

| Field | Description |
|---|---|
| id | Subreddit id |
| name | Subreddit name |
| url | Link to the subreddit |
| description | Public description |
| weekly_visitors | Unique visitors in the last week, as Reddit states it |
| weekly_contributions | Posts and comments in the last week |
| created_at | Creation date, ISO 8601 UTC |
| rules | List of `number`, `title` and `description` |

### search

| Field | Description |
|---|---|
| id, title, url | The post |
| subreddit, author | Where and who |
| created_at | Post time, ISO 8601 UTC |
| score, comment_count | Votes and comments |
| is_nsfw | Adult-content flag |

## How it works

1. It sends requests as Chrome, with the same headers Reddit's own site sends. [curl_cffi](https://github.com/lexiforest/curl_cffi) matches the browser's TLS fingerprint as well as its headers. Reddit's old `.json` URLs are blocked, so the script does not use them.
2. Reddit's site fills its feeds, comment lists and search with small HTML pages from `/svc/shreddit/`. The data sits in the attributes of elements such as `<shreddit-post>` and `<shreddit-comment>`. `post` also reads the post's own page for the text and flags.
3. [Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/) reads those attributes and the script cleans them into the fields above. To get more than one page, it builds the next-page cursor from the last post id.

A longer walkthrough with timed runs and a CSV example: [Reddit scraper in Python](https://toolzerhub.com/blog/reddit-scraper-python?utm_source=github&utm_medium=readme&utm_campaign=reddit-scraper).

## Limits

- Public data only. Private and banned communities are not available.
- `post` returns the first batch of comments only (about 25, replies included). Deeper threads are not followed.
- `search` finds posts only, not communities, people or comments. `user` returns posts only, not comments, and has to page through comments to find them, so a user who mostly comments returns fewer posts.
- `about` has no member count. The pages the script reads do not state one, so it gives weekly visitors.
- Feeds are live. `hot` and `top` change from one run to the next, and scores move.
- Reddit blocks most cloud and datacenter IPs, with HTTP 403 or a "Prove your humanity" page. Run it from a home connection, or pass `--proxy` (a residential proxy works best). An ordinary IP is blocked now and then too. Run the command again.
- No retries, no concurrency. That is on purpose: the script stays short enough to read in one sitting.
- It breaks when Reddit changes its pages. The `CLIENT_VERSION` at the top of the script is a frontend build id that Reddit retires over time. See "How we keep it working".

## Scaling up

The script is for learning and small jobs. At scale you run into blocks, changing page formats and proxy costs. The [ToolzerHub Reddit API](https://toolzerhub.com/apis/reddit?utm_source=github&utm_medium=readme&utm_campaign=reddit-scraper) handles all of that:

| | This script | ToolzerHub API |
|---|---|---|
| Data | Subreddit posts, subreddit details, one post with first comments, post search, a user's posts | 9 endpoints at 1 credit each: subreddit posts and info, search, post details, full comment trees, r/popular, user profiles, posts and comments |
| Blocks and proxies | Your problem | Handled |
| When Reddit changes | Wait for a fix here | Fixed on our side |
| Cost | Free, plus your proxy | 100 free credits a month, then from $0.99 per 1,000 calls |

## How we keep it working

Every command is run against live Reddit pages before each update, and the "last verified" badge shows the last day they all passed. If something breaks, [open an issue](https://github.com/toolzerhub/reddit-scraper/issues).

## FAQ

**Is scraping Reddit legal?**
Scraping publicly available data is generally allowed in many places, but it depends on your country, what you collect and how you use it. Read the Legal section below.

**Why am I getting "Reddit blocked the request"?**
Reddit blocks most cloud and datacenter IP addresses. Use a home connection or a residential proxy, and slow down.

**Can it get every comment on a post, or a user's comments?**
No. The script reads the first batch of comments and a user's posts. The [ToolzerHub API](https://toolzerhub.com/apis/reddit?utm_source=github&utm_medium=readme&utm_campaign=reddit-scraper) returns user comments and comment replies.

## Related scrapers

- [instagram-scraper](https://github.com/toolzerhub/instagram-scraper): public Instagram profiles, posts, comments and search

## Legal and responsible use

This project is for education and for collecting **publicly available** data. You are responsible for how you use it.

- **Public data only.** The script reads pages anyone can see without an account. Do not use it to get around logins, paywalls, CAPTCHAs or other access controls.
- **Terms and robots rules.** Reddit's terms of service may restrict automated access. Read them and decide for yourself; following them is your responsibility.
- **Personal data.** Posts and comments can contain personal data, such as usernames. Laws such as the GDPR (EU and UK) and the CCPA (California) may apply. Collect only what you need, have a lawful basis, keep it secure, delete it when you no longer need it, and respect people's requests to access or erase their data.
- **Copyright.** Posts, images and videos belong to their creators. Do not republish them without permission.
- **Be gentle.** Keep request rates low and do not disrupt the service.
- **No warranty.** The software is provided "as is" under the MIT License, without warranty of any kind. The authors are not liable for any claim or damage arising from its use.
- **Not affiliated.** This project is not affiliated with, endorsed by or sponsored by Reddit, Inc. Reddit is a trademark of Reddit, Inc.
- **Takedown requests.** If you own rights in something here and want it changed or removed, email contact@toolzerhub.com.

This section is not legal advice. If you are unsure, talk to a lawyer.

## License

[MIT](LICENSE) © ToolzerHub
