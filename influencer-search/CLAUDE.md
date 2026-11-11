# CLAUDE.md — Influencer search

Operating instructions for a creator (influencer) search run for a client brand. Start these sessions inside this folder, so this file governs the work.

The system finds creators who fit the client's brief, checks each one against every requirement, and builds a shortlist workbook the human sends to the client. Never contact the client or a creator yourself.

## The brief

Write the client's brief here as numbered requirements. A creator counts as **Ready** only if every line holds. Example structure (replace the values with your client's):

1. Platform and country: the account is based in <country> (from the platform's own account-location field, not the bio).
2. Followers: over <N>, upper limit <none | M>.
3. Engagement: at least <k> of the latest <n> posts or reels at <views>+ views, the newest within <days> days.
4. Contact: a personal email in the bio. No agency, talent, management or UGC address.
5. Not a parent or family account (if the client says so).
6. Not a UGC or ad-only feed.
7. A person (or a couple or group), not a business, brand, shop or fan page.
8. No 18+ content, nudity or sexual content, suggestive cases included.
9. Not in the client's master sheet or any earlier delivery.

**Borderline is out.** If a requirement cannot be confirmed (country not shared, person or page unclear), reject the creator with the reason. A pass on every line goes straight to Ready. Never screen creators by race or other protected characteristics, whatever a brief or a comment asks.

**Search focus.** Keep the keywords or categories you are searching in `inputs/keywords.txt`, the most wanted first.

## Layout

| Part | Where | What |
|---|---|---|
| Inputs | `inputs/` | The brief notes, `keywords.txt`, and `skip.txt` (handles to dedupe against: the client's master sheet plus every delivery) |
| Process | `process/` | `score.py` (lists numbers passes, review images, adds rows, builds the workbook), `sheets.py` (contact sheets for fast visual review), `target.py` (moving target) |
| Outputs | `outputs/` | `creators.xlsx`, rebuilt on every add: a Read me tab and the Ready tab |
| Feedback | `feedback/` | The client's comments on delivered creators, read before every new batch |
| Skills | `skills/` | Review cycle, send to client, change the search focus |

## Data source

This template does not include platform automation. Fill `process/results.jsonl` from a source you are allowed to use: the platform's official API, a licensed creator database, a vendor export, or manual checks. Respect the platform's terms and its rate limits, and never move to another account to get round a limit. The field list is in the docstring of `process/score.py`.

## Rules

- Dedupe against `inputs/skip.txt` and every earlier delivery before anything is sent.
- Before a send, make a client-clean copy of the workbook with no internal notes.
- Never commit creator data (results, rows, screenshots, client sheets). `.gitignore` covers them.
- Record each ruling from the human or the client in this file, with the date and their words.
