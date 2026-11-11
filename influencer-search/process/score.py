"""Creator search: scoring, review and workbook. Run from process/ with python -I.

  python -I score.py                     list new numbers passes from results.jsonl and write review images
  python -I score.py add ready '<json>'  add a reviewed row (handle, name, email, based, content) and rebuild
  python -I score.py reject <handle> <why>   reviewed and left out, with the reason
  python -I score.py count

results.jsonl holds one JSON object per checked profile, from whatever source you use (a sanctioned API,
a vendor export, or manual checks). Fields: h (handle), f (followers), em (list of emails), bio,
vs (latest reel views, newest first), k9 (how many of the latest 9 cleared the view bar), latest
(newest reel date, YYYY-MM-DD), based (account country). Screenshots go to shots/<handle>.png and
shots/<handle>_reels.png for review images. The numbers rule below is set in BRIEF; a numbers pass
still needs the visual review against the full brief in CLAUDE.md.
"""
import datetime, json, os, sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
D = os.path.dirname(os.path.abspath(__file__))
F = lambda n: os.path.join(D, n)
ROWS = F("rows.json")
REJ = F("rejected.json")
OUT = os.path.join(os.path.dirname(D), "outputs", "creators.xlsx")
FMIN = 10000  # minimum followers (exclusive); set to your brief
# Rows carrying "sent" went to the client already; the live workbook shows only unsent rows.


def load(p, default):
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else default


def results():
    best = {}
    if os.path.exists(F("results.jsonl")):
        for line in open(F("results.jsonl"), encoding="utf-8"):
            try:
                d = json.loads(line)
            except Exception:
                continue
            best[d["h"]] = d
    return best


def is_pass(d, cutoff):
    return (d.get("f") or 0) > FMIN and d.get("em") and (d.get("k9") or 0) >= 6 and (d.get("latest") or "") >= cutoff


def review_image(h):
    from PIL import Image
    os.makedirs(F("review"), exist_ok=True)
    out = F("review/%s.jpg" % h)
    if os.path.exists(out):
        return out
    ims = []
    for name in (h + ".png", h + "_reels.png"):
        p = os.path.join(F("shots"), name)
        if os.path.exists(p):
            im = Image.open(p).convert("RGB")
            im = im.crop((0, 0, im.width, min(im.height, 1000)))
            ims.append(im.resize((im.width // 2, im.height // 2)))
    if not ims:
        return None
    w = sum(i.width for i in ims)
    hh = max(i.height for i in ims)
    canvas = Image.new("RGB", (w, hh), "white")
    x = 0
    for i in ims:
        canvas.paste(i, (x, 0))
        x += i.width
    canvas.save(out, quality=70)
    return out


def score():
    cutoff = (datetime.date.today() - datetime.timedelta(days=14)).isoformat()
    rows = load(ROWS, {"ready": [], "held": []})
    seen = {r["handle"] for r in rows["ready"] + rows["held"]} | set(load(REJ, {}))
    res = results()
    n = sum(1 for d in res.values())
    inb = sum(1 for d in res.values() if (d.get("f") or 0) > FMIN)
    passes = [d for d in res.values() if is_pass(d, cutoff)]
    new = [d for d in passes if d["h"] not in seen]
    print("checked %d, in band %d, numbers passes %d, new to review %d" % (n, inb, len(passes), len(new)))
    for d in new:
        print("PASS %s f=%s k9=%s latest=%s based=%s em=%s src=%s\n  vs=%s\n  bio=%s\n  about=%s\n  img=%s" % (
            d["h"], d.get("f"), d.get("k9"), d.get("latest"), d.get("based"), d.get("em"), d.get("src"),
            d.get("vs"), d.get("bio"), d.get("about") or d.get("basedErr"), review_image(d["h"])))


def add(kind, row):
    rows = load(ROWS, {"ready": [], "held": []})
    row = json.loads(row)
    if row["handle"] in {r["handle"] for r in rows["ready"] + rows["held"]}:
        print("already added:", row["handle"])
        return
    d = results().get(row["handle"], {})
    vs = (d.get("vs") or [])[:9]
    row.setdefault("followers", d.get("f"))
    row.setdefault("reels", " ".join(str(v) for v in vs))
    row.setdefault("k9", d.get("k9"))
    row.setdefault("last", d.get("latest"))
    row.setdefault("checked", datetime.date.today().isoformat())
    if kind == "held" and not row.get("why"):
        sys.exit("held rows need a why")
    rows["ready" if kind == "ready" else "held"].append(row)
    json.dump(rows, open(ROWS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    build()
    count()


def reject(h, why):
    rej = load(REJ, {})
    rej[h] = why
    json.dump(rej, open(REJ, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("rejected", h, "-", why, "| total rejected", len(rej))


def build():
    import openpyxl
    from openpyxl.styles import Font
    rows = load(ROWS, {"ready": [], "held": []})
    rows["ready"] = [x for x in rows["ready"] if not x.get("sent")]
    link = lambda h: "https://www.instagram.com/%s/" % h
    wb = openpyxl.Workbook()
    rm = wb.active
    rm.title = "Read me"
    for ln in [
        "Creator shortlist (unsent rows)",
        None,
        "Ready to send: %d new creators that meet the full brief." % len(rows["ready"]),
        "Reel rule: at least 6 of the latest 9 unpinned reels at 1,000+ views, and the newest reel within the last two weeks.",
        "View counts were read logged in. 'Based' is Instagram's own 'About this account' country unless it says otherwise.",
        "Each row was checked against its profile and reels screenshots for age, polish, mum or family content, UGC selling and agency emails.",
        "Brief: US; over 10,000 followers; personal email in bio; young; no mom or family content; everyday, not polished; not UGC; posting recently.",
        "None of these is in the client's master sheet or any earlier delivery.",
    ]:
        rm.append([ln])
    rm.column_dimensions["A"].width = 120
    ws = wb.create_sheet("Ready to send")
    head = ["Handle", "Link", "Followers", "First name", "Email", "Based", "Content", "Latest 9 reel views (newest first)", "Reels at 1,000+ (of 9)", "Last reel", "Checked live"]
    ws.append(head)
    for c in ws[1]:
        c.font = Font(bold=True)
    for x in rows["ready"]:
        ws.append([x["handle"], link(x["handle"]), x.get("followers"), x.get("name"), x.get("email"), x.get("based"), x.get("content"), x.get("reels"), x.get("k9"), x.get("last"), x.get("checked")])
    for i, h in enumerate(head):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i + 1)].width = 44 if "views" in h or h == "Content" else 22
    fl = wb.create_sheet("Held for your call")
    h2 = ["Handle", "Link", "Followers", "Email", "Based", "Latest 9 reel views (newest first)", "Reels at 1,000+ (of 9)", "Last reel", "Why held"]
    fl.append(h2)
    for c in fl[1]:
        c.font = Font(bold=True)
    for x in rows["held"]:
        fl.append([x["handle"], link(x["handle"]), x.get("followers"), x.get("email"), x.get("based"), x.get("reels"), x.get("k9"), x.get("last"), x.get("why")])
    for i, h in enumerate(h2):
        fl.column_dimensions[openpyxl.utils.get_column_letter(i + 1)].width = 60 if h == "Why held" else 24
    wb.save(OUT)


def count():
    rows = load(ROWS, {"ready": [], "held": []})
    new = [x for x in rows["ready"] if not x.get("sent")]
    print("Ready %d (unsent; %d already sent), Held %d, rejected %d" % (len(new), len(rows["ready"]) - len(new), len(rows["held"]), len(load(REJ, {}))))


if __name__ == "__main__":
    a = sys.argv[1:] or ["score"]
    if a[0] == "score":
        score()
    elif a[0] == "add":
        add(a[1], a[2])
    elif a[0] == "reject":
        reject(a[1], " ".join(a[2:]))
    elif a[0] == "count":
        count()
