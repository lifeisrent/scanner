"""
Market event poster scanner utilities.

Provides functions to extract text from poster images using OCR and export the
results into spreadsheet-friendly formats for downstream processing.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable, List, Sequence

import pandas as pd
from PIL import Image
import pytesseract
from pytesseract import Output


SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"}


@dataclass
class DetectedText:
    """A single text detection result."""

    source: Path
    text: str
    confidence: float
    left: int
    top: int
    width: int
    height: int

    @property
    def bbox(self) -> tuple[int, int, int, int]:
        """Return the bounding box (left, top, right, bottom)."""
        return (self.left, self.top, self.left + self.width, self.top + self.height)


def _is_image_file(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS


def scan_image(
    path: Path,
    *,
    min_confidence: float = 50.0,
    language: str = "eng",
    psm: int | None = 3,
    resize: float | None = None,
) -> List[DetectedText]:
    """Extract text from a single image using Tesseract OCR.

    Args:
        path: Path to an image file.
        min_confidence: Minimum confidence (0-100) required to keep a detected word.
        language: Tesseract language code(s), e.g. ``"eng"`` or ``"kor+eng"``.
        psm: Page segmentation mode (``--psm``) passed to Tesseract. ``None`` means
            use the default configured value.
        resize: Optional scaling factor to enlarge small-text posters before OCR,
            e.g. ``2.0`` doubles width/height.

    Returns:
        A list of ``DetectedText`` entries for each detected word.
    """

    if not path.is_file():
        raise FileNotFoundError(f"Image file not found: {path}")

    image = Image.open(path).convert("RGB")
    if resize and resize > 0:
        new_size = (int(image.width * resize), int(image.height * resize))
        image = image.resize(new_size)

    config_parts: list[str] = []
    if psm is not None:
        config_parts.append(f"--psm {psm}")
    config_value = " ".join(config_parts)

    ocr_data = pytesseract.image_to_data(
        image,
        lang=language,
        config=config_value,
        output_type=Output.DICT,
    )

    entries: List[DetectedText] = []
    for idx, text in enumerate(ocr_data["text"]):
        cleaned_text = text.strip()
        if not cleaned_text:
            continue

        confidence_value = float(ocr_data["conf"][idx])
        if confidence_value < min_confidence:
            continue

        entries.append(
            DetectedText(
                source=path,
                text=cleaned_text,
                confidence=confidence_value,
                left=int(ocr_data["left"][idx]),
                top=int(ocr_data["top"][idx]),
                width=int(ocr_data["width"][idx]),
                height=int(ocr_data["height"][idx]),
            )
        )

    return entries


def scan_inputs(
    inputs: Iterable[Path],
    *,
    min_confidence: float = 50.0,
    language: str = "eng",
    psm: int | None = 3,
    resize: float | None = None,
) -> List[DetectedText]:
    """Scan many images and aggregate the detections.

    Args:
        inputs: Iterable of image paths or directories containing images.
        min_confidence: Minimum confidence (0-100) required to keep a detected word.

    Returns:
        A combined list of detections from all provided inputs.
    """

    results: List[DetectedText] = []

    for input_path in inputs:
        if input_path.is_dir():
            for child in sorted(input_path.iterdir()):
                if child.is_file() and _is_image_file(child):
                    results.extend(
                        scan_image(
                            child,
                            min_confidence=min_confidence,
                            language=language,
                            psm=psm,
                            resize=resize,
                        )
                    )
        elif input_path.is_file() and _is_image_file(input_path):
            results.extend(
                scan_image(
                    input_path,
                    min_confidence=min_confidence,
                    language=language,
                    psm=psm,
                    resize=resize,
                )
            )
        else:
            raise ValueError(f"Unsupported input: {input_path}. Must be an image or directory of images.")

    return results


def detections_to_dataframe(detections: Sequence[DetectedText]) -> pd.DataFrame:
    """Convert detections to a pandas DataFrame for spreadsheet export."""

    records = []
    for detection in detections:
        record = asdict(detection)
        # Represent paths as strings to make CSV/XLSX export friendly.
        record["source"] = str(detection.source)
        record["bbox"] = detection.bbox
        records.append(record)

    return pd.DataFrame.from_records(records, columns=[
        "source", "text", "confidence", "left", "top", "width", "height", "bbox"
    ])


def export_to_spreadsheet(detections: Sequence[DetectedText], output_path: Path) -> Path:
    """Export detections to a CSV or XLSX spreadsheet.

    Args:
        detections: Sequence of detected text entries.
        output_path: Destination path ending with ``.csv`` or ``.xlsx``.

    Returns:
        The path to the generated file.
    """

    df = detections_to_dataframe(detections)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    suffix = output_path.suffix.lower()
    if suffix == ".csv":
        df.to_csv(output_path, index=False)
    elif suffix in {".xls", ".xlsx"}:
        df.to_excel(output_path, index=False)
    else:
        raise ValueError("Output path must end with .csv or .xlsx")

    return output_path


def scan_to_spreadsheet(
    inputs: Iterable[Path],
    output_path: Path,
    *,
    min_confidence: float = 50.0,
    language: str = "eng",
    psm: int | None = 3,
    resize: float | None = None,
) -> Path:
    """High-level helper: scan images and export detections to a spreadsheet."""

    detections = scan_inputs(
        inputs,
        min_confidence=min_confidence,
        language=language,
        psm=psm,
        resize=resize,
    )
    return export_to_spreadsheet(detections, output_path)


def main(argv: Sequence[str] | None = None) -> None:
    """CLI entry point for quick testing.

    Examples:
        python scanner.py poster.jpg --output events.csv
        python scanner.py ./posters --output events.xlsx --min-confidence 60
    """

    import argparse

    parser = argparse.ArgumentParser(description="Market event poster scanner")
    parser.add_argument("inputs", nargs="+", type=Path, help="Image files or directories containing poster images")
    parser.add_argument("--output", required=True, type=Path, help="Destination .csv or .xlsx file")
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=50.0,
        help="Minimum OCR confidence (0-100) to keep a word",
    )
    parser.add_argument(
        "--language",
        type=str,
        default="eng",
        help="Tesseract language code(s), e.g. 'eng' or 'kor+eng'",
    )
    parser.add_argument(
        "--psm",
        type=int,
        default=3,
        help="Tesseract page segmentation mode (--psm). Use -1 to keep default",
    )
    parser.add_argument(
        "--resize",
        type=float,
        default=None,
        help="Optional scale factor to enlarge images before OCR (e.g. 2.0)",
    )

    args = parser.parse_args(argv)

    detections = scan_inputs(
        args.inputs,
        min_confidence=args.min_confidence,
        language=args.language,
        psm=None if args.psm == -1 else args.psm,
        resize=args.resize,
    )
    export_to_spreadsheet(detections, args.output)
    print(f"Exported {len(detections)} detections to {args.output}")


if __name__ == "__main__":
    main()
