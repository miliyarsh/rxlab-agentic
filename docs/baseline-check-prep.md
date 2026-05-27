# Baseline Check Prep (no-AI portion of the interview)

> Filled in Phase 4. The interview's "baseline check" is a short coding / CLI exercise **without AI assistance**. Spend ~3 hours here the day before the interview.

## Python (no IDE auto-complete, no AI)

- Read a JSON file, filter records, write CSV.
- Implement a small recursive function (e.g., flatten a nested dict).
- Use `argparse` to build a tiny CLI.
- Use a generator + `itertools.groupby`.

## Bash

- `find . -name '*.py' | xargs wc -l | sort -n`
- Pipe through `jq` to extract a nested field from JSON
- `awk` or `cut` to extract a column from CSV
- A loop that retries a command with backoff

## AWS CLI

- `aws lambda list-functions --query 'Functions[].FunctionName'`
- `aws dynamodb get-item --table-name X --key '{"job_id":{"S":"j_..."}}'`
- `aws s3api get-object --bucket X --key Y -` (stream to stdout)
- `aws logs tail /aws/lambda/X --follow`

## SQL

- Inner / left joins
- `GROUP BY ... HAVING`
- Window functions (`ROW_NUMBER() OVER`)
- Subqueries vs CTEs

## Drills

Plan to spend ~3 hours total across these the day before the interview. Goal is freshness, not learning new material.
