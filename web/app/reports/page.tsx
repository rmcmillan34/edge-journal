"use client";

import { useEffect, useState } from "react";

interface ReportHistoryItem {
  id: number;
  filename: string;
  report_type: string;
  created_at: string;
  file_size: number;
}

export default function ReportsPage() {
  const [reports, setReports] = useState<ReportHistoryItem[]>([]);
  const [token, setToken] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);

  const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

  useEffect(() => {
    try {
      setToken(localStorage.getItem("ej_token") || "");
    } catch {}
  }, []);

  useEffect(() => {
    if (token) {
      fetchReports();
    }
  }, [token]);

  const fetchReports = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE}/api/reports/history`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setReports(data);
      } else {
        setError("Failed to fetch report history");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch reports");
    } finally {
      setLoading(false);
    }
  };

  const downloadReport = async (filename: string) => {
    try {
      const response = await fetch(
        `${API_BASE}/api/reports/download/${filename}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      } else {
        alert("Failed to download report");
      }
    } catch (err) {
      alert("Failed to download report");
    }
  };

  const deleteReport = async (filename: string) => {
    try {
      const response = await fetch(`${API_BASE}/api/reports/${filename}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.ok) {
        setReports((prev) => prev.filter((r) => r.filename !== filename));
        setDeleteConfirm(null);
      } else {
        alert("Failed to delete report");
      }
    } catch (err) {
      alert("Failed to delete report");
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleString();
  };

  if (!token) {
    return (
      <div className="p-8">
        <p className="text-subtext0">Please log in to view reports.</p>
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-semibold text-text">Report History</h1>
        <button
          onClick={fetchReports}
          className="px-4 py-2 bg-surface1 hover:bg-surface2 rounded transition-colors text-text"
        >
          🔄 Refresh
        </button>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red/10 border border-red rounded text-red">
          {error}
        </div>
      )}

      {loading ? (
        <div className="text-center py-8 text-subtext0">Loading reports...</div>
      ) : reports.length === 0 ? (
        <div className="text-center py-8 text-subtext0">
          <p>No reports generated yet.</p>
          <p className="mt-2 text-sm">
            Go to the Dashboard and click "📊 Generate Report" to create your
            first report.
          </p>
        </div>
      ) : (
        <div className="bg-surface0 rounded-lg overflow-hidden">
          <table className="w-full">
            <thead className="bg-surface1">
              <tr>
                <th className="text-left px-4 py-3 text-text font-medium">
                  Report Type
                </th>
                <th className="text-left px-4 py-3 text-text font-medium">
                  Filename
                </th>
                <th className="text-left px-4 py-3 text-text font-medium">
                  Created
                </th>
                <th className="text-left px-4 py-3 text-text font-medium">
                  Size
                </th>
                <th className="text-right px-4 py-3 text-text font-medium">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {reports.map((report) => (
                <tr
                  key={report.id}
                  className="border-t border-surface2 hover:bg-surface1 transition-colors"
                >
                  <td className="px-4 py-3 text-text">
                    <span className="inline-block px-2 py-1 bg-blue/10 text-blue rounded text-sm capitalize">
                      {report.report_type}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-text font-mono text-sm">
                    {report.filename}
                  </td>
                  <td className="px-4 py-3 text-subtext0 text-sm">
                    {formatDate(report.created_at)}
                  </td>
                  <td className="px-4 py-3 text-subtext0 text-sm">
                    {formatFileSize(report.file_size)}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex justify-end space-x-2">
                      <button
                        onClick={() => downloadReport(report.filename)}
                        className="px-3 py-1 bg-blue hover:bg-blue/90 text-base rounded transition-colors text-sm"
                        title="Download"
                      >
                        ⬇ Download
                      </button>
                      {deleteConfirm === report.filename ? (
                        <div className="flex space-x-1">
                          <button
                            onClick={() => deleteReport(report.filename)}
                            className="px-3 py-1 bg-red hover:bg-red/90 text-base rounded transition-colors text-sm"
                          >
                            ✓ Confirm
                          </button>
                          <button
                            onClick={() => setDeleteConfirm(null)}
                            className="px-3 py-1 bg-surface2 hover:bg-surface1 text-text rounded transition-colors text-sm"
                          >
                            ✕ Cancel
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => setDeleteConfirm(report.filename)}
                          className="px-3 py-1 bg-surface2 hover:bg-red/20 text-text hover:text-red rounded transition-colors text-sm"
                          title="Delete"
                        >
                          🗑 Delete
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
