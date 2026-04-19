# Data Sources and License Registry

This document tracks every external data source used in the project,
along with its license, attribution requirement, and handling policy.
No data file enters `data/` without a corresponding entry here.

## Handling Principles

1. **License first.** A source is not used until its license has been
   read, recorded in this file, and judged compatible with the intended
   use (research, non-commercial evaluation, potential publication).
2. **No silent downloads.** YouTube videos are never persisted as files.
   Live streams are processed frame-by-frame through an ffmpeg pipe and
   only the extracted features / detections are stored.
3. **Attribution at the record level.** Each Xeno-canto or Macaulay
   recording cached locally keeps its recordist, country, license, and
   original URL in a sidecar JSON.
4. **Deletion on request.** If a rights holder requests removal, the
   cached file and all derived artefacts are deleted within 7 days.

## Tier 1: Public Bioacoustic Archives

### Xeno-canto

- URL: https://xeno-canto.org/
- API: `https://xeno-canto.org/api/3/recordings?query=...&key=<API_KEY>`
  - API v2 was retired (the endpoint returns
    `{"error":"server_error","message":"Xeno-canto API v2 is no longer available..."}`).
  - v3 requires a free API key. Register at
    https://xeno-canto.org/account and set
    `XENO_CANTO_API_KEY` in the environment before running
    `src/xeno_canto_test.py`.
  - Useful v3 query params: `query`, `key`, `page`, `per_page`.
  - Query syntax keeps the v2 field operators (`q:A`, `grp:birds`,
    `cnt:Japan`, `len:>60`, etc.).
- Licenses: Creative Commons (CC0, CC-BY, CC-BY-NC, CC-BY-SA, and
  CC-BY-NC-SA variants). The exact license is returned per recording in
  the `lic` field.
- Attribution (per recording): recordist name, xeno-canto ID (`XC######`),
  source URL, license URL.
- Policy: commercial derivatives **not** produced; CC-BY-NC content is
  acceptable for this research project. Each cached file is paired with
  a `.json` sidecar containing the metadata above.

### Macaulay Library (Cornell Lab)

- URL: https://www.macaulaylibrary.org/
- License: research / educational use under the Cornell terms. Bulk
  download is not available via a public API.
- Policy: only used if a specific recording is needed and cannot be
  sourced from Xeno-canto. Each use is logged in this file with ML ID,
  URL, and date accessed.

## Tier 2: YouTube Live Streams

- Policy: **no download, no persistent video file**. Streams are opened
  with `yt-dlp --get-url`, piped into `ffmpeg` for frame / audio
  extraction, and only the extracted features (detections, embeddings,
  spectrograms) are written to disk.
- Files stored under `data/youtube_streams/` must be derived artefacts
  only (CSV of detections, NPY of embeddings). No `.mp4`, `.webm`, or
  equivalent container formats are kept.
- Attribution: channel name, stream URL, ISO8601 timestamp of capture.

## Tier 3: CC-Licensed Video

- Sources: Wikimedia Commons, Internet Archive, Pexels (video section
  under its free-use terms), or direct upload by researchers.
- Each clip is logged below with title, author, license, and URL.

## Tier 4: Balcony (Self-Recorded)

- Hardware: Raspberry Pi 4B + Camera Module HQ (SC0870 wide-angle lens).
- License held by: Katsuma Murashita. Usage within this project is
  unrestricted. A separate public release license will be decided when
  the dataset is published.

## Per-Item License Registry (Template)

Add one row per file or session. Keep sorted by date.

| Date (ISO) | Tier | Source / ID | Species | License | Attribution URL | Local path | Notes |
|------------|------|-------------|---------|---------|-----------------|-----------|-------|
| YYYY-MM-DD | 1    | XC######    | genus species | CC-BY-NC | https://xeno-canto.org/###### | data/xeno_canto/XC######.wav | - |
| YYYY-MM-DD | 2    | youtube:VIDEOID | (stream) | (N/A, no file) | https://youtube.com/... | data/youtube_streams/<run_id>/ | derived only |
| YYYY-MM-DD | 4    | balcony:<run_id> | (mixed)  | held locally | - | data/balcony/<run_id>/ | Pi HQ cam |

## Removal / Takedown Log

| Date | Item | Requester | Action taken |
|------|------|-----------|--------------|
|      |      |           |              |
