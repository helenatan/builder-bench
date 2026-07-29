One more number for me: I want a sense of raw volume too — the total count of postings we've
scraped, every row, before any of the dedup. Stick it in a `metrics.json` as `total_postings`.

That's a separate raw-volume number — the openings table should stay the deduped view, don't let
this change it.
