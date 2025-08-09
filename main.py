from fastapi import FastAPI, HTTPException, Query, Path
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List, Optional
from pathlib import Path as SysPath
import mimetypes

app = FastAPI(title="Ticker Logos API", description="Return logo images by ticker from the logos directory", version="1.0.0")

# Allow CORS for convenience (adjust origins as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Base directory containing logos
BASE_DIR = SysPath(__file__).parent
LOGOS_DIR = BASE_DIR / "logos"

# Supported image extensions in order of preference if duplicates exist for same ticker
IMAGE_EXT_PREFERENCE: List[str] = [
    ".png", ".svg", ".webp", ".jpg", ".jpeg", ".ico"
]

# Subdirectory preference order (if the same ticker exists in multiple categories)
SUBDIR_PREFERENCE: List[str] = [
    "ticker_icons",  # default stock tickers
    "crypto_icons",  # crypto symbols
    "forex_icons",   # forex pairs
    "exchange_icons" # exchanges
]

# An index mapping lowercase ticker -> best matching file path
INDEX: Dict[str, SysPath] = {}


def _is_image_file(p: SysPath) -> bool:
    if not p.is_file():
        return False
    return p.suffix.lower() in IMAGE_EXT_PREFERENCE


def _ext_rank(ext: str) -> int:
    try:
        return IMAGE_EXT_PREFERENCE.index(ext.lower())
    except ValueError:
        return len(IMAGE_EXT_PREFERENCE)


def _subdir_rank(p: SysPath) -> int:
    # determine immediate subdir under logos/
    try:
        # Find the part immediately after logos
        parts = p.relative_to(LOGOS_DIR).parts
        if not parts:
            return len(SUBDIR_PREFERENCE)
        sub = parts[0]
        return SUBDIR_PREFERENCE.index(sub) if sub in SUBDIR_PREFERENCE else len(SUBDIR_PREFERENCE)
    except Exception:
        return len(SUBDIR_PREFERENCE)


def build_index() -> None:
    # Scan all image files under logos and build an index
    if not LOGOS_DIR.exists():
        return

    candidates: Dict[str, List[SysPath]] = {}

    for path in LOGOS_DIR.rglob("*"):
        if _is_image_file(path):
            ticker_key = path.stem.lower()
            candidates.setdefault(ticker_key, []).append(path)

    # Choose best candidate per ticker based on subdir and extension preference then path name
    for ticker_key, paths in candidates.items():
        best = sorted(
            paths,
            key=lambda p: (
                _subdir_rank(p),
                _ext_rank(p.suffix),
                str(p).lower(),
            ),
        )[0]
        INDEX[ticker_key] = best


# Build index at startup
build_index()


@app.get("/", summary="API Info")
async def root() -> JSONResponse:
    return JSONResponse({
        "name": "Ticker Logos API",
        "version": "1.0.0",
        "endpoints": {
            "get_logo_path_param": "/logo/{ticker}",
            "get_logo_query_param": "/logo?ticker=ETSY"
        },
        "notes": "Searches recursively under the 'logos' directory and returns the best match image by ticker (case-insensitive)."
    })


def _file_response_for(path: SysPath) -> FileResponse:
    # Guess MIME type; fall back to octet-stream if unknown
    mime, _ = mimetypes.guess_type(str(path))
    if not mime and path.suffix.lower() == ".svg":
        mime = "image/svg+xml"
    return FileResponse(path=path, media_type=mime or "application/octet-stream", filename=path.name)


@app.get(
    "/logo/{ticker}",
    response_class=FileResponse,
    responses={404: {"description": "Ticker logo not found"}},
    summary="Get logo by ticker (path parameter)",
)
async def get_logo_by_path(ticker: str = Path(..., description="Ticker symbol, case-insensitive")):
    ticker_key = ticker.strip().lower()
    if not ticker_key:
        raise HTTPException(status_code=400, detail="Ticker must not be empty")

    # Try index first
    path = INDEX.get(ticker_key)

    # Fallback: if not in index, attempt direct lookup by scanning (e.g., in case new file added after startup)
    if path is None and LOGOS_DIR.exists():
        for p in LOGOS_DIR.rglob("*"):
            if _is_image_file(p) and p.stem.lower() == ticker_key:
                path = p
                # Update index for future hits
                if ticker_key in INDEX:
                    # compare and keep best
                    current = INDEX[ticker_key]
                    better = sorted([current, p], key=lambda f: (_subdir_rank(f), _ext_rank(f.suffix), str(f).lower()))[0]
                    INDEX[ticker_key] = better
                else:
                    INDEX[ticker_key] = p
                break

    if path and path.exists():
        return _file_response_for(path)

    raise HTTPException(status_code=404, detail=f"Logo not found for ticker '{ticker}'")


@app.get(
    "/logo",
    response_class=FileResponse,
    responses={
        302: {"description": "Redirects to /logo/{ticker}"},
        404: {"description": "Ticker logo not found"},
    },
    summary="Get logo by ticker (query parameter)",
)
async def get_logo_by_query(ticker: Optional[str] = Query(None, description="Ticker symbol, case-insensitive")):
    if ticker is None:
        # Redirect to docs if no ticker provided
        return RedirectResponse(url="/docs")
    return await get_logo_by_path(ticker)


# Convenience: allow running with `python main.py`
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
