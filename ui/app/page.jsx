"use client";

import { useState } from "react";

const DEFAULT_API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8001/api/ask/";

const QUICK_PROMPTS = [
  "What is the mobiscore per ha?",
  "What does Art. 0.4 say about trees?",
  "Define bouwlaag.",
  "Which areas are overstromingsgevoelige?",
];

export default function Home() {
  const [apiUrl, setApiUrl] = useState(DEFAULT_API_URL);
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

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

    try {
      const response = await fetch(apiUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: trimmed }),
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

      setResult(payload);
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
              placeholder="http://127.0.0.1:8000/api/ask/"
              required
            />
            <small>Include the full /api/ask/ endpoint.</small>
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

          <button className="button" type="submit" disabled={loading}>
            {loading ? "Asking..." : "Ask the API"}
          </button>
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
            <div className={`tag tag-${result.source}`}>{result.source}</div>
            <div className="answer">{result.answer}</div>
          </div>
        ) : null}
      </section>
    </main>
  );
}
