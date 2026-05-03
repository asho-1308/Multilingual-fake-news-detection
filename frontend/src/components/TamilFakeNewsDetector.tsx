import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Upload, FileText, Image as ImageIcon, Loader2 } from "lucide-react";
import { SERVICE_ENDPOINTS } from "@/lib/serviceUrls";

interface PredictionResult {
  status?: string;
  message?: string;
  original_text: string;
  prediction: string;
  confidence: number;
  confidence_level?: string;
  recommendation?: string;
  linguistic_analysis?: {
    intensity: string;
    markers_found: string[];
    sensationalism_score: number;
  };
  cleaned_text?: string;
  explanation?: {
    summary: string;
    trigger_words: Array<{ word: string; contribution: number }>;
  };
  metadata?: {
    language_detected: string;
    processing_time_ms: number;
    model_version: string;
    timestamp?: string;
  };
}

const TamilFakeNewsDetector = () => {
  const [textInput, setTextInput] = useState("");
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imageUrl, setImageUrl] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState<PredictionResult | null>(null);
  const [error, setError] = useState("");

  const handleTextPrediction = async () => {
    if (!textInput.trim()) return;

    setIsAnalyzing(true);
    setError("");

    try {
      const response = await fetch(SERVICE_ENDPOINTS.tamilPredict, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ text: textInput }),
      });

      const data = await response.json();
      
      if (!response.ok) {
        if (data.detail) {
          setError(data.detail);
        } else {
          setError(`Server error: ${response.status}`);
        }
        return;
      }
      
      if (data.status === "error") {
        setError(data.message || "Failed to analyze text");
        return;
      }
      
      setResult(data);
    } catch (err) {
      setError("Failed to analyze text. Please try again.");
      console.error(err);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleImageUpload = async () => {
    if (!imageFile) return;

    setIsAnalyzing(true);
    setError("");

    try {
      const formData = new FormData();
      formData.append("file", imageFile);

      const response = await fetch(SERVICE_ENDPOINTS.tamilImageUpload, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();
      
      if (!response.ok) {
        // Handle HTTP errors
        if (data.detail) {
          setError(data.detail);
        } else {
          setError(`Server error: ${response.status}`);
        }
        return;
      }
      
      if (data.status === "error") {
        setError(data.message || "Failed to analyze image");
        return;
      }
      
      setResult(data);
    } catch (err) {
      setError("Failed to analyze image. Please try again.");
      console.error(err);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleImageUrl = async () => {
    if (!imageUrl.trim()) return;

    setIsAnalyzing(true);
    setError("");

    try {
      const response = await fetch(SERVICE_ENDPOINTS.tamilImageUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ url: imageUrl }),
      });

      const data = await response.json();
      
      if (!response.ok) {
        if (data.detail) {
          setError(data.detail);
        } else {
          setError(`Server error: ${response.status}`);
        }
        return;
      }
      
      if (data.status === "error") {
        setError(data.message || "Failed to analyze image URL");
        return;
      }
      
      setResult(data);
    } catch (err) {
      setError("Failed to analyze image URL. Please try again.");
      console.error(err);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const getResultColor = (prediction: string) => {
    return prediction.toLowerCase() === "fake" ? "text-red-600" : "text-green-600";
  };

  const getResultBg = (prediction: string) => {
    return prediction.toLowerCase() === "fake" ? "bg-red-50 border-red-200" : "bg-green-50 border-green-200";
  };

  const getConfidenceColor = (level?: string) => {
    switch (level?.toLowerCase()) {
      case 'high': return 'text-green-600';
      case 'medium': return 'text-yellow-600';
      case 'low': return 'text-orange-600';
      default: return 'text-gray-600';
    }
  };

  const getLinguisticBadge = (intensity?: string) => {
    switch (intensity?.toLowerCase()) {
      case 'high': return 'bg-red-100 text-red-700 border-red-200';
      case 'medium': return 'bg-orange-100 text-orange-700 border-orange-200';
      case 'low': return 'bg-blue-100 text-blue-700 border-blue-200';
      default: return 'bg-gray-100 text-gray-700 border-gray-200';
    }
  };

  return (
    <div className="space-y-6">
      <Tabs defaultValue="text" className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="text" className="flex items-center gap-2">
            <FileText className="h-4 w-4" />
            Text Input
          </TabsTrigger>
          <TabsTrigger value="upload" className="flex items-center gap-2">
            <Upload className="h-4 w-4" />
            Image Upload
          </TabsTrigger>
          {/* <TabsTrigger value="url" className="flex items-center gap-2">
            <ImageIcon className="h-4 w-4" />
            Image URL
          </TabsTrigger> */}
        </TabsList>

        <TabsContent value="text" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Enter Tamil Text</CardTitle>
              <CardDescription>
                Paste or type Tamil text to check if it's fake news
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Textarea
                placeholder="Enter Tamil news text here..."
                value={textInput}
                onChange={(e) => setTextInput(e.target.value)}
                rows={6}
                className="w-full"
              />
            </CardContent>
            <CardFooter>
              <Button
                onClick={handleTextPrediction}
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
        </TabsContent>

        <TabsContent value="upload" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Upload Image</CardTitle>
              <CardDescription>
                Upload an image containing Tamil text to analyze
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <Input
                  type="file"
                  accept="image/*"
                  onChange={(e) => setImageFile(e.target.files?.[0] || null)}
                  className="w-full"
                />
                {imageFile && (
                  <div className="text-sm text-gray-600">
                    Selected: {imageFile.name}
                  </div>
                )}
              </div>
            </CardContent>
            <CardFooter>
              <Button
                onClick={handleImageUpload}
                disabled={!imageFile || isAnalyzing}
                className="w-full"
              >
                {isAnalyzing ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Analyzing...
                  </>
                ) : (
                  "Analyze Image"
                )}
              </Button>
            </CardFooter>
          </Card>
        </TabsContent>

        <TabsContent value="url" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Image URL</CardTitle>
              <CardDescription>
                Enter the URL of an image containing Tamil text
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Input
                type="url"
                placeholder="https://example.com/image.jpg"
                value={imageUrl}
                onChange={(e) => setImageUrl(e.target.value)}
                className="w-full"
              />
            </CardContent>
            <CardFooter>
              <Button
                onClick={handleImageUrl}
                disabled={!imageUrl.trim() || isAnalyzing}
                className="w-full"
              >
                {isAnalyzing ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Analyzing...
                  </>
                ) : (
                  "Analyze URL"
                )}
              </Button>
            </CardFooter>
          </Card>
        </TabsContent>
      </Tabs>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {result && (
        <Card className={getResultBg(result.prediction)}>
          <CardHeader>
            <div className="flex justify-between items-start">
              <div>
                <CardTitle className={`text-2xl font-bold ${getResultColor(result.prediction)}`}>
                  {result.prediction.toUpperCase()}
                </CardTitle>
                <CardDescription>
                  Confidence: <span className={`font-semibold ${getConfidenceColor(result.confidence_level)}`}>{result.confidence_level}</span> ({(result.confidence * 100).toFixed(2)}%)
                </CardDescription>
              </div>
              <div className="text-right text-xs text-gray-400">
                v{result.metadata?.model_version} | {result.metadata?.processing_time_ms}ms
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Warning Message or Recommendation */}
            <Alert className={`${result.prediction.toLowerCase() === "fake" ? "bg-red-100 border-red-300 text-red-800" : "bg-blue-50 border-blue-200 text-blue-800"}`}>
              <AlertDescription className="font-medium">
                {result.prediction.toLowerCase() === "fake" ? "⚠️ " : "ℹ️ "}
                {result.recommendation || (result.prediction.toLowerCase() === "fake" 
                  ? "This content has been flagged as potentially misleading. Please verify with trusted news sources."
                  : "This content appears consistent with real news patterns.")}
              </AlertDescription>
            </Alert>

            {/* Linguistic Tone & Sensationalism */}
            {result.linguistic_analysis && (
              <div className="space-y-3 p-4 bg-white/40 rounded-lg border shadow-sm">
                <div className="flex justify-between items-center">
                  <h4 className="text-sm font-bold text-gray-700">Sensationalism Analysis:</h4>
                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase border ${getLinguisticBadge(result.linguistic_analysis.intensity)}`}>
                    Tone Intensity: {result.linguistic_analysis.intensity}
                  </span>
                </div>
                {result.linguistic_analysis.markers_found.length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {result.linguistic_analysis.markers_found.map((marker, i) => (
                      <span key={i} className="text-xs bg-white text-gray-600 px-2 py-1 rounded border border-gray-100 flex items-center gap-1 font-tamil">
                        🔍 {marker}
                      </span>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-gray-500 italic">No exaggerated linguistic markers detected.</p>
                )}
              </div>
            )}

            {/* Trigger Words / Key Phrases */}
            {result.explanation && result.explanation.trigger_words.length > 0 && (
              <div className="space-y-3">
                <h4 className="text-sm font-semibold text-gray-700">Keyword/Phrase Highlights:</h4>
                <div className="flex flex-wrap gap-2">
                  {result.explanation.trigger_words.map((tw, idx) => (
                    <div 
                      key={idx} 
                      className="px-3 py-1 bg-white border rounded-full text-sm flex items-center gap-2 shadow-sm"
                      title={`Contribution: ${tw.contribution}`}
                    >
                      <span className="font-tamil">{tw.word}</span>
                      <span className="text-[10px] bg-red-50 text-red-600 px-1 rounded font-mono">
                        +{Math.round(tw.contribution * 100)}%
                      </span>
                    </div>
                  ))}
                </div>
                <p className="text-xs text-gray-500 italic">
                  {result.explanation.summary}
                </p>
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {result.original_text && (
                <div className="space-y-1">
                  <span className="text-xs font-bold text-gray-500 uppercase">Input Text:</span>
                  <div className="p-3 bg-white/50 rounded border text-sm max-h-32 overflow-y-auto font-tamil">
                    {result.original_text}
                  </div>
                </div>
              )}
              {result.cleaned_text && result.cleaned_text !== result.original_text && (
                <div className="space-y-1">
                  <span className="text-xs font-bold text-gray-500 uppercase">Analyzed (Tamil Only):</span>
                  <div className="p-3 bg-white/50 rounded border text-sm max-h-32 overflow-y-auto font-tamil text-blue-800">
                    {result.cleaned_text}
                  </div>
                </div>
              )}
            </div>
          </CardContent>
          <CardFooter className="text-xs text-gray-400 border-t pt-4 flex justify-between">
            <span>Detected Language: Tamil ({result.metadata?.language_detected})</span>
            {result.metadata?.timestamp && <span>Analyzed on: {result.metadata.timestamp}</span>}
          </CardFooter>
        </Card>
      )}
    </div>
  );
};

export default TamilFakeNewsDetector;