# Review cycle

Run on a schedule (for example every 30 minutes while a search is running) and whenever the human asks for the count. The brief in `CLAUDE.md` is the only test.

1. From `process/`, run `python -I score.py`. It lists each new numbers pass with its followers, views, newest post, account country, email and bio, and writes a review image.
2. Reject on the text first: wrong country, agency or management email, parent or family, UGC, business or page, adult content. `python -I score.py reject <handle> <why>`.
3. For the rest, build contact sheets: `python -I sheets.py sheets_<time> <handles...>` (4 per image). Check each: is it a person, is there parent or family content, is it an ad-only feed, is there nudity or suggestive content?
4. Add passes with `python -I score.py add ready '<json>'` (handle, name, email, based, content). Borderline is out: reject anything you cannot confirm.
5. Run `python -I target.py` and report in one or two lines: new Ready and the unsent total.
