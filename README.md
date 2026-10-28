# Trump's Day in 5 Quotes

Automated daily Instagram Reel: five word-for-word quotes from the previous day (US Eastern), plus a
link-in-bio "receipts" page with every speech transcript, video and Truth Social post.

**How it runs**
1. ~4:47am Pacific: a scheduled Claude task follows `RESEARCH.md`: researches yesterday, verifies quotes,
   writes `days/DATE.json`, renders the video (`produce.py`) and pushes.
2. The push starts `.github/workflows/post.yml` on GitHub Actions: it fetches every post for the receipts page
   (`build_page.py` -> `docs/index.html`), posts the Reel (`post_next.py`) and saves the results.
   A backup run at 8:23am Pacific catches anything missed.

**Secrets** (Settings > Secrets and variables > Actions): `IG_ACCESS_TOKEN` (Instagram token),
`GH_PAT` (lets the workflow save Meta's renewed token).
**Receipts page**: Settings > Pages > Deploy from branch `main`, folder `/docs`.
Then it lives at https://jck-bllli.github.io/trumps-day/ (put that in the Instagram bio).

Unofficial recap. Not affiliated with Donald Trump or the White House.
