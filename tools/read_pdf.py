"""Read PDF text using the project's installed pypdf reader."""

import argparse
import sys
from pathlib import Path

from pypdf import PdfReader


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        reader = PdfReader(args.pdf)
        for number, page in enumerate(reader.pages, 1):
            print(f"--- Page {number} ---")
            print(page.extract_text() or "[No selectable text on this page]")
    except (OSError, ValueError) as error:
        parser.exit(1, f"Could not read PDF: {error}\n")


if __name__ == "__main__":
    main()
