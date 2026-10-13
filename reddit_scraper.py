"""Scrape public Reddit subreddits, posts, comments, search and user posts with Python. No login, one file."""
import argparse
import base64
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from urllib.parse import parse_qsl, quote, urlencode

from bs4 import BeautifulSoup
from curl_cffi import requests

BASE = "https://www.reddit.com"
# Reddit's web app loads its feeds as small HTML pages from /svc/shreddit/. These headers
# are what Chrome sends. Drop them and Reddit shows a "Prove your humanity" page instead.
CLIENT_VERSION = "2026-08-14T16:41Z~a71400ba"  # a frontend build id; if every call is gated, refresh it from a browser
HEADERS = {
    "referer": BASE + "/",
    "sec-ch-ua": '"Chromium";v="149", "Not)A;Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Linux"',
    "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
    "x-original-referer": "https://www.google.com/",
    "x-reddit-client-version": CLIENT_VERSION,
    "x-reddit-retry": "attempt=0, max=2",
}
FRAGMENT_ACCEPT = "text/vnd.reddit.partial+html, text/html;q=0.9"
PAGE_ACCEPT = "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
GATES = ("Prove your humanity", "blocked by network security")
POST_URL = re.compile(r"/r/([A-Za-z0-9_]+)/comments/([a-z0-9]+)")
SORTS = ("hot", "new", "top", "rising", "controversial")
PAGE_PAUSE = 1  # seconds between pages of one feed


class ScrapeError(Exception):
    pass


def iso(value):
    """Reddit writes '2026-10-13T00:00:07.766000+0000'; return ISO 8601 UTC without fractions."""
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%f%z").astimezone(timezone.utc).replace(microsecond=0).isoformat()
    except (TypeError, ValueError):
        return None


def to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def cursor_for(fullname):
    # Reddit's `after` is base64 of the last item's fullname. The '=' padding matters:
    # without it Reddit answers 200 with an empty feed, which looks like the end.
    return base64.b64encode(fullname.encode()).decode()


def clean_name(value, prefix):
    """'r/python', '/r/python/' or a full URL -> 'python' (prefix is 'r' or 'u')."""
    value = value.strip().strip("/")
    m = re.search(r"(?:^|/)(?:u|user)/([A-Za-z0-9_-]+)" if prefix == "u" else r"(?:^|/)r/([A-Za-z0-9_]+)", value)
    return m.group(1) if m else value.split("/")[-1]


def block_text(node):
    """Readable text of a post or comment body: one paragraph per block, list items as '- '."""
    parts = []
    for child in node.children:
        if not getattr(child, "name", None):
            text = re.sub(r"\s+", " ", str(child)).strip()
            if text:
                parts.append(text)
        elif child.name in ("ul", "ol"):
            parts.append("\n".join("- " + re.sub(r"\s+", " ", li.get_text()).strip() for li in child.find_all("li")))
        elif child.name == "pre":
            parts.append(child.get_text().strip("\n"))
        else:
            text = re.sub(r"\s+", " ", child.get_text()).strip()
            if text:
                parts.append(text)
    return "\n\n".join(parts) or None


def body_of(el, fullname):
    """The rendered body sits in a div with id '<fullname>-post-rtjson-content'."""
    body = el.find(id=f"{fullname}-post-rtjson-content")
    return block_text(body) if body else None


def clean_post(el):
    flair = el.find("shreddit-post-flair")
    domain = el.get("domain") or ""
    permalink = el.get("permalink")
    return {
        "id": el["id"][3:],
        "title": el.get("post-title"),
        "url": BASE + permalink,
        "subreddit": el.get("subreddit-name"),
        "author": el.get("author"),
        "created_at": iso(el.get("created-timestamp")),
        "score": to_int(el.get("score")),
        "upvote_ratio": float(el["upvote-ratio"]) if el.get("upvote-ratio") else None,
        "comment_count": to_int(el.get("comment-count")),
        "post_type": el.get("post-type"),
        "flair": flair.get_text(" ", strip=True) or None if flair else None,
        # For link and media posts this is the outbound link or the image; text posts have none.
        "content_url": None if domain.startswith("self.") else el.get("content-href"),
        "domain": domain or None,
        "text": body_of(el, el["id"]),
        "is_pinned": el.has_attr("stickied"),
        "is_locked": el.has_attr("locked"),
        "is_spoiler": el.has_attr("spoiler"),
    }


def clean_comment(el):
    fullname = el["thingid"]
    parent = el.get("parentid")
    return {
        "id": fullname[3:],
        "parent_id": parent[3:] if parent else None,
        "depth": to_int(el.get("depth")),
        "author": el.get("author"),
        "created_at": iso(el.get("created")),
        "score": to_int(el.get("score")),
        "text": body_of(el, fullname),
        "is_op": el.has_attr("is-op"),
        "url": BASE + el["permalink"] if el.get("permalink") else None,
    }


class Reddit:
    def __init__(self, proxy=None):
        self.proxies = {"http": proxy, "https": proxy} if proxy else None

    def get(self, path, params=None, referer=None, page=False):
        """One GET. Fragments and full pages differ only in the Accept header."""
        url = BASE + path + ("?" + urlencode(params) if params else "")
        headers = {**HEADERS, "accept": PAGE_ACCEPT if page else FRAGMENT_ACCEPT}
        if referer:
            headers["referer"] = BASE + referer
        try:
            # A new session per call, so each request looks like a fresh visitor.
            resp = requests.Session(impersonate="chrome", proxies=self.proxies).get(url, headers=headers, timeout=45)
        except requests.RequestsError as exc:
            raise ScrapeError(f"Network error: {exc}") from exc
        text = resp.text or ""
        if resp.status_code in (403, 429, 503) or any(g in text[:200000] for g in GATES):
            raise ScrapeError(
                f"Reddit blocked the request (HTTP {resp.status_code}). Cloud and datacenter IPs are blocked; "
                "try a home connection or --proxy. A residential IP is sometimes blocked once too: run it again."
            )
        if resp.status_code == 404:
            raise ScrapeError("Not found.")
        if resp.status_code >= 400 or (page and not text.strip()):
            raise ScrapeError(f"Reddit answered HTTP {resp.status_code} with {len(text)} bytes. Try again in a minute.")
        return BeautifulSoup(text, "html.parser")

    # --- feeds -----------------------------------------------------------

    def subreddit(self, name, sort="hot", period="day", limit=25):
        posts, seen, cursor = [], set(), None
        for _ in range(limit // 10 + 3):
            params = {"name": name, "t": period.upper(), "feedLength": 25}
            if cursor:
                params["after"] = cursor
            soup = self.get(f"/svc/shreddit/community-more-posts/{sort}/", params, referer=f"/r/{name}/")
            batch = [p for p in soup.find_all("shreddit-post") if p.get("id", "").startswith("t3_")]
            fresh = [p for p in batch if p["id"] not in seen]
            if not batch and not posts:
                raise ScrapeError(f"No posts found in r/{name}. It may not exist, or it may be private or banned.")
            posts += [clean_post(p) for p in fresh]
            seen.update(p["id"] for p in fresh)
            if len(posts) >= limit or not fresh:
                break
            cursor = cursor_for(batch[-1]["id"])
            time.sleep(PAGE_PAUSE)
        return posts[:limit]

    def user_posts(self, username, limit=25):
        """The overview feed mixes posts and comments; the cursor is the last item of either kind."""
        posts, seen, cursor = [], set(), None
        for _ in range(limit // 5 + 4):
            params = {"name": username, "feedLength": 25}
            if cursor:
                params["after"] = cursor
            soup = self.get("/svc/shreddit/profiles/profile_overview-more-posts/new/", params, referer=f"/user/{username}/")
            items = soup.find_all(["shreddit-post", "shreddit-profile-comment"])
            if not items and not posts:
                raise ScrapeError(f"Nothing found for u/{username}. The user may not exist, or may have no public posts.")
            ids = [i.get("id") or i.get("comment-id") for i in items]
            fresh = [i for i, n in zip(items, ids) if n and n not in seen and i.name == "shreddit-post"]
            new_ids = [n for n in ids if n and n not in seen]
            seen.update(ids)
            posts += [clean_post(p) for p in fresh]
            if len(posts) >= limit or not new_ids:  # no new items: the cursor stopped moving
                break
            cursor = cursor_for(ids[-1])
            time.sleep(PAGE_PAUSE)
        return posts[:limit]

    def search(self, query, limit=25):
        out, seen, cursor = [], set(), None
        for _ in range(limit // 5 + 3):
            params = {"q": query, "type": "posts"}
            if cursor:
                params["cursor"] = cursor
            soup = self.get("/svc/shreddit/search/", params, referer=f"/search/?q={quote(query)}")
            found = 0
            for t in soup.find_all("search-telemetry-tracker", attrs={"view-events": "search/view/post"}):
                ctx = json.loads(t.get("data-faceplate-tracking-context") or "{}")
                post, link = ctx.get("post") or {}, t.find("a", href=POST_URL)
                if not post.get("id") or post["id"] in seen or not link:
                    continue
                seen.add(post["id"])
                found += 1
                ago = t.find("faceplate-timeago")
                counts = t.find(attrs={"data-testid": "search-counter-row"})
                nums = [to_int(n.get("number")) for n in counts.find_all("faceplate-number")] if counts else []
                out.append({
                    "id": post["id"][3:],
                    "title": post.get("title"),
                    "url": BASE + link["href"],
                    "subreddit": (ctx.get("subreddit") or {}).get("name"),
                    "author": (ctx.get("profile") or {}).get("name"),
                    "created_at": iso(ago.get("ts")) if ago else None,
                    "score": nums[0] if len(nums) > 0 else None,
                    "comment_count": nums[1] if len(nums) > 1 else None,
                    "is_nsfw": post.get("nsfw"),
                })
            # The next page's cursor sits in the lazy-load placeholder at the bottom.
            nxt = None
            for part in soup.find_all("faceplate-partial", src=re.compile(r"/svc/shreddit/search/")):
                nxt = dict(parse_qsl(part["src"].split("?", 1)[-1])).get("cursor") or nxt
            if len(out) >= limit or not found or not nxt:
                break
            cursor = nxt
            time.sleep(PAGE_PAUSE)
        if not out:
            raise ScrapeError(f"No results for {query!r}.")
        return out[:limit]

    # --- one post --------------------------------------------------------

    def post(self, url, max_comments=10):
        m = POST_URL.search(url)
        if not m:
            raise ScrapeError("Expected a post URL like https://www.reddit.com/r/python/comments/<id>/...")
        sub, post_id = m.groups()
        # The comment fragment is the reliable call. It also holds the post's real permalink,
        # and the post page only loads with its slug in the URL.
        soup = self.get(f"/svc/shreddit/comments/r/{quote(sub)}/{quote(post_id)}", referer=f"/r/{sub}/")
        tree = soup.find("shreddit-comment-tree", attrs={"permalink": True})
        if not tree:
            raise ScrapeError(f"Post not found: {post_id}")
        page = self.get(tree["permalink"], referer=f"/r/{sub}/", page=True)
        el = page.find("shreddit-post", id=True)
        if not el:
            raise ScrapeError("Reddit sent its post page without the post. This happens now and then; try again in a minute.")
        data = clean_post(el)
        data["comments"] = [clean_comment(c) for c in soup.find_all("shreddit-comment", thingid=True)][:max_comments]
        return data

    # --- subreddit info --------------------------------------------------

    def about(self, name):
        soup = self.get("/svc/shreddit/feeds/subreddit-right-rail", {"name": name}, referer=f"/r/{name}/")
        head = soup.find("shreddit-subreddit-header")
        if not head:
            raise ScrapeError(f"Subreddit not found: r/{name}")
        created = soup.find("faceplate-timeago")
        rules = []
        for d in soup.find_all("details"):
            title = d.find("h2")
            if not title:
                continue
            number = d.find("summary").find("span", class_="text-neutral-content-weak")
            d.find("summary").extract()
            rules.append({
                "number": to_int(number.get_text(strip=True)) if number else len(rules) + 1,
                "title": title.get_text(strip=True),
                "description": block_text(d),
            })
        return {
            "id": head.get("subreddit-id", "")[3:] or None,
            "name": head.get("name"),
            "url": f"{BASE}/r/{head.get('name')}/",
            "description": (head.get("description") or "").strip() or None,
            "weekly_visitors": to_int(head.get("weekly-active-users")),
            "weekly_contributions": to_int(head.get("weekly-contributions")),
            "created_at": iso(created.get("ts")) if created else None,
            "rules": rules,
        }


def main():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--proxy", default=os.environ.get("HTTPS_PROXY"), help="proxy URL, e.g. http://user:pass@host:port")
    common.add_argument("-o", "--output", help="write JSON to this file")
    parser = argparse.ArgumentParser(description="Scrape public Reddit data. No login.")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("subreddit", parents=[common], help="posts in a subreddit")
    p.add_argument("name", help="subreddit name or URL, e.g. python")
    p.add_argument("--sort", choices=SORTS, default="hot")
    p.add_argument("--time", choices=("hour", "day", "week", "month", "year", "all"), default="day", help="time window for top and controversial")
    p.add_argument("--limit", type=int, default=25)
    sub.add_parser("about", parents=[common], help="subreddit details and rules").add_argument("names", nargs="+", help="subreddit names")
    p = sub.add_parser("post", parents=[common], help="one post with its first comments")
    p.add_argument("url", help="post URL")
    p.add_argument("--comments", type=int, default=10, help="how many comments to include (the first batch holds about 25)")
    p = sub.add_parser("search", parents=[common], help="search posts")
    p.add_argument("query")
    p.add_argument("--limit", type=int, default=25)
    p = sub.add_parser("user", parents=[common], help="recent posts by a user")
    p.add_argument("username", help="username without u/")
    p.add_argument("--limit", type=int, default=25)
    args = parser.parse_args()

    try:
        reddit = Reddit(args.proxy)
        if args.command == "subreddit":
            data = reddit.subreddit(clean_name(args.name, "r"), args.sort, args.time, args.limit)
        elif args.command == "about":
            data = [reddit.about(clean_name(n, "r")) for n in args.names]
        elif args.command == "post":
            data = reddit.post(args.url, args.comments)
        elif args.command == "search":
            data = reddit.search(args.query, args.limit)
        else:
            data = reddit.user_posts(clean_name(args.username, "u"), args.limit)
    except ScrapeError as exc:
        sys.exit(f"Error: {exc}")

    if args.command == "about" and len(data) == 1:
        data = data[0]
    text = json.dumps(data, indent=2, ensure_ascii=False)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(text + "\n")
        print(f"Saved to {args.output}")
    else:
        print(text)


if __name__ == "__main__":
    main()
