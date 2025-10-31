import { useState, useEffect } from "react";
import axios from "axios";
import { Upload, Phone, TrendingUp, Activity } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const Dashboard = () => {
  const [calls, setCalls] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const navigate = useNavigate();

  useEffect(() => {
    fetchCalls();
  }, []);

  const fetchCalls = async () => {
    try {
      const response = await axios.get(`${API}/calls`);
      setCalls(response.data);
    } catch (error) {
      console.error("Error fetching calls:", error);
      toast.error("Failed to load calls");
    }
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setUploading(true);
    setUploadProgress(10);

    try {
      const formData = new FormData();
      formData.append("file", file);

      setUploadProgress(30);
      const uploadResponse = await axios.post(`${API}/upload-call`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      const callId = uploadResponse.data.call_id;
      setUploadProgress(50);
      toast.success("File uploaded! Starting transcription...");

      // Transcribe
      await axios.post(`${API}/transcribe/${callId}`);
      setUploadProgress(75);
      toast.success("Transcription complete! Analyzing call...");

      // Analyze
      await axios.post(`${API}/analyze/${callId}`);
      setUploadProgress(100);
      toast.success("Analysis complete!");

      // Refresh calls list
      await fetchCalls();
      
      setTimeout(() => {
        setUploading(false);
        setUploadProgress(0);
        navigate(`/call/${callId}`);
      }, 1000);
    } catch (error) {
      console.error("Upload error:", error);
      toast.error(error.response?.data?.detail || "Upload failed");
      setUploading(false);
      setUploadProgress(0);
    }
  };

  const getStatusBadge = (status) => {
    const statusConfig = {
      completed: { variant: "default", label: "Completed", className: "bg-emerald-500 hover:bg-emerald-600" },
      processing: { variant: "secondary", label: "Processing", className: "bg-amber-500 hover:bg-amber-600" },
      pending: { variant: "outline", label: "Pending", className: "border-slate-400 text-slate-600" },
      failed: { variant: "destructive", label: "Failed" },
    };
    const config = statusConfig[status] || statusConfig.pending;
    return <Badge className={config.className} data-testid={`status-badge-${status}`}>{config.label}</Badge>;
  };

  const stats = {
    totalCalls: calls.length,
    avgScore: calls.length > 0
      ? Math.round(calls.filter(c => c.overall_score).reduce((sum, c) => sum + c.overall_score, 0) / calls.filter(c => c.overall_score).length)
      : 0,
    completedAnalysis: calls.filter(c => c.analysis_status === "completed").length,
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-sky-50 to-blue-50">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-md border-b border-slate-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 bg-gradient-to-br from-sky-400 to-blue-500 rounded-xl flex items-center justify-center shadow-lg">
                <Phone className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-slate-800" data-testid="app-title">AI Sales Call Analyzer</h1>
                <p className="text-sm text-slate-500">Performance insights powered by AI</p>
              </div>
            </div>
            <label htmlFor="file-upload">
              <Button
                className="bg-gradient-to-r from-sky-500 to-blue-600 hover:from-sky-600 hover:to-blue-700 text-white px-6 shadow-lg"
                disabled={uploading}
                data-testid="upload-button"
                asChild
              >
                <span>
                  <Upload className="w-4 h-4 mr-2" />
                  {uploading ? "Processing..." : "Upload Call"}
                </span>
              </Button>
              <input
                id="file-upload"
                type="file"
                accept=".mp3,.wav,.m4a,.mp4,.mpeg,.mpga,.webm"
                onChange={handleFileUpload}
                className="hidden"
                disabled={uploading}
                data-testid="file-input"
              />
            </label>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Upload Progress */}
        {uploading && (
          <Card className="mb-8 p-6 bg-white/90 backdrop-blur-sm border-sky-200 shadow-xl" data-testid="upload-progress-card">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-slate-700">Processing your call...</span>
                <span className="text-sm text-slate-500">{uploadProgress}%</span>
              </div>
              <Progress value={uploadProgress} className="h-2" data-testid="upload-progress-bar" />
            </div>
          </Card>
        )}

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <Card className="p-6 bg-white/90 backdrop-blur-sm border-sky-200 shadow-lg hover:shadow-xl transition-all duration-300" data-testid="stat-total-calls">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-500 mb-1">Total Calls</p>
                <p className="text-3xl font-bold text-slate-800">{stats.totalCalls}</p>
              </div>
              <div className="w-12 h-12 bg-sky-100 rounded-lg flex items-center justify-center">
                <Phone className="w-6 h-6 text-sky-600" />
              </div>
            </div>
          </Card>

          <Card className="p-6 bg-white/90 backdrop-blur-sm border-teal-200 shadow-lg hover:shadow-xl transition-all duration-300" data-testid="stat-avg-score">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-500 mb-1">Average Score</p>
                <p className="text-3xl font-bold text-slate-800">{stats.avgScore || 0}</p>
              </div>
              <div className="w-12 h-12 bg-teal-100 rounded-lg flex items-center justify-center">
                <TrendingUp className="w-6 h-6 text-teal-600" />
              </div>
            </div>
          </Card>

          <Card className="p-6 bg-white/90 backdrop-blur-sm border-blue-200 shadow-lg hover:shadow-xl transition-all duration-300" data-testid="stat-completed">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-500 mb-1">Completed Analysis</p>
                <p className="text-3xl font-bold text-slate-800">{stats.completedAnalysis}</p>
              </div>
              <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                <Activity className="w-6 h-6 text-blue-600" />
              </div>
            </div>
          </Card>
        </div>

        {/* Calls Table */}
        <Card className="p-6 bg-white/90 backdrop-blur-sm border-slate-200 shadow-xl" data-testid="calls-table-card">
          <h2 className="text-xl font-bold text-slate-800 mb-6">Recent Analysis</h2>
          
          {calls.length === 0 ? (
            <div className="text-center py-12" data-testid="empty-state">
              <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Phone className="w-8 h-8 text-slate-400" />
              </div>
              <p className="text-slate-500 mb-2">No calls analyzed yet</p>
              <p className="text-sm text-slate-400">Upload your first sales call to get started</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full" data-testid="calls-table">
                <thead>
                  <tr className="border-b border-slate-200">
                    <th className="text-left py-3 px-4 text-sm font-semibold text-slate-600">File Name</th>
                    <th className="text-left py-3 px-4 text-sm font-semibold text-slate-600">Date</th>
                    <th className="text-left py-3 px-4 text-sm font-semibold text-slate-600">Status</th>
                    <th className="text-left py-3 px-4 text-sm font-semibold text-slate-600">Score</th>
                    <th className="text-left py-3 px-4 text-sm font-semibold text-slate-600">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {calls.map((call) => (
                    <tr
                      key={call.id}
                      className="border-b border-slate-100 hover:bg-sky-50/50 transition-colors duration-200"
                      data-testid={`call-row-${call.id}`}
                    >
                      <td className="py-4 px-4 text-sm text-slate-700" data-testid={`call-filename-${call.id}`}>{call.filename}</td>
                      <td className="py-4 px-4 text-sm text-slate-500">
                        {new Date(call.upload_timestamp).toLocaleDateString()}
                      </td>
                      <td className="py-4 px-4">
                        {getStatusBadge(call.analysis_status)}
                      </td>
                      <td className="py-4 px-4">
                        {call.overall_score ? (
                          <span className="text-sm font-semibold text-slate-700" data-testid={`call-score-${call.id}`}>
                            {call.overall_score}/100
                          </span>
                        ) : (
                          <span className="text-sm text-slate-400">-</span>
                        )}
                      </td>
                      <td className="py-4 px-4">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => navigate(`/call/${call.id}`)}
                          className="text-sky-600 hover:text-sky-700 hover:bg-sky-100"
                          data-testid={`view-details-button-${call.id}`}
                        >
                          View Details
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </main>
    </div>
  );
};

export default Dashboard;