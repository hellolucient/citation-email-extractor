# Email Extractor - Citation Author Contact Finder

A web application that processes CSV files containing academic citations and extracts **all authors** with their contact information using multiple data sources and intelligent search capabilities.

## Features

### Core Processing
- **Multi-format CSV support**: Handles simple citations or indexed footnotes
- **All authors extraction**: Gets every author from each paper, not just the first
- **Smart DOI/PMID detection**: Enhanced regex patterns for various citation formats
- **Multiple data sources**: Crossref API, PubMed API, and Google Custom Search
- **Intelligent email discovery**: Google Search fallback when APIs don't provide emails

### User Experience
- **Two processing modes**: 
  - Preview mode: Review results before download
  - Immediate download: Auto-download when processing completes (no server storage)
- **Progress tracking**: Real-time counters and processing status
- **Summary statistics**: Total processed, emails found, top domains, etc.
- **Deduplication tool**: Remove duplicate authors based on name and email

### Technical Features
- **API quota management**: Caching, query limits, and checkpointing
- **Production ready**: Deployed on Render with proper WSGI server
- **Environment configuration**: Secure API key management
- **Excel support**: Process .csv, .xlsx, and .xls files

## Quick Start

### Production (Recommended)
The app is deployed on Render: **https://citation-email-extractor.onrender.com/**

### Local Development

#### Option 1: Using the startup script
```bash
cd "Email Extractor"
./start.sh
```

#### Option 2: Manual setup
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

4. Set up environment variables (create `.env` file):
```bash
GOOGLE_API_KEY=your_google_api_key
GOOGLE_SEARCH_ENGINE_ID=your_search_engine_id
MAX_GOOGLE_QUERIES_PER_RUN=80
```

5. Run the application:
```bash
python app.py
```

6. Open your browser and go to: `http://localhost:5001`

## Usage

### Main Citation Processing

1. **Prepare your data**: CSV/Excel file with citations (see Input Format below)

2. **Choose processing mode**:
   - **Preview Mode**: Upload → Review results → Download link
   - **Immediate Download**: Check "Download immediately" → Auto-download when ready

3. **Upload and process**: The app will:
   - Extract DOIs/PMIDs from citations
   - Query Crossref and PubMed APIs for all authors
   - Search Google for missing email addresses (quota-limited)
   - Generate comprehensive results with statistics

4. **Review results**: Get detailed summary including:
   - Total papers processed
   - Unique authors found
   - Emails discovered
   - Top email domains
   - Processing status for each citation

### Deduplication Tool

1. **Upload processed file**: Use the "Remove Duplicates" section
2. **Automatic deduplication**: Based on author name + email combination
3. **Get cleaned results**: Download deduplicated file with removal statistics

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

The application generates a CSV file with the following columns:

- `citation`: Original citation text
- `doi`: Extracted DOI or PMID
- `corresponding_author`: Author name (ALL authors, not just corresponding)
- `email`: Author's email address (from APIs or Google Search)
- `affiliation`: Author's institutional affiliation
- `status`: Processing status (Success/Error/API_limit_reached)

**Plus Summary Section** (appended to CSV):
- Total rows processed
- Unique authors found
- Total emails discovered
- Unique email addresses
- Top email domains with counts

## Data Sources & APIs

### Primary Sources
- **Crossref API**: DOI-based paper metadata and author information
- **PubMed API**: PMID-based citations and author details

### Enhanced Email Discovery
- **Google Custom Search JSON API**: Searches for author emails when not available from primary sources
- **Intelligent caching**: Prevents duplicate searches and manages quotas
- **Configurable limits**: Default 80 Google searches per run (customizable)

## Configuration

### Environment Variables
```bash
GOOGLE_API_KEY=your_google_custom_search_api_key
GOOGLE_SEARCH_ENGINE_ID=your_programmable_search_engine_id
MAX_GOOGLE_QUERIES_PER_RUN=80  # Optional, defaults to 80
```

### API Setup
1. **Google Custom Search**: 
   - Create a Programmable Search Engine at [Google CSE](https://cse.google.com/)
   - Get API key from [Google Cloud Console](https://console.cloud.google.com/)
   - Free tier: 100 searches/day

## Technical Notes

- **Respectful API usage**: Built-in delays and caching to avoid rate limits
- **Persistent caching**: Email search results cached in `email_cache.json`
- **Error handling**: Graceful fallbacks when APIs are unavailable
- **Memory efficient**: Processes large files without loading everything into memory
- **Production ready**: Gunicorn WSGI server for deployment

## Sample Data

A sample CSV file (`sample_citations.csv`) is included for testing.

## Deployment

### Render (Production)
The application is configured for one-click deployment on Render:

1. **Connect GitHub repo** to Render
2. **Set environment variables**:
   - `GOOGLE_API_KEY`
   - `GOOGLE_SEARCH_ENGINE_ID`
   - `PIP_ONLY_BINARY=pandas,numpy` (if needed)
3. **Deploy**: Render automatically uses `render.yaml` configuration

### Local Development
See "Quick Start" section above for local setup instructions.

## File Structure

```
Email Extractor/
├── app.py              # Main Flask application
├── templates/          # Web interface templates
│   └── index.html     # Main web page with dual upload modes
├── uploads/           # Temporary file storage
├── cache/             # Email search cache directory
├── requirements.txt   # Python dependencies
├── render.yaml        # Render deployment configuration
├── runtime.txt        # Python version for deployment
├── .env              # Environment variables (local only)
├── .gitignore        # Git ignore rules
├── start.sh          # Local startup script
├── README.md         # This documentation
└── sample_citations.csv  # Test data
```

## Performance & Limitations

- **File size limit**: 16MB upload limit
- **Google Search quota**: 100 free searches/day, 80 per run default
- **Processing time**: ~1-3 seconds per citation (depending on API response times)
- **Memory usage**: Efficient streaming processing for large files
- **Concurrent users**: Production deployment supports multiple users

## Troubleshooting

### Common Issues
1. **"No module named 'pandas'"**: Activate virtual environment first
2. **Google API errors**: Check API key and search engine ID in environment
3. **Port already in use**: Kill existing Flask process or use different port
4. **Build failures on Render**: Ensure `PIP_ONLY_BINARY=pandas,numpy` is set

### Support
- Check terminal output for detailed error messages
- Review processing logs for API response issues
- Verify input CSV format matches expected structure
