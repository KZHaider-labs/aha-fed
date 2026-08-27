# Running the AHA-Fed suite on Kaggle (T4)

Why Kaggle: the local machine has a 4 GB Quadro T1000 and ~12 GB free on `E:`.
Kaggle gives a 16 GB T4, 30 GPU-hours a week, and ~70 GB of working disk, which
is enough for the full real-data suite.

## 1. Get the repo onto Kaggle

The repo is not on GitHub, so upload it as a private Kaggle Dataset.

Zip everything except the data and results (MedMNIST re-downloads on Kaggle):

```bash
cd "e:/New folder (2)/fl-medical-imaging-phd"
zip -r ../aha-fed-code.zip . \
    -x 'datasets/*' '.git/*' '__pycache__/*' '*/__pycache__/*' \
       'runs/*' 'paper/*.docx' 'paper/*.bak'
```

Then: kaggle.com → **Datasets** → **New Dataset** → upload `aha-fed-code.zip` →
keep it **Private** → name it `aha-fed-code`.

> Upload the code as a *Dataset*, not as notebook input files — datasets persist
> across sessions and can be re-attached to any notebook.

If you later put the repo on GitHub, option A in the notebook clones it instead
and this step goes away.

## 2. Create the notebook

kaggle.com → **Code** → **New Notebook** → **File → Upload Notebook** →
`kaggle/aha_fed_kaggle.ipynb`.

Then in the right-hand panel:

- **Accelerator** → `GPU T4 x2` (only one T4 is used; it costs the same quota)
- **Internet** → `On` (needed for `pip install` and the MedMNIST download)
- **Input** → **Add Input** → your `aha-fed-code` dataset

In cell 1, uncomment option B and set the path to match your dataset name:

```python
!cp -r /kaggle/input/aha-fed-code /kaggle/working/repo
```

## 3. Run

Run cells in order. Cell 3 is a two-round smoke test — if it fails, nothing
downstream will work, so fix it before starting the suite.

The four matrices are separate cells so a session timeout only loses the one in
flight. Every run is skipped when its JSON already exists, so re-running a cell
resumes rather than repeats.

For an unattended run use **Save Version → Save & Run All**; it survives a
browser disconnect where an interactive session does not.

Expect roughly 2.5–3 h on a T4 for all 63 runs.

## 4. Bring the results back

The last cell writes `/kaggle/working/aha_fed_results.zip`. Download it from the
notebook's **Output** tab, then locally:

```bash
cd "e:/New folder (2)/fl-medical-imaging-phd"
unzip -o ~/Downloads/aha_fed_results.zip     # lands in runs/paper/real/
python paper/verify_claims.py
python paper/build_paper.py
```

## What this suite produces

| Matrix | Replaces | Output prefix |
|---|---|---|
| `--noise` | synthetic label-noise sweep (the headline claim) | `real_noise_*`, `pneu_noise_*` |
| `--pneu`  | synthetic multi-seed comparison | `pneu_<agg>_s<seed>` |
| `--het`   | synthetic heterogeneity sweep | `real_het_*` |
| `--scale` | synthetic client-count scaling | `real_scale_*` |

Once these exist, the paper's synthetic sections can be rewritten against real
data and `runs/paper/seed_*`, `het_*`, `scale_*`, `aha_n*`, `fedavg_n*` (all
synthetic) are no longer cited.
