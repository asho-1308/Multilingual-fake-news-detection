import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { FileText, Loader2 } from "lucide-react";

interface PredictionResult {
  label: string;
  confidence: number;
}

const SinhalaFakeNewsDetector = () => {
  const [textInput, setTextInput] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState<PredictionResult | null>(null);
  const [error, setError] = useState("");

  const handlePrediction = async () => {
    if (!textInput.trim()) return;

    setIsAnalyzing(true);
    setError("");

    try {
      const response = await fetch("http://127.0.0.1:2000/predict", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ text: textInput }),
      });

      if (!response.ok) {
        throw new Error("Failed to get prediction");
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError("Failed to analyze text. Please ensure the Sinhala classifier service is running.");
      console.error(err);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const getResultColor = (label: string) => {
    return label.toLowerCase() === "fake" ? "text-red-600" : "text-green-600";
  };

  const getResultBg = (label: string) => {
    return label.toLowerCase() === "fake" ? "bg-red-50 border-red-200" : "bg-green-50 border-green-200";
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Sinhala Fake News Detection
          </CardTitle>
          <CardDescription>
            Enter Sinhala text to check if it's fake news
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Textarea
            placeholder="Enter Sinhala news text here..."
            value={textInput}
            onChange={(e) => setTextInput(e.target.value)}
            rows={6}
            className="w-full"
          />
        </CardContent>
        <CardFooter>
          <Button
            onClick={handlePrediction}
            disabled={!textInput.trim() || isAnalyzing}
            className="w-full"
          >
            {isAnalyzing ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Analyzing...
              </>
            ) : (
              "Analyze Text"
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
        <Card className={getResultBg(result.label)}>
          <CardHeader>
            <CardTitle className={`text-xl ${getResultColor(result.label)}`}>
              Prediction: {result.label.toUpperCase()}
            </CardTitle>
            <CardDescription>
              Confidence Score: {(result.confidence * 100).toFixed(2)}%
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <span>Result:</span>
                <span className={`font-bold ${getResultColor(result.label)}`}>
                  {result.label}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span>Confidence:</span>
                <span className="font-bold">
                  {(result.confidence * 100).toFixed(2)}%
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default SinhalaFakeNewsDetector;