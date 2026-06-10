Load `fixtures/postings.csv`.

Important: the same role is often posted in multiple cities. Treat one role as one opening —
**dedupe by company + title, NOT by location.**

Build a small table of unique openings per company. Write it to a file named
`unique_openings.csv` in the current directory, with exactly these columns:

    company,unique_openings

Keep this file accurate for the rest of our work.
