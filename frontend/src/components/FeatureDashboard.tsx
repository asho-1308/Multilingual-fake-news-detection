
import { useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import TamilFakeNewsDetector from "./TamilFakeNewsDetector";
import SinhalaFakeNewsDetector from "./SinhalaFakeNewsDetector";
import SemanticSimilarityMatcher from "./SemanticSimilarityMatcher";
import SourceCredibilityPredictor from "./SourceCredibilityPredictor";
import { 
  FileText, 
  Image, 
  Users, 
  BookOpen, 
  AlertTriangle, 
  Globe, 
  Bookmark,
  BarChart3,
  Languages,
  CheckCircle,
  Search,
  Shield
} from "lucide-react";

const FeatureDashboard = () => {
  const [activeTab, setActiveTab] = useState("tamil-detection");

  const features = [
    {
      id: "tamil-detection",
      label: "Tamil Fake News",
      icon: Languages,
      component: <TamilFakeNewsDetector />,
      description: "Detect fake news in Tamil language (text or image input)"
    },
    {
      id: "sinhala-detection", 
      label: "Sinhala Fake News",
      icon: Languages,
      component: <SinhalaFakeNewsDetector />,
      description: "Detect fake news in Sinhala language (text input)"
    },
    {
      id: "similarity-matching",
      label: "Similarity Matching",
      icon: Search,
      component: <SemanticSimilarityMatcher />,
      description: "Check semantic similarity with verified sources"
    },
    {
      id: "credibility-predictor",
      label: "Source Credibility",
      icon: Shield,
      component: <SourceCredibilityPredictor />,
      description: "Predict credibility of news sources"
    }
  ];

  return (
    <div className="w-full max-w-7xl mx-auto">
      <div className="mb-6">
        <h2 className="text-3xl font-bold mb-2">Multilingual Fake News Detection</h2>
        <p className="text-gray-600">AI-powered fake news detection for Tamil, Sinhala, and multilingual content</p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid grid-cols-2 lg:grid-cols-4 mb-6">
          {features.map((feature) => (
            <TabsTrigger 
              key={feature.id} 
              value={feature.id}
              className="flex flex-col items-center gap-1 p-3 h-auto text-xs"
            >
              <feature.icon className="h-4 w-4" />
              <span className="hidden sm:inline">{feature.label}</span>
            </TabsTrigger>
          ))}
        </TabsList>

        {features.map((feature) => (
          <TabsContent key={feature.id} value={feature.id} className="mt-6">
            <Card className="mb-4">
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2">
                  <feature.icon className="h-5 w-5" />
                  {feature.label}
                  <Badge variant="secondary">BETA</Badge>
                </CardTitle>
                <CardDescription>{feature.description}</CardDescription>
              </CardHeader>
            </Card>
            
            <div className="space-y-6">
              {feature.component}
            </div>
          </TabsContent>
        ))}
      </Tabs>

      <div className="mt-8 p-6 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg">
        <h3 className="text-lg font-semibold mb-2">🚀 Core Features</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 text-sm">
          <div className="flex items-center gap-2">
            <Languages className="h-4 w-4 text-blue-500" />
            <span>Tamil Language Support</span>
          </div>
          <div className="flex items-center gap-2">
            <Languages className="h-4 w-4 text-green-500" />
            <span>Sinhala Language Support</span>
          </div>
          <div className="flex items-center gap-2">
            <Image className="h-4 w-4 text-purple-500" />
            <span>Image Input Support</span>
          </div>
          <div className="flex items-center gap-2">
            <Search className="h-4 w-4 text-red-500" />
            <span>Semantic Similarity</span>
          </div>
          <div className="flex items-center gap-2">
            <Shield className="h-4 w-4 text-orange-500" />
            <span>Source Credibility</span>
          </div>
          <div className="flex items-center gap-2">
            <CheckCircle className="h-4 w-4 text-teal-500" />
            <span>Real-time Detection</span>
          </div>
          <div className="flex items-center gap-2">
            <BarChart3 className="h-4 w-4 text-pink-500" />
            <span>Confidence Scores</span>
          </div>
          <div className="flex items-center gap-2">
            <Globe className="h-4 w-4 text-indigo-500" />
            <span>Multilingual Support</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default FeatureDashboard;
