Hey — quick one. We've been scraping job postings into `fixtures/postings.csv`, and I want a read
on how many roles each company actually has open right now.

One thing to watch: our scraper lists the same job separately for every city it's hiring in, so a
single opening can show up five or six times. I don't care about the per-city breakdown — I just
want the real number of distinct openings each company has.

Can you pull together a little table — one row per company, with how many openings they've got —
and drop it in a CSV I can open later? `unique_openings.csv` in this folder is fine. We'll keep
building on this, so try to get it right.
