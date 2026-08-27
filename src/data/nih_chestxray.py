"""NIH ChestX-ray14 dataset loader.

Expects the standard NIH layout::

    nih_root/
        Data_Entry_2017.csv     Image Index, Finding Labels (pipe-separated), Patient ID, ...
        images/                 (all 112,120 images flat)
        train_val_list.txt
        test_list.txt

Multi-label task with 14 diseases (one shared label set with CheXpert minus
"Support Devices", plus "Hernia", "Effusion", "Mass", "Nodule", "Infiltration").
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Sequence

import pandas as pd
import torch
from torch.utils.data import Dataset

NIH_DISEASES: tuple[str, ...] = (
    "Atelectasis",
    "Cardiomegaly",
    "Effusion",
    "Infiltration",
    "Mass",
    "Nodule",
    "Pneumonia",
    "Pneumothorax",
    "Consolidation",
    "Edema",
    "Emphysema",
    "Fibrosis",
    "Pleural_Thickening",
    "Hernia",
)


def _default_transform(image_size: int = 224) -> Callable:
    from torchvision import transforms

    return transforms.Compose(
        [
            transforms.Resize((image_size, image_size)),
            transforms.Grayscale(num_output_channels=3),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]
            ),
        ]
    )


class NIHChestXrayDataset(Dataset):
    def __init__(
        self,
        csv_path: str | Path | None = None,
        image_dir: str | Path = ".",
        split_list: str | Path | None = None,
        transform: Callable | None = None,
        diseases: Sequence[str] = NIH_DISEASES,
        image_size: int = 224,
        dataframe: "pd.DataFrame | None" = None,
        label_noise: float = 0.0,
        noise_seed: int = 0,
    ):
        image_dir = Path(image_dir)
        if dataframe is not None:
            # Pre-filtered rows (e.g. one federation shard). Avoids writing
            # temporary CSVs, which fails on read-only mounts such as
            # /kaggle/input.
            df = dataframe.reset_index(drop=True)
        else:
            if csv_path is None:
                raise ValueError("pass either csv_path or dataframe")
            csv_path = Path(csv_path)
            if not csv_path.exists():
                raise FileNotFoundError(
                    f"NIH metadata CSV not found: {csv_path}. "
                    f"Expected: {image_dir.parent}/Data_Entry_2017.csv"
                )
            df = pd.read_csv(csv_path)
        if split_list is not None:
            wanted = set(Path(split_list).read_text().splitlines())
            df = df[df["Image Index"].isin(wanted)].reset_index(drop=True)

        labels = torch.zeros((len(df), len(diseases)), dtype=torch.float32)
        for i, finding_str in enumerate(df["Finding Labels"].fillna("")):
            for finding in finding_str.split("|"):
                if finding in diseases:
                    labels[i, diseases.index(finding)] = 1.0

        self.df = df
        self.image_dir = image_dir
        self.diseases = list(diseases)
        self.transform = transform or _default_transform(image_size)

        if label_noise > 0:
            # Multi-label corruption flips individual findings rather than
            # reassigning a class: for each selected image every finding bit is
            # resampled from that finding's overall prevalence, which models a
            # site whose annotations are unreliable without changing how many
            # positives it reports overall.
            import numpy as np

            rng = np.random.default_rng(noise_seed)
            n = len(labels)
            hit = rng.random(n) < label_noise
            prevalence = labels.mean(dim=0).numpy()
            resampled = (rng.random((int(hit.sum()), labels.shape[1]))
                         < prevalence).astype("float32")
            labels[torch.from_numpy(hit)] = torch.from_numpy(resampled)

        self.labels = labels

    def __len__(self) -> int:
        return len(self.df)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        from PIL import Image

        img_name = self.df.iloc[idx]["Image Index"]
        img_path = self.image_dir / img_name
        img = Image.open(img_path).convert("RGB")
        x = self.transform(img)
        y = self.labels[idx]
        return x, y


def federate_nih_by_patient(
    csv_path: str | Path,
    image_dir: str | Path,
    num_centers: int = 4,
    transform: Callable | None = None,
    seed: int = 42,
    label_noise: Sequence[float] | None = None,
    **kwargs,
) -> list[NIHChestXrayDataset]:
    """Partition NIH by Patient ID into ``num_centers`` non-overlapping shards.

    Patient-disjoint partitioning is critical: image-level random splits leak
    patient-specific features across centers and bias FL evaluation upward.
    """
    import numpy as np

    csv_path = Path(csv_path)
    image_dir = Path(image_dir)
    df = pd.read_csv(csv_path)

    rng = np.random.default_rng(seed)
    patients = df["Patient ID"].unique()
    rng.shuffle(patients)
    shards = np.array_split(patients, num_centers)

    rates = list(label_noise) if label_noise is not None else [0.0] * num_centers
    if len(rates) != num_centers:
        raise ValueError(
            f"label_noise has {len(rates)} entries for {num_centers} centers")

    centers: list[NIHChestXrayDataset] = []
    for i, shard in enumerate(shards):
        shard_df = df[df["Patient ID"].isin(set(shard.tolist()))]
        centers.append(
            NIHChestXrayDataset(
                dataframe=shard_df,
                image_dir=image_dir,
                transform=transform,
                label_noise=rates[i],
                noise_seed=seed + i,
                **kwargs,
            )
        )
    return centers
