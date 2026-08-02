import React, { useEffect, useState } from "react";
import axios from "axios";
import {
  PieChart, Pie, Cell, ResponsiveContainer, Tooltip, BarChart, Bar, XAxis, YAxis, Legend, CartesianGrid
} from "recharts";
import { MdDownload, MdWarningAmber } from "react-icons/md";
import styles from "./layout/AdminLayout.module.css";
import AlertsPanel from "./AlertsPanel";

export default function RiskMonitoring() {
  const [riskData, setRiskData] = useState<any[]>([]);
  const [trendData, setTrendData] = useState<any[]>([]);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [riskRes, trendRes, alertRes] = await Promise.all([
        axios.get("/api/admin/risk-analytics"),
        axios.get("/api/admin/risk-trends"),
        axios.get("/api/admin/alerts")
      ]);
      
      const rData = riskRes.data;
      setRiskData([
        { name: "Level 0 - Stable", count: rData.level_0 || 0, color: "#10b981" },
        { name: "Level 1 - Distressed", count: rData.level_1 || 0, color: "#facc15" },
        { name: "Level 2 - Soft Crisis", count: rData.level_2 || 0, color: "#f97316" },
        { name: "Level 3 - High Crisis", count: rData.level_3 || 0, color: "#ef4444" }
      ]);
      setTrendData(trendRes.data);
      setAlerts(alertRes.data);
    } catch (err) {
      console.error("Failed to fetch risk data", err);
    } finally {
      setLoading(false);
    }
  };

  const renderCustomizedLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent }: any) => {
    const RADIAN = Math.PI / 180;
    const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
    const x = cx + radius * Math.cos(-midAngle * RADIAN);
    const y = cy + radius * Math.sin(-midAngle * RADIAN);
  
    if (percent === 0) return null;
    return (
      <text x={x} y={y} fill="white" textAnchor="middle" dominantBaseline="central" fontSize={"12px"} fontWeight={"bold"}>
        {`${(percent * 100).toFixed(0)}%`}
      </text>
    );
  };

  const hasCriticalAlerts = alerts.some((a: any) => a.risk_level >= 2);

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem" }}>
        <h2 style={{ fontSize: "1.5rem", fontWeight: "bold", color: "#1e293b", margin: 0 }}>
          Risk Monitoring & Early Detection
        </h2>
        <div style={{ display: "flex", gap: "1rem" }}>
          <button className={styles.reviewBtn} style={{ display: "flex", alignItems: "center", gap: "0.5rem", height: '42px', backgroundColor: "#fff", border: '1px solid #e2e8f0' }} onClick={fetchData}>
            <FaSync className={loading ? "spin" : ""} /> Refresh
          </button>
          <button className={styles.reviewBtn} style={{ display: "flex", alignItems: "center", gap: "0.5rem", backgroundColor: "#ffedd5", color: "#ea580c" }}>
            <MdDownload /> Export Risk Log
          </button>
        </div>
      </div>

      {hasCriticalAlerts && (
        <div style={{ backgroundColor: "#fef2f2", color: "#991b1b", padding: "1rem 1.5rem", borderRadius: "0.5rem", marginBottom: "1.5rem", display: "flex", alignItems: "center", gap: "0.75rem", border: "1px solid #fecaca" }}>
          <MdWarningAmber size={24} color="#dc2626" />
          <div>
            <h4 style={{ margin: 0, fontWeight: "bold" }}>Critical Alert Activity Detected</h4>
            <p style={{ margin: 0, fontSize: "0.875rem", marginTop: "0.25rem" }}>AI has identified students with signs of severe distress. Deployment of counselor outreach recommended.</p>
          </div>
        </div>
      )}

      <div className={styles.chartsGrid} style={{ marginBottom: "2rem", display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
        <div className={styles.chartContainer} style={{ background: '#fff', padding: '1.5rem', borderRadius: '12px', boxShadow: '0 4px 6px rgba(0,0,0,0.05)' }}>
          <h3 className={styles.chartTitle} style={{ marginBottom: '1rem', color: '#64748b', fontSize: '0.9rem', fontWeight: '600' }}>RISK DISTRIBUTION (ENTIRE CAMPUS)</h3>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie
                data={riskData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={90}
                paddingAngle={5}
                dataKey="count"
                labelLine={false}
                label={renderCustomizedLabel}
              >
                {riskData.map((d, index) => (
                  <Cell key={`cell-${index}`} fill={d.color} />
                ))}
              </Pie>
              <Tooltip />
              <Legend verticalAlign="bottom" height={36}/>
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className={styles.chartContainer} style={{ background: '#fff', padding: '1.5rem', borderRadius: '12px', boxShadow: '0 4px 6px rgba(0,0,0,0.05)' }}>
          <h3 className={styles.chartTitle} style={{ marginBottom: '1rem', color: '#64748b', fontSize: '0.9rem', fontWeight: '600' }}>ESCALATION TRENDS (LAST 30 DAYS)</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={trendData}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="level_2" name="Soft Crisis (L2)" stackId="a" fill="#f97316" />
              <Bar dataKey="level_3" name="High Crisis (L3)" stackId="a" fill="#ef4444" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <AlertsPanel alerts={alerts} />
    </div>
  );
}

// Add FaSync import at the top
import { FaSync } from "react-icons/fa";

