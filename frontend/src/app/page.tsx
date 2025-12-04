"use client";

import { useState } from "react";
import { checkSingleNews, checkBulkNews, PredictionResult, ApiError } from "@/lib/api";

export default function Home() {
  const [text, setText] = useState("");
  const [results, setResults] = useState<PredictionResult[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleCheck = async () => {
    const headlines = text.trim().split('\n').filter(line => line.trim() !== '');

    if (headlines.length === 0) {
      setError("Please enter at least one headline.");
      return;
    }

    setLoading(true);
    setError("");
    setResults(null);

    try {
      let response: PredictionResult[] | PredictionResult | ApiError;
      if (headlines.length > 1) {
        response = await checkBulkNews(headlines);
      } else {
        response = await checkSingleNews(headlines[0]);
      }

      if ('status' in response && response.status === 'error') {
        setError(response.message);
      } else if (Array.isArray(response)) {
        setResults(response);
      } else {
        setResults([response as PredictionResult]);
      }
    } catch (err) {
      setError("Failed to connect to the server.");
    } finally {
      setLoading(false);
    }
  };

  const renderResult = (result: PredictionResult) => {
    const isReal = result.prediction === "Real";
    const realProb = isReal ? result.confidence : 1 - result.confidence;
    const fakeProb = 1 - realProb;

    return (
      <div key={result.original_text} className={`mt-6 p-6 rounded-xl border ${isReal
        ? "bg-green-900/20 border-green-500/50"
        : "bg-red-900/20 border-red-500/50"
        } animate-in fade-in slide-in-from-bottom-4 duration-500`}>
        
        <p className="text-gray-300 mb-4 border-b border-gray-700 pb-2">"{result.original_text}"</p>

        <div className="flex items-center justify-between mb-4">
          <h3 className="text-xl font-semibold text-gray-200">Analysis Result</h3>
          <span className={`px-4 py-1 rounded-full text-sm font-bold ${isReal
            ? "bg-green-500/20 text-green-400"
            : "bg-red-500/20 text-red-400"
            }`}>
            {result.prediction?.toUpperCase() || "UNKNOWN"}
          </span>
        </div>

        <div className="space-y-4">
          <div>
            <div className="flex justify-between text-sm mb-1">
              <span className="text-gray-400">Confidence Score</span>
              <span className="text-white font-medium">{(result.confidence * 100).toFixed(1)}%</span>
            </div>
            <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
              <div
                className={`h-full transition-all duration-1000 ease-out ${isReal ? "bg-green-500" : "bg-red-500"
                  }`}
                style={{ width: `${result.confidence * 100}%` }}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4 pt-4 border-t border-gray-700/50">
            <div className="text-center p-3 bg-gray-900/50 rounded-lg">
              <div className="text-xs text-gray-500 uppercase tracking-wider">Real Probability</div>
              <div className="text-lg font-mono text-green-400">
                {(realProb * 100).toFixed(1)}%
              </div>
            </div>
            <div className="text-center p-3 bg-gray-900/50 rounded-lg">
              <div className="text-xs text-gray-500 uppercase tracking-wider">Fake Probability</div>
              <div className="text-lg font-mono text-red-400">
                {(fakeProb * 100).toFixed(1)}%
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-6 bg-gray-900 text-white">
      <div className="w-full max-w-2xl space-y-8">
        <div className="text-center space-y-2">
          <h1 className="text-4xl font-bold tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-purple-500">
            Tamil Fake News Detector
          </h1>
          <p className="text-gray-400">
            Enter one or more Tamil news headlines (one per line) to verify their authenticity.
          </p>
        </div>

        <div className="bg-gray-800 p-8 rounded-2xl shadow-xl border border-gray-700 space-y-6">
          <div className="space-y-2">
            <label htmlFor="headline" className="block text-sm font-medium text-gray-300">
              News Headline(s) (Tamil)
            </label>
            <textarea
              id="headline"
              rows={4}
              className="w-full rounded-lg bg-gray-900 border-gray-600 text-white placeholder-gray-500 focus:ring-2 focus:ring-blue-500 focus:border-transparent p-4 transition-all resize-none"
              placeholder="Enter headline(s) here, one per line..."
              value={text}
              onChange={(e) => setText(e.target.value)}
            />
          </div>

          {error && (
            <div className="p-4 bg-red-900/50 border border-red-500/50 rounded-lg text-red-200 text-sm">
              {error}
            </div>
          )}

          <button
            onClick={handleCheck}
            disabled={loading}
            className={`w-full py-4 px-6 rounded-lg font-semibold text-lg transition-all transform active:scale-95 ${loading
              ? "bg-gray-600 cursor-not-allowed"
              : "bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 shadow-lg hover:shadow-blue-500/25"
              }`}
          >
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <svg className="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Analyzing...
              </span>
            ) : (
              "Check Authenticity"
            )}
          </button>

          {results && (
            <div className="space-y-4">
              {results.map(renderResult)}
            </div>
          )}
        </div>
      </div>
    </main>
  );
}