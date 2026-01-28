# Question-Answering Agent API

A small Django REST Framework API that routes questions to a mock geo dataset or a mock regulation dataset and returns a JSON answer with the chosen source. An optional Next.js UI is included for easy demos.

## Setup

1. Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

2. Run the server (example uses port 8001):

```bash
python3 manage.py runserver 8001
```

The API will be available at `http://127.0.0.1:8001/api/ask/`.

Note: This project does **not** use a database by design (per the assignment).

## Quick start (API)

```bash
curl -X POST http://127.0.0.1:8001/api/ask/ \
  -H "Content-Type: application/json" \
  -d '{"question":"What is the mobiscore per ha?"}'
```

## API endpoints

- `GET /` health check
- `POST /api/ask/` question-answer endpoint

## Example curl

```bash
curl -X POST http://127.0.0.1:8001/api/ask/ \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the mobiscore per ha?"}'
```

Example response:

```json
{
  "answer": "Match in geo data: Mobiscore per ha. status=1; distance_m=0; overlap_fraction=1; details=Geeft_per_ha-cel_de_totale_mobiscore_tussen_0_en_10_weer=7.759283065795898.",
  "source": "geo",
  "meta": {
    "confidence": 0.83,
    "route_confidence": 1.0,
    "match_confidence": 0.67,
    "route_scores": { "geo": 6, "regulation": 0 },
    "top_matches": [
      {
        "name": "Mobiscore per ha",
        "score": 2,
        "status": "1",
        "distance_m": "0",
        "overlap_fraction": "1",
        "details": "Geeft_per_ha-cel_de_totale_mobiscore_tussen_0_en_10_weer=7.759283065795898"
      }
    ],
    "processing_ms": 2,
    "data_file": "mock_geo_data.csv"
  }
}
```

## Request options

- `top_k` (optional): integer 1-5, controls how many top matches are returned in `meta.top_matches`.

## Example questions

Geo dataset (`mock_geo_data.csv`)
- “What is the mobiscore per ha?”
- “Show overstromingsgevoelige gebieden.”
- “What is the maximum hoogte luchtvaart?”
- “What does the Wegenregister say about wegcategorie?”

Regulation dataset (`mock_regulation_data.txt`)
- “What does Art. 0.4 say about trees?”
- “Define bouwlaag.”
- “What is a bouwvlak?”
- “What does Art. 0.7 say about groendaken?”

Unknown source (should return `source: "unknown"`)
- “What is the capital of France?”
- “Tell me about the weather.”

## Optional Next.js UI

The UI lives in `ui/` and calls the API endpoint directly.
It includes quick prompts, metadata display, and a short history of recent questions.

```bash
cd ui
npm install
npm run dev
```

By default it expects the API at `http://127.0.0.1:8001/api/ask/`.
To override, set `NEXT_PUBLIC_API_URL` (see `ui/.env.example`).

## How the data is used

- Geo questions are matched against `mock_geo_data.csv` (CSV rows with `name`, `status`, `distance_m`, `overlap_fraction`, and `api_name`).
- Regulation questions are matched against `mock_regulation_data.txt` (text blocks and articles).
- No database is used. All answers come directly from the two mock files.

## Extras beyond the base requirements

- Optional Next.js UI for demos and manual testing.
- Health endpoint at `GET /`.
- Metadata in responses (`meta`) with confidence scores, routing scores, timings, and top matches.
- Enhanced routing logic (keyword + token overlap scoring, article reference boosts).

## Routing logic

- The router uses keyword + token overlap scoring to decide between `geo` and `regulation`.
- Article references like `Art. 0.4` strongly boost the regulation route.
- If both sources score similarly (or no meaningful signals are found), the source is `unknown`.
- For a chosen source, the system searches the corresponding mock file and returns the best matching block or row plus `top_matches` metadata.

## Data file formats

- `mock_geo_data.csv`: CSV with columns `name`, `status`, `distance_m`, `overlap_fraction`, `api_name`.
  - The `api_name` column contains JSON-like data used for quick summaries.
- `mock_regulation_data.txt`: Plain text containing regulation articles and definitions.

## Tests

Run the automated tests:

```bash
python3 manage.py test
```

## Reviewer checklist

Quick steps a reviewer can follow to verify the assignment:

1. Install deps: `python3 -m pip install -r requirements.txt`
2. Run server: `python3 manage.py runserver 8001`
3. Send a request:
   ```bash
   curl -X POST http://127.0.0.1:8001/api/ask/ \
     -H "Content-Type: application/json" \
     -d '{"question":"What is the mobiscore per ha?"}'
   ```
4. Run tests: `python3 manage.py test`
5. (Optional) UI: `cd ui && npm install && npm run dev`

## Architecture (short)

- `ask/views.py`: API endpoints (`/` health, `/api/ask/` question route)
- `ask/logic.py`: routing + search + scoring, returns `answer`, `source`, and metadata
- `ask/data.py`: loads mock files (CSV + TXT) with caching
- `mock_geo_data.csv` / `mock_regulation_data.txt`: the only data sources
- `ui/`: optional Next.js UI for manual testing and demos
