import re
import pandas as pd
import logging
from rich import print as rprint
from rich.progress import Progress

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

savefile = 'omni_eye_df.csv'

# Read HTML from file
logger.debug("Attempting to read HTML file: raw_page_html.html")
try:
    with open('raw_page_html.html', 'r') as file:
        html = file.read()
    logger.info("Successfully read HTML file")
except FileNotFoundError:
    logger.error("HTML file 'raw_page_html.html' not found")
    raise

# Base URL
base_url = 'https://www.webcamtaxi.com'
logger.debug(f"Base URL set to: {base_url}")

# Find all <a> tags
logger.debug("Searching for <a> tags in HTML")
a_tags = re.findall(r'<a\s[^>]+>', html)
logger.info(f"Found {len(a_tags)} <a> tags")

# Initialize list to store data
data = []
logger.debug("Initialized empty data list for storing results")
valid_tags = 0
skipped_tags = 0

# Create a progress bar
with Progress() as progress:
    task = progress.add_task("[cyan]Processing <a> tags...", total=len(a_tags))
    for tag in a_tags:
        logger.debug(f"Processing tag: {tag}")
        # Extract href (quoted or unquoted) and title
        href_match = re.search(r'href\s*=\s*["\']?([^"\s>]+)["\']?', tag)
        title_match = re.search(r'title="([^"]+)"', tag)

        # Log match results for debugging
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
            # Convert relative URL to full URL
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
            if not href_match and not title_match:
                logger.debug("Skipping tag: Missing both href and title attributes")
            elif not href_match:
                logger.debug("Skipping tag: Missing href attribute")
            elif not title_match:
                logger.debug("Skipping tag: Missing title attribute")
        progress.update(task, advance=1)

# Log summary of processing
logger.info(f"Processing complete: {valid_tags} valid tags processed, {skipped_tags} tags skipped")

# Create DataFrame
logger.debug("Creating pandas DataFrame from collected data")
df = pd.DataFrame(data)
logger.info(f"Created DataFrame with {len(df)} entries")

# Save to CSV
logger.debug(f"Attempting to save DataFrame to CSV: {savefile}")
df.to_csv(savefile, index=False)
logger.info(f"DataFrame successfully saved to {savefile}")

# Print success message with rich
rprint(f"[green]Data successfully saved to {savefile}[/green]")