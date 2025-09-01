from flask import Flask, render_template, request, send_file, jsonify
import requests
import json
import re
import time
import os
import csv
import io
import pandas as pd
from dotenv import load_dotenv

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Load environment variables
load_dotenv()
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
GOOGLE_SEARCH_ENGINE_ID = os.getenv('GOOGLE_SEARCH_ENGINE_ID')
MAX_GOOGLE_QUERIES_PER_RUN = int(os.getenv('MAX_GOOGLE_QUERIES_PER_RUN', '80'))

# Simple on-disk caches to reduce API usage across runs
CACHE_DIR = app.config['UPLOAD_FOLDER']
EMAIL_CACHE_PATH = os.path.join(CACHE_DIR, 'email_cache.json')

def _load_json(path, default):
    try:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Cache read error {path}: {e}")
    return default

def _save_json(path, data):
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Cache write error {path}: {e}")

email_cache = _load_json(EMAIL_CACHE_PATH, {})  # key -> email
google_queries_used = 0

def google_custom_search(query, num_results=5):
    """Run a Google Custom Search query and return result items."""
    if not GOOGLE_API_KEY or not GOOGLE_SEARCH_ENGINE_ID:
        return []
    global google_queries_used
    if google_queries_used >= MAX_GOOGLE_QUERIES_PER_RUN:
        return []
    try:
        url = 'https://www.googleapis.com/customsearch/v1'
        params = {
            'key': GOOGLE_API_KEY,
            'cx': GOOGLE_SEARCH_ENGINE_ID,
            'q': query,
            'num': max(1, min(num_results, 10)),
            'safe': 'off'
        }
        resp = requests.get(url, params=params, timeout=12)
        if resp.status_code == 200:
            google_queries_used += 1
            data = resp.json()
            return data.get('items', []) or []
    except Exception as e:
        print(f"Google search error for '{query}': {e}")
    return []

def extract_emails_from_text(text):
    """Extract email-like strings from text using regex."""
    if not text:
        return []
    email_regex = r'[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}'
    return re.findall(email_regex, text)

def fetch_page_and_find_email(url):
    """Fetch a URL and try to find emails in the page content."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (compatible; EmailExtractor/1.0)'}
        resp = requests.get(url, headers=headers, timeout=12)
        if resp.status_code == 200:
            emails = extract_emails_from_text(resp.text)
            # Return first reasonable email if any
            for email in emails:
                if not any(bad in email.lower() for bad in ['example.com', 'noreply', 'no-reply', 'support@', 'info@', 'contact@']):
                    return email
    except Exception as e:
        print(f"Fetch page error ({url}): {e}")
    return None

def find_email_for_author(author_name, affiliation):
    """Attempt to discover an author's email using Google search results."""
    if not GOOGLE_API_KEY or not GOOGLE_SEARCH_ENGINE_ID:
        return None
    # Cache key to avoid repeated lookups across runs
    normalized_aff = (affiliation or '').strip().lower()
    key = f"{(author_name or '').strip().lower()}|{normalized_aff}"
    cached = email_cache.get(key)
    if cached:
        return cached
    queries = []
    if author_name:
        queries.append(f"{author_name} email")
        if affiliation:
            queries.append(f"{author_name} {affiliation} email")
            queries.append(f"{author_name} contact {affiliation}")
        queries.append(f"{author_name} faculty email")
        queries.append(f"{author_name} profile email")
    for q in queries:
        items = google_custom_search(q, num_results=5)
        for item in items:
            # Try snippet first
            snippet_email_matches = extract_emails_from_text(item.get('snippet', ''))
            for email in snippet_email_matches:
                if not any(bad in email.lower() for bad in ['example.com', 'noreply', 'no-reply', 'support@', 'info@', 'contact@']):
                    email_cache[key] = email
                    _save_json(EMAIL_CACHE_PATH, email_cache)
                    return email
            # Then try visiting the page
            link = item.get('link')
            if link:
                email = fetch_page_and_find_email(link)
                if email:
                    email_cache[key] = email
                    _save_json(EMAIL_CACHE_PATH, email_cache)
                    return email
        # Be respectful
        time.sleep(0.6)
    return None

def extract_doi_from_citation(citation):
    """Extract DOI from citation text using regex patterns"""
    # Pattern for DOI with various formats
    doi_patterns = [
        r'doi:\s*([^\s]+)',  # doi: 10.1234/abc
        r'doi\s*([^\s]+)',   # doi 10.1234/abc
        r'DOI:\s*([^\s]+)',  # DOI: 10.1234/abc
        r'DOI\s*([^\s]+)',   # DOI 10.1234/abc
        r'https?://doi\.org/([^\s]+)',  # https://doi.org/10.1234/abc
        r'https?://dx\.doi\.org/([^\s]+)',  # https://dx.doi.org/10.1234/abc
    ]
    
    for pattern in doi_patterns:
        doi_match = re.search(pattern, citation, re.IGNORECASE)
        if doi_match:
            doi = doi_match.group(1)
            # Clean up the DOI
            doi = doi.strip('.,;:')
            return doi
    
    # Pattern for PMID
    pmid_patterns = [
        r'PMID:\s*(\d+)',
        r'PMID\s*(\d+)',
        r'pmid:\s*(\d+)',
        r'pmid\s*(\d+)',
    ]
    
    for pattern in pmid_patterns:
        pmid_match = re.search(pattern, citation, re.IGNORECASE)
        if pmid_match:
            return f"PMID:{pmid_match.group(1)}"
    
    return None

def get_author_info_from_crossref(doi):
    """Get author information from Crossref API"""
    try:
        url = f"https://api.crossref.org/works/{doi}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            authors = data.get('message', {}).get('author', [])
            
            # Try to find corresponding author with email
            for author in authors:
                if 'email' in author:
                    return [author]
            
            # If no email found, return all authors
            return authors
        else:
            print(f"Crossref API returned status {response.status_code} for DOI: {doi}")
    except Exception as e:
        print(f"Error getting Crossref data for {doi}: {e}")
    return []

def get_author_info_from_pubmed(pmid):
    """Get author information from PubMed API"""
    try:
        url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        params = {
            'db': 'pubmed',
            'id': pmid,
            'retmode': 'xml'
        }
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            # Parse XML to find corresponding author
            content = response.text
            # Look for corresponding author email
            email_pattern = r'Electronic address:\s*([^\s]+@[^\s]+)'
            email_match = re.search(email_pattern, content)
            if email_match:
                return [{'email': email_match.group(1)}]
            
            # Look for author affiliations
            author_pattern = r'<Author[^>]*>.*?<LastName>([^<]+)</LastName>.*?<ForeName>([^<]+)</ForeName>.*?<AffiliationInfo>.*?<Affiliation>([^<]+)</Affiliation>'
            authors = re.findall(author_pattern, content, re.DOTALL)
            return [{'given': f"{first} {last}", 'family': last, 'affiliation': [aff]} for last, first, aff in authors]
    except Exception as e:
        print(f"Error getting PubMed data: {e}")
    return []

def extract_corresponding_author(authors_data):
    """Extract corresponding author information from authors data"""
    if not authors_data:
        return None
    
    # Look for corresponding author indicators
    for author in authors_data:
        # Check if author has email
        if 'email' in author:
            return {
                'name': f"{author.get('given', '')} {author.get('family', '')}".strip(),
                'email': author['email'],
                'affiliation': author.get('affiliation', [])
            }
    
    # If no email found, return first author
    first_author = authors_data[0]
    return {
        'name': f"{first_author.get('given', '')} {first_author.get('family', '')}".strip(),
        'email': None,
        'affiliation': first_author.get('affiliation', [])
    }

def process_citation(citation):
    """Process a single citation and extract author information"""
    doi = extract_doi_from_citation(citation)
    
    if not doi:
        return [{
            'citation': citation,
            'doi': None,
            'corresponding_author': None,
            'email': None,
            'affiliation': None,
            'status': 'No DOI/PMID found'
        }]
    
    print(f"Processing DOI: {doi}")
    
    # Try Crossref first
    authors_data = get_author_info_from_crossref(doi)
    
    # If no data from Crossref and it's a PMID, try PubMed
    if not authors_data and doi.startswith('PMID:'):
        pmid = doi.replace('PMID:', '')
        authors_data = get_author_info_from_pubmed(pmid)
    
    print(f"Found {len(authors_data)} authors for DOI: {doi}")
    
    # Create a result for each author
    results = []
    for author in authors_data:
        author_name = f"{author.get('given', '')} {author.get('family', '')}".strip()
        author_email = author.get('email', None)
        author_affiliation = '; '.join([str(aff) for aff in author.get('affiliation', [])]) if author.get('affiliation') else None
        
        # If no email from APIs, try to discover via Google
        if not author_email:
            author_email = find_email_for_author(author_name, author_affiliation)
        
        results.append({
            'citation': citation,
            'doi': doi,
            'corresponding_author': author_name,
            'email': author_email,
            'affiliation': author_affiliation,
            'status': 'Success' if author_name else 'No author data found'
        })
    
    # If no authors found, return a single result with no author data
    if not results:
        results = [{
            'citation': citation,
            'doi': doi,
            'corresponding_author': None,
            'email': None,
            'affiliation': None,
            'status': 'No author data found'
        }]
    
    return results

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not file.filename.endswith('.csv'):
        return jsonify({'error': 'Please upload a CSV file'}), 400
    
    try:
        # Read the CSV file
        content = file.read().decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(content))
        
        # Get the column names
        fieldnames = csv_reader.fieldnames
        if not fieldnames:
            return jsonify({'error': 'CSV file is empty or has no headers'}), 400
        
        # Determine which column contains the citations
        citation_column = None
        if 'Footnote' in fieldnames:
            citation_column = 'Footnote'
        elif 'Reference' in fieldnames:
            citation_column = 'Reference'
        else:
            # Fall back to first column as before
            citation_column = fieldnames[0]
        
        # Process each citation
        all_results = []
        csv_reader = csv.DictReader(io.StringIO(content))  # Reset reader
        for row in csv_reader:
            citation = str(row[citation_column])
            # Skip empty citations
            if not citation.strip():
                continue
            result_list = process_citation(citation)
            all_results.extend(result_list)
            
            # Add a small delay to be respectful to APIs
            time.sleep(0.5)
        
        # Create output CSV (in-memory)
        output = io.StringIO()
        fieldnames = ['citation', 'doi', 'corresponding_author', 'email', 'affiliation', 'status']
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_results)

        # Build summary metrics
        unique_authors = set()
        emails = []
        for r in all_results:
            name = (r.get('corresponding_author') or '').strip().lower()
            if name:
                unique_authors.add(name)
            email = (r.get('email') or '').strip()
            if email and '@' in email:
                emails.append(email.lower())
        from collections import Counter
        domain_counts = Counter(e.split('@')[-1] for e in emails)
        top_domains = domain_counts.most_common(10)

        # Append summary section to CSV (as rows)
        writer.writerow({})
        writer.writerow({'citation': 'SUMMARY'})
        writer.writerow({'citation': 'total_rows', 'status': str(len(all_results))})
        writer.writerow({'citation': 'unique_authors', 'status': str(len(unique_authors))})
        writer.writerow({'citation': 'emails_found', 'status': str(len(emails))})
        writer.writerow({'citation': 'unique_emails', 'status': str(len(set(emails)))})
        writer.writerow({'citation': 'top_email_domains (domain=count)'})
        for dom, cnt in top_domains:
            writer.writerow({'citation': dom, 'status': str(cnt)})

        # If stream mode requested, return CSV directly (no disk write)
        if request.args.get('stream') == '1':
            csv_bytes = io.BytesIO(output.getvalue().encode('utf-8'))
            csv_bytes.seek(0)
            stream_filename = f"processed_footnotes_{int(time.time())}.csv"
            return send_file(
                csv_bytes,
                as_attachment=True,
                download_name=stream_filename,
                mimetype='text/csv'
            )
        
        # Save to file
        output_filename = f"processed_footnotes_{int(time.time())}.csv"
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_results)
            # Replicate summary section in saved CSV
            writer.writerow({})
            writer.writerow({'citation': 'SUMMARY'})
            writer.writerow({'citation': 'total_rows', 'status': str(len(all_results))})
            writer.writerow({'citation': 'unique_authors', 'status': str(len(unique_authors))})
            writer.writerow({'citation': 'emails_found', 'status': str(len(emails))})
            writer.writerow({'citation': 'unique_emails', 'status': str(len(set(emails)))})
            writer.writerow({'citation': 'top_email_domains (domain=count)'})
            for dom, cnt in top_domains:
                writer.writerow({'citation': dom, 'status': str(cnt)})
        
        return jsonify({
            'success': True,
            'filename': output_filename,
            'results': all_results[:5],  # Return first 5 results for preview
            'total_processed': len(all_results),
            'summary': {
                'unique_authors': len(unique_authors),
                'emails_found': len(emails),
                'unique_emails': len(set(emails)),
                'top_domains': top_domains,
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Error processing file: {str(e)}'}), 500

@app.route('/download/<filename>')
def download_file(filename):
    try:
        return send_file(
            os.path.join(app.config['UPLOAD_FOLDER'], filename),
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({'error': f'File not found: {str(e)}'}), 404

@app.route('/dedupe', methods=['POST'])
def dedupe_file():
    """Remove duplicates from uploaded CSV based on author name and email"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not file.filename.lower().endswith(('.csv', '.xlsx', '.xls')):
        return jsonify({'error': 'Please upload a CSV or Excel file'}), 400
    
    try:
        # Read the file
        if file.filename.lower().endswith('.csv'):
            content = file.read().decode('utf-8')
            df = pd.read_csv(io.StringIO(content))
        else:
            df = pd.read_excel(file)
        
        # Store original count
        original_count = len(df)
        
        # Create deduplication key based on author name and email
        df['dedup_key'] = df.apply(lambda row: (
            str(row.get('corresponding_author', '')).strip().lower(),
            str(row.get('email', '')).strip().lower()
        ), axis=1)
        
        # Remove duplicates, keeping first occurrence
        df_deduped = df.drop_duplicates(subset=['dedup_key'], keep='first')
        
        # Remove the temporary dedup_key column
        df_deduped = df_deduped.drop('dedup_key', axis=1)
        
        # Calculate stats
        final_count = len(df_deduped)
        removed_count = original_count - final_count
        
        # Count unique emails
        unique_emails = df_deduped['email'].dropna()
        unique_emails = unique_emails[unique_emails.str.contains('@', na=False)]
        email_count = len(unique_emails)
        
        # Save deduplicated file
        output_filename = f"deduped_{int(time.time())}.csv"
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)
        
        df_deduped.to_csv(output_path, index=False, encoding='utf-8')
        
        # Add summary section to the CSV
        with open(output_path, 'a', newline='', encoding='utf-8') as f:
            f.write('\n\n--- DEDUPLICATION SUMMARY ---\n')
            f.write(f'Original rows,{original_count}\n')
            f.write(f'Deduplicated rows,{final_count}\n')
            f.write(f'Duplicates removed,{removed_count}\n')
            f.write(f'Unique emails found,{email_count}\n')
        
        return jsonify({
            'success': True,
            'filename': output_filename,
            'original_count': original_count,
            'final_count': final_count,
            'removed_count': removed_count,
            'email_count': email_count,
            'preview': df_deduped.head(5).to_dict('records')
        })
        
    except Exception as e:
        return jsonify({'error': f'Error processing file: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
