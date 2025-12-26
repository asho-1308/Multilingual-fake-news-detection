"use client";

import { useState } from "react";
import { 
  checkSingleNews, 
  checkBulkNews, 
  checkImageUpload, 
  checkImageURL, 
  PredictionResult, 
  ApiError 
} from "@/lib/api";
import { 
  AlertCircle, 
  CheckCircle2, 
  FileText, 
  Image as ImageIcon, 
  Link as LinkIcon, 
  Upload, 
  Zap, 
  ShieldCheck, 
  ShieldAlert 
} from "lucide-react";

export default function Home() {
  const [activeTab, setActiveTab] = useState<'text' | 'image'>('text');
  const [imageMode, setImageMode] = useState<'upload' | 'url'>('upload');
  
  // State
  const [text, setText] = useState("");
  const [results, setResults] = useState<PredictionResult[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  
  // Image State
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imageUrl, setImageUrl] = useState("");

  const handleTextCheck = async () => {
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
      handleResponse(response);
    } catch (err) {
      setError("Failed to connect to the server.");
    } finally {
      setLoading(false);
    }
  };

  const handleImageCheck = async () => {
    if (imageMode === 'upload' && !imageFile) {
      setError("Please select an image file.");
      return;
    }
    if (imageMode === 'url' && !imageUrl.trim()) {
      setError("Please enter a valid URL.");
      return;
    }

    setLoading(true);
    setError("");
    setResults(null);

    try {
      let resp;
      if (imageMode === 'upload' && imageFile) {
        resp = await checkImageUpload(imageFile);
      } else {
        resp = await checkImageURL(imageUrl.trim());
      }
      handleResponse(resp);
    } catch (e) {
      setError("Failed to analyze image.");
    } finally {
      setLoading(false);
    }
  };

  const handleResponse = (response: any) => {
    if ('status' in response && response.status === 'error') {
      setError(response.message);
    } else if (Array.isArray(response)) {
      setResults(response);
    } else {
      setResults([response as PredictionResult]);
    }
  };

  const renderResult = (result: PredictionResult, index: number) => {
    const isReal = result.prediction === "Real";
    const confidencePercent = Math.round(result.confidence * 100);

    return (
      <div 
        key={index} 
        className="group relative overflow-hidden rounded-2xl border border-white/10 bg-white/5 backdrop-blur-sm p-6 transition-all hover:border-white/20 hover:bg-white/10"
      >
        {/* Decorative Glow */}
        <div className={`absolute -right-10 -top-10 h-32 w-32 rounded-full blur-3xl opacity-20 ${isReal ? "bg-emerald-500" : "bg-rose-500"}`} />

        <div className="relative z-10">
          <div className="flex items-start justify-between gap-4 mb-4">
            <p className="text-lg font-medium text-slate-200 leading-relaxed font-serif">
              "{result.original_text}"
            </p>
            <div className={`flex flex-col items-center justify-center rounded-xl p-3 min-w-[90px] ${
              isReal ? "bg-emerald-500/10 text-emerald-400" : "bg-rose-500/10 text-rose-400"
            }`}>
              {isReal ? <ShieldCheck size={24} /> : <ShieldAlert size={24} />}
              <span className="mt-1 text-xs font-bold uppercase tracking-wider">{result.prediction}</span>
            </div>
          </div>

          <div className="space-y-3">
            <div className="flex justify-between text-sm text-slate-400">
              <span>Confidence Score</span>
              <span className="text-white font-mono">{confidencePercent}%</span>
            </div>
            
            {/* Custom Progress Bar */}
            <div className="h-3 w-full rounded-full bg-slate-800 overflow-hidden relative">
              <div 
                className={`absolute h-full rounded-full transition-all duration-1000 ease-out ${
                  isReal ? "bg-gradient-to-r from-emerald-600 to-emerald-400" : "bg-gradient-to-r from-rose-600 to-rose-400"
                }`}
                style={{ width: `${confidencePercent}%` }}
              />
            </div>

            <div className="flex justify-between text-xs text-slate-500 pt-2 font-mono">
              <div className={isReal ? "text-emerald-500/70" : ""}>REAL PROB: {isReal ? confidencePercent : 100 - confidencePercent}%</div>
              <div className={!isReal ? "text-rose-500/70" : ""}>FAKE PROB: {!isReal ? confidencePercent : 100 - confidencePercent}%</div>
            </div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 selection:bg-indigo-500/30">
      {/* Background Ambient Effects */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-[20%] -left-[10%] w-[50%] h-[50%] rounded-full bg-indigo-500/10 blur-[100px]" />
        <div className="absolute top-[20%] -right-[10%] w-[40%] h-[40%] rounded-full bg-purple-500/10 blur-[100px]" />
      </div>

      <div className="relative max-w-3xl mx-auto px-6 py-20">
        {/* Header */}
        <div className="text-center mb-12 space-y-4">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-sm font-medium mb-4">
            <Zap size={16} /> AI-Powered Verification
          </div>
          <h1 className="text-5xl font-bold tracking-tight text-transparent bg-clip-text bg-gradient-to-b from-white to-slate-400">
            Truth Detector
          </h1>
          <p className="text-slate-400 text-lg max-w-lg mx-auto">
            Instantly verify Tamil news headlines using advanced machine learning models.
          </p>
        </div>

        {/* Main Card */}
        <div className="bg-slate-900/50 backdrop-blur-md border border-white/10 rounded-3xl overflow-hidden shadow-2xl">
          
          {/* Tabs */}
          <div className="flex border-b border-white/5">
            <button
              onClick={() => { setActiveTab('text'); setError(""); setResults(null); }}
              className={`flex-1 flex items-center justify-center gap-2 py-4 text-sm font-medium transition-colors ${
                activeTab === 'text' 
                  ? "bg-indigo-500/10 text-indigo-400 border-b-2 border-indigo-500" 
                  : "text-slate-400 hover:text-slate-200 hover:bg-white/5"
              }`}
            >
              <FileText size={18} /> Text Analysis
            </button>
            <button
              onClick={() => { setActiveTab('image'); setError(""); setResults(null); }}
              className={`flex-1 flex items-center justify-center gap-2 py-4 text-sm font-medium transition-colors ${
                activeTab === 'image' 
                  ? "bg-purple-500/10 text-purple-400 border-b-2 border-purple-500" 
                  : "text-slate-400 hover:text-slate-200 hover:bg-white/5"
              }`}
            >
              <ImageIcon size={18} /> Image Analysis
            </button>
          </div>

          <div className="p-8">
            {/* Text Input Section */}
            {activeTab === 'text' && (
              <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
                <div className="relative">
                  <textarea
                    rows={4}
                    className="w-full bg-slate-950/50 border border-slate-700 rounded-xl p-4 text-slate-200 placeholder:text-slate-600 focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-all resize-none outline-none"
                    placeholder="Paste Tamil news headlines here (one per line)..."
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                  />
                  <div className="absolute right-3 bottom-3 text-xs text-slate-600">
                    {text.split('\n').length} Lines
                  </div>
                </div>
                
                <button
                  onClick={handleTextCheck}
                  disabled={loading || !text.trim()}
                  className="w-full py-4 rounded-xl font-semibold bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white shadow-lg shadow-indigo-500/20 transition-all active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {loading ? (
                    <>
                      <div className="h-5 w-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      Analyzing...
                    </>
                  ) : (
                    <>Run Analysis <CheckCircle2 size={18} /></>
                  )}
                </button>
              </div>
            )}

            {/* Image Input Section */}
            {activeTab === 'image' && (
              <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
                <div className="flex gap-2 p-1 bg-slate-950/50 rounded-lg w-fit mx-auto border border-slate-800">
                  <button
                    onClick={() => setImageMode('upload')}
                    className={`px-4 py-1.5 rounded-md text-xs font-medium transition-all ${
                      imageMode === 'upload' ? 'bg-slate-800 text-white shadow-sm' : 'text-slate-500 hover:text-slate-300'
                    }`}
                  >
                    Upload File
                  </button>
                  <button
                    onClick={() => setImageMode('url')}
                    className={`px-4 py-1.5 rounded-md text-xs font-medium transition-all ${
                      imageMode === 'url' ? 'bg-slate-800 text-white shadow-sm' : 'text-slate-500 hover:text-slate-300'
                    }`}
                  >
                    Paste URL
                  </button>
                </div>

                <div className="min-h-[150px] flex flex-col justify-center">
                  {imageMode === 'upload' ? (
                    <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-slate-700 rounded-xl cursor-pointer hover:border-purple-500 hover:bg-purple-500/5 transition-all group">
                      <div className="flex flex-col items-center justify-center pt-5 pb-6">
                        <Upload className="w-8 h-8 mb-3 text-slate-500 group-hover:text-purple-400" />
                        <p className="text-sm text-slate-400">
                          {imageFile ? <span className="text-purple-400 font-medium">{imageFile.name}</span> : "Click to upload image"}
                        </p>
                      </div>
                      <input 
                        type="file" 
                        className="hidden" 
                        accept="image/*"
                        onChange={(e) => setImageFile(e.target.files?.[0] || null)}
                      />
                    </label>
                  ) : (
                    <div className="relative">
                      <LinkIcon className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
                      <input
                        type="text"
                        className="w-full bg-slate-950/50 border border-slate-700 rounded-xl py-4 pl-12 pr-4 text-slate-200 placeholder:text-slate-600 focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500 transition-all outline-none"
                        placeholder="https://example.com/news-image.jpg"
                        value={imageUrl}
                        onChange={(e) => setImageUrl(e.target.value)}
                      />
                    </div>
                  )}
                </div>

                <button
                  onClick={handleImageCheck}
                  disabled={loading || (imageMode === 'upload' && !imageFile) || (imageMode === 'url' && !imageUrl)}
                  className="w-full py-4 rounded-xl font-semibold bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white shadow-lg shadow-purple-500/20 transition-all active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {loading ? "Scanning..." : "Analyze Image"}
                </button>
              </div>
            )}

            {/* Error Message */}
            {error && (
              <div className="mt-6 p-4 bg-rose-500/10 border border-rose-500/20 rounded-xl flex items-center gap-3 text-rose-300 animate-in fade-in slide-in-from-top-2">
                <AlertCircle size={20} />
                <p className="text-sm font-medium">{error}</p>
              </div>
            )}
          </div>
        </div>

        {/* Results Section */}
        {results && (
          <div className="mt-12 space-y-6">
            <h2 className="text-xl font-semibold text-slate-300 flex items-center gap-2">
              Analysis Results <span className="text-slate-600 text-sm font-normal">({results.length} found)</span>
            </h2>
            <div className="space-y-4 animate-in fade-in slide-in-from-bottom-4 duration-700">
              {results.map((result, idx) => renderResult(result, idx))}
            </div>
          </div>
        )}
      </div>
    </main>
  );
}