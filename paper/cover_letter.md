# Cover letter — IEEE Access

*Replace the bracketed fields before submitting. Keep it to one page; Access
editors read these quickly.*

---

Dear Editor,

We submit **"Adaptive Heterogeneity-Aware Aggregation for Calibrated Federated
Learning in Medical Imaging"** for consideration in IEEE Access.

Federated learning lets hospitals train shared models without moving patient
data, but volume-weighted aggregation silently amplifies annotation noise at
any single site. We propose AHA-Fed, an aggregation rule that weights clients
by data volume, distance from the label-prior consensus, and a self-supervised
quality signal derived from local training loss. It reduces to FedAvg as a
strict special case, so any existing deployment can adopt it and recover
identical behaviour by zeroing two hyperparameters.

Three aspects may interest the reviewers:

**A convergence guarantee, not only an empirical result.** We prove the
softmax weights are bounded away from zero (Proposition 1), which places
AHA-Fed inside the class of weighted-averaging schemes the standard FedAvg
rate covers rather than requiring a separate analysis. The proposition is
asserted by unit tests, so it fails loudly if the scoring rule changes.

**A deployment diagnostic.** The quality term helps only when corruption moves
local loss further than ordinary differences between healthy sites do. That
ratio is computable from one round of ordinary federated training, before
committing to an aggregation rule: 2.37 on one of our corpora, where the
corrupted client is identified in 10 of 10 runs, and 0.46 on another, where it
is identified in 6. Diagnosing that failure also produced a fix, reported in
Section 5.7.

**Reproducibility.** Every number in the paper is traceable to a stored run
artifact, and the submission includes a script that re-checks each numeric
claim against those artifacts. All results are on real medical imaging —
PathMNIST, PneumoniaMNIST, and full-resolution NIH ChestX-ray14 — with no
synthetic or simulated data.

We also report three results that run against the method: it loses to every
baseline on binary chest radiography, its advantage disappears as the
federation grows past four clients, and under DP-SGD both aggregators fall to
chance. We state these as prominently as the positive findings, and Section
7.1 lists six limitations. We would rather a reviewer see the boundary of the
method from us than discover it themselves.

The manuscript is original, has not been published elsewhere, and is not under
consideration by another journal. All authors have approved the submission and
declare no competing interests. No external funding supported this work.

Thank you for your consideration.

Sincerely,

[Corresponding author name]
[Department, Institution]
[City, Country]
[email]

---

## Submission checklist

- [ ] Author names, affiliations, and corresponding-author email filled in
      (`paper/build_ieee_access.py`, or edit the .docx directly)
- [ ] ORCID iDs for all authors
- [ ] `paper/AHA_Fed_IEEE_Access.docx` opened in Word and read once — figures
      legible at column width, no table split awkwardly across a page break
- [ ] Figures also uploaded separately if Access requests source files
- [ ] Suggested reviewers, if the portal asks
- [ ] Graphical abstract, if you want one (optional for Access)

## Notes for the revision round

If a reviewer asks for more, these are the cheapest additions in order:

1. **NIH at ten seeds** — the corrupted-site comparison is at six; ten would
   settle whether the 12.9% ECE gap is real. About 17 GPU-hours.
2. **A second full-resolution corpus** — CheXpert or MIMIC-CXR. Both need
   credentialed access, so start the application early if this is likely.
3. **The relative-quality variant at full resolution** — currently tested only
   at 28×28. About 5 GPU-hours.
