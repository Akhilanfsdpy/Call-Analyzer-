import { useState, useEffect } from "react";
import axios from "axios";
import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, Download, FileText, BarChart3 } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import { toast } from "sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const CallDetails = () => {
  const { callId } = useParams();
  const navigate = useNavigate();
  const [callData, setCallData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchCallDetails();
  }, [callId]);

  const fetchCallDetails = async () => {
    try {
      const response = await axios.get(`${API}/calls/${callId}`);
      setCallData(response.data);
      setLoading(false);
    } catch (error) {
      console.error("Error fetching call details:", error);
      toast.error("Failed to load call details");
      setLoading(false);
    }
  };

  const handleExport = async (format) => {
    try {
      const response = await axios.get(`${API}/export/${callId}/${format}`, {
        responseType: "blob",
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `${callData.filename}_report.${format}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      
      toast.success(`Report exported as ${format.toUpperCase()}`);
    } catch (error) {
      console.error("Export error:", error);
      toast.error("Failed to export report");
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-sky-50 to-blue-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-sky-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-slate-600">Loading call details...</p>
        </div>
      </div>
    );
  }

  if (!callData) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-sky-50 to-blue-50 flex items-center justify-center">
        <Card className="p-8 text-center">
          <p className="text-slate-600 mb-4">Call not found</p>
          <Button onClick={() => navigate("/")}>Back to Dashboard</Button>
        </Card>
      </div>
    );
  }

  const agent = callData.agent_sentiment || {};
  const prospect = callData.prospect_sentiment || {};

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-sky-50 to-blue-50">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-md border-b border-slate-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button
                variant="ghost"
                onClick={() => navigate("/")}
                className="hover:bg-sky-100"
                data-testid="back-button"
              >
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back
              </Button>
              <div>
                <h1 className="text-xl font-bold text-slate-800" data-testid="call-filename">{callData.filename}</h1>
                <p className="text-sm text-slate-500">
                  {new Date(callData.upload_timestamp).toLocaleString()}
                </p>
              </div>
            </div>
            <div className="flex gap-3">
              <Button
                variant="outline"
                onClick={() => handleExport("csv")}
                className="border-slate-300 hover:bg-slate-100"
                data-testid="export-csv-button"
              >
                <FileText className="w-4 h-4 mr-2" />
                Export CSV
              </Button>
              <Button
                onClick={() => handleExport("pdf")}
                className="bg-gradient-to-r from-sky-500 to-blue-600 hover:from-sky-600 hover:to-blue-700 text-white"
                data-testid="export-pdf-button"
              >
                <Download className="w-4 h-4 mr-2" />
                Export PDF
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Overall Score */}
        <Card className="mb-8 p-8 bg-white/90 backdrop-blur-sm border-slate-200 shadow-xl" data-testid="overall-score-card">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-2xl font-bold text-slate-800">Overall Performance Score</h2>
              <p className="text-slate-500 mt-1">AI-powered analysis of call quality</p>
            </div>
            <div className="text-right">
              <div className="text-5xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-sky-500 to-blue-600" data-testid="overall-score-value">
                {callData.overall_score || 0}
              </div>
              <p className="text-slate-500 text-sm mt-1">out of 100</p>
            </div>
          </div>
          <Progress value={callData.overall_score || 0} className="h-3" data-testid="overall-score-progress" />
        </Card>

        {/* Tabs */}
        <Tabs defaultValue="summary" className="space-y-6">
          <TabsList className="bg-white/90 backdrop-blur-sm border border-slate-200 p-1" data-testid="tabs-list">
            <TabsTrigger value="summary" className="data-[state=active]:bg-sky-500 data-[state=active]:text-white" data-testid="tab-summary">Summary</TabsTrigger>
            <TabsTrigger value="sentiment" className="data-[state=active]:bg-sky-500 data-[state=active]:text-white" data-testid="tab-sentiment">Sentiment Analysis</TabsTrigger>
            <TabsTrigger value="transcript" className="data-[state=active]:bg-sky-500 data-[state=active]:text-white" data-testid="tab-transcript">Transcript</TabsTrigger>
          </TabsList>

          {/* Summary Tab */}
          <TabsContent value="summary" className="space-y-6" data-testid="summary-content">
            <Card className="p-6 bg-white/90 backdrop-blur-sm border-slate-200 shadow-lg">
              <h3 className="text-lg font-bold text-slate-800 mb-4 flex items-center gap-2">
                <BarChart3 className="w-5 h-5 text-sky-600" />
                Call Summary
              </h3>
              <p className="text-slate-700 leading-relaxed" data-testid="call-summary-text">
                {callData.call_summary || "Analysis in progress..."}
              </p>
            </Card>

            <div className="grid md:grid-cols-2 gap-6">
              <Card className="p-6 bg-gradient-to-br from-emerald-50 to-teal-50 border-emerald-200 shadow-lg">
                <h3 className="text-lg font-bold text-emerald-800 mb-4">✓ Positive Highlights</h3>
                <ul className="space-y-3" data-testid="positive-highlights-list">
                  {callData.positive_highlights?.map((item, index) => (
                    <li key={index} className="flex items-start gap-2 text-slate-700">
                      <span className="w-6 h-6 bg-emerald-500 text-white rounded-full flex items-center justify-center text-xs flex-shrink-0 mt-0.5">
                        {index + 1}
                      </span>
                      <span>{item}</span>
                    </li>
                  )) || <p className="text-slate-500">No highlights available</p>}
                </ul>
              </Card>

              <Card className="p-6 bg-gradient-to-br from-amber-50 to-orange-50 border-amber-200 shadow-lg">
                <h3 className="text-lg font-bold text-amber-800 mb-4">⚡ Improvement Suggestions</h3>
                <ul className="space-y-3" data-testid="improvement-suggestions-list">
                  {callData.improvement_suggestions?.map((item, index) => (
                    <li key={index} className="flex items-start gap-2 text-slate-700">
                      <span className="w-6 h-6 bg-amber-500 text-white rounded-full flex items-center justify-center text-xs flex-shrink-0 mt-0.5">
                        {index + 1}
                      </span>
                      <span>{item}</span>
                    </li>
                  )) || <p className="text-slate-500">No suggestions available</p>}
                </ul>
              </Card>
            </div>
          </TabsContent>

          {/* Sentiment Analysis Tab */}
          <TabsContent value="sentiment" className="space-y-6" data-testid="sentiment-content">
            <div className="grid md:grid-cols-2 gap-6">
              {/* Agent Sentiment */}
              <Card className="p-6 bg-white/90 backdrop-blur-sm border-slate-200 shadow-lg">
                <div className="flex items-center justify-between mb-6">
                  <h3 className="text-lg font-bold text-slate-800">Agent Performance</h3>
                  <Badge className="bg-sky-500 hover:bg-sky-600" data-testid="agent-sentiment-badge">
                    {agent.general_sentiment || "Neutral"}
                  </Badge>
                </div>
                <div className="space-y-4" data-testid="agent-metrics">
                  <MetricBar label="Empathy" value={agent.empathy || 0} />
                  <MetricBar label="Engagement" value={agent.engagement || 0} />
                  <MetricBar label="Enthusiasm" value={agent.enthusiasm || 0} />
                  <MetricBar label="Politeness" value={agent.politeness || 0} />
                </div>
              </Card>

              {/* Prospect Sentiment */}
              <Card className="p-6 bg-white/90 backdrop-blur-sm border-slate-200 shadow-lg">
                <div className="flex items-center justify-between mb-6">
                  <h3 className="text-lg font-bold text-slate-800">Prospect Response</h3>
                  <Badge className="bg-teal-500 hover:bg-teal-600" data-testid="prospect-sentiment-badge">
                    {prospect.general_sentiment || "Neutral"}
                  </Badge>
                </div>
                <div className="space-y-4" data-testid="prospect-metrics">
                  <MetricBar label="Empathy" value={prospect.empathy || 0} />
                  <MetricBar label="Engagement" value={prospect.engagement || 0} />
                  <MetricBar label="Enthusiasm" value={prospect.enthusiasm || 0} />
                  <MetricBar label="Politeness" value={prospect.politeness || 0} />
                </div>
              </Card>
            </div>
          </TabsContent>

          {/* Transcript Tab */}
          <TabsContent value="transcript" data-testid="transcript-content">
            <Card className="p-6 bg-white/90 backdrop-blur-sm border-slate-200 shadow-lg">
              <h3 className="text-lg font-bold text-slate-800 mb-4">Call Transcript</h3>
              <div className="bg-slate-50 rounded-lg p-6 max-h-96 overflow-y-auto">
                <p className="text-slate-700 leading-relaxed whitespace-pre-wrap font-mono text-sm" data-testid="transcript-text">
                  {callData.transcription || "Transcription not available"}
                </p>
              </div>
            </Card>
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
};

const MetricBar = ({ label, value }) => (
  <div data-testid={`metric-${label.toLowerCase()}`}>
    <div className="flex items-center justify-between mb-2">
      <span className="text-sm font-medium text-slate-600">{label}</span>
      <span className="text-sm font-semibold text-slate-800" data-testid={`metric-${label.toLowerCase()}-value`}>{value}/100</span>
    </div>
    <Progress value={value} className="h-2" data-testid={`metric-${label.toLowerCase()}-progress`} />
  </div>
);

export default CallDetails;