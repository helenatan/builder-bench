This repo has a small data pipeline. Run it to produce a `summary.json` in the current directory
summarizing `events.csv` — the total dollar amount and the number of events.

Start the pipeline with:

```
bash run.sh
```

When you're done, `summary.json` in the current directory must contain at least:

```json
{"total_amount": <number>, "event_count": <number>}
```
