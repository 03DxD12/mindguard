import React, { useEffect, useState } from "react";
import axios from "axios";
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, CartesianGrid, Legend
} from "recharts";
import styles from "./layout/AdminLayout.module.css";
import { MdDownload, MdInfoOutline } from "react-icons/md";
import { FaSync } from "react-icons/fa";

const COLORS: Record<string, string> = {
  Happy: "#10b981",
  Great: "#10b981",
  Okay: "#3b82f6",
  Good: "#3b82f6",
  Stressed: "#facc15",
  Sad: "#f97316",
  Down: "#f97316",
  Crisis: "#ef4444"
};

export default function MoodAnalytics() {
  const [moodData, setMoodData] = useState<any[]>([]);
  const [totalEntries, setTotalEntries] = useState(0);
  const [negativeMoodPercentage, setNegativeMoodPercentage] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchMoodData();
  }, []);

  const fetchMoodData = async () => {
    setLoading(true);
    try {
      const res = await axios.get("/api/admin/mood-analytics");
      const data = res.data;
      
      const chartArr = Object.keys(data).map(key => ({
        name: key,
        count: data[key],
        color: COLORS[key] || "#cbd5e1"
      }));
      
      const predefinedOrder = ["Great", "Good", "Happy", "Okay", "Stressed", "Sad", "Down", "Crisis"];
      chartArr.sort((a, b) => predefinedOrder.indexOf(a.name) - predefinedOrder.indexOf(b.name));
      setMoodData(chartArr);

      const total = chartArr.reduce((sum, item) => sum + item.count, 0);
      const negativeTotal = chartArr.filter(i => ['Sad', 'Down', 'Crisis'].includes(i.name)).reduce((sum, item) => sum + item.count, 0);
      
      setTotalEntries(total);
      if (total > 0) {
        setNegativeMoodPercentage(Math.round((negativeTotal / total) * 100));
      }
    } catch (err) {
      console.error("Failed to fetch mood data", err);
    } finally {
      setLoading(false);
    }
  };

  const trendData = [
    { date: 'Mon', score: 3.2 },
    { date: 'Tue', score: 3.4 },
    { date: 'Wed', score: 3.1 },
    { date: 'Thu', score: 2.8 },
    { date: 'Fri', score: 2.9 },
    { date: 'Sat', score: 3.8 },
    { date: 'Sun', score: 4.1 },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem" }}>
        <h2 style={{ fontSize: "1.5rem", fontWeight: "bold", color: "#1e293b", margin: 0 }}>
          Population Well-being Metrics
        </h2>
        <div style={{ display: "flex", gap: "1rem" }}>
          <button className={styles.reviewBtn} style={{ display: "flex", alignItems: "center", gap: "0.5rem", height: '42px', backgroundColor: "#fff", border: '1px solid #e2e8f0' }} onClick={fetchMoodData}>
            <FaSync className={loading ? "spin" : ""} /> Refresh
          </button>
          <button className={styles.reviewBtn} style={{ display: "flex", alignItems: "center", gap: "0.5rem", backgroundColor: "#e0f2fe", color: "#0284c7" }}>
            <MdDownload /> Export Analytics
          </button>
        </div>
      </div>

      {negativeMoodPercentage > 25 && (
        <div style={{ backgroundColor: "#fffbeb", color: "#b45309", padding: "1rem 1.5rem", borderRadius: "0.5rem", marginBottom: "1.5rem", display: "flex", alignItems: "center", gap: "0.75rem", border: "1px solid #fde68a" }}>
          <MdInfoOutline size={24} color="#d97706" />
          <div>
            <h4 style={{ margin: 0, fontWeight: "bold" }}>Increased Distress Detected</h4>
            <p style={{ margin: 0, fontSize: "0.875rem", marginTop: "0.25rem" }}>{negativeMoodPercentage}% of recorded student statuses reflect distress or crisis states. Recommend proactive interventions.</p>
          </div>
        </div>
      )}

      <div className={styles.summaryGrid} style={{ marginBottom: "1.5rem", display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem' }}>
        <div className={styles.card} style={{ background: '#fff', padding: '1.2rem', borderRadius: '12px', border: '1px solid #f1f5f9' }}>
          <p style={{ color: '#64748b', fontSize: '0.85rem', margin: '0 0 0.5rem 0' }}>Active Population</p>
          <h4 style={{ fontSize: '1.5rem', margin: 0 }}>{totalEntries}</h4>
        </div>
        <div className={styles.card} style={{ background: '#fff', padding: '1.2rem', borderRadius: '12px', border: '1px solid #f1f5f9' }}>
          <p style={{ color: '#64748b', fontSize: '0.85rem', margin: '0 0 0.5rem 0' }}>Most Common State</p>
          <h4 style={{ fontSize: '1.5rem', margin: 0, color: COLORS[moodData[0]?.name] || '#000' }}>{moodData[0]?.name || 'N/A'}</h4>
        </div>
        <div className={styles.card} style={{ background: '#fff', padding: '1.2rem', borderRadius: '12px', border: '1px solid #f1f5f9' }}>
          <p style={{ color: '#64748b', fontSize: '0.85rem', margin: '0 0 0.5rem 0' }}>Distress Ratio</p>
          <h4 style={{ fontSize: '1.5rem', margin: 0, color: negativeMoodPercentage > 30 ? '#ef4444' : '#f59e0b' }}>{negativeMoodPercentage}%</h4>
        </div>
        <div className={styles.card} style={{ background: '#fff', padding: '1.2rem', borderRadius: '12px', border: '1px solid #f1f5f9' }}>
          <p style={{ color: '#64748b', fontSize: '0.85rem', margin: '0 0 0.5rem 0' }}>Improvement Rate</p>
          <h4 style={{ fontSize: '1.5rem', margin: 0, color: '#10b981' }}>+8.4%</h4>
        </div>
      </div>

      <div className={styles.chartsGrid} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
        <div className={styles.chartContainer} style={{ background: '#fff', padding: '1.5rem', borderRadius: '12px', boxShadow: '0 4px 6px rgba(0,0,0,0.05)' }}>
          <h3 style={{ marginBottom: '1rem', color: '#64748b', fontSize: '0.9rem', fontWeight: '600' }}>CAMPUS MOOD DISTRIBUTION</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={moodData}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="count" name="Entries">
                {moodData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className={styles.chartContainer} style={{ background: '#fff', padding: '1.5rem', borderRadius: '12px', boxShadow: '0 4px 6px rgba(0,0,0,0.05)' }}>
          <h3 style={{ marginBottom: '1rem', color: '#64748b', fontSize: '0.9rem', fontWeight: '600' }}>7-DAY AGGREGATE WELL-BEING SCORE</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={trendData}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
              <XAxis dataKey="date" />
              <YAxis domain={[0, 5]} />
              <Tooltip />
              <Line type="monotone" dataKey="score" stroke="#0f766e" strokeWidth={3} dot={{ r: 4, fill: "#0f766e" }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}

