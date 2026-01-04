import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Shield, Loader2 } from "lucide-react";

interface CredibilityResult {
  credibility_score: number;
  prediction_label: string;
  confidence_breakdown: {
    High: number;
    Low: number;
    Medium: number;
  };
}

const SourceCredibilityPredictor = () => {
  const [formData, setFormData] = useState({
    past_fake: "",
    past_real: "",
    domain_age_years: "",
    followers: "",
    language: ""
  });
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState<CredibilityResult | null>(null);
  const [error, setError] = useState("");

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleCredibilityCheck = async () => {
    const { past_fake, past_real, domain_age_years, followers, language } = formData;
    if (!past_fake || !past_real || !domain_age_years || !followers || !language) {
      setError("Please fill in all fields.");
      return;
    }

    setIsAnalyzing(true);
    setError("");

    try {
      const response = await fetch("http://localhost:4000/predict", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          past_fake: parseInt(past_fake),
          past_real: parseInt(past_real),
          domain_age_years: parseFloat(domain_age_years),
          followers: parseInt(followers),
          language: language
        }),
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
            Enter source features to predict credibility score
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <Label htmlFor="past_fake">Past Fake News Count</Label>
              <Input
                id="past_fake"
                type="number"
                placeholder="0"
                value={formData.past_fake}
                onChange={(e) => handleInputChange("past_fake", e.target.value)}
                className="w-full mt-1"
              />
            </div>
            <div>
              <Label htmlFor="past_real">Past Real News Count</Label>
              <Input
                id="past_real"
                type="number"
                placeholder="0"
                value={formData.past_real}
                onChange={(e) => handleInputChange("past_real", e.target.value)}
                className="w-full mt-1"
              />
            </div>
            <div>
              <Label htmlFor="domain_age_years">Domain Age (Years)</Label>
              <Input
                id="domain_age_years"
                type="number"
                step="0.1"
                placeholder="0.0"
                value={formData.domain_age_years}
                onChange={(e) => handleInputChange("domain_age_years", e.target.value)}
                className="w-full mt-1"
              />
            </div>
            <div>
              <Label htmlFor="followers">Followers Count</Label>
              <Input
                id="followers"
                type="number"
                placeholder="0"
                value={formData.followers}
                onChange={(e) => handleInputChange("followers", e.target.value)}
                className="w-full mt-1"
              />
            </div>
            <div>
              <Label htmlFor="language">Language</Label>
              <Select value={formData.language} onValueChange={(value) => handleInputChange("language", value)}>
                <SelectTrigger className="w-full mt-1">
                  <SelectValue placeholder="Select a language" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Tamil">Tamil</SelectItem>
                  <SelectItem value="Sinhala">Sinhala</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
        <CardFooter>
          <Button
            onClick={handleCredibilityCheck}
            disabled={isAnalyzing}
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

              <div className="flex justify-between items-center">
                <span>Prediction Label:</span>
                <span className="font-medium">{result.prediction_label}</span>
              </div>

              <div>
                <span className="font-medium">Confidence Breakdown:</span>
                <div className="mt-2 space-y-1">
                  <div className="flex justify-between">
                    <span>High:</span>
                    <span>{result.confidence_breakdown.High}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Medium:</span>
                    <span>{result.confidence_breakdown.Medium}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Low:</span>
                    <span>{result.confidence_breakdown.Low}%</span>
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default SourceCredibilityPredictor;