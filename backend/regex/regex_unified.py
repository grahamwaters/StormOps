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
UNPARSED_DIR = 'UnParsed'
MAX_LOG_LINES_DISPLAY = 70
REQUEST_TIMEOUT_SECONDS = 20

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

# Video platform patterns
VIDEO_PATTERNS = [
    r'<iframe[^>]+src="https?://www\.youtube\.com/embed/[^"]+"[^>]*></iframe>',  # YouTube
    r'<iframe[^>]+src="https?://player\.vimeo\.com/video/[^"]+"[^>]*></iframe>',  # Vimeo
    r'<iframe[^>]+src="https?://www\.dailymotion\.com/embed/video/[^"]+"[^>]*></iframe>',  # Dailymotion
]

# Create directories
for directory in [HTML_CACHE_DIR, WEBCAM_DIR, UNPARSED_DIR]:
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

# HTML template for a single page with multiple webcams
def create_all_webcams_html(webcams):
    cards = ""
    for webcam in webcams:
        cards += f"""
        <div class="card">
            <h2>{webcam['Name']}</h2>
            <div class="video-container">
                {webcam['Embed_Code']}
            </div>
        </div>
        """
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>All Webcams</title>
    <style>
        body {{
            font-family: 'Segoe UI', Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #1a1a1a;
            color: #e0e0e0;
        }}
        .masonry {{
            column-count: 1;
            column-gap: 20px;
            max-width: 1200px;
            margin: 0 auto;
        }}
        .card {{
            break-inside: avoid;
            background: #2a2a2a;
            border-radius: 12px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.3);
            margin-bottom: 20px;
            padding: 20px;
            transition: transform 0.2s;
        }}
        .card:hover {{
            transform: translateY(-5px);
        }}
        h2 {{
            margin: 0 0 15px;
            font-size: 1.6em;
            color: #00ccff;
        }}
        .video-container {{
            position: relative;
            width: 100%;
            aspect-ratio: 16 / 9;
            border-radius: 8px;
            overflow: hidden;
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

# Function to save the HTML file
def save_webcams_html(webcams, filename):
    if webcams:
        logger.debug(f"Saving HTML file: {filename} with {len(webcams)} webcams")
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(create_all_webcams_html(webcams))
            logger.info(f"Saved all webcams to {filename}")
        except Exception as e:
            logger.error(f"Failed to save all webcams HTML to {filename}: {str(e)}")
    else:
        logger.debug(f"No webcams to save to {filename}")

# Verify number of embeds in HTML file
def verify_html_file(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        iframe_count = len(re.findall(r'<iframe[^>]+src="https?://(www\.youtube\.com|player\.vimeo\.com|www\.dailymotion\.com)/[^"]+"[^>]*></iframe>', content, re.IGNORECASE))
        logger.info(f"Verified {filename}: {iframe_count} embeds")
        return {'File': os.path.basename(filename), 'Embed Count': iframe_count}
    except Exception as e:
        logger.error(f"Failed to verify {filename}: {str(e)}")
        return {'File': os.path.basename(filename), 'Embed Count': 'Error'}

# Read last log lines for display
def get_last_log_lines():
    try:
        with open('scraper.log', 'r') as f:
            lines = f.readlines()
            return lines[-MAX_LOG_LINES_DISPLAY:] if len(lines) > MAX_LOG_LINES_DISPLAY else lines
    except Exception:
        return []

# Function from regex_master.py: Extract URLs and names from HTML
def process_master(html, progress, task_id, base_url='https://www.webcamtaxi.com'):
    logger.debug("Searching for <a> tags in HTML")
    a_tags = re.findall(r'<a\s[^>]+>', html)
    logger.info(f"Found {len(a_tags)} <a> tags")

    data = []
    valid_tags = 0
    skipped_tags = 0

    sub_task = progress.add_task("[cyan]Processing <a> tags...", total=len(a_tags))
    for tag in a_tags:
        logger.debug(f"Processing tag: {tag}")
        href_match = re.search(r'href\s*=\s*["\']?([^"\s>]+)["\']?', tag)
        title_match = re.search(r'title="([^"]+)"', tag)

        logger.debug(f"href_match: {'Found' if href_match else 'Not found'}")
        if href_match:
            logger.debug(f"href value: {href_match.group(1)}")
        logger.debug(f"title_match: {'Found' if title_match else 'Not found'}")
        if title_match:
            logger.debug(f"title value: {title_match.group(1)}")

        if href_match and title_match:
            valid_tags += 1
            href = href_match.group(1)
            title = title_match.group(1)
            logger.debug(f"Valid tag found - Extracted href: {href}, title: {title}")
            if href.startswith('/'):
                full_url = base_url + href
                logger.debug(f"Converted relative URL {href} to full URL: {full_url}")
            else:
                full_url = href
                logger.debug(f"Using absolute URL: {full_url}")
            data.append({'URL': full_url, 'Name': title})
            logger.debug(f"Added entry to data: URL={full_url}, Name={title}")
        else:
            skipped_tags += 1
            logger.debug("Skipping tag: Missing href or title attribute")
        progress.update(sub_task, advance=1)

    logger.info(f"Master processing complete: {valid_tags} valid tags processed, {skipped_tags} tags skipped")
    progress.update(task_id, advance=1)
    return data

# Function from regex_extract.py: Extract webcam URLs from HTML
def process_extract(html, progress, task_id):
    patterns = [
        r'<a\s+[^>]*href="(/en/[^/]+/[^/]+/[^/]+\.html)"[^>]*>',
        r'<a\s+[^>]*href="(https?://www\.webcamtaxi\.com/en/[^/]+/[^/]+/[^/]+\.html)"[^>]*>',
        r'<a\s+[^>]*href="(/en/[^/]+/[^/]+/[^/]+(?:\.html|\.html\?[^"]*))"[^>]*>',
        r'<div\s+class="nspArt[^>]*>[\s\S]*?<a\s+[^>]*href="(/en/[^/]+/[^/]+/[^/]+\.html)"[^>]*>',
        r'<a\s+[^>]*href="(/en/[^/]+/[^/]+/[^/]+\.html)"\s+[^>]*class="nspImageWrapper[^"]*"[^>]*>',
        r'<a\s+[^>]*href="(/en/[^/]+/[^/]+/[^/]+\.html)"\s+title="[^"]*Cam[^"]*"[^>]*>',
        r'<a\s+[^>]*href="(/en/[a-zA-Z0-9\-]+/[a-zA-Z0-9\-]+/[a-zA-Z0-9\-]+\.html)"[^>]*>',
        r'<div\s+class="nspCol[13]"[^>]*>[\s\S]*?<a\s+[^>]*href="(/en/[^/]+/[^/]+/[^/]+\.html)"[^>]*>',
        r'<a\s+[^>]*href="(/en/[^/]+/[^/]+/[^/]+\.html)"\s+[^>]*class="[^"]*webcam[^"]*"[^>]*>',
        r'<a\s+[^>]*href="(/en/[^/]+/[^/]+/[^/]+\.html)"\s+[^>]*class="[^"]*thumbnail[^"]*"[^>]*>'
    ]

    webcam_links = set()
    for pattern in patterns:
        matches = re.finditer(pattern, html, re.MULTILINE | re.IGNORECASE)
        for match in matches:
            url = match.group(1)
            if url.startswith('http'):
                url = url.replace('https://www.webcamtaxi.com', '')
            if re.match(r'^/en/[^/]+/[^/]+/[^/]+\.html(?:\?[^"]*)?$', url):
                webcam_links.add(url)

    logger.info(f"Extract processing complete: {len(webcam_links)} webcam URLs found")
    progress.update(task_id, advance=1)
    return [{'URL': f"https://www.webcamtaxi.com{url}", 'Name': url.split('/')[-1].replace('.html', '').replace('-', ' ').title()} for url in sorted(webcam_links)]

# Function to extract embed codes from HTML
def extract_embed_code(html):
    for pattern in VIDEO_PATTERNS:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            return match.group(0)
    return None

# Function from regex_slave.py: Process URLs and extract embeds
def process_slave(urls_df, webcams, all_webcams_filename, progress, task_id):
    processed_urls = set()
    if os.path.exists(OUTPUT_CSV):
        try:
            existing_df = pd.read_csv(OUTPUT_CSV)
            processed_urls = set(existing_df['URL'].dropna())
            logger.info(f"Loaded {len(processed_urls)} processed URLs from {OUTPUT_CSV}")
        except Exception as e:
            logger.warning(f"Failed to read existing CSV {OUTPUT_CSV}: {str(e)}")

    data = list(existing_df.to_dict('records')) if 'existing_df' in locals() else []
    valid_embeds = 0
    skipped_urls = 0
    failed_urls = 0

    unprocessed_df = urls_df[~urls_df['URL'].isin(processed_urls)]
    logger.info(f"Found {len(unprocessed_df)} unprocessed URLs to scrape")

    sub_task = progress.add_task("[cyan]Processing URLs for video embeds...", total=len(unprocessed_df))
    for index, (idx, row) in enumerate(unprocessed_df.iterrows()):
        url = row['URL']
        name = row['Name']
        logger.debug(f"Processing URL: {url} (Name: {name})")

        try:
            html = fetch_html(url)
            logger.info(f"Successfully fetched HTML from {url}")

            html_filename = os.path.join(HTML_CACHE_DIR, sanitize_for_filename(urlparse(url).path))
            logger.debug(f"Saving HTML to: {html_filename}")
            try:
                with open(html_filename, 'w', encoding='utf-8') as f:
                    f.write(html)
                logger.info(f"Saved HTML to {html_filename}")
            except Exception as e:
                logger.error(f"Failed to save HTML to {html_filename}: {str(e)}")

            embed_code = extract_embed_code(html)
            logger.debug(f"embed_code: {'Found' if embed_code else 'Not found'}")
            if embed_code:
                logger.debug(f"Extracted embed code: {embed_code}")
                rprint(f"[green]Successfully extracted embed code for {name}[/green]")
                data.append({'URL': url, 'Name': name, 'Embed_Code': embed_code})
                webcams.append({'Name': name, 'Embed_Code': embed_code})
                valid_embeds += 1
                save_webcams_html(webcams, all_webcams_filename)
            else:
                logger.debug("No video iframe found for this URL")
                data.append({'URL': url, 'Name': name, 'Embed_Code': None})
                skipped_urls += 1

            processed_urls.add(url)
            pd.DataFrame(data).to_csv(OUTPUT_CSV, index=False)
            logger.debug(f"Saved progress to {OUTPUT_CSV}")

            if (index + 1) % 10 == 0:
                try:
                    existing_df = pd.read_csv(OUTPUT_CSV)
                    data = existing_df.to_dict('records')
                    processed_urls = set(existing_df['URL'].dropna())
                    unprocessed_df = urls_df[~urls_df['URL'].isin(processed_urls)]
                    logger.info(f"Resumed with {len(unprocessed_df)} unprocessed URLs remaining")
                    progress.update(sub_task, total=len(unprocessed_df))
                except Exception as e:
                    logger.error(f"Failed to reload {OUTPUT_CSV}: {str(e)}")
                save_webcams_html(webcams, all_webcams_filename)

            progress.update(sub_task, advance=1)
            time.sleep(RATE_LIMIT_SECONDS)

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch {url} after {MAX_RETRIES} attempts: {str(e)}")
            data.append({'URL': url, 'Name': name, 'Embed_Code': None})
            failed_urls += 1
            pd.DataFrame(data).to_csv(OUTPUT_CSV, index=False)
            logger.debug(f"Saved progress to {OUTPUT_CSV}")
            save_webcams_html(webcams, all_webcams_filename)
            progress.update(sub_task, advance=1)
            time.sleep(RATE_LIMIT_SECONDS)
            continue

    progress.update(task_id, advance=1)
    return valid_embeds, skipped_urls, failed_urls, data

# Main processing function
def main():
    all_webcams_filename = os.path.join(WEBCAM_DIR, "all_webcams.html")
    webcams = []
    total_valid_embeds = 0
    total_skipped_urls = 0
    total_failed_urls = 0
    all_data = []

    with Progress() as progress:
        # Process UnParsed folder
        if os.path.exists(UNPARSED_DIR):
            html_files = [f for f in os.listdir(UNPARSED_DIR) if f.endswith('.html')]
            logger.info(f"Found {len(html_files)} HTML files in {UNPARSED_DIR}")

            task_files = progress.add_task("[cyan]Processing UnParsed HTML files...", total=len(html_files))
            for html_file in html_files:
                filepath = os.path.join(UNPARSED_DIR, html_file)
                logger.info(f"Processing {html_file}")

                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        html = f.read()
                    logger.info(f"Successfully read {html_file}")
                except Exception as e:
                    logger.error(f"Failed to read {html_file}: {str(e)}")
                    progress.update(task_files, advance=1)
                    continue

                # Step 1: regex_master.py
                master_data = process_master(html, progress, task_files)
                if master_data:
                    df = pd.DataFrame(master_data)
                    if os.path.exists(INPUT_CSV):
                        existing_df = pd.read_csv(INPUT_CSV)
                        df = pd.concat([existing_df, df]).drop_duplicates(subset=['URL'])
                    df.to_csv(INPUT_CSV, index=False)
                    logger.info(f"Appended {len(master_data)} URLs to {INPUT_CSV}")

                # Step 2: regex_slave.py
                if os.path.exists(INPUT_CSV):
                    urls_df = pd.read_csv(INPUT_CSV)
                    v_embeds, s_urls, f_urls, data = process_slave(urls_df, webcams, all_webcams_filename, progress, task_files)
                    total_valid_embeds += v_embeds
                    total_skipped_urls += s_urls
                    total_failed_urls += f_urls
                    all_data.extend(data)

                # Step 3: regex_extract.py
                extract_data = process_extract(html, progress, task_files)
                if extract_data:
                    df = pd.DataFrame(extract_data)
                    if os.path.exists(INPUT_CSV):
                        existing_df = pd.read_csv(INPUT_CSV)
                        df = pd.concat([existing_df, df]).drop_duplicates(subset=['URL'])
                    df.to_csv(INPUT_CSV, index=False)
                    logger.info(f"Appended {len(extract_data)} URLs from extract to {INPUT_CSV}")

                    # Process extracted URLs with regex_slave.py
                    urls_df = pd.read_csv(INPUT_CSV)
                    v_embeds, s_urls, f_urls, data = process_slave(urls_df, webcams, all_webcams_filename, progress, task_files)
                    total_valid_embeds += v_embeds
                    total_skipped_urls += s_urls
                    total_failed_urls += f_urls
                    all_data.extend(data)

                progress.update(task_files, advance=1)

        else:
            logger.warning(f"{UNPARSED_DIR} does not exist")
            # Process raw_page_html.html if available
            if os.path.exists('raw_page_html.html'):
                logger.info("Processing raw_page_html.html")
                task_single = progress.add_task("[cyan]Processing raw_page_html.html...", total=3)  # 3 steps: master, slave, extract
                with open('raw_page_html.html', 'r', encoding='utf-8') as f:
                    html = f.read()

                master_data = process_master(html, progress, task_single)
                if master_data:
                    df = pd.DataFrame(master_data)
                    if os.path.exists(INPUT_CSV):
                        existing_df = pd.read_csv(INPUT_CSV)
                        df = pd.concat([existing_df, df]).drop_duplicates(subset=['URL'])
                    df.to_csv(INPUT_CSV, index=False)
                    logger.info(f"Appended {len(master_data)} URLs to {INPUT_CSV}")

                if os.path.exists(INPUT_CSV):
                    urls_df = pd.read_csv(INPUT_CSV)
                    v_embeds, s_urls, f_urls, data = process_slave(urls_df, webcams, all_webcams_filename, progress, task_single)
                    total_valid_embeds += v_embeds
                    total_skipped_urls += s_urls
                    total_failed_urls += f_urls
                    all_data.extend(data)

                extract_data = process_extract(html, progress, task_single)
                if extract_data:
                    df = pd.DataFrame(extract_data)
                    if os.path.exists(INPUT_CSV):
                        existing_df = pd.read_csv(INPUT_CSV)
                        df = pd.concat([existing_df, df]).drop_duplicates(subset=['URL'])
                    df.to_csv(INPUT_CSV, index=False)
                    logger.info(f"Appended {len(extract_data)} URLs from extract to {INPUT_CSV}")

                    urls_df = pd.read_csv(INPUT_CSV)
                    v_embeds, s_urls, f_urls, data = process_slave(urls_df, webcams, all_webcams_filename, progress, task_single)
                    total_valid_embeds += v_embeds
                    total_skipped_urls += s_urls
                    total_failed_urls += f_urls
                    all_data.extend(data)

    # Final save of the HTML file
    save_webcams_html(webcams, all_webcams_filename)
    if not webcams:
        logger.warning("No valid webcams found to create the HTML file")

    # Save final CSV
    result_df = pd.DataFrame(all_data).drop_duplicates(subset=['URL'])
    result_df.to_csv(OUTPUT_CSV, index=False)
    logger.info(f"Final DataFrame saved to {OUTPUT_CSV}")

    # Verify HTML file
    verification_results = [verify_html_file(all_webcams_filename)] if os.path.exists(all_webcams_filename) else []

    # Create summary table
    table = Table(title="Processing Summary", style="cyan", header_style="bold green")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Total URLs Processed", str(len(set([d['URL'] for d in all_data]))))
    table.add_row("Valid Embed Codes Found", str(total_valid_embeds))
    table.add_row("URLs Without Embeds", str(total_skipped_urls))
    table.add_row("Failed URLs", str(total_failed_urls))
    table.add_row("Output CSV", OUTPUT_CSV)
    table.add_row("HTML Cache Directory", HTML_CACHE_DIR)
    table.add_row("Webcam Directory", WEBCAM_DIR)
    table.add_row("UnParsed Directory", UNPARSED_DIR)
    rprint(table)

    # Create verification table
    if verification_results:
        verify_table = Table(title="HTML File Verification", style="cyan", header_style="bold green")
        verify_table.add_column("File", style="cyan")
        verify_table.add_column("Embed Count", style="green")
        for result in verification_results:
            verify_table.add_row(result['File'], str(result['Embed Count']))
        rprint(verify_table)

    # Display last log lines in a sleek panel
    log_lines = get_last_log_lines()
    log_content = "".join(log_lines).strip()
    rprint(Panel(log_content, title="System Logs", border_style="green", expand=False, style="cyan"))

    # Print success message
    rprint(f"[green bold]✔ Processing complete! Data saved to {OUTPUT_CSV} and {all_webcams_filename}[/green bold]")

if __name__ == "__main__":
    main()