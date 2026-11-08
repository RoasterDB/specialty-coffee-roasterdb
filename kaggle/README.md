# Kaggle deployment

Staging for the Kaggle dataset + starter notebook. Built for a **10.0 / 10.0 usability score**
(subtitle < 80 chars, 5 tags, declared license, file + column descriptions, full markdown
description) plus a **working starter notebook**.

Kaggle CLI is invoked as `python -m kaggle` (credentials at `~/.kaggle/kaggle.json`).
On Windows, always prefix with `$env:PYTHONUTF8=1;` so the CLI reads UTF-8 (avoids the
`'charmap' codec` crash on the em-dashes / `·` in the metadata).

## 1. Publish the dataset (first time)

Upload from a **one-word staging folder**, made the same way as in section 3: new and empty, in a
scratch folder outside the repo, holding only the CSV and the metadata file. On Windows a `-p` path
with a `/` stops with `Errno 2` before the dataset is created (first note under section 3). `$repo`
is this checkout:

```powershell
$repo = "C:\path\to\RoasterDB-public"
mkdir kaggle_upload
cp "$repo\kaggle\dataset\roasterdb_sample.csv", "$repo\kaggle\dataset\dataset-metadata.json" kaggle_upload
$env:PYTHONUTF8=1; python -m kaggle datasets create -p kaggle_upload --dir-mode zip
```

Check ingestion status until it reads `ready`:

```powershell
python -m kaggle datasets status dataengineered/roasterdb-specialty-coffee-sample
```

## 2. Push the starter notebook (attached to the dataset)

```powershell
$env:PYTHONUTF8=1; python -m kaggle kernels push -p kaggle/notebook
```

## 3. Later updates (new snapshot)

Refresh `dataset/roasterdb_sample.csv` (and `dataset/dataset-metadata.json` if its text changed), then
upload a new version from a **one-word staging folder**. Create it new and empty in a scratch folder
outside the repo and put only the CSV and the metadata file in it: every other file in it is
uploaded too. `$repo` is this checkout:

```powershell
$repo = "C:\path\to\RoasterDB-public"
mkdir kaggle_upload
cp "$repo\kaggle\dataset\roasterdb_sample.csv", "$repo\kaggle\dataset\dataset-metadata.json" kaggle_upload

# 1. Compare the live card with the repo's before uploading
$env:PYTHONUTF8=1; $env:PYTHONIOENCODING="utf-8"
python -m kaggle datasets metadata -p kaggle_live dataengineered/roasterdb-specialty-coffee-sample
python -c "import json; a = json.load(open('kaggle_live/dataset-metadata.json', encoding='utf-8'))['info']; b = json.load(open(r'$repo\kaggle\dataset\dataset-metadata.json', encoding='utf-8')); print({k: set(a[k]) == set(b[k]) if k == 'keywords' else a[k] == b[k] for k in ('title', 'subtitle', 'description', 'keywords')})"

# 2. Upload
python -m kaggle datasets version -p kaggle_upload -m "Snapshot YYYY.MM"
```

Check ingestion as in step 1, then push the notebook from the repo root:

```powershell
$env:PYTHONUTF8=1; python -m kaggle kernels push -p kaggle/notebook
```

- **On Windows, `-p` must be a single folder name, with no `/`.** The CLI names its resume-cache file
  (`%TEMP%\.kaggle\uploads\<path>.json`) after the path of each file it uploads and replaces only `\`
  and `:` in that path. With `-p kaggle/dataset` the name keeps its `/`, which points into a cache
  folder that does not exist, and the command stops with `Errno 2` before a version is created.
- **Do not add `-d`.** It is short for `--delete-old-versions` (see `datasets version -h`) and
  deletes the dataset's older versions.
- **What a version upload changes:** the data file and, from `dataset-metadata.json`, the card's
  description, subtitle and keywords. It does not change the title or the licence (the CLI does not
  send them), and Kaggle keeps the previous version's column notes (the CLI sends them, but after
  this dataset's 2026-09-29 upload Kaggle still showed the previous version's notes). Set those
  three in the Kaggle web UI, logged in as the dataset's owner.
- **Compare first.** The upload replaces the live description, subtitle and keywords with the
  repo's, so an edit made on Kaggle is lost unless the repo file has it. The check prints `False`
  for a field whose text differs: if the live text is just the older one, go ahead; if it holds an
  edit the repo lacks, copy that into `dataset/dataset-metadata.json` (in a PR) first. Download into
  its own folder: the download writes `dataset-metadata.json` into `-p` and would overwrite the
  staged copy.

## Files

| File | Purpose |
| :--- | :--- |
| `dataset/roasterdb_sample.csv` | The 100-row sample (identical to `../samples/`) |
| `dataset/dataset-metadata.json` | Title, subtitle, tags, license, description, **all 20 column descriptions** |
| `notebook/roasterdb-starter-notebook.ipynb` | Working, pre-executed starter (load → preview → flavor & price analysis → provenance) |
| `notebook/kernel-metadata.json` | Kernel config; sources the dataset above |

## Notes

- The dataset `id` and the notebook's `dataset_sources` both use
  `dataengineered/roasterdb-specialty-coffee-sample`. If you change the slug, change it in
  **both** files.
- Kaggle occasionally needs column descriptions confirmed once in the web **Data** tab if the
  CSV was ingested asynchronously — open the dataset after publish and verify the 10.0 score.
