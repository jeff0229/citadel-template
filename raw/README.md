# raw/

The PDF wing of the archive. Contents are immutable; only moving a PDF to a better topic folder is allowed.

- Make one numbered subfolder per topic: `01-<topic>/`, `02-<topic>/`, and so on.
- `99-unclassified/` holds PDFs not yet triaged. A PDF dropped at the top level of `raw/` is a new drop: `new-drop.sh` reports it, and the ingest files it into its topic folder.
- `new-drop.sh` also reports every PDF that no source page claims, by content (the source page whose longest quote is in that PDF), never by filename.
- Folders starting `00-` hold your own drafts and rubrics and are excluded from the un-ingested sweep.
