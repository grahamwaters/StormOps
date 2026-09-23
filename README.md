# StormOps

StormOps currently includes an offline-first cloud image simulator and an optional command-line webcam embed collector. The simulator is the primary app; the collector is a separate research utility and does not feed live camera data into the interface.

## Run the Cloud Lab

Requirements: Python 3 for a local static-file server. The image simulator runs entirely in your browser and does not require Python packages or an internet connection.

```sh
python3 -m http.server 8000 --bind 127.0.0.1 --directory frontend
```

Open <http://127.0.0.1:8000>. Choose a PNG, JPEG, or WebP image up to 12 MB and select **Build cloud field**. The app samples bright regions locally, animates them on the canvas, and can export a standalone HTML visualization. Double-click the canvas or use **Expand canvas** to enlarge it; press Escape to return.

Image brightness is only a visual heuristic. This tool does not interpret radar, determine storm structure, or issue forecasts or warnings. Images are not uploaded or persisted by the app.

## Webcam Embed Collector (Experimental)

The collector in `backend/regex_unified.py` is an opt-in command-line utility for locally supplied Webcamtaxi HTML pages or URL records. It can make HTTPS requests to `webcamtaxi.com` and stores its CSV, HTML, cache, and log outputs in the current working directory. It is not connected to the Cloud Lab UI. Use only where permitted by the source site's terms and access rules.

Install the Python dependencies, place source HTML files in `UnParsed/` (or `raw_page_html.html` in the repository root), then run:

```sh
./setup.sh
.venv/bin/python backend/regex_unified.py
```

The collector only requests HTTPS URLs on `webcamtaxi.com` and does not follow redirects. Extracted player frames are rebuilt from an allowlist of YouTube, Vimeo, and Dailymotion embed URLs; names are HTML-escaped. Review generated output before sharing it. The collector remains experimental: site markup changes may cause missed cameras, and a completed run does not imply that a camera is live.

## Project Layout

- `frontend/index.html` — Cloud Lab interface
- `frontend/css/style.css` — responsive styles and focus states
- `frontend/js/app.js` — local image sampling, animation, and export
- `backend/regex_unified.py` — experimental webcam extraction CLI
- `setup.sh` — creates a project-local virtual environment and installs CLI dependencies

## Local Static Checks

```sh
node --check frontend/js/app.js
python3 -m py_compile backend/regex_unified.py
bash -n setup.sh
git diff --check
```

No license terms have been selected for this repository yet. The existing `LICENSE` file is empty.
