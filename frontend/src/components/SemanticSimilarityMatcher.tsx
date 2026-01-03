import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Search, Loader2, ExternalLink } from "lucide-react";

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
  const [topK, setTopK] = useState(3);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState<SimilarityResult | null>(null);
  const [error, setError] = useState("");

  const handleSimilarityCheck = async () => {
    if (!claim.trim()) return;

    setIsAnalyzing(true);
    setError("");

    try {
      // Assuming similarity matcher runs on port 5001
      const response = await fetch("http://localhost:5001/api/verify", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          claim: claim,
          top_k: topK
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to check similarity");
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError("Failed to check similarity. Please ensure the similarity matcher service is running.");
      console.error(err);
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
              onChange={(e) => setTopK(parseInt(e.target.value) || 3)}
              className="w-full mt-1"
            />
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
              Top {result.top_k} similar sources found
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {result.similar_sources.map((source, index) => (
                <div key={index} className="border rounded-lg p-4">
                  <div className="flex justify-between items-start mb-2">
                    <h4 className="font-semibold text-sm">{source.source}</h4>
                    <span className="text-sm font-mono bg-gray-100 px-2 py-1 rounded">
                      {(source.similarity_score * 100).toFixed(2)}% similar
                    </span>
                  </div>
                  {source.title && (
                    <p className="text-sm text-gray-600 mb-2">{source.title}</p>
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
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default SemanticSimilarityMatcher;