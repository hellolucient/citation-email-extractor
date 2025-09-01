# Email Extractor - Footnote Citation Processor

A web application that processes CSV files containing academic citations and extracts corresponding author contact information.

## Features

- Upload CSV files with citations
- Extract DOI/PMID from citations
- Find corresponding author information using Crossref and PubMed APIs
- Export results to CSV with author names, emails, and affiliations
- Modern web interface with drag-and-drop upload

## Quick Start

### Option 1: Using the startup script (Recommended)
```bash
cd "Email Extractor"
./start.sh
```

### Option 2: Manual setup
1. Navigate to the Email Extractor folder:
```bash
cd "Email Extractor"
```

2. Create and activate virtual environment:
```bash
python3 -m venv ../venv
source ../venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the application:
```bash
python app.py
```

5. Open your browser and go to: `http://localhost:5001`

## Usage

1. Prepare a CSV file with your citations in the first column
2. Upload the CSV file through the web interface
3. Wait for processing to complete (may take several minutes for large files)
4. Download the results CSV file

## Input Format

Your CSV file should have citations in one of the following formats:

### Format 1: Simple citation column
```csv
Citation
Thompson RC, Courtene-Jones W, Boucher J, Pahl S, Raubenheimer K, Koelmans AA. Twenty years of microplastic pollution research-what have we learned? Science. 2024 Oct 25;386(6720):eadl2746. doi: 10.1126/science.adl2746. Epub 2024 Oct 25. PMID: 39298564.
Leslie HA, van Velzen MJM, Brandsma SH, Vethaak AD, Garcia-Vallejo JJ, Lamoree MH. Discovery and quantification of plastic particle pollution in human blood. Environ Int. 2022 May;163:107199. doi: 10.1016/j.envint.2022.107199. Epub 2022 Mar 24. PMID: 35367073.
```

### Format 2: Indexed footnotes (preferred)
```csv
Index,Reference,Footnote
1,,"Thompson RC, Courtene-Jones W, Boucher J, Pahl S, Raubenheimer K, Koelmans AA. Twenty years of microplastic pollution research-what have we learned? Science. 2024 Oct 25;386(6720):eadl2746. doi: 10.1126/science.adl2746. Epub 2024 Oct 25. PMID: 39298564."
2,,"Leslie HA, van Velzen MJM, Brandsma SH, Vethaak AD, Garcia-Vallejo JJ, Lamoree MH. Discovery and quantification of plastic particle pollution in human blood. Environ Int. 2022 May;163:107199. doi: 10.1016/j.envint.2022.107199. Epub 2022 Mar 24. PMID: 35367073."
```

The application will automatically detect the format and use the appropriate column:
- If a `Footnote` column exists, it will use that
- If a `Reference` column exists, it will use that
- Otherwise, it will use the first column

## Output Format

The application will generate a CSV file with the following columns:

- `citation`: Original citation text
- `doi`: Extracted DOI or PMID
- `corresponding_author`: Name of the corresponding author
- `email`: Author's email address (if found)
- `affiliation`: Author's institutional affiliation
- `status`: Processing status (Success/Error)

## API Sources

- **Crossref API**: For DOI-based citations
- **PubMed API**: For PMID-based citations

## Notes

- The application includes delays between API calls to be respectful to the services
- Processing time depends on the number of citations and API response times
- Some citations may not return complete author information
- Maximum file size: 16MB

## Sample Data

A sample CSV file (`sample_citations.csv`) is included for testing.

## File Structure

```
Email Extractor/
├── app.py              # Main Flask application
├── templates/          # Web interface templates
│   └── index.html     # Main web page
├── uploads/           # Folder for processed files
├── requirements.txt   # Python dependencies
├── start.sh          # Startup script
├── README.md         # This file
└── sample_citations.csv  # Test data
```
