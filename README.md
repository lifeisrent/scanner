# Scanner

Utilities for turning market event posters into structured spreadsheet data.
The script uses Tesseract OCR (via `pytesseract`) to read text from poster
images, aggregates detections, and exports them to CSV or Excel.

## Requirements
- Python 3.10+
- Tesseract OCR installed and available on PATH
- Python packages in `requirements.txt` (`pip install -r requirements.txt`)

## Quick start
1. Install system dependency (Ubuntu example):
   ```bash
   sudo apt-get update && sudo apt-get install -y tesseract-ocr
   ```
2. Install Python dependencies:
   ```bash
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. Run the scanner against image files or a directory of posters:
   ```bash
   python scanner.py ./posters --output events.csv --min-confidence 60
   ```
   The output spreadsheet will include the detected word, bounding box, OCR
   confidence, and the source image path.

### Tip for the provided Korean market poster
The sample poster shared in the prompt mixes Korean and English text. Enabling
the Korean language data in Tesseract produces better results:

```bash
sudo apt-get install -y tesseract-ocr-kor
python scanner.py ./posters/market-poster.jpg \
  --output events.csv \
  --language kor+eng \
  --psm 6 \
  --resize 1.5
```
Use ``--resize`` to upscale small print and ``--psm 6`` (assume a block of text)
to improve word segmentation on dense flyers.

## Embedding in a web app
Import the high-level helper to plug into your web app logic:
```python
from pathlib import Path
from scanner import scan_to_spreadsheet

def process_posters(image_paths: list[str], destination: str) -> str:
    return str(scan_to_spreadsheet([Path(p) for p in image_paths], Path(destination)))
```

Lower-level helpers are also available when you need more control:
- `scan_image(path, min_confidence=50.0)` – scan a single image and return
  detected words with bounding boxes.
- `scan_inputs(paths, min_confidence=50.0)` – scan multiple images or a mix of
  images and directories.
- `detections_to_dataframe(detections)` – convert detections into a pandas
  DataFrame for custom processing.
- `export_to_spreadsheet(detections, output_path)` – write detections to CSV or
  Excel based on the file extension.

## Notes
- Supported image types: JPG/JPEG, PNG, BMP, TIFF, and WEBP.
- Adjust `--min-confidence` if you want to keep lower-confidence OCR hits.
- The OCR output is optimized for English by default; configure your Tesseract
  installation for other languages as needed.
