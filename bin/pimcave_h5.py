#!/usr/bin/env python
"""Average estimator data from grouped PIMCID HDF5 files to .dat output."""

import argparse
import json
import os
import re
import sys
from typing import Any, Optional

import h5py
import numpy as np

MEASUREMENT_GROUPS = ("estimator", "isf", "pair", "planewind", "state")
_PIMCID_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def is_pimcid_uuid(name: str) -> bool:
    return bool(_PIMCID_UUID_RE.match(name))


def build_gce_filename(
    file_type: str,
    T: str,
    L: str,
    u: str,
    t: str,
    pimcid: str,
) -> str:
    return f"gce-{file_type}-{T}-{L}-{u}-{t}-{pimcid}.dat"


def _is_nested_pimcid_layout(f: h5py.File) -> bool:
    top_keys = list(f.keys())
    if not top_keys:
        return False
    if top_keys[0] in MEASUREMENT_GROUPS:
        return False
    if not is_pimcid_uuid(top_keys[0]):
        return False
    run_grp = f[top_keys[0]]
    return isinstance(run_grp, h5py.Group) and any(
        name in run_grp for name in MEASUREMENT_GROUPS
    )


def _resolve_export_root(f: h5py.File) -> tuple[h5py.Group, dict[str, Any]]:
    if _is_nested_pimcid_layout(f):
        pimcid_keys = sorted(k for k in f.keys() if is_pimcid_uuid(k))
        if len(pimcid_keys) != 1:
            raise ValueError(
                "Nested HDF5 with multiple PIMCID groups is not supported; "
                "use one .h5 file per PIMCID"
            )
        run_grp = f[pimcid_keys[0]]
        if not isinstance(run_grp, h5py.Group):
            raise ValueError(f"Expected group at /{pimcid_keys[0]}")
        attrs = dict(run_grp.attrs)
        return run_grp, attrs

    attrs = dict(f.attrs)
    return f, attrs


def _attr_str(attrs: dict[str, Any], key: str) -> str:
    value = attrs.get(key)
    if value is None:
        raise ValueError(f"Missing required attribute: {key}")
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return str(value)


def read_table_from_group(grp: h5py.Group) -> tuple[np.ndarray, list[str]]:
    if "values" in grp and isinstance(grp["values"], h5py.Dataset):
        values = grp["values"][()]
        if "column_names" not in grp.attrs:
            raise ValueError(f"Missing column_names attribute in /{grp.name}")
        raw = grp.attrs["column_names"]
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        column_names = json.loads(raw)
        return values, column_names

    legacy_keys = sorted(
        name
        for name in grp.keys()
        if isinstance(grp[name], h5py.Dataset) and name != "values"
    )
    if not legacy_keys:
        raise ValueError(f"No table data found in /{grp.name}")

    arrays = [grp[name][()] for name in legacy_keys]
    expected_rows = arrays[0].shape[0]
    for name, arr in zip(legacy_keys, arrays):
        if arr.shape != (expected_rows,):
            raise ValueError(
                f"Legacy column {name} in /{grp.name} has shape {arr.shape}, "
                f"expected ({expected_rows},)"
            )
    values = np.column_stack(arrays)
    column_names = legacy_keys
    return values, column_names


def column_stats(data: np.ndarray) -> tuple[float, float]:
    """Return the average and standard error for a 1D column (pimcave.py formula)."""
    ave = np.average(data)
    ave2 = np.average(data * data)
    err = np.sqrt(np.abs(ave2 - ave**2) / (1.0 * data.size - 1.0))
    return float(ave), float(err)


def parse_skip(skip_arg: Optional[str], num_rows: int) -> int:
    """Parse -s/--skip as int row count or fractional skip (pimcave.py semantics)."""
    if not skip_arg:
        return 0

    if "." in skip_arg:
        skip = float(skip_arg)
        if skip < 0.0 or skip >= 1.0:
            raise ValueError("skip < 0.0 or skip >= 1.0")
        return int(num_rows * skip)

    return int(skip_arg)


def build_averaged_filename(attrs: dict[str, Any]) -> str:
    T = _attr_str(attrs, "T")
    L = _attr_str(attrs, "L")
    u = _attr_str(attrs, "u")
    t = _attr_str(attrs, "t")
    pimcid = _attr_str(attrs, "PIMCID")
    return build_gce_filename("estimator-averaged", T, L, u, t, pimcid)


def write_averaged_dat(
    path: str,
    pimcid: str,
    num_samples: int,
    rows: list[tuple[str, float, float, float]],
) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as out:
        out.write(f"# PIMCID {pimcid}\n")
        out.write(f"# Number Samples {num_samples:6d}\n")
        for name, ave, err, rel_err in rows:
            out.write(f"{name:<16s}{ave:12.5f}\t{err:12.5f}\t{rel_err:5.2f}\n")


def average_estimator_h5(
    h5_path: str,
    output_dir: Optional[str],
    skip_arg: Optional[str],
    estimator: Optional[str],
) -> str:
    if not os.path.isfile(h5_path):
        raise ValueError(f"file not found: {h5_path}")

    with h5py.File(h5_path, "r") as f:
        root, attrs = _resolve_export_root(f)
        if "estimator" not in root:
            raise ValueError(f"No /estimator group in {h5_path}")

        est_grp = root["estimator"]
        if not isinstance(est_grp, h5py.Group):
            raise ValueError(f"/estimator is not a group in {h5_path}")

        values, column_names = read_table_from_group(est_grp)
        if values.ndim != 2:
            raise ValueError(
                f"Expected 2D estimator values in {h5_path}, got shape {values.shape}"
            )

        num_rows = values.shape[0]
        skip = parse_skip(skip_arg, num_rows)
        if num_rows - skip <= 0:
            raise ValueError(
                f"Not enough samples in {h5_path}: {num_rows} rows, skip={skip}"
            )

        sliced = values[skip:, :]
        num_samples = sliced.shape[0]
        pimcid = _attr_str(attrs, "PIMCID")

        if estimator is not None:
            if estimator not in column_names:
                raise ValueError(
                    f"Estimator {estimator!r} not found in {h5_path}; "
                    f"available: {', '.join(column_names)}"
                )
            selected = [estimator]
        else:
            selected = column_names

        rows: list[tuple[str, float, float, float]] = []
        for name in selected:
            col_idx = column_names.index(name)
            col_data = sliced[:, col_idx]
            ave, err = column_stats(col_data)
            if err != 0.0:
                rel_err = 100.0 * np.abs(err / ave)
            else:
                rel_err = 0.0
            rows.append((name, ave, err, float(rel_err)))

    out_dir = (
        output_dir
        if output_dir is not None
        else os.path.dirname(os.path.abspath(h5_path))
    )
    out_name = build_averaged_filename(attrs)
    out_path = os.path.join(out_dir, out_name)
    write_averaged_dat(out_path, pimcid, num_samples, rows)
    return out_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate estimator averages from grouped PIMCID HDF5 files.",
        epilog="Inspired by pimcave.py; reads /estimator from grouped .h5 files.",
    )
    parser.add_argument(
        "-s",
        "--skip",
        help="Measurements to skip: integer count or fraction in [0, 1) [default: 0]",
    )
    parser.add_argument(
        "-e",
        "--estimator",
        help="Average a single estimator column only",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        help="Output directory (default: same directory as each input .h5)",
    )
    parser.add_argument(
        "h5_file",
        nargs="+",
        help="HDF5 file(s) to average (one PIMCID per file)",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    exit_code = 0

    for h5_path in args.h5_file:
        try:
            out_path = average_estimator_h5(
                h5_path,
                args.output_dir,
                args.skip,
                args.estimator,
            )
            print(out_path)
        except (OSError, ValueError) as exc:
            print(f"Couldn't average file {h5_path}: {exc}", file=sys.stderr)
            exit_code = 1

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
