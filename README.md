# Kobo Notes Exporter

A Python script to export highlights and annotations from a Kobo eReader's SQLite database. The script can export in plain text, markdown, or JSON formats.

## Features
- Exports highlights and annotations with book metadata
- Shows reading progress for each highlight
- Preserves highlight context and creation dates
- Multiple output formats (text, markdown, JSON)

## Usage
```bash
python export_kobo_notes.py -d /path/to/KoboReader.sqlite [-f format] [-o output_file]

Arguments:
  -d, --database    Path to KoboReader.sqlite database file (required)
  -f, --format      Output format: text, markdown, or json (default: text)
  -o, --output      Output file (if not specified, prints to stdout)
```

## Compatibility Note
This script has only been minimally tested with a Kobo Clara BW. While it should work with other Kobo devices that use a similar database structure, your mileage may vary.

## ⚠️ Warning
This code was generated with the assistance of an AI language model (Claude-3.5-Sonnet by Anthropic). While it has been tested with basic use cases, it may contain bugs or unexpected behavior. Review the code carefully before use, especially since it interacts with your eReader's database. Use at your own risk.
