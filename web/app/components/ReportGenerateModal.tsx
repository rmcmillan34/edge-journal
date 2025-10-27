"use client";

import { useState, useEffect } from "react";

interface ReportGenerateModalProps {
  isOpen: boolean;
  onClose: () => void;
  defaultType?: "monthly" | "weekly" | "daily" | "ytd" | "yearly" | "alltime";
  defaultPeriod?: { year?: number; month?: number; date?: string };
}

interface Account {
  id: number;
  name: string;
  broker_label?: string;
  status: string;
}

export default function ReportGenerateModal({
  isOpen,
  onClose,
  defaultType = "monthly",
  defaultPeriod,
}: ReportGenerateModalProps) {
  const [reportType, setReportType] = useState<string>(defaultType);
  const [year, setYear] = useState<number>(
    defaultPeriod?.year || new Date().getFullYear()
  );
  const [month, setMonth] = useState<number>(
    defaultPeriod?.month || new Date().getMonth() + 1
  );
  const [week, setWeek] = useState<number>(1);
  const [date, setDate] = useState<string>(
    defaultPeriod?.date || new Date().toISOString().split("T")[0]
  );
  const [theme, setTheme] = useState<"light" | "dark">("light");
  const [includeScreenshots, setIncludeScreenshots] = useState<boolean>(true);

  // Account selection state
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [selectedAccounts, setSelectedAccounts] = useState<number[]>([]);
  const [accountSeparationMode, setAccountSeparationMode] = useState<
    "combined" | "grouped" | "separate"
  >("combined");

  // UI state
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

  // Fetch accounts on mount
  useEffect(() => {
    const fetchAccounts = async () => {
      const token = localStorage.getItem("ej_token");
      if (!token) return;

      try {
        const response = await fetch(`${API_BASE}/api/accounts`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (response.ok) {
          const data = await response.json();
          setAccounts(data.filter((acc: Account) => acc.status === "active"));
          // Select all accounts by default
          setSelectedAccounts(
            data
              .filter((acc: Account) => acc.status === "active")
              .map((acc: Account) => acc.id)
          );
        }
      } catch (err) {
        console.error("Failed to fetch accounts:", err);
      }
    };

    if (isOpen) {
      fetchAccounts();
    }
  }, [isOpen, API_BASE]);

  const handleAccountToggle = (accountId: number) => {
    setSelectedAccounts((prev) =>
      prev.includes(accountId)
        ? prev.filter((id) => id !== accountId)
        : [...prev, accountId]
    );
  };

  const handleSelectAllAccounts = () => {
    setSelectedAccounts(accounts.map((acc) => acc.id));
  };

  const handleDeselectAllAccounts = () => {
    setSelectedAccounts([]);
  };

  const handleGenerate = async () => {
    console.log("[ReportModal] Generate button clicked");
    setLoading(true);
    setError(null);

    const token = localStorage.getItem("ej_token");
    if (!token) {
      console.error("[ReportModal] No token found");
      setError("Not authenticated. Please log in.");
      setLoading(false);
      return;
    }

    // Build period object based on report type
    let period: any = {};
    if (reportType === "monthly") {
      period = { year, month };
    } else if (reportType === "weekly") {
      period = { year, week };
    } else if (reportType === "daily") {
      period = { date };
    } else if (reportType === "yearly") {
      period = { year };
    }
    // YTD and alltime don't need period

    const payload = {
      type: reportType,
      period,
      account_ids: selectedAccounts.length > 0 ? selectedAccounts : null,
      account_separation_mode: accountSeparationMode,
      theme,
      include_screenshots: includeScreenshots,
    };

    console.log("[ReportModal] Sending request:", payload);

    try {
      const response = await fetch(`${API_BASE}/api/reports/generate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      console.log("[ReportModal] Response status:", response.status);

      if (response.ok) {
        // Download PDF
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;

        // Get filename from Content-Disposition header if available
        const contentDisposition = response.headers.get("Content-Disposition");
        let filename = `report_${reportType}_${year}${
          month ? `_${month.toString().padStart(2, "0")}` : ""
        }.pdf`;
        if (contentDisposition) {
          const match = contentDisposition.match(/filename="?(.+)"?/);
          if (match) filename = match[1];
        }

        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

        // Close modal on success
        console.log("[ReportModal] Report generated successfully");
        onClose();
      } else {
        const errorData = await response.json();
        console.error("[ReportModal] API error:", errorData);
        setError(errorData.detail || "Failed to generate report");
      }
    } catch (err) {
      console.error("[ReportModal] Exception:", err);
      setError(
        err instanceof Error ? err.message : "Failed to generate report"
      );
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
      onClick={onClose}
    >
      <div
        className="bg-surface0 rounded-lg p-6 max-w-md w-full mx-4 max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold text-text">Generate Report</h2>
          <button
            onClick={onClose}
            className="text-subtext0 hover:text-text transition-colors"
          >
            ✕
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red/10 border border-red rounded text-red text-sm">
            {error}
          </div>
        )}

        <div className="space-y-4">
          {/* Report Type */}
          <div>
            <label className="block text-sm font-medium text-text mb-1">
              Report Type
            </label>
            <select
              value={reportType}
              onChange={(e) => setReportType(e.target.value)}
              className="w-full px-3 py-2 bg-surface1 border border-surface2 rounded text-text focus:outline-none focus:ring-2 focus:ring-blue"
            >
              <option value="monthly">Monthly</option>
              <option value="weekly">Weekly</option>
              <option value="daily">Daily</option>
              <option value="yearly">Yearly</option>
              <option value="ytd">Year-to-Date</option>
              <option value="alltime">All-Time</option>
            </select>
          </div>

          {/* Period Selection */}
          {reportType === "monthly" && (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-text mb-1">
                  Year
                </label>
                <input
                  type="number"
                  value={year}
                  onChange={(e) => setYear(parseInt(e.target.value))}
                  className="w-full px-3 py-2 bg-surface1 border border-surface2 rounded text-text focus:outline-none focus:ring-2 focus:ring-blue"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-text mb-1">
                  Month
                </label>
                <select
                  value={month}
                  onChange={(e) => setMonth(parseInt(e.target.value))}
                  className="w-full px-3 py-2 bg-surface1 border border-surface2 rounded text-text focus:outline-none focus:ring-2 focus:ring-blue"
                >
                  {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => (
                    <option key={m} value={m}>
                      {new Date(2000, m - 1).toLocaleString("default", {
                        month: "long",
                      })}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          )}

          {reportType === "weekly" && (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-text mb-1">
                  Year
                </label>
                <input
                  type="number"
                  value={year}
                  onChange={(e) => setYear(parseInt(e.target.value))}
                  className="w-full px-3 py-2 bg-surface1 border border-surface2 rounded text-text focus:outline-none focus:ring-2 focus:ring-blue"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-text mb-1">
                  Week
                </label>
                <input
                  type="number"
                  min="1"
                  max="53"
                  value={week}
                  onChange={(e) => setWeek(parseInt(e.target.value))}
                  className="w-full px-3 py-2 bg-surface1 border border-surface2 rounded text-text focus:outline-none focus:ring-2 focus:ring-blue"
                />
              </div>
            </div>
          )}

          {reportType === "daily" && (
            <div>
              <label className="block text-sm font-medium text-text mb-1">
                Date
              </label>
              <input
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                className="w-full px-3 py-2 bg-surface1 border border-surface2 rounded text-text focus:outline-none focus:ring-2 focus:ring-blue"
              />
            </div>
          )}

          {reportType === "yearly" && (
            <div>
              <label className="block text-sm font-medium text-text mb-1">
                Year
              </label>
              <input
                type="number"
                value={year}
                onChange={(e) => setYear(parseInt(e.target.value))}
                className="w-full px-3 py-2 bg-surface1 border border-surface2 rounded text-text focus:outline-none focus:ring-2 focus:ring-blue"
              />
            </div>
          )}

          {/* Account Selection */}
          {accounts.length > 0 && (
            <div>
              <div className="flex justify-between items-center mb-2">
                <label className="block text-sm font-medium text-text">
                  Accounts
                </label>
                <div className="space-x-2">
                  <button
                    type="button"
                    onClick={handleSelectAllAccounts}
                    className="text-xs text-blue hover:underline"
                  >
                    All
                  </button>
                  <button
                    type="button"
                    onClick={handleDeselectAllAccounts}
                    className="text-xs text-blue hover:underline"
                  >
                    None
                  </button>
                </div>
              </div>
              <div className="space-y-2 max-h-40 overflow-y-auto bg-surface1 border border-surface2 rounded p-2">
                {accounts.map((account) => (
                  <label
                    key={account.id}
                    className="flex items-center space-x-2 cursor-pointer hover:bg-surface2 p-1 rounded"
                  >
                    <input
                      type="checkbox"
                      checked={selectedAccounts.includes(account.id)}
                      onChange={() => handleAccountToggle(account.id)}
                      className="text-blue focus:ring-blue"
                    />
                    <span className="text-sm text-text">
                      {account.name}
                      {account.broker_label && (
                        <span className="text-subtext0 ml-1">
                          ({account.broker_label})
                        </span>
                      )}
                    </span>
                  </label>
                ))}
              </div>
              <p className="text-xs text-subtext0 mt-1">
                {selectedAccounts.length} of {accounts.length} selected
              </p>
            </div>
          )}

          {/* Account Separation Mode (only show if >1 account selected) */}
          {selectedAccounts.length > 1 && (
            <div>
              <label className="block text-sm font-medium text-text mb-1">
                Account Separation
              </label>
              <select
                value={accountSeparationMode}
                onChange={(e) =>
                  setAccountSeparationMode(
                    e.target.value as "combined" | "grouped" | "separate"
                  )
                }
                className="w-full px-3 py-2 bg-surface1 border border-surface2 rounded text-text focus:outline-none focus:ring-2 focus:ring-blue"
              >
                <option value="combined">
                  Combined (merge all accounts together)
                </option>
                <option value="grouped">
                  Grouped (combined + per-account sections)
                </option>
                <option value="separate">
                  Separate (individual PDFs per account)
                </option>
              </select>
            </div>
          )}

          {/* Theme */}
          <div>
            <label className="block text-sm font-medium text-text mb-1">
              Theme
            </label>
            <select
              value={theme}
              onChange={(e) => setTheme(e.target.value as "light" | "dark")}
              className="w-full px-3 py-2 bg-surface1 border border-surface2 rounded text-text focus:outline-none focus:ring-2 focus:ring-blue"
            >
              <option value="light">Light</option>
              <option value="dark">Dark</option>
            </select>
          </div>

          {/* Include Screenshots */}
          <div>
            <label className="flex items-center space-x-2 cursor-pointer">
              <input
                type="checkbox"
                checked={includeScreenshots}
                onChange={(e) => setIncludeScreenshots(e.target.checked)}
                className="text-blue focus:ring-blue"
              />
              <span className="text-sm text-text">
                Include trade screenshots and notes
              </span>
            </label>
          </div>
        </div>

        {/* Actions */}
        <div className="flex justify-end space-x-3 mt-6">
          <button
            onClick={onClose}
            className="px-4 py-2 text-text hover:bg-surface1 rounded transition-colors"
            disabled={loading}
          >
            Cancel
          </button>
          <button
            onClick={handleGenerate}
            disabled={loading}
            className="px-4 py-2 bg-blue text-base hover:bg-blue/90 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? "Generating..." : "Generate Report"}
          </button>
        </div>
      </div>
    </div>
  );
}
