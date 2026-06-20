import React, { useState } from "react";
import { MdDownload, MdInsertDriveFile, MdBarChart, MdPictureAsPdf } from "react-icons/md";
import styles from "./layout/AdminLayout.module.css";

export default function Reports() {
  const [reportType, setReportType] = useState("mood");
  const [dateRange, setDateRange] = useState("7days");
  const [isGenerating, setIsGenerating] = useState(false);
  const [showPreview, setShowPreview] = useState(false);

  const handleGenerate = () => {
    setIsGenerating(true);
    setShowPreview(false);
    // Simulate generation delay
    setTimeout(() => {
      setIsGenerating(false);
      setShowPreview(true);
    }, 1000);
  };

  const handleExport = (format: string) => {
    // In a real app, this would trigger a backend download
    alert(`Downloading ${reportType} report as ${format.toUpperCase()}...`);
  };

  return (
    <div>
      <div style={{ marginBottom: "2rem" }}>
        <h2 style={{ fontSize: "1.5rem", fontWeight: "bold", color: "#1e293b", margin: 0 }}>
          Generate Reports
        </h2>
        <p style={{ color: "#64748b", marginTop: "0.25rem", fontSize: "0.875rem" }}>
          Create and export aggregated data summaries for administrative review.
        </p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "1.5rem", marginBottom: "2rem" }}>
        {/* Report Controls */}
        <div style={{ background: "white", padding: "1.5rem", borderRadius: "1rem", boxShadow: "0 4px 6px -1px rgba(0,0,0,0.05)", border: "1px solid #f1f5f9" }}>
          <h3 style={{ fontSize: "1.1rem", fontWeight: 600, color: "#334155", marginBottom: "1rem" }}>Report Settings</h3>
          
          <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            <div>
              <label style={{ display: "block", fontSize: "0.875rem", fontWeight: 500, color: "#475569", marginBottom: "0.5rem" }}>Report Type</label>
              <select 
                value={reportType} 
                onChange={(e) => setReportType(e.target.value)}
                style={{ width: "100%", padding: "0.75rem", borderRadius: "0.5rem", border: "1px solid #cbd5e1", outline: "none", backgroundColor: "#f8fafc" }}
              >
                <option value="mood">Mood Summary & Trends</option>
                <option value="risk">Risk Levels & Alerts Log</option>
                <option value="student">Student Activity Overview</option>
              </select>
            </div>

            <div>
              <label style={{ display: "block", fontSize: "0.875rem", fontWeight: 500, color: "#475569", marginBottom: "0.5rem" }}>Date Range</label>
              <select 
                value={dateRange} 
                onChange={(e) => setDateRange(e.target.value)}
                style={{ width: "100%", padding: "0.75rem", borderRadius: "0.5rem", border: "1px solid #cbd5e1", outline: "none", backgroundColor: "#f8fafc" }}
              >
                <option value="7days">Last 7 Days</option>
                <option value="1month">Last 30 Days</option>
                <option value="semester">Current Semester</option>
                <option value="all">All Time</option>
              </select>
            </div>

            <button 
              onClick={handleGenerate}
              disabled={isGenerating}
              style={{
                marginTop: "1rem",
                padding: "0.875rem",
                backgroundColor: "#0f766e",
                color: "white",
                border: "none",
                borderRadius: "0.5rem",
                fontWeight: 600,
                cursor: isGenerating ? "not-allowed" : "pointer",
                opacity: isGenerating ? 0.7 : 1,
                display: "flex",
                justifyContent: "center",
                alignItems: "center",
                gap: "0.5rem"
              }}
            >
              {isGenerating ? "Generating..." : "Generate Preview"}
            </button>
          </div>
        </div>

        {/* Preview Area */}
        <div style={{ background: "white", padding: "1.5rem", borderRadius: "1rem", boxShadow: "0 4px 6px -1px rgba(0,0,0,0.05)", border: "1px solid #f1f5f9", display: "flex", flexDirection: "column" }}>
          <h3 style={{ fontSize: "1.1rem", fontWeight: 600, color: "#334155", marginBottom: "1rem" }}>Report Preview</h3>
          
          <div style={{ flex: 1, backgroundColor: "#f8fafc", borderRadius: "0.5rem", border: "1px dashed #cbd5e1", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "2rem", textAlign: "center", minHeight: "200px" }}>
            {!showPreview ? (
              <>
                <MdInsertDriveFile size={48} color="#cbd5e1" style={{ marginBottom: "1rem" }} />
                <p style={{ color: "#94a3b8", fontSize: "0.875rem" }}>Select settings and generate to see preview</p>
              </>
            ) : (
              <>
                <MdBarChart size={48} color="#0f766e" style={{ marginBottom: "1rem" }} />
                <h4 style={{ color: "#1e293b", margin: "0 0 0.5rem 0" }}>Preview Available</h4>
                <p style={{ color: "#64748b", fontSize: "0.875rem", margin: 0 }}>
                  Showing sample aggregation for {reportType} over {dateRange}.<br/>
                  Total records analyzed: ~142
                </p>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Export Options (Only show if preview generated) */}
      {showPreview && (
        <div style={{ background: "white", padding: "1.5rem", borderRadius: "1rem", boxShadow: "0 4px 6px -1px rgba(0,0,0,0.05)", border: "1px solid #f1f5f9" }}>
          <h3 style={{ fontSize: "1.1rem", fontWeight: 600, color: "#334155", marginBottom: "1rem" }}>Export Options</h3>
          <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
            <button 
              onClick={() => handleExport('pdf')}
              style={{ display: "flex", alignItems: "center", gap: "0.5rem", padding: "0.75rem 1.25rem", backgroundColor: "#fef2f2", color: "#dc2626", border: "1px solid #fecaca", borderRadius: "0.5rem", fontWeight: 600, cursor: "pointer" }}
            >
              <MdPictureAsPdf size={20} /> Export as PDF
            </button>
            <button 
              onClick={() => handleExport('csv')}
              style={{ display: "flex", alignItems: "center", gap: "0.5rem", padding: "0.75rem 1.25rem", backgroundColor: "#f0fdf4", color: "#16a34a", border: "1px solid #bbf7d0", borderRadius: "0.5rem", fontWeight: 600, cursor: "pointer" }}
            >
              <MdDownload size={20} /> Export as CSV
            </button>
            <button 
              onClick={() => handleExport('excel')}
              style={{ display: "flex", alignItems: "center", gap: "0.5rem", padding: "0.75rem 1.25rem", backgroundColor: "#f0f9ff", color: "#0284c7", border: "1px solid #bae6fd", borderRadius: "0.5rem", fontWeight: 600, cursor: "pointer" }}
            >
              <MdDownload size={20} /> Export as Excel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
