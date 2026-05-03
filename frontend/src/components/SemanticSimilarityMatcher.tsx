import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Search, Loader2, ExternalLink } from "lucide-react";
import { SERVICE_ENDPOINTS } from "@/lib/serviceUrls";

interface SimilarityResult {
  claim: string;
  similar_sources: Array<{
    source: string;
    similarity_score: number;
    url?: string;
    title?: string;
  }>;
  top_k: number;
}

const SemanticSimilarityMatcher = () => {
  const [claim, setClaim] = useState("");
  const [mode, setMode] = useState("auto");
  const [topK, setTopK] = useState(1);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState<SimilarityResult | null>(null);
  const [error, setError] = useState("");
  const [expandedSamples, setExpandedSamples] = useState<Record<number, boolean>>({});

  // Support both backend response shapes: `neighbors` (new) and `similar_sources` (legacy)
  const matches = result ? ((result as any).neighbors ?? (result as any).similar_sources ?? []) : [];

  const handleSimilarityCheck = async () => {
    if (!claim.trim()) return;

    setIsAnalyzing(true);
    setError("");

    try {
      // Debug: log outgoing payload
      console.log("[SM] Sending similarity request", { claim, top_k: topK, mode });
      console.log("[SM] Using similarity endpoint:", SERVICE_ENDPOINTS.similarityVerify);
      const response = await fetch(SERVICE_ENDPOINTS.similarityVerify, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          claim: claim,
          top_k: topK,
          mode: mode
        }),
      });

      // Debug: capture raw response text for better diagnostics
      const rawText = await response.text();
      console.log("[SM] Similarity response status", response.status, "body:", rawText);

      if (!response.ok) {
        // try to parse json if possible, otherwise include raw text
        let details = rawText;
        try {
          details = JSON.parse(rawText);
        } catch (e) {
          // keep raw
        }
        throw new Error(`Failed to check similarity: ${response.status} ${JSON.stringify(details)}`);
      }

      const data = JSON.parse(rawText || '{}');
      console.log("[SM] Similarity parsed response", data);
      setResult(data);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setError("Failed to check similarity. See console for details.");
      console.error("[SM] Similarity request failed:", msg, err);
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Search className="h-5 w-5" />
            Semantic Similarity Matching
          </CardTitle>
          <CardDescription>
            Check how similar your claim is to verified sources in our database
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label htmlFor="claim">News Claim</Label>
            <Textarea
              id="claim"
              placeholder="Enter the news claim to check against verified sources..."
              value={claim}
              onChange={(e) => setClaim(e.target.value)}
              rows={4}
              className="w-full mt-1"
            />
          </div>
          <div>
            <Label htmlFor="topK">Number of Results</Label>
            <Input
              id="topK"
              type="number"
              min="1"
              max="10"
              value={topK}
              onChange={(e) => setTopK(parseInt(e.target.value) || 1)}
              className="w-full mt-1"
            />
          </div>
          <div>
            <Label htmlFor="mode">Search Mode</Label>
            <select
              id="mode"
              value={mode}
              onChange={(e) => setMode(e.target.value)}
              className="w-full mt-1 border rounded px-2 py-1"
            >
              <option value="auto">Auto</option>
              <option value="local">Local (FAISS)</option>
              <option value="online">Online (live)</option>
              <option value="both">Both</option>
            </select>
          </div>
        </CardContent>
        <CardFooter>
          <Button
            onClick={handleSimilarityCheck}
            disabled={!claim.trim() || isAnalyzing}
            className="w-full"
          >
            {isAnalyzing ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Checking Similarity...
              </>
            ) : (
              "Check Similarity"
            )}
          </Button>
        </CardFooter>
      </Card>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {result && (
        <Card>
          <CardHeader>
            <CardTitle>Similarity Results</CardTitle>
            <CardDescription>
              Top {((result as any).top_k ?? matches.length)} similar sources found{( (result as any).detected_language ? ` — Detected: ${(result as any).detected_language}` : '')}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {matches && matches.length > 0 ? (
              <div className="space-y-4">
                {matches.map((source: any, index: number) => {
                  const rawSim = Number(source.similarity ?? source.similarity_score ?? 0);
                  // Handle backend returning fraction (0..1) or percentage (0..100).
                  // Tolerate tiny floating-point >1 values (e.g. 1.000000119) as full 100%.
                  let similarity = 0;
                  if (!Number.isFinite(rawSim)) {
                    similarity = 0;
                  } else if (rawSim >= 0 && rawSim <= 1.001) {
                    // Treat values in [0,1.001] as fractions (handles tiny FP noise like 1.0000001)
                    similarity = rawSim * 100;
                  } else {
                    similarity = rawSim;
                  }
                  const title = source.title ?? source.headline ?? source.claim;
                  const isExpanded = !!expandedSamples[index];
                  const highlightClass = similarity >= 90 ? 'border-green-500 bg-green-50' : '';
                  return (
                    <div key={index} className={`border rounded-lg p-4 ${highlightClass}`}>
                      <div className="flex justify-between items-start mb-2">
                        <div className="flex items-center gap-2">
                          <h4 className="font-semibold text-sm">{source.source}</h4>
                          {similarity >= 90 && (
                            <span className="text-xs bg-yellow-100 text-yellow-800 px-2 py-1 rounded">Exact match</span>
                          )}
                        </div>
                        <span className="text-sm font-mono bg-gray-100 px-2 py-1 rounded">
                          {similarity.toFixed(2)}% similar
                        </span>
                      </div>

                      {source.verdict && <p className="text-sm mb-1"><strong>Verdict:</strong> {source.verdict}</p>}
                      {title && <p className="text-sm text-gray-600 mb-2">{title}</p>}

                      <div className="flex items-center gap-2 mb-2">
                        {source.full_text_used && (
                          <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded">Full text used</span>
                        )}
                        {source.is_online && (
                          <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">Online</span>
                        )}
                        {source.source && (
                          <span className="text-xs bg-gray-100 text-gray-800 px-2 py-1 rounded">{source.source}</span>
                        )}
                      </div>

                      {source.text_sample && (
                        <div className="mb-2">
                          <button
                            className="text-sm text-blue-600 hover:underline"
                            onClick={() => setExpandedSamples(prev => ({ ...prev, [index]: !prev[index] }))}
                          >
                            {isExpanded ? 'Hide text sample' : 'Show text sample'}
                          </button>
                          {isExpanded && (
                            <pre className="mt-2 whitespace-pre-wrap bg-gray-50 p-3 rounded text-sm">{source.text_sample}</pre>
                          )}
                        </div>
                      )}

                      {source.url && (
                        <a
                          href={source.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-600 hover:text-blue-800 text-sm flex items-center gap-1"
                        >
                          View Source <ExternalLink className="h-3 w-3" />
                        </a>
                      )}
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="p-4 text-sm text-gray-600">No matches found.</div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default SemanticSimilarityMatcher;