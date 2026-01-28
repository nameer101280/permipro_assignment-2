# Question-Answering Agent API

A small Django REST Framework API that routes questions to a mock geo dataset or a mock regulation dataset and returns a JSON answer with the chosen source.

## Setup

1. Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

2. Run the server:

```bash
python3 manage.py runserver
```

The API will be available at `http://127.0.0.1:8000/api/ask/`.

## API endpoints

- `GET /` health check
- `POST /api/ask/` question-answer endpoint

## Example curl

```bash
curl -X POST http://127.0.0.1:8000/api/ask/ \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the mobiscore per ha?"}'
```

Example response:

```json
{
  "answer": "Match in geo data: Mobiscore per ha. status=1; distance_m=0; overlap_fraction=1; details=Geeft_per_ha-cel_de_totale_mobiscore_tussen_0_en_10_weer=7.759283065795898.",
  "source": "geo"
}
```

## Optional Next.js UI

The UI lives in `ui/` and calls the API endpoint directly.

```bash
cd ui
npm install
npm run dev
```

By default it expects the API at `http://127.0.0.1:8001/api/ask/`.
To override, set `NEXT_PUBLIC_API_URL` (see `ui/.env.example`).

## Routing logic

- The router uses keyword matching to decide between `geo` and `regulation`.
- If both sources score the same (or no keywords are found), the source is `unknown`.
- For a chosen source, the system searches the corresponding mock file and returns the best matching block or row.

## Data file formats

- `mock_geo_data.csv`: CSV with columns `name`, `status`, `distance_m`, `overlap_fraction`, `api_name`.
  - The `api_name` column contains JSON-like data used for quick summaries.
- `mock_regulation_data.txt`: Plain text containing regulation articles and definitions.

## Tests

Run the automated tests:

```bash
python3 manage.py test
```
