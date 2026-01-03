import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Upload, FileText, Image as ImageIcon, Loader2 } from "lucide-react";

interface PredictionResult {
  status?: string;
  message?: string;
  original_text: string;
  prediction: string;
  confidence: number;
  cleaned_text?: string;
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
      const response = await fetch("http://localhost:1000/predict", {
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

      const response = await fetch("http://localhost:1000/predict_image_upload", {
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
      const response = await fetch("http://localhost:1000/predict_image_url", {
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
          <TabsTrigger value="url" className="flex items-center gap-2">
            <ImageIcon className="h-4 w-4" />
            Image URL
          </TabsTrigger>
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
            <CardTitle className={`text-xl ${getResultColor(result.prediction)}`}>
              Prediction: {result.prediction.toUpperCase()}
            </CardTitle>
            <CardDescription>
              Confidence Score: {(result.confidence * 100).toFixed(2)}%
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <span>Result:</span>
                <span className={`font-bold ${getResultColor(result.prediction)}`}>
                  {result.prediction}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span>Confidence:</span>
                <span className="font-bold">
                  {(result.confidence * 100).toFixed(2)}%
                </span>
              </div>
              {result.original_text && (
                <div>
                  <span className="font-medium">Original Text:</span>
                  <p className="text-sm text-gray-600 mt-1">{result.original_text}</p>
                </div>
              )}
              {result.cleaned_text && result.cleaned_text !== result.original_text && (
                <div>
                  <span className="font-medium">Cleaned Text:</span>
                  <p className="text-sm text-gray-600 mt-1">{result.cleaned_text}</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default TamilFakeNewsDetector;