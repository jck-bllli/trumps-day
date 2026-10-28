# Daily research job: Trump's day in 5 quotes

The daily scheduled task follows this file. It covers **yesterday, as a calendar day in US Eastern time** (call it DATE).

## 1. Find everything he said on DATE

Search the web (several searches, sent together) for:
- Every speech, rally, remarks, press gaggle, press conference, interview, call-in and sit-down on DATE.
  Good places: rollcall.com/factbase, whitehouse.gov (briefings and remarks), C-SPAN, rev.com, singjupost.com,
  YouTube channels (White House, RSBN, C-SPAN), plus news coverage (AP, Reuters, Fox, CNN, The Hill, Politico).
- His Truth Social posts on DATE: trumpstruth.org status pages from search results, plus news coverage of posts.
  (GitHub Actions fetches the full post list for the page separately, so you only need the notable ones.)

For each event, record a title, a transcript link and a video link when they exist.

## 2. Pick 5 quotes

The vibe: **people can like him or hate him from the quotes, and both sides want to comment.** Pick lines that are
surprising, funny, boastful, bold, or sharp jabs at opponents. Avoid dry policy lines unless they're punchy.
Mix the topics; don't use five lines about the same thing.

Hard rules:
- **Word for word.** Every quote must match a primary source exactly: a full transcript, the video, or the post
  itself. Prefer a second source (news report) too. If you can't confirm the exact wording, don't use it.
  Never use a "post" that fact-checkers (Snopes, PolitiFact, AP) have flagged as fake.
- Keep enough surrounding words that the quote isn't misleading. Trim only at sentence boundaries.
- Quotes must be from DATE. If he has said the same line before, set `"said_before": true` and a short
  `"said_before_note"` (e.g. "First floated in September 2026").
- Skip: attacks on someone's religion, ethnicity, nationality or immigration background; slurs; sexual remarks;
  anything about deaths, shootings, disasters or other tragedies; threats of violence; claims about a person's
  health. These clash with the playful sound effects and get accounts reported.
- Jabs at opponents, nicknames, boasts and tall claims are fine. We present, we don't judge: no commentary.
- If a day is quiet, 3 or 4 strong quotes beat 5 weak ones (the video adapts). If he made no public remarks,
  quotes can come from posts (`where`: "Truth Social post").

## 3. Write days/DATE.json

```json
{
  "date": "2026-10-27",
  "intro_say": "Trump's day, in five quotes. Let's go!",
  "outro_say": "Love it or hate it, every speech and post from today is linked in the caption. Follow for tomorrow's five!",
  "quotes": [
    {
      "topic": "ON THE STRAIT OF HORMUZ",
      "emoji": "🚢",
      "where": "Rally · Corpus Christi, Texas",
      "quote": "We're thinking about renaming it the Trump Strait.",
      "intro_say": "On the Strait of Hormuz.",
      "sfx": "ding",
      "sources": ["https://full-transcript-url", "https://news-report-url"],
      "said_before": true,
      "said_before_note": "First floated in September 2026"
    }
  ],
  "day_log": {
    "speeches": [
      {"title": "Rally in Lubbock, Texas", "transcript": "example.com/transcript", "video": "youtube.com/watch?v=..."}
    ],
    "post_count": 34
  }
}
```

Field notes:
- `intro_say` / `outro_say`: say the real number ("in four quotes") when there are fewer than 5.
- `topic`: "ON ..." in caps, 26 characters max. `where`: 40 characters max, format "Type · City, State".
- `quote`: 190 characters max. Add `"quote_say"` only if the voice would misread something (numbers like
  "51st" → "fifty-first", abbreviations, symbols). The screen always shows `quote`.
- `intro_say`: a short neutral lead-in ("On Senator Ted Cruz."). Give context if the quote needs it
  ("And on Venezuela's oil, retelling a joke from oilman Harold Hamm.").
- `sfx`, matched to the mood: cash (money, tariffs, deals), gavel (courts, judges, laws), stamp (orders,
  signing, official moves), cheer (crowd moments, wins), applause (praise), chime (warm moments, prizes),
  drumroll (big reveals, punchlines), boing (zingers, odd moments), whoosh_up (bold plans), ding (anything else).
- `day_log.speeches`: every event from step 1. Links are written without `https://` (they show as plain text in
  the caption); empty string if none. `post_count` is optional (only if a source states it).

## 4. Render, check, push

```bash
bash render/setup.sh                 # once per machine
python3 produce.py days/DATE.json    # validates, voices, renders, adds to queue.json
```

Fix anything the validator reports. Then extract 2 frames (one mid-quote, the end card) with ffmpeg and look at
them: text fits, nothing overlaps. Check the caption in queue.json is under 2,200 characters.

Commit `days/DATE.json`, `videos/DATE.mp4`, `videos/DATE_cover.jpg` and `queue.json`, then
`git pull --rebase` and push to main. The push triggers the GitHub Actions workflow, which builds the receipts
page and posts to Instagram. Do not post to Instagram yourself, and don't edit posted.json, the workflow or secrets.
