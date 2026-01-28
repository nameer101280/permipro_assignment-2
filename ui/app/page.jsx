"use client";

import { useMemo, useState } from "react";

const DEFAULT_API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8001/api/ask/";

const QUICK_PROMPTS = [
  "What is the mobiscore per ha?",
  "What does Art. 0.4 say about trees?",
  "Define bouwlaag.",
  "Which areas are overstromingsgevoelige?",
];

const clampNumber = (value, min, max, fallback) => {
  const numeric = Number(value);
  if (Number.isNaN(numeric)) {
    return fallback;
  }
  return Math.min(max, Math.max(min, numeric));
};

const buildHealthUrl = (apiUrl) => {
  try {
    const parsed = new URL(apiUrl);
    parsed.pathname = "/";
    parsed.search = "";
    return parsed.toString();
  } catch (error) {
    return apiUrl.replace(/\/api\/ask\/?$/, "/");
  }
};

export default function Home() {
  const [apiUrl, setApiUrl] = useState(DEFAULT_API_URL);
  const [question, setQuestion] = useState("");
  const [topK, setTopK] = useState(3);
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [apiStatus, setApiStatus] = useState(null);
  const [showJson, setShowJson] = useState(false);

  const safeTopK = useMemo(() => clampNumber(topK, 1, 5, 3), [topK]);
  const healthUrl = useMemo(() => buildHealthUrl(apiUrl), [apiUrl]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed) {
      setError("Please enter a question.");
      return;
    }

    setError("");
    setResult(null);
    setLoading(true);
    setShowJson(false);

    const startedAt = performance.now();

    try {
      const response = await fetch(apiUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: trimmed, top_k: safeTopK }),
      });

      let payload = null;
      try {
        payload = await response.json();
      } catch (parseError) {
        throw new Error("Invalid JSON response from the API.");
      }

      if (!response.ok) {
        throw new Error(payload?.error || "Request failed.");
      }

      const clientMs = Math.round(performance.now() - startedAt);
      const enriched = { ...payload, _client_ms: clientMs };
      setResult(enriched);
      setHistory((prev) =>
        [{ question: trimmed, response: enriched, at: new Date() }, ...prev].slice(0, 6)
      );
    } catch (requestError) {
      setError(requestError.message || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  };

  const handlePromptClick = (prompt) => {
    setQuestion(prompt);
    setError("");
  };

  const handleCheckApi = async () => {
    setApiStatus("checking");
    try {
      const response = await fetch(healthUrl, { method: "GET" });
      if (!response.ok) {
        throw new Error("API health check failed.");
      }
      setApiStatus("ok");
    } catch (error) {
      setApiStatus("error");
    }
  };

  const handleCopy = async (text) => {
    try {
      await navigator.clipboard.writeText(text);
    } catch (copyError) {
      setError("Unable to copy to clipboard.");
    }
  };

  const meta = result?.meta || {};
  const routeScores = meta.route_scores || {};
  const topMatches = meta.top_matches || [];

  return (
    <main className="page">
      <section className="card">
        <header className="hero">
          <div className="eyebrow">Question-Answering Agent</div>
          <h1>Ask the mock datasets a question</h1>
          <p>
            This UI sends a question to the Django API and displays the routed
            answer from either geo data or regulation data.
          </p>
        </header>

        <form className="form" onSubmit={handleSubmit}>
          <label className="field">
            <span>API URL</span>
            <input
              type="url"
              value={apiUrl}
              onChange={(event) => setApiUrl(event.target.value)}
              placeholder="http://127.0.0.1:8001/api/ask/"
              required
            />
            <small>Include the full /api/ask/ endpoint.</small>
          </label>

          <label className="field">
            <span>Top matches to return</span>
            <input
              type="number"
              min={1}
              max={5}
              value={topK}
              onChange={(event) => setTopK(event.target.value)}
            />
            <small>Controls how many top matches appear in metadata.</small>
          </label>

          <label className="field">
            <span>Your question</span>
            <textarea
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Ask about mobiscore, water, bouwlaag, Art. 0.4..."
              rows={4}
              required
            />
          </label>

          <div className="actions">
            <button className="button" type="submit" disabled={loading}>
              {loading ? "Asking..." : "Ask the API"}
            </button>
            <button
              className="ghost"
              type="button"
              onClick={handleCheckApi}
              disabled={apiStatus === "checking"}
            >
              {apiStatus === "checking" ? "Checking..." : "Check API"}
            </button>
            {apiStatus ? (
              <span className={`status status-${apiStatus}`}>{apiStatus}</span>
            ) : null}
          </div>
        </form>

        <div className="quick">
          <div className="quick-title">Quick prompts</div>
          <div className="quick-grid">
            {QUICK_PROMPTS.map((prompt) => (
              <button
                key={prompt}
                type="button"
                className="chip"
                onClick={() => handlePromptClick(prompt)}
              >
                {prompt}
              </button>
            ))}
          </div>
        </div>

        {error ? (
          <div className="alert error" role="alert">
            {error}
          </div>
        ) : null}

        {result ? (
          <div className="result" aria-live="polite">
            <div className="result-head">
              <div className={`tag tag-${result.source}`}>{result.source}</div>
              <div className="result-actions">
                <button
                  type="button"
                  className="ghost"
                  onClick={() => handleCopy(result.answer)}
                >
                  Copy answer
                </button>
                <button
                  type="button"
                  className="ghost"
                  onClick={() => handleCopy(JSON.stringify(result, null, 2))}
                >
                  Copy JSON
                </button>
              </div>
            </div>
            <div className="answer">{result.answer}</div>

            <div className="meta-grid">
              <div className="meta-card">
                <span>Confidence</span>
                <strong>
                  {meta.confidence !== undefined ? meta.confidence : "--"}
                </strong>
              </div>
              <div className="meta-card">
                <span>Server time</span>
                <strong>
                  {meta.processing_ms !== undefined
                    ? `${meta.processing_ms} ms`
                    : "--"}
                </strong>
              </div>
              <div className="meta-card">
                <span>Client time</span>
                <strong>
                  {result._client_ms !== undefined
                    ? `${result._client_ms} ms`
                    : "--"}
                </strong>
              </div>
              <div className="meta-card">
                <span>Route scores</span>
                <strong>
                  geo {routeScores.geo ?? 0} · regulation {routeScores.regulation ?? 0}
                </strong>
              </div>
            </div>

            {topMatches.length ? (
              <div className="matches">
                <div className="section-title">Top matches</div>
                <div className="match-grid">
                  {topMatches.map((match, index) => (
                    <div className="match" key={`${match.name || match.title}-${index}`}>
                      <div className="match-title">
                        {match.name || match.title || "Match"}
                      </div>
                      <div className="match-meta">
                        score {match.score}
                        {match.article ? ` · ${match.article}` : ""}
                      </div>
                      {match.details ? (
                        <div className="match-snippet">{match.details}</div>
                      ) : null}
                      {match.snippet ? (
                        <div className="match-snippet">{match.snippet}</div>
                      ) : null}
                    </div>
                  ))}
                </div>
              </div>
            ) : null}

            <div className="json-toggle">
              <button
                type="button"
                className="ghost"
                onClick={() => setShowJson((prev) => !prev)}
              >
                {showJson ? "Hide" : "Show"} raw JSON
              </button>
            </div>
            {showJson ? (
              <pre className="json">{JSON.stringify(result, null, 2)}</pre>
            ) : null}
          </div>
        ) : null}

        {history.length ? (
          <div className="history">
            <div className="section-title">Recent questions</div>
            <div className="history-grid">
              {history.map((item, index) => (
                <div className="history-card" key={`${item.at}-${index}`}>
                  <div className="history-question">{item.question}</div>
                  <div className={`tag tag-${item.response.source}`}>
                    {item.response.source}
                  </div>
                  <div className="history-answer">{item.response.answer}</div>
                </div>
              ))}
            </div>
            <button
              type="button"
              className="ghost"
              onClick={() => setHistory([])}
            >
              Clear history
            </button>
          </div>
        ) : null}
      </section>
    </main>
  );
}
