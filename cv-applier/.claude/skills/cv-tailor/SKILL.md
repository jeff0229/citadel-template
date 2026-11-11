---
name: cv-tailor
description: Run one job application end to end. Audits the CV against a job description, repositions, aligns keywords, converts bullets to outcomes, rebuilds the CV and cover letter, and renders verified PDFs. Use whenever a job title, job description or company name appears, or when asked to tailor, audit or rebuild a CV or cover letter.
---

# cv-tailor

Run one application end to end. Read `CLAUDE.md` at the repo root first, it carries the hard rules and the style. Read `data/verified_facts.md` before writing any date or figure.

## Gate

Do not start without all of these. Ask, do not guess.

1. Target role title
2. Full job description, pasted
3. Company name
4. Which base to use, default `data/master_cv.md`
5. Whether the role sits inside or outside the current track

If several job descriptions arrive, ask which one or run them separately.

## Hard rules, above everything else

1. Every bullet ends at the employer's work.
2. One claim, not a credential list.
3. Nothing ships unless the candidate confirmed it. Ask for missing numbers, do not bracket and ship.
4. The sector paragraph names a live pressure this year, researched fresh, never from the company website.
5. Right-to-work wording only where `data/verified_facts.md` says it goes, in its exact wording.
6. Flag a seniority or structural gap once, then drop it.
7. Dates come from `data/verified_facts.md`, never from a CV file.

## Steps

**1. Audit, diagnostic only.** Estimated ATS score out of 100 marked as an estimate. 15 to 20 ranked missing keywords. Top 3 red flags visible in ten seconds. Section relevance 1 to 10 with reasons. Weak phrasing quoted verbatim. Action plan split critical 1 to 3, important 4 to 6, fine tuning 7 to 10. No rewriting.

**2. Positioning.** Pull core responsibilities, required skills, tools, seniority signals and implied success metrics from the JD. Write the summary at 50 to 70 words across three or four lines: strongest credential for this role, quantified achievement, sector terminology from the advert, specific value delivered.

**3. Keywords.** Map hard skills, tools, domain terms and stated soft skills. List gaps and irrelevant terms. Plan placement by section with mention counts. Five terminology swaps. Flag parsing risks. No stuffing.

**4. Bullets.** XYZ, accomplished X as measured by Y by doing Z, or STAR where XYZ does not fit. 15 to 25 words. Past tense. Verbs from your power-verb list. Return original, rewrite, rationale, suggested metric range, verb chosen. Prioritise revenue, cost, time, quality, volume, risk. Cut duties without outcomes, filler, duplicates.

**5. Structure.** Header, summary, key skills, experience reverse chronological, education and extras last. Put education first where the market expects it. Strongest two bullets first in each role. Key skills block of 8 to 12 items. Top third of page one carries title alignment, two or three quantified achievements, core skills.

**6. Tone.** Active voice, no filler, no vague claims. Every bullet carries an outcome. No line past two clauses. No repeated verb across adjacent bullets.

**7. Cover letter.** Use `data/cover_letter_bank.md`. Swap paragraph two from the bank. Research the sector paragraph fresh. One page: why this employer, why the candidate, what happens next.

**8. Output.** Write to `applications/<company>_<role>/`. Produce CV markdown, letter markdown, both PDFs, a keyword coverage checklist, an ATS-safe plain text CV, and a list of open questions.

## Build and verify

```bash
python3 scripts/build.py applications/<dir>/cv.md
python3 scripts/verify.py applications/<dir>/cv.pdf
python3 scripts/build.py applications/<dir>/letter.md --letter
python3 scripts/verify.py applications/<dir>/letter.pdf
```

Every check in `verify.py` must pass before the document is called finished. A missing link annotation, a leaked source note, or a stale string is a failed build, not a cosmetic issue.

## After shipping

Append the application to `logs/application_history.md` with employer, role, reference, date and status. Update the status when a reply arrives.
