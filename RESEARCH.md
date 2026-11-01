# Daily research job: Trump's day in 6 quotes (two posts)

The daily scheduled task follows this file. It covers **yesterday, as a calendar day in US Eastern time** (call it DATE).

## 1. Find everything he said on DATE

Search the web (several searches, sent together) for:
- Every speech, rally, remarks, press gaggle, press conference, interview, call-in and sit-down on DATE.
  Good places: rollcall.com/factbase, whitehouse.gov (briefings and remarks), C-SPAN, rev.com, singjupost.com,
  YouTube channels (White House, RSBN, C-SPAN), plus news coverage (AP, Reuters, Fox, CNN, The Hill, Politico).
- His Truth Social posts on DATE: trumpstruth.org status pages from search results, plus news coverage of posts.
  (GitHub Actions fetches the full post list for the page separately, so you only need the notable ones.)

For each event, record a title, a transcript link and a video link when they exist.

## 2. Pick 6 quotes (morning post gets quotes 1-3, evening post gets 4-6)

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
- Interesting beats important. The best quote makes someone stop scrolling and want to argue in the comments:
  a bold claim, a strange comparison, a jab, a boast, a line that sounds made up but is real. Skip filler.
- Order matters: quote 1 and quote 4 open each post, so put the two strongest there.
- If a day is quiet, 4 or 5 strong quotes beat 6 weak ones (5 = 3 morning + 2 evening; 3 or fewer = morning only). If he made no public remarks,
  quotes can come from posts (`where`: "Truth Social post").

## 2b. Turn some quotes into mini-games

Each post rotates through a visual style automatically. Inside it, make about two of every three quotes a game
(mix the types within a post; a plain quote is fine too). The joke is in the game, never in commentary.
- `topic`: "What was he talking about?" Viewers see the quote, then 3 options for the topic. Use when the
  real context is surprising. The reveal is spoken from `intro_say`, so write `intro_say` as the answer.
- `blank`: "Finish the quote." One key word or phrase is hidden. `blank` must appear exactly once in the quote,
  and the right option must equal `blank` exactly.
- `number`: same as blank, but the hidden part is a number (`"blank": "$25 trillion"`). The number must not
  appear anywhere else in the quote, or it gives the answer away. Add `"blank_say"` if the voice needs words.
Wrong options must be plausible but clearly wrong, real-sounding, and never invented quotes or claims about
anyone. Options are 28 characters max. `answer` is 0, 1 or 2 (vary it).
- Optional `highlight`: an exact piece of the quote (2 to 6 words) to mark in red, the most striking part.

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
      "said_before_note": "First floated in September 2026",
      "highlight": "the Trump Strait"
    },
    {
      "topic": "ON THE NEW ARCH",
      "emoji": "🏛️",
      "where": "Remarks · Palm Beach, Florida",
      "quote": "The arch is going to be more beautiful than the Arc de Triomphe.",
      "intro_say": "On his planned arch in Washington.",
      "sfx": "whoosh_up",
      "sources": ["https://..."],
      "game": {"type": "blank", "blank": "Arc de Triomphe", "options": ["Eiffel Tower", "Taj Mahal", "Arc de Triomphe"], "answer": 2}
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
- `intro_say` / `outro_say` at the top level are kept for the receipts page; the videos don't use them.
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

## 4. Check and push (the home PC renders)

```bash
python3 -c "import json,produce; produce.validate(json.load(open('days/DATE.json')))"
```

Fix anything the validator reports. Do not render: Jack's home PC does that.

Commit only `days/DATE.json`, then `git pull --rebase` and push to main. The push starts `render.yml` on the
home PC, which renders both videos, adds them to queue.json and starts the post workflow. The morning post goes
out right away; the evening post waits until 4:17pm Pacific. If the PC is offline, the
8:23am PT backup run renders in the cloud and posts. Do not post to Instagram yourself, and don't edit
posted.json, queue.json, the workflows or secrets.
