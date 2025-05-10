# import re
# import pandas as pd
# import requests
# import logging
# import time
# import os
# import random
# from rich import print as rprint
# from rich.progress import Progress
# from rich.table import Table
# from rich.panel import Panel
# from urllib.parse import urlparse
# from retrying import retry

# # --- Logging Setup ---
# logging.basicConfig(
#     filename='scraper.log',
#     level=logging.INFO,
#     format='%(asctime)s - %(levelname)s - %(module)s - %(message)s',
#     datefmt='%Y-%m-%d %H:%M:%S'
# )
# logger = logging.getLogger(__name__)
# console_handler = logging.StreamHandler()
# console_handler.setLevel(logging.INFO)
# console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
# logger.addHandler(console_handler)

# # --- Configuration Constants ---
# RATE_LIMIT_SECONDS = 0.5
# RETRY_SLEEP_SECONDS = 5
# MAX_RETRIES = 2
# INPUT_CSV = 'omni_eye_df.csv'
# OUTPUT_CSV = 'video_embeds.csv'
# HTML_CACHE_DIR = 'html_cache'
# WEBCAM_DIR = 'webcam_directory'
# MAX_LOG_LINES_DISPLAY = 70
# REQUEST_TIMEOUT_SECONDS = 20

# USER_AGENTS = [
#     'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
#     'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15',
#     'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0',
#     'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
#     'VLC/3.0.20 LibVLC/3.0.20',
#     'Lavf/60.3.100',
#     'QuickTime/7.7.3 (qtver=7.7.3;os=Windows NT 6.1)',
#     'Windows-Media-Player/12.0.19041.3636'
# ]

# # Create directories
# for directory in [HTML_CACHE_DIR, WEBCAM_DIR]:
#     if not os.path.exists(directory):
#         logger.debug(f"Creating directory: {directory}")
#         os.makedirs(directory)
#         logger.info(f"Created directory: {directory}")

# # Sanitize URL or name for filename
# def sanitize_for_filename(text):
#     return re.sub(r'[^\w\-_\.]', '_', text).strip('_')

# # Retry decorator for requests
# @retry(
#     stop_max_attempt_number=MAX_RETRIES,
#     wait_fixed=RETRY_SLEEP_SECONDS * 1000,
#     retry_on_exception=lambda e: isinstance(e, requests.exceptions.RequestException)
# )
# def fetch_html(url):
#     headers = {'User-Agent': random.choice(USER_AGENTS)}
#     logger.debug(f"Sending GET request to {url} with User-Agent: {headers['User-Agent']}")
#     response = requests.get(url, timeout=REQUEST_TIMEOUT_SECONDS, headers=headers)
#     response.raise_for_status()
#     return response.text

# # HTML template for a single page with multiple webcams
# def create_all_webcams_html(webcams):
#     cards = ""
#     for webcam in webcams:
#         cards += f"""
#         <div class="card">
#             <h2>{webcam['Name']}</h2>
#             <div class="video-container">
#                 {webcam['Embed_Code']}
#             </div>
#         </div>
#         """
#     return f"""
# <!DOCTYPE html>
# <html lang="en">
# <head>
#     <meta charset="UTF-8">
#     <meta name="viewport" content="width=device-width, initial-scale=1.0">
#     <title>All Webcams</title>
#     <style>
#         body {{
#             font-family: Arial, sans-serif;
#             margin: 0;
#             padding: 20px;
#             background-color: #f4f4f4;
#         }}
#         .masonry {{
#             column-count: 1;
#             column-gap: 20px;
#             max-width: 1200px;
#             margin: 0 auto;
#         }}
#         .card {{
#             break-inside: avoid;
#             background: white;
#             border-radius: 8px;
#             box-shadow: 0 2px 5px rgba(0,0,0,0.1);
#             margin-bottom: 20px;
#             padding: 15px;
#         }}
#         h2 {{
#             margin: 0 0 10px;
#             font-size: 1.5em;
#             color: #333;
#         }}
#         .video-container {{
#             position: relative;
#             width: 100%;
#             aspect-ratio: 16 / 9;
#         }}
#         iframe {{
#             width: 100%;
#             height: 100%;
#             border: none;
#         }}
#         @media (min-width: 600px) {{
#             .masonry {{
#                 column-count: 2;
#             }}
#         }}
#         @media (min-width: 900px) {{
#             .masonry {{
#                 column-count: 3;
#             }}
#         }}
#     </style>
# </head>
# <body>
#     <div class="masonry">
#         {cards}
#     </div>
# </body>
# </html>
# """

# # Function to save the HTML file
# def save_webcams_html(webcams, filename):
#     if webcams:
#         logger.debug(f"Saving HTML file: {filename} with {len(webcams)} webcams")
#         try:
#             with open(filename, 'w', encoding='utf-8') as f:
#                 f.write(create_all_webcams_html(webcams))
#             logger.info(f"Saved all webcams to {filename}")
#         except Exception as e:
#             logger.error(f"Failed to save all webcams HTML to {filename}: {str(e)}")
#     else:
#         logger.debug(f"No webcams to save to {filename}")

# # Read input CSV
# logger.debug(f"Attempting to read input CSV: {INPUT_CSV}")
# try:
#     df = pd.read_csv(INPUT_CSV)
#     logger.info(f"Successfully read {INPUT_CSV} with {len(df)} entries")
# except FileNotFoundError:
#     logger.error(f"Input CSV '{INPUT_CSV}' not found")
#     raise

# # Read existing output CSV to resume progress
# processed_urls = set()
# if os.path.exists(OUTPUT_CSV):
#     logger.debug(f"Reading existing output CSV to resume: {OUTPUT_CSV}")
#     try:
#         existing_df = pd.read_csv(OUTPUT_CSV)
#         processed_urls = set(existing_df['URL'].dropna())
#         logger.info(f"Loaded {len(processed_urls)} processed URLs from {OUTPUT_CSV}")
#     except Exception as e:
#         logger.warning(f"Failed to read existing CSV {OUTPUT_CSV}: {str(e)}")

# # Initialize list to store data
# data = list(existing_df.to_dict('records')) if 'existing_df' in locals() else []
# logger.debug("Initialized data list for storing results")
# valid_embeds = 0
# skipped_urls = 0
# failed_urls = 0
# webcams = []  # To collect all webcams for the single HTML file

# # Filter unprocessed URLs
# unprocessed_df = df[~df['URL'].isin(processed_urls)]
# logger.info(f"Found {len(unprocessed_df)} unprocessed URLs to scrape")

# # Read last log lines for display
# def get_last_log_lines():
#     try:
#         with open('scraper.log', 'r') as f:
#             lines = f.readlines()
#             return lines[-MAX_LOG_LINES_DISPLAY:] if len(lines) > MAX_LOG_LINES_DISPLAY else lines
#     except Exception:
#         return []

# # Create a progress bar
# with Progress() as progress:
#     task = progress.add_task("[cyan]Processing URLs for video embeds...", total=len(unprocessed_df))
#     all_webcams_filename = os.path.join(WEBCAM_DIR, "all_webcams.html")
#     for index, (idx, row) in enumerate(unprocessed_df.iterrows()):
#         url = row['URL']
#         name = row['Name']
#         logger.debug(f"Processing URL: {url} (Name: {name})")

#         # Fetch HTML with retries
#         try:
#             html = fetch_html(url)
#             logger.info(f"Successfully fetched HTML from {url}")
#         except requests.exceptions.RequestException as e:
#             logger.error(f"Failed to fetch {url} after {MAX_RETRIES} attempts: {str(e)}")
#             data.append({'URL': url, 'Name': name, 'Embed_Code': None})
#             failed_urls += 1
#             progress.update(task, advance=1)
#             # Save progress to CSV
#             pd.DataFrame(data).to_csv(OUTPUT_CSV, index=False)
#             logger.debug(f"Saved progress to {OUTPUT_CSV}")
#             # Save HTML file periodically
#             save_webcams_html(webcams, all_webcams_filename)
#             time.sleep(RATE_LIMIT_SECONDS)
#             continue

#         # Save HTML to cache
#         html_filename = os.path.join(HTML_CACHE_DIR, sanitize_for_filename(urlparse(url).path))
#         logger.debug(f"Saving HTML to: {html_filename}")
#         try:
#             with open(html_filename, 'w', encoding='utf-8') as f:
#                 f.write(html)
#             logger.info(f"Saved HTML to {html_filename}")
#         except Exception as e:
#             logger.error(f"Failed to save HTML to {html_filename}: {str(e)}")

#         # Extract iframe embed code
#         logger.debug("Searching for YouTube iframe embed code")
#         iframe_match = re.search(
#             r'<iframe[^>]+src="https://www\.youtube\.com/embed/[^"]+"[^>]*></iframe>',
#             html,
#             re.IGNORECASE
#         )

#         # Log match results
#         logger.debug(f"iframe_match: {'Found' if iframe_match else 'Not found'}")
#         if iframe_match:
#             embed_code = iframe_match.group(0)
#             logger.debug(f"Extracted embed code: {embed_code}")
#             rprint(f"[green]Successfully extracted embed code for {name}[/green]")
#             data.append({'URL': url, 'Name': name, 'Embed_Code': embed_code})
#             webcams.append({'Name': name, 'Embed_Code': embed_code})
#             valid_embeds += 1
#             # Save HTML file after each valid embed
#             save_webcams_html(webcams, all_webcams_filename)
#         else:
#             logger.debug("No YouTube iframe found for this URL")
#             data.append({'URL': url, 'Name': name, 'Embed_Code': None})
#             skipped_urls += 1

#         # Save progress to CSV
#         pd.DataFrame(data).to_csv(OUTPUT_CSV, index=False)
#         logger.debug(f"Saved progress to {OUTPUT_CSV}")

#         # Every 10 URLs, reload CSV and save HTML
#         if (index + 1) % 10 == 0:
#             logger.debug(f"Reloading {OUTPUT_CSV} to resume progress")
#             try:
#                 existing_df = pd.read_csv(OUTPUT_CSV)
#                 data = existing_df.to_dict('records')
#                 processed_urls = set(existing_df['URL'].dropna())
#                 unprocessed_df = df[~df['URL'].isin(processed_urls)]
#                 logger.info(f"Resumed with {len(unprocessed_df)} unprocessed URLs remaining")
#                 # Update progress bar total
#                 progress.update(task, total=len(unprocessed_df))
#             except Exception as e:
#                 logger.error(f"Failed to reload {OUTPUT_CSV}: {str(e)}")
#             # Save HTML file periodically
#             save_webcams_html(webcams, all_webcams_filename)

#         progress.update(task, advance=1)
#         time.sleep(RATE_LIMIT_SECONDS)

# # Final save of the HTML file
# save_webcams_html(webcams, all_webcams_filename)
# if not webcams:
#     logger.warning("No valid webcams found to create the HTML file")

# # Log summary of processing
# logger.info(f"Processing complete: {valid_embeds} embed codes found, {skipped_urls} URLs without embeds, {failed_urls} URLs failed")

# # Create final DataFrame
# logger.debug("Creating final pandas DataFrame from collected data")
# result_df = pd.DataFrame(data)
# logger.info(f"Created DataFrame with {len(result_df)} entries")

# # Save final CSV
# logger.debug(f"Saving final DataFrame to CSV: {OUTPUT_CSV}")
# result_df.to_csv(OUTPUT_CSV, index=False)
# logger.info(f"Final DataFrame saved to {OUTPUT_CSV}")

# # Create summary table with Rich
# table = Table(title="Processing Summary")
# table.add_column("Metric", style="cyan")
# table.add_column("Value", style="green")
# table.add_row("Total URLs Processed", str(len(unprocessed_df)))
# table.add_row("Valid Embed Codes Found", str(valid_embeds))
# table.add_row("URLs Without Embeds", str(skipped_urls))
# table.add_row("Failed URLs", str(failed_urls))
# table.add_row("Output CSV", OUTPUT_CSV)
# table.add_row("HTML Cache Directory", HTML_CACHE_DIR)
# table.add_row("Webcam Directory", WEBCAM_DIR)
# rprint(table)

# # Display last log lines in Rich panel
# log_lines = get_last_log_lines()
# log_content = "".join(log_lines).strip()
# rprint(Panel(log_content, title="Last Log Entries", border_style="blue", expand=False))

# # Print success message with Rich
# rprint(f"[green]Data successfully saved to {OUTPUT_CSV}[/green]")


#! Patch 1

import csv
import logging
import os
import re
import requests
from rich import print as rprint

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Define video platform patterns
VIDEO_PATTERNS = [
    r'<iframe[^>]+src="https?://www\.youtube\.com/embed/[^"]+"[^>]*></iframe>',  # YouTube
    r'<iframe[^>]+src="https?://player\.vimeo\.com/video/[^"]+"[^>]*></iframe>',  # Vimeo
    r'<iframe[^>]+src="https?://www\.dailymotion\.com/embed/video/[^"]+"[^>]*></iframe>',  # Dailymotion
    # Add more patterns as needed
]

def extract_embed(html):
    """Extract the first video embed code from HTML content using multiple platform patterns."""
    for pattern in VIDEO_PATTERNS:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            return match.group(0)
    return None

def process_unparsed_folder():
    """Process HTML files in the UnParsed folder and extract embed codes."""
    if not os.path.exists('UnParsed'):
        logger.info("UnParsed folder does not exist")
        return []

    html_files = [f for f in os.listdir('UnParsed') if f.endswith('.html')]
    webcams = []

    for html_file in html_files:
        filepath = os.path.join('UnParsed', html_file)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                html = f.read()
            embed_code = extract_embed(html)
            if embed_code:
                name = os.path.splitext(html_file)[0]  # Use filename without extension as name
                webcams.append({'Name': name, 'Embed_Code': embed_code})
                logger.info(f"Extracted embed code from {html_file}")
                rprint(f"[green]Successfully extracted embed code from {html_file}[/green]")
            else:
                logger.warning(f"No embed code found in {html_file}")
        except Exception as e:
            logger.error(f"Failed to process {html_file}: {str(e)}")

    return webcams

def create_all_webcams_html(webcams):
    """Generate HTML content with all webcam embeds."""
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>All Webcams</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .webcam { margin-bottom: 20px; }
        iframe { max-width: 100%; }
    </style>
</head>
<body>
    <h1>All Webcams</h1>
"""
    for webcam in webcams:
        html_content += f"""    <div class="webcam">
        <h2>{webcam['Name']}</h2>
        {webcam['Embed_Code']}
    </div>
"""
    html_content += """</body>
</html>"""
    return html_content

def save_webcams_html(webcams, filename):
    """Save the HTML content to a file."""
    if webcams:
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(create_all_webcams_html(webcams))
            logger.info(f"Saved all webcams to {filename}")
        except Exception as e:
            logger.error(f"Failed to save all webcams HTML to {filename}: {str(e)}")
    else:
        logger.debug("No webcams to save")

def main():
    input_csv = 'webcams.csv'
    output_csv = 'processed_webcams.csv'
    all_webcams_filename = 'all_webcams.html'

    # Read the input CSV
    data = []
    try:
        with open(input_csv, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            data = [row for row in reader]
    except FileNotFoundError:
        logger.error(f"Input CSV file {input_csv} not found")
        return
    except Exception as e:
        logger.error(f"Failed to read CSV file {input_csv}: {str(e)}")
        return

    # Process HTML files in UnParsed folder
    webcams = process_unparsed_folder().copy()

    # Process URLs from CSV
    headers = {'User-Agent': 'Mozilla/5.0'}
    processed_count = 0

    for i, row in enumerate(data):
        url = row.get('URL')
        name = row.get('Name', f"Webcam {i+1}")
        if not url:
            logger.warning(f"No URL found for row {i+1}")
            continue

        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            html = response.text

            embed_code = extract_embed(html)
            if embed_code:
                data[i]['Embed_Code'] = embed_code
                webcams.append({'Name': name, 'Embed_Code': embed_code})
                logger.info(f"Successfully processed {url}")
                rprint(f"[green]Successfully processed {url} - {name}[/green]")

                # Save HTML file after each successful embed
                save_webcams_html(webcams, all_webcams_filename)
            else:
                logger.warning(f"No embed code found at {url}")
                data[i]['Embed_Code'] = ''

            processed_count += 1
            if processed_count % 10 == 0:
                save_webcams_html(webcams, all_webcams_filename)
                logger.info(f"Processed {processed_count} URLs")

        except requests.RequestException as e:
            logger.error(f"Failed to fetch {url}: {str(e)}")
            data[i]['Embed_Code'] = ''
        except Exception as e:
            logger.error(f"Unexpected error processing {url}: {str(e)}")
            data[i]['Embed_Code'] = ''

    # Save final HTML file
    save_webcams_html(webcams, all_webcams_filename)

    # Save processed data to CSV
    try:
        with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['URL', 'Name', 'Embed_Code']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        logger.info(f"Saved processed data to {output_csv}")
    except Exception as e:
        logger.error(f"Failed to save processed CSV to {output_csv}: {str(e)}")

if __name__ == "__main__":
    main()