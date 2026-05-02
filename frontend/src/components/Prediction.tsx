"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/components/ui/use-toast";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

// Define the structure of the prediction results
interface ClassifierResult {
  prediction: string;
  confidence: number;
}

interface SimilarityMatch {
  claim: string;
  similarity: number;
  source: string;
  url: string;
  verdict: string;
}

interface SimilarityResult {
  final_verdict: string;
  confidence: number;
  neighbors: SimilarityMatch[];
}

interface CredibilityResult {
  prediction_label: string;
  credibility_score: number;
  sensitivity_metrics?: {
    linguistic_impact: string;
    real_news_ratio: string;
    domain_authority: string;
    social_reach: string;
  };
}

interface PredictionResponse {
  language: string;
  classifier: ClassifierResult | null;
  similarity: SimilarityResult | null;
  credibility: CredibilityResult | null;
  final_prediction: string;
  final_confidence: number;
}

const Prediction = () => {
  const [text, setText] = useState("");
  const [pastFake, setPastFake] = useState("0");
  const [pastReal, setPastReal] = useState("0");
  const [domainAge, setDomainAge] = useState("0");
  const [followers, setFollowers] = useState("0");
  const [mode, setMode] = useState("auto");
  const [topK, setTopK] = useState(3);
  const [result, setResult] = useState<PredictionResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  // Guard `useToast` in case the hook isn't available during rendering
  const toastApi = useToast() as any;
  const toast = toastApi?.toast ?? ((opts: any) => console.log("toast:", opts));

  const handleSubmit = async () => {
    if (!text.trim()) {
      toast({
        title: "Error",
        description: "Please enter some text to analyze.",
        variant: "destructive",
      });
      return;
    }

    setIsLoading(true);
    setResult(null);

    try {
      const payload = {
        text,
        past_fake: parseInt(pastFake || "0"),
        past_real: parseInt(pastReal || "0"),
        domain_age_years: parseFloat(domainAge || "0"),
        followers: parseInt(followers || "0"),
        mode: mode,
        top_k: topK,
      };

      const response = await fetch("http://127.0.0.1:5000/predict", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error("Network response was not ok");
      }

      const data: PredictionResponse = await response.json();
      
      if (data.final_prediction === "Ignored") {
        toast({
          title: "Language Not Supported",
          description: "This tool only supports analysis for Tamil and Sinhala news content.",
          variant: "destructive",
        });
        setResult(null);
        return;
      }
      
      setResult(data);
    } catch (error) {
      console.error("Failed to fetch prediction:", error);
      toast({
        title: "Error",
        description: "Failed to get a prediction. Please try again later.",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Card className="w-full max-w-4xl mx-auto">
      <CardHeader>
        <CardTitle>Analyze News Article</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid w-full gap-4">
          <Textarea
            placeholder="Enter Sinhala or Tamil news text here..."
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={6}
          />

          <div className="grid grid-cols-4 gap-2">
            <div>
              <label className="text-sm">Past Fake</label>
              <input
                className="w-full border rounded px-2 py-1"
                type="number"
                min={0}
                value={pastFake}
                onChange={(e) => setPastFake(e.target.value)}
              />
            </div>
            <div>
              <label className="text-sm">Past Real</label>
              <input
                className="w-full border rounded px-2 py-1"
                type="number"
                min={0}
                value={pastReal}
                onChange={(e) => setPastReal(e.target.value)}
              />
            </div>
            <div>
              <label className="text-sm">Domain Age (years)</label>
              <input
                className="w-full border rounded px-2 py-1"
                type="number"
                min={0}
                step="0.1"
                value={domainAge}
                onChange={(e) => setDomainAge(e.target.value)}
              />
            </div>
            <div>
              <label className="text-sm">Followers</label>
              <input
                className="w-full border rounded px-2 py-1"
                type="number"
                min={0}
                value={followers}
                onChange={(e) => setFollowers(e.target.value)}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm">Search Mode</label>
              <select
                className="w-full border rounded px-2 py-1"
                value={mode}
                onChange={(e) => setMode(e.target.value)}
              >
                <option value="auto">Auto (Smart)</option>
                <option value="local">Local Only</option>
                <option value="online">Online Search Only</option>
                <option value="both">Both (Local + Online)</option>
              </select>
            </div>
            <div>
              <label className="text-sm">Top results</label>
              <input
                className="w-full border rounded px-2 py-1"
                type="number"
                min={1}
                max={10}
                value={topK}
                onChange={(e) => setTopK(parseInt(e.target.value) || 1)}
              />
            </div>
          </div>

          <Button onClick={handleSubmit} disabled={isLoading}>
            {isLoading ? "Analyzing..." : "Analyze"}
          </Button>
        </div>

        {isLoading && (
          <div className="mt-6 space-y-4">
            <Skeleton className="h-8 w-1/4" />
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-8 w-1/4 mt-4" />
            <Skeleton className="h-24 w-full" />
          </div>
        )}

        {result && (
          <div className="mt-6 space-y-6">
            <div>
              <h3 className="text-lg font-semibold">Analysis Results</h3>
              <div>
                Detected Language: <Badge>{result.language}</Badge>
              </div>
            </div>

            {result.classifier && (
              <Card>
                <CardHeader>
                  <CardTitle>Fake News Prediction</CardTitle>
                </CardHeader>
                <CardContent>
                  <div>
                    Prediction:{" "}
                    <Badge
                      variant={
                        result.classifier.prediction.toLowerCase() === "real"
                          ? "default"
                          : "destructive"
                      }
                    >
                      {result.classifier.prediction}
                    </Badge>
                  </div>
                  <div className="text-sm text-muted-foreground">
                    Confidence:{" "}
                    {(result.classifier.confidence * 100).toFixed(2)}%
                  </div>
                </CardContent>
              </Card>
            )}

            {result.similarity && (
              <Card>
                <CardHeader>
                  <CardTitle>Similarity Evidence</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center gap-2">
                    Verdict:{" "}
                    <Badge variant={result.similarity.final_verdict?.toLowerCase().includes('true') || result.similarity.final_verdict?.toLowerCase().includes('real') ? 'secondary' : 'destructive'}>
                      {result.similarity.final_verdict || "No match found"}
                    </Badge>
                  </div>
                  {result.similarity.neighbors && result.similarity.neighbors.length > 0 ? (
                    <ul className="space-y-4">
                      {result.similarity.neighbors.map((match, index) => (
                        <li key={index} className="border-b pb-2 last:border-0">
                          <p className="text-sm">
                            <strong>Source:</strong> {match.source}
                          </p>
                          <p className="text-sm">
                            <strong>Claim:</strong>{" "}
                            {match.url ? (
                              <a
                                href={match.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-blue-500 hover:underline"
                              >
                                {match.claim}
                              </a>
                            ) : (
                              match.claim
                            )}
                          </p>
                          <p className="text-sm italic">
                            Verdict: {match.verdict} ({(match.similarity * 100).toFixed(1)}% similarity)
                          </p>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-sm text-muted-foreground italic">
                      No matching records found in selected search mode.
                    </p>
                  )}
                </CardContent>
              </Card>
            )}

            {result.credibility && (
              <Card>
                <CardHeader>
                  <CardTitle>Source Credibility Details</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <span className="font-medium">Status:</span>
                      <Badge
                        variant={
                          result.credibility.prediction_label.toLowerCase() === "high"
                            ? "default"
                            : "destructive"
                        }
                      >
                        {result.credibility.prediction_label}
                      </Badge>
                    </div>
                    
                    <div className="flex items-center justify-between">
                      <span className="font-medium">Overall Trust Score:</span>
                      <span className="text-lg font-bold">
                        {result.credibility.credibility_score.toFixed(4)}%
                      </span>
                    </div>

                    {result.credibility.sensitivity_metrics && (
                      <div className="pt-2 border-t grid grid-cols-2 gap-2 text-xs text-muted-foreground">
                        <div>
                          <strong>Language Impact:</strong> {result.credibility.sensitivity_metrics.linguistic_impact}
                        </div>
                        <div>
                          <strong>News Ratio:</strong> {result.credibility.sensitivity_metrics.real_news_ratio}
                        </div>
                        <div>
                          <strong>Authority (Age):</strong> {result.credibility.sensitivity_metrics.domain_authority}
                        </div>
                        <div>
                          <strong>Social Reach:</strong> {result.credibility.sensitivity_metrics.social_reach}
                        </div>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            )}

            <Card>
              <CardHeader>
                <CardTitle>Final Prediction</CardTitle>
              </CardHeader>
              <CardContent>
                <div>
                  Overall Prediction:{" "}
                  <Badge
                    variant={
                      result.final_prediction.toLowerCase() === "real"
                        ? "default"
                        : "destructive"
                    }
                  >
                    {result.final_prediction}
                  </Badge>
                </div>
                <p>
                  Confidence:{" "}
                  {(result.final_confidence * 100).toFixed(2)}%
                </p>
              </CardContent>
            </Card>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default Prediction;