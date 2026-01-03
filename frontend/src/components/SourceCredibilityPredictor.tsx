import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Label } from "@/components/ui/label";
import { Shield, Loader2, Globe } from "lucide-react";

interface CredibilityResult {
  source: string;
  credibility_score: number;
  category?: string;
  description?: string;
}

const SourceCredibilityPredictor = () => {
  const [sourceUrl, setSourceUrl] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState<CredibilityResult | null>(null);
  const [error, setError] = useState("");

  const handleCredibilityCheck = async () => {
    if (!sourceUrl.trim()) return;

    setIsAnalyzing(true);
    setError("");

    try {
      // Assuming credibility predictor runs on port 8002 (need to check actual port)
      const response = await fetch("http://localhost:8002/predict", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ url: sourceUrl }),
      });

      if (!response.ok) {
        throw new Error("Failed to check credibility");
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError("Failed to check source credibility. Please ensure the credibility predictor service is running.");
      console.error(err);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const getCredibilityColor = (score: number) => {
    if (score >= 80) return "text-green-600";
    if (score >= 60) return "text-yellow-600";
    return "text-red-600";
  };

  const getCredibilityBg = (score: number) => {
    if (score >= 80) return "bg-green-50 border-green-200";
    if (score >= 60) return "bg-yellow-50 border-yellow-200";
    return "bg-red-50 border-red-200";
  };

  const getCredibilityLabel = (score: number) => {
    if (score >= 80) return "High Credibility";
    if (score >= 60) return "Medium Credibility";
    return "Low Credibility";
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Source Credibility Predictor
          </CardTitle>
          <CardDescription>
            Check the credibility score of a news source URL
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div>
            <Label htmlFor="sourceUrl">Source URL</Label>
            <Input
              id="sourceUrl"
              type="url"
              placeholder="https://example.com"
              value={sourceUrl}
              onChange={(e) => setSourceUrl(e.target.value)}
              className="w-full mt-1"
            />
          </div>
        </CardContent>
        <CardFooter>
          <Button
            onClick={handleCredibilityCheck}
            disabled={!sourceUrl.trim() || isAnalyzing}
            className="w-full"
          >
            {isAnalyzing ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Analyzing...
              </>
            ) : (
              "Check Credibility"
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
        <Card className={getCredibilityBg(result.credibility_score)}>
          <CardHeader>
            <CardTitle className={`text-xl ${getCredibilityColor(result.credibility_score)}`}>
              {getCredibilityLabel(result.credibility_score)}
            </CardTitle>
            <CardDescription>
              Credibility Score: {result.credibility_score}/100
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <Globe className="h-4 w-4" />
                <span className="font-medium">Source:</span>
                <a
                  href={result.source}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:text-blue-800 underline"
                >
                  {result.source}
                </a>
              </div>

              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <span>Credibility Score:</span>
                  <span className={`font-bold ${getCredibilityColor(result.credibility_score)}`}>
                    {result.credibility_score}/100
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full ${
                      result.credibility_score >= 80 ? 'bg-green-500' :
                      result.credibility_score >= 60 ? 'bg-yellow-500' : 'bg-red-500'
                    }`}
                    style={{ width: `${result.credibility_score}%` }}
                  ></div>
                </div>
              </div>

              {result.category && (
                <div className="flex justify-between items-center">
                  <span>Category:</span>
                  <span className="font-medium">{result.category}</span>
                </div>
              )}

              {result.description && (
                <div>
                  <span className="font-medium">Description:</span>
                  <p className="text-sm text-gray-600 mt-1">{result.description}</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default SourceCredibilityPredictor;