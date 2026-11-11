# Send a batch to the client

The human sends; Claude prepares the file.

1. Re-export the client's master sheet and check every unsent Ready handle and email against all its tabs. Drop any repeat.
2. Make a client-clean copy of `outputs/creators.xlsx`: the Read me and Ready tabs only, no internal notes.
3. When the human confirms the send, mark those rows `"sent": "<date>"` in `process/rows.json` (back it up first). The live workbook then shows only unsent rows.
