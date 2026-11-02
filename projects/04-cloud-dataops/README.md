# 04 — Cloud Data Modernization & DataOps Framework

A runnable local medallion-pipeline demo: preserve a bronze copy of a synthetic event feed, validate and quarantine rows into silver, compute a daily gold summary with SQLite SQL, and write a run manifest with an input SHA-256.

## Run

```powershell
python projects/04-cloud-dataops/src/medallion.py
```

The default lakehouse is written beneath `projects/04-cloud-dataops/output/lakehouse/`:

- `bronze/events.csv` — byte-for-byte source copy
- `silver/clean_events.csv` — accepted and typed events
- `silver/quarantined_events.csv` — rejected rows and reasons
- `gold/daily_summary.csv` — event count and amount by event date
- `manifest.json` — source hash, record counts, and run status

## Data flow

```mermaid
flowchart LR
    I[events.csv] --> B[Bronze immutable input]
    B --> V[Validate ID, date, type, amount]
    V --> S[Silver clean events]
    V --> Q[Silver quarantine with reason]
    S --> G[Gold SQL daily aggregate]
    B --> M[Manifest with source SHA-256]
    S --> M
    Q --> M
    G --> M
```

## Class diagram

```mermaid
classDiagram
    class MedallionPipeline {
        +run(input_path, lakehouse_dir)
        +validate(row)
        +summarize(rows)
    }
    class LayerWriter {
        +copy_bronze(source, destination)
        +write_csv(path, headers, rows)
        +write_manifest(path, metadata)
    }
    MedallionPipeline --> LayerWriter
```

## Testing

```powershell
python -m unittest discover -s projects -p "test_*.py" -v
```

Tests cover accepted/rejected events, deterministic output, daily totals, and the bronze hash.

## Deployment

Run the command above locally to generate and inspect the layer files. The GitHub Pages site is a static portfolio overview; it does not run the pipeline.

The filesystem layout models medallion layers but is not an AWS service deployment. Adapting it to S3, Glue, or another cloud requires an account, least-privilege identity, encryption and retention policies, environment-specific configuration, and a reviewed infrastructure plan. No infrastructure is created automatically.
