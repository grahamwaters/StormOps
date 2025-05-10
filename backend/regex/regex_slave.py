import re
import pandas as pd
import requests
import logging
import time
import os
import random
from rich import print as rprint
from rich.progress import Progress
from rich.table import Table
from rich.panel import Panel
from urllib.parse import urlparse
from retrying import retry

# --- Logging Setup ---
logging.basicConfig(
    filename='scraper.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(module)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(console_handler)

# --- Configuration Constants ---
RATE_LIMIT_SECONDS = 0.5
RETRY_SLEEP_SECONDS = 5
MAX_RETRIES = 2
INPUT_CSV = 'omni_eye_df.csv'
OUTPUT_CSV = 'video_embeds.csv'
HTML_CACHE_DIR = 'html_cache'
WEBCAM_DIR = 'webcam_directory'
MAX_LOG_LINES_DISPLAY = 70
REQUEST_TIMEOUT_SECONDS = 20
MIN_VIDEOS_PER_HTML = 10

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    'VLC/3.0.20 LibVLC/3.0.20',
    'Lavf/60.3.100',
    'QuickTime/7.7.3 (qtver=7.7.3;os=Windows NT 6.1)',
    'Windows-Media-Player/12.0.19041.3636'
]

# Create directories
for directory in [HTML_CACHE_DIR, WEBCAM_DIR]:
    if not os.path.exists(directory):
        logger.debug(f"Creating directory: {directory}")
        os.makedirs(directory)
        logger.info(f"Created directory: {directory}")

# Sanitize URL or name for filename
def sanitize_for_filename(text):
    return re.sub(r'[^\w\-_\.]', '_', text).strip('_')

# Retry decorator for requests
@retry(
    stop_max_attempt_number=MAX_RETRIES,
    wait_fixed=RETRY_SLEEP_SECONDS * 1000,
    retry_on_exception=lambda e: isinstance(e, requests.exceptions.RequestException)
)
def fetch_html(url):
    headers = {'User-Agent': random.choice(USER_AGENTS)}
    logger.debug(f"Sending GET request to {url} with User-Agent: {headers['User-Agent']}")
    response = requests.get(url, timeout=REQUEST_TIMEOUT_SECONDS, headers=headers)
    response.raise_for_status()
    return response.text

# HTML template for webcam page
def create_webcam_html(videos):
    cards = "".join(
        f"""
        <div class="card">
            <h2>{video['name']}</h2>
            <div class="video-container">
                {video['embed_code']}
            </div>
        </div>
        """
        for video in videos
    )
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Webcam Collection</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f4f4f4;
        }}
        .masonry {{
            column-count: 1;
            column-gap: 20px;
            max-width: 1200px;
            margin: 0 auto;
        }}
        .card {{
            break-inside: avoid;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            margin-bottom: 20px;
            padding: 15px;
        }}
        h2 {{
            margin: 0 0 10px;
            font-size: 1.5em;
            color: #333;
        }}
        .video-container {{
            position: relative;
            width: 100%;
            aspect-ratio: 16 / 9;
        }}
        iframe {{
            width: 100%;
            height: 100%;
            border: none;
        }}
        @media (min-width: 600px) {{
            .masonry {{
                column-count: 2;
            }}
        }}
        @media (min-width: 900px) {{
            .masonry {{
                column-count: 3;
            }}
        }}
    </style>
</head>
<body>
    <div class="masonry">
        {cards}
    </div>
</body>
</html>
"""

# Verify number of embeds in HTML files
def verify_html_files():
    html_files = [f for f in os.listdir(WEBCAM_DIR) if f.endswith('.html')]
    verification_results = []
    for html_file in html_files:
        try:
            with open(os.path.join(WEBCAM_DIR, html_file), 'r', encoding='utf-8') as f:
                content = f.read()
            iframe_count = len(re.findall(r'<iframe[^>]+src="https://www\.youtube\.com/embed/[^"]+"[^>]*></iframe>', content, re.IGNORECASE))
            verification_results.append({'File': html_file, 'Embed Count': iframe_count})
            logger.info(f"Verified {html_file}: {iframe_count} embeds")
        except Exception as e:
            logger.error(f"Failed to verify {html_file}: {str(e)}")
            verification_results.append({'File': html_file, 'Embed Count': 'Error'})
    return verification_results

# Read last log lines for display
def get_last_log_lines():
    try:
        with open('scraper.log', 'r') as f:
            lines = f.readlines()
            return lines[-MAX_LOG_LINES_DISPLAY:] if len(lines) > MAX_LOG_LINES_DISPLAY else lines
    except Exception:
        return []

# Read input CSV
logger.debug(f"Attempting to read input CSV: {INPUT_CSV}")
try:
    df = pd.read_csv(INPUT_CSV)
    logger.info(f"Successfully read {INPUT_CSV} with {len(df)} entries")
except FileNotFoundError:
    logger.error(f"Input CSV '{INPUT_CSV}' not found")
    raise

# Read existing output CSV to resume progress
processed_urls = set()
if os.path.exists(OUTPUT_CSV):
    logger.debug(f"Reading existing output CSV to resume: {OUTPUT_CSV}")
    try:
        existing_df = pd.read_csv(OUTPUT_CSV)
        processed_urls = set(existing_df['URL'].dropna())
        logger.info(f"Loaded {len(processed_urls)} processed URLs from {OUTPUT_CSV}")
    except Exception as e:
        logger.warning(f"Failed to read existing CSV {OUTPUT_CSV}: {str(e)}")

# Initialize lists to store data
data = list(existing_df.to_dict('records')) if 'existing_df' in locals() else []
valid_videos = []  # Store videos for HTML grouping
logger.debug("Initialized data list for storing results")
valid_embeds = 0
skipped_urls = 0
failed_urls = 0
cached_files_processed = 0

# Create a URL-to-Name mapping from input CSV
url_to_name = dict(zip(df['URL'], df['Name']))

# Process cached HTML files
logger.debug(f"Checking for cached HTML files in {HTML_CACHE_DIR}")
cached_files = [f for f in os.listdir(HTML_CACHE_DIR) if f.endswith('.html')]
with Progress() as progress:
    task = progress.add_task("[cyan]Processing cached HTML files...", total=len(cached_files))
    for cached_file in cached_files:
        cached_filepath = os.path.join(HTML_CACHE_DIR, cached_file)
        # Reconstruct URL from filename (reverse sanitize_for_filename)
        url_path = cached_file.replace('_', '/').replace('.html', '')
        url = f"https://www.webcamtaxi.com{url_path}"
        name = url_to_name.get(url, "Unknown")
        logger.debug(f"Processing cached HTML file: {cached_filepath} (URL: {url}, Name: {name})")

        # Skip if URL already processed
        if url in processed_urls:
            logger.debug(f"Skipping already processed URL: {url}")
            progress.update(task, advance=1)
            continue

        try:
            with open(cached_filepath, 'r', encoding='utf-8') as f:
                html = f.read()
            logger.info(f"Successfully read cached HTML from {cached_filepath}")
        except Exception as e:
            logger.error(f"Failed to read cached HTML {cached_filepath}: {str(e)}")
            data.append({'URL': url, 'Name': name, 'Embed_Code': None})
            failed_urls += 1
            cached_files_processed += 1
            # Save progress to CSV
            pd.DataFrame(data).to_csv(OUTPUT_CSV, index=False)
            logger.debug(f"Saved progress to {OUTPUT_CSV}")
            progress.update(task, advance=1)
            continue

        # Extract iframe embed code
        logger.debug("Searching for YouTube iframe embed code in cached file")
        iframe_match = re.search(
            r'<iframe[^>]+src="https://www\.youtube\.com/embed/[^"]+"[^>]*></iframe>',
            html,
            re.IGNORECASE
        )

        logger.debug(f"iframe_match: {'Found' if iframe_match else 'Not found'}")
        if iframe_match:
            embed_code = iframe_match.group(0)
            logger.debug(f"Extracted embed code: {embed_code}")
            rprint(f"[green]Successfully extracted embed code for {name} from cached file[/green]")
            data.append({'URL': url, 'Name': name, 'Embed_Code': embed_code})
            valid_videos.append({'name': name, 'embed_code': embed_code})
            valid_embeds += 1
        else:
            logger.debug("No YouTube iframe found in cached file")
            data.append({'URL': url, 'Name': name, 'Embed_Code': None})
            skipped_urls += 1

        cached_files_processed += 1
        processed_urls.add(url)
        # Save progress to CSV
        pd.DataFrame(data).to_csv(OUTPUT_CSV, index=False)
        logger.debug(f"Saved progress to {OUTPUT_CSV}")

        # Every 10 cached files, reload CSV
        if cached_files_processed % 10 == 0:
            logger.debug(f"Reloading {OUTPUT_CSV} to resume progress")
            try:
                existing_df = pd.read_csv(OUTPUT_CSV)
                data = existing_df.to_dict('records')
                processed_urls = set(existing_df['URL'].dropna())
                logger.info(f"Resumed with {len(cached_files) - cached_files_processed} cached files remaining")
            except Exception as e:
                logger.error(f"Failed to reload {OUTPUT_CSV}: {str(e)}")

        progress.update(task, advance=1)

# Filter unprocessed URLs
unprocessed_df = df[~df['URL'].isin(processed_urls)]
logger.info(f"Found {len(unprocessed_df)} unprocessed URLs to scrape")

# Crawl remaining URLs
with Progress() as progress:
    task = progress.add_task("[cyan]Processing URLs for video embeds...", total=len(unprocessed_df))
    for index, (idx, row) in enumerate(unprocessed_df.iterrows()):
        url = row['URL']
        name = row['Name']
        logger.debug(f"Processing URL: {url} (Name: {name})")

        # Fetch HTML with retries
        try:
            html = fetch_html(url)
            logger.info(f"Successfully fetched HTML from {url}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch {url} after {MAX_RETRIES} attempts: {str(e)}")
            data.append({'URL': url, 'Name': name, 'Embed_Code': None})
            failed_urls += 1
            progress.update(task, advance=1)
            # Save progress to CSV
            pd.DataFrame(data).to_csv(OUTPUT_CSV, index=False)
            logger.debug(f"Saved progress to {OUTPUT_CSV}")
            time.sleep(RATE_LIMIT_SECONDS)
            continue

        # Save HTML to cache
        html_filename = os.path.join(HTML_CACHE_DIR, sanitize_for_filename(urlparse(url).path))
        logger.debug(f"Saving HTML to: {html_filename}")
        try:
            with open(html_filename, 'w', encoding='utf-8') as f:
                f.write(html)
            logger.info(f"Saved HTML to {html_filename}")
        except Exception as e:
            logger.error(f"Failed to save HTML to {html_filename}: {str(e)}")

        # Extract iframe embed code
        logger.debug("Searching for YouTube iframe embed code")
        iframe_match = re.search(
            r'<iframe[^>]+src="https://www\.youtube\.com/embed/[^"]+"[^>]*></iframe>',
            html,
            re.IGNORECASE
        )

        logger.debug(f"iframe_match: {'Found' if iframe_match else 'Not found'}")
        if iframe_match:
            embed_code = iframe_match.group(0)
            logger.debug(f"Extracted embed code: {embed_code}")
            rprint(f"[green]Successfully extracted embed code for {name}[/green]")
            data.append({'URL': url, 'Name': name, 'Embed_Code': embed_code})
            valid_videos.append({'name': name, 'embed_code': embed_code})
            valid_embeds += 1
        else:
            logger.debug("No YouTube iframe found for this URL")
            data.append({'URL': url, 'Name': name, 'Embed_Code': None})
            skipped_urls += 1

        processed_urls.add(url)
        # Save emulsion to CSV
        pd.DataFrame(data).to_csv(OUTPUT_CSV, index=False)
        logger.debug(f"Saved progress to {OUTPUT_CSV}")

        # Every 10 URLs, reload CSV
        if (index + 1) % 10 == 0:
            logger.debug(f"Reloading {OUTPUT_CSV} to resume progress")
            try:
                existing_df = pd.read_csv(OUTPUT_CSV)
                data = existing_df.to_dict('records')
                processed_urls = set(existing_df['URL'].dropna())
                unprocessed_df = df[~df['URL'].isin(processed_urls)]
                logger.info(f"Resumed with {len(unprocessed_df)} unprocessed URLs remaining")
                # Update progress bar total
                progress.update(task, total=len(unprocessed_df))
            except Exception as e:
                logger.error(f"Failed to reload {OUTPUT_CSV}: {str(e)}")

        progress.update(task, advance=1)
        time.sleep(RATE_LIMIT_SECONDS)

# Generate HTML files with at least 10 videos each
html_file_counts = []
logger.debug("Generating HTML files for webcam videos")
for i in range(0, len(valid_videos), MIN_VIDEOS_PER_HTML):
    video_batch = valid_videos[i:i + MIN_VIDEOS_PER_HTML]
    if video_batch:
        html_filename = os.path.join(WEBCAM_DIR, f"webcams_{i // MIN_VIDEOS_PER_HTML + 1}.html")
        logger.info(f"Creating webcam HTML file: {html_filename} with {len(video_batch)} videos")
        try:
            with open(html_filename, 'w', encoding='utf-8') as f:
                f.write(create_webcam_html(video_batch))
            logger.info(f"Saved webcam HTML to {html_filename}")
            html_file_counts.append({'File': html_filename, 'Embed Count': len(video_batch)})
        except Exception as e:
            logger.error(f"Failed to save webcam HTML to {html_filename}: {str(e)}")
            html_file_counts.append({'File': html_filename, 'Embed Count': 'Error'})

# Verify HTML files
logger.debug("Verifying HTML files in webcam_directory")
verification_results = verify_html_files()

# Log summary of processing
logger.info(f"Processing complete: {valid_embeds} embed codes found, {skipped_urls} URLs without embeds, {failed_urls} URLs failed, {cached_files_processed} cached files processed")

# Create final DataFrame
logger.debug("Creating final pandas DataFrame from collected data")
result_df = pd.DataFrame(data)
logger.info(f"Created DataFrame with {len(result_df)} entries")

# Save final CSV
logger.debug(f"Saving final DataFrame to CSV: {OUTPUT_CSV}")
result_df.to_csv(OUTPUT_CSV, index=False)
logger.info(f"Final DataFrame saved to {OUTPUT_CSV}")

# Create summary table with Rich
table = Table(title="Processing Summary")
table.add_column("Metric", style="cyan")
table.add_column("Value", style="green")
table.add_row("Total URLs Processed", str(len(unprocessed_df)))
table.add_row("Cached Files Processed", str(cached_files_processed))
table.add_row("Valid Embed Codes Found", str(valid_embeds))
table.add_row("URLs Without Embeds", str(skipped_urls))
table.add_row("Failed URLs", str(failed_urls))
table.add_row("HTML Files Created", str(len(html_file_counts)))
table.add_row("Output CSV", OUTPUT_CSV)
table.add_row("HTML Cache Directory", HTML_CACHE_DIR)
table.add_row("Webcam Directory", WEBCAM_DIR)
rprint(table)

# Create verification table with Rich
if verification_results:
    verify_table = Table(title="HTML File Verification")
    verify_table.add_column("File", style="cyan")
    verify_table.add_column("Embed Count", style="green")
    for result in verification_results:
        verify_table.add_row(result['File'], str(result['Embed Count']))
    rprint(verify_table)

# Display last log lines in Rich panel
log_lines = get_last_log_lines()
log_content = "".join(log_lines).strip()
rprint(Panel(log_content, title="Last Log Entries", border_style="blue", expand=False))

# Print success message with Rich
rprint(f"[green]Data successfully saved to {OUTPUT_CSV}[/green]")