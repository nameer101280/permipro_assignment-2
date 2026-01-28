
# Assignment: Question-Answering Agent API (Django REST Framework + Optional Next.js UI)

## 1. Goal

Build a small Django REST Framework (DRF) API that exposes a single endpoint where a user can submit a natural-language question.
Your system must:

1. Determine which data source to use based on the question:
   - Geo data file
   - Regulation data file
2. Load and search the correct mock data file
3. Return a clear JSON answer, including which source was used

- The API must always return a `source` value, which must be one of: `"geo"`, `"regulation"`, `"unknown"`
- You must also include automated tests validating the main logic and API behavior.
- Use the two mock files provided for geo and regulation data.
- As an optional bonus task, you may build a minimal Next.js UI that sends questions to your API and displays the response.


## 2. Technical Requirements

- Django REST Framework
- Implement a single endpoint: `POST /api/ask/`
- Implement simple routing logic that analyzes the question and returns a source: `"geo"`, `"regulation"`, or `"unknown"`
- Read and query the two mock data files
- Do not use a database
- Implement proper error handling:

### Expected API Response

Every successful response must contain:

```json
{
  "answer": "<string>",
  "source": "geo | regulation | unknown"
}
```

## 3. Deliverables

Please provide:

1. Source code (zip or repo link)
2. A README with:
   - How to run the project
   - Example curl commands
   - Explanation of the routing logic
   - Description of the data file formats
3. Automated tests


