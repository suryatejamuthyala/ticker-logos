# Ticker Logos API

A minimal FastAPI application that serves logo images by ticker symbol from the `logos/` directory.

## Run locally

1. Install dependencies:

```bash
pip install fastapi uvicorn --break-system-packages
```

2. Start the server from the repository root:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

3. Open the interactive Swagger UI:

- http://127.0.0.1:8000/docs

## Usage

- By path parameter:
  - `GET /logo/ETSY`
- By query parameter:
  - `GET /logo?ticker=ETSY`

The app searches recursively under the `logos/` directory for a file whose name (without extension) matches the ticker (case-insensitive). If multiple files exist for the same ticker, it prefers:

1. Subdirectory order: `ticker_icons` > `crypto_icons` > `forex_icons` > `exchange_icons`
2. File extension order: `.png` > `.svg` > `.webp` > `.jpg` > `.jpeg` > `.ico`

If a new logo is added after startup, the endpoint will still find it via a fallback scan and update the in-memory index for subsequent requests.
