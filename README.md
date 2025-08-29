# Phone List Analysis Suite

A comprehensive data analysis toolkit for comparing and tracking changes in phone list CSV files, with specialized tools for organizational data management.

## Project Overview

This project contains two main components:

1. **CSV Diff Tool** - General-purpose CSV comparison utility
2. **Phone List Change Tracker** - Specialized tool for tracking changes in employee/contact data

## Features

### CSV Diff Tool
- **Exact matching** by default (no trimming or normalization)
- **Row additions/removals** and **cell-level modifications**
- Compare by **primary key columns** or by **row order/index**
- Works in **unordered** mode (set-like) or **ordered** mode (sequence)
- Output as **markdown** (default), **JSON**, **HTML**, or **summary**
- Optional **raw text diff** of files

### Phone List Change Tracker
- **Smart entity resolution** using name and Chinese name combinations
- **Change detection** with similarity scoring for different change types
- **Comprehensive reporting** in HTML, JSON, and text formats
- **Statistical analysis** of organizational changes
- **Ignores new joiners and resignees** - focuses only on existing employee changes
- **Multi-field comparison** across Name, Title, Phone, Fax, and Location

## Requirements

- Python 3.10+
- pandas
- difflib (built-in)
- csv (built-in)

## Installation

```bash
cd /Users/anson0621/Desktop/phonelist
pip install pandas
```

## Usage

### Phone List Change Tracker (Primary Tool)

Analyze changes between two phone list CSV files:

```bash
python3 change_tracker.py
```

This will:
1. Compare `phonelistfiles/lotus.csv` (old) with `phonelistfiles/corp.csv` (new)
2. Generate comprehensive reports in multiple formats
3. Output detailed statistics and change analysis

**Generated Reports:**
- `change_tracking_report.html` - Interactive HTML report with styling
- `change_tracking_report.json` - Machine-readable JSON format
- `change_tracking_report.txt` - Human-readable text summary

### CSV Diff Tool (General Purpose)

For general CSV comparison needs:

```bash
python3 -m csv_diff --help
```

#### Examples:

**Unordered compare by key columns:**
```bash
python3 -m csv_diff phonelistfiles/lotus.csv phonelistfiles/corp.csv --key "Name"
```

**Ordered compare by row index:**
```bash
python3 -m csv_diff old.csv new.csv --ordered
```

**JSON output:**
```bash
python3 -m csv_diff old.csv new.csv --key id --format json --output diff.json
```

**HTML output with raw diff:**
```bash
python3 -m csv_diff old.csv new.csv --key id --format html --include-raw-diff
```

### CLI Reference

```bash
python3 -m csv_diff OLD_CSV NEW_CSV [options]

Options:
  --key KEY[,KEY...]      Column name(s) to use as the primary key for matching rows (unordered comparison).
  --ordered               Compare by row index in sequence (ignores --key).
  --format {markdown,json,summary,html}
                          Output format (default: markdown).
  --output PATH           Output file path (default: stdout). Use '-' for stdout.
  --include-raw-diff      Append a unified raw text diff of the two files.
  --encoding1 ENC         Force encoding for the first file (default: auto).
  --encoding2 ENC         Force encoding for the second file (default: auto).
  --delimiter DELIM       Force CSV delimiter (default: auto-sniff).
  --max-print-rows N      Limit number of changed rows printed per section (default: 1000).

Exit codes:
- 0: No differences
- 1: Differences found
- 2: Error
```

## Data Structure

The phone list CSV files should contain columns:
- **Name** - Employee full name
- **Chi Name** - Chinese name (optional)
- **Title** - Job title/position
- **Phone** - Contact phone number
- **Fax** - Fax number (optional)
- **Location** - Office location/department

## Known Issues & Limitations

### Duplicate Entries
**⚠️ Important Notice:** The current dataset contains duplicate entries that may cause analysis errors:

- **Wong Yuk Ting, Yuki** appears twice in the phone lists with potentially different information
- This duplication can cause the entity resolution algorithm to produce inconsistent results
- When reviewing reports, please manually verify any changes related to this individual
- Future versions will include enhanced duplicate detection and resolution

### Other Limitations
- The tool assumes UTF-8 or Latin-1 encoding for CSV files
- Chinese character support requires proper encoding
- Large files (>10MB) may require increased memory allocation
- Similarity scoring is optimized for English names and may need adjustment for other languages

## Technical Details

### Change Detection Algorithm
1. **Entity Resolution**: Creates unique keys using normalized English names + Chinese names
2. **Field Comparison**: Compares each field (Name, Title, Phone, Fax, Location) for common users
3. **Similarity Scoring**: Uses difflib.SequenceMatcher to categorize changes:
   - **Minor Change**: >80% similarity (possible typos)
   - **Moderate Change**: 50-80% similarity
   - **Major Change**: <50% similarity
4. **Classification**: Categorizes as Added, Removed, or Modified fields

### Output Formats
- **HTML**: Interactive report with color-coded changes and statistics
- **JSON**: Machine-readable format for integration with other tools
- **Text**: Human-readable summary for quick review

## Project Structure

```
phonelist/
├── change_tracker.py          # Main analysis tool
├── csv_diff/                  # General CSV comparison module
│   ├── __init__.py
│   ├── __main__.py           # CLI interface
│   ├── core.py               # Core comparison logic
│   └── formatting.py         # Output formatting
├── phonelistfiles/           # Data directory
│   ├── lotus.csv            # Old phone list
│   └── corp.csv             # New phone list
├── pyproject.toml           # Python project configuration
└── README.md               # This file
```

## Contributing

This project is designed as a data analysis and comparison toolkit. When making modifications:

1. Ensure backward compatibility with existing CSV formats
2. Test with both English and Chinese character data
3. Validate output formats (HTML, JSON, text) after changes
4. Update this README with any new features or limitations


