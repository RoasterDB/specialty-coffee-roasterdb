# Kaggle deployment

Staging for the Kaggle dataset + starter notebook. Built for a **10.0 / 10.0 usability score**
(subtitle < 80 chars, 5 tags, declared license, file + column descriptions, full markdown
description) plus a **working starter notebook**.

Kaggle CLI is invoked as `python -m kaggle` (credentials at `~/.kaggle/kaggle.json`).
On Windows, always prefix with `$env:PYTHONUTF8=1;` so the CLI reads UTF-8 (avoids the
`'charmap' codec` crash on the em-dashes / `·` in the metadata).

## 1. Publish the dataset (first time)

```powershell
$env:PYTHONUTF8=1; python -m kaggle datasets create -p kaggle/dataset --dir-mode zip
```

Check ingestion status until it reads `ready`:

```powershell
python -m kaggle datasets status ahtiticheamine/roasterdb-specialty-coffee-sample
```

## 2. Push the starter notebook (attached to the dataset)

```powershell
$env:PYTHONUTF8=1; python -m kaggle kernels push -p kaggle/notebook
```

## 3. Later updates (new snapshot)

```powershell
# refresh the CSV, then:
$env:PYTHONUTF8=1; python -m kaggle datasets version -p kaggle/dataset -m "Snapshot 2026.08" -d
$env:PYTHONUTF8=1; python -m kaggle kernels push -p kaggle/notebook
```

`-d` purges remote files not present in the staging folder (prevents duplicate artifacts).

## Files

| File | Purpose |
| :--- | :--- |
| `dataset/roasterdb_sample.csv` | The 100-row sample (identical to `../samples/`) |
| `dataset/dataset-metadata.json` | Title, subtitle, tags, license, description, **all 20 column descriptions** |
| `notebook/roasterdb-starter-notebook.ipynb` | Working, pre-executed starter (load → preview → flavor & price analysis → provenance) |
| `notebook/kernel-metadata.json` | Kernel config; sources the dataset above |

## Notes

- The dataset `id` and the notebook's `dataset_sources` both use
  `ahtiticheamine/roasterdb-specialty-coffee-sample`. If you change the slug, change it in
  **both** files.
- Kaggle occasionally needs column descriptions confirmed once in the web **Data** tab if the
  CSV was ingested asynchronously — open the dataset after publish and verify the 10.0 score.
