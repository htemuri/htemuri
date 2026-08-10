"""
Fetches books from a Goodreads shelf (via RSS, since the official API is
deprecated) and writes a cover-image grid into README.md between two
HTML comment markers.

Env vars (all optional, defaults match the shelf in the original widget):
    GOODREADS_USER_ID   e.g. "183200963"
    GOODREADS_SHELF     e.g. "engineering"
    GOODREADS_SORT      e.g. "avg_rating"
    GOODREADS_ORDER     "a" (ascending) or "d" (descending)
    NUM_BOOKS           max covers to show, default 20
    COVERS_PER_ROW      default 6
"""

import os
import re

import feedparser

GOODREADS_USER_ID = os.environ.get("GOODREADS_USER_ID", "183200963")
SHELF = os.environ.get("GOODREADS_SHELF", "engineering")
SORT = os.environ.get("GOODREADS_SORT", "avg_rating")
ORDER = os.environ.get("GOODREADS_ORDER", "a")
NUM_BOOKS = int(os.environ.get("NUM_BOOKS", "20"))
COVERS_PER_ROW = int(os.environ.get("COVERS_PER_ROW", "6"))

RSS_URL = (
    f"https://www.goodreads.com/review/list_rss/{GOODREADS_USER_ID}"
    f"?shelf={SHELF}&sort={SORT}&order={ORDER}"
)

README_PATH = "README.md"
START_MARKER = "<!-- GOODREADS-BOOKS:START -->"
END_MARKER = "<!-- GOODREADS-BOOKS:END -->"


def fetch_books():
    feed = feedparser.parse(RSS_URL)
    if not feed.entries:
        reason = getattr(feed, "bozo_exception", "no entries returned")
        raise RuntimeError(f"Could not read Goodreads RSS feed at {RSS_URL}: {reason}")

    books = []
    for entry in feed.entries[:NUM_BOOKS]:
        title = getattr(entry, "title", "Untitled").strip()
        link = getattr(entry, "link", "#")

        image = (
            getattr(entry, "book_large_image_url", None)
            or getattr(entry, "book_medium_image_url", None)
            or getattr(entry, "book_image_url", None)
        )
        if not image:
            # Fallback: some feed variants only put the cover inside the
            # HTML description as an <img> tag.
            desc = getattr(entry, "description", "") or getattr(entry, "summary", "")
            match = re.search(r'<img[^>]+src="([^"]+)"', desc)
            image = match.group(1) if match else ""

        books.append({"title": title, "link": link, "image": image})

    return books


def render_grid(books):
    if not books:
        return "_No books found on this shelf yet._"

    cells = [
        f'<a href="{b["link"]}" title="{b["title"]}">'
        f'<img src="{b["image"]}" alt="{b["title"]}" width="80" /></a>'
        for b in books
        if b["image"]
    ]

    rows = [cells[i : i + COVERS_PER_ROW] for i in range(0, len(cells), COVERS_PER_ROW)]
    body = "\n".join(
        "<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows
    )
    return f"<table>\n{body}\n</table>"


def update_readme(snippet):
    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    if START_MARKER not in content or END_MARKER not in content:
        raise RuntimeError(
            f"Couldn't find {START_MARKER} / {END_MARKER} in {README_PATH}. "
            "Add those two lines wherever you want the book grid to appear."
        )

    pattern = re.compile(re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER), re.DOTALL)
    new_block = f"{START_MARKER}\n{snippet}\n{END_MARKER}"
    content = pattern.sub(new_block, content)

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(content)


def main():
    books = fetch_books()
    snippet = render_grid(books)
    update_readme(snippet)
    print(f"Updated README.md with {len(books)} books from shelf '{SHELF}'.")


if __name__ == "__main__":
    main()
