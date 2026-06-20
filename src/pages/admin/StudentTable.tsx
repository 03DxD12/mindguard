import React, { useEffect, useState } from "react";
import axios from "axios";
import { format } from "date-fns";
import styles from "./layout/AdminLayout.module.css";

// Helper for colored risk badges

interface Student {
  session_id: string;
  user_id: number;
  user_email: string;
  student_id: string;
  fullname: string;
  latest_mood: string;
  highest_risk_level: number;
  alert: boolean;
  action: string;
  last_interaction: string;
  total_sessions: number;
  total_turns: number;
}

function RiskBadge({ level }: { level: number }) {
  const colors: Record<number, string> = {
    0: styles["bg-green"],
    1: styles["bg-yellow"],
    2: styles["bg-orange"],
    3: styles["bg-red"]
  };

  return (
    <span className={`${styles.badge} ${colors[level] || styles["bg-green"]}`}>
      Level {level}
    </span>
  );
}

export default function StudentTable() {
  const [students, setStudents] = useState<Student[]>([]);
  const [search, setSearch] = useState("");
  const [riskFilter, setRiskFilter] = useState("all");
  const [sortOrder, setSortOrder] = useState("desc");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStudents();
    const interval = setInterval(fetchStudents, 15000);
    return () => clearInterval(interval);
  }, []);

  const fetchStudents = async () => {
    try {
      const res = await axios.get("/api/admin/students");
      setStudents(res.data);
      setLoading(false);
    } catch (err) {
      console.error("Failed to fetch students", err);
      setLoading(false);
    }
  };

  const filteredStudents = students
    .filter(student =>
      (student.session_id || "").toLowerCase().includes(search.toLowerCase()) ||
      (student.fullname || "").toLowerCase().includes(search.toLowerCase()) ||
      (student.student_id || "").toLowerCase().includes(search.toLowerCase())
    )
    .filter(student =>
      riskFilter === "all" ? true : student.highest_risk_level === Number(riskFilter)
    )
    .sort((a, b) =>
      sortOrder === "desc"
        ? (b.highest_risk_level || 0) - (a.highest_risk_level || 0)
        : (a.highest_risk_level || 0) - (b.highest_risk_level || 0)
    );

  return (
    <div className={styles.tableContainer}>
      <h3 className={styles.chartTitle}>Student Risk Overview</h3>

      <div className={styles.tableFilters}>
        <input
          type="text"
          placeholder="Search by Session ID, Name, or Student ID..."
          className={styles.filterInput}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ flex: 1 }}
        />

        <select
          className={styles.filterSelect}
          value={riskFilter}
          onChange={(e) => setRiskFilter(e.target.value)}
        >
          <option value="all">All Risk Levels</option>
          <option value="0">Level 0 (Stable)</option>
          <option value="1">Level 1 (Distress)</option>
          <option value="2">Level 2 (Soft Crisis)</option>
          <option value="3">Level 3 (High Crisis)</option>
        </select>

        <select
          className={styles.filterSelect}
          value={sortOrder}
          onChange={(e) => setSortOrder(e.target.value)}
        >
          <option value="desc">Highest Risk First</option>
          <option value="asc">Lowest Risk First</option>
        </select>
      </div>

      <div className={styles.studentTableWrapper}>
        <table className={styles.studentTable}>
          <thead>
            <tr>
              <th>Session ID</th>
              <th>Full Name</th>
              <th>Student ID</th>
              <th>Latest Mood</th>
              <th>Risk Level</th>
              <th>Crisis Alert</th>
              <th>Action Taken</th>
              <th>Last Interaction</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={8} style={{ textAlign: "center", padding: "2rem" }}>Loading student data...</td></tr>
            ) : filteredStudents.length === 0 ? (
              <tr><td colSpan={8} style={{ textAlign: "center", padding: "2rem" }}>No matching records found.</td></tr>
            ) : (
              filteredStudents.map((student) => {
                let formattedDate = student.last_interaction;
                try {
                   formattedDate = format(new Date(student.last_interaction), "MMM d, yyyy h:mm a");
                } catch(e) {}

                return (
                  <tr key={student.session_id}>
                    <td style={{ fontWeight: 500, fontFamily: "monospace", fontSize: "0.8rem", color: "#64748b" }}>
                      {student.session_id.substring(0, 8)}...
                    </td>
                    <td style={{ fontWeight: 600, color: "#1e293b" }}>{student.fullname !== "N/A" ? student.fullname : "Anonymous"}</td>
                    <td style={{ fontWeight: 500, color: "#475569" }}>{student.student_id !== "N/A" ? student.student_id : "—"}</td>
                    <td>{student.latest_mood || "—"}</td>
                    <td>
                      <RiskBadge level={student.highest_risk_level || 0} />
                    </td>
                    <td style={{ color: student.alert ? "#ef4444" : "#10b981", fontWeight: student.alert ? "bold" : "normal" }}>
                      {student.alert ? "Triggered" : "No"}
                    </td>
                    <td style={{ color: "#64748b" }}>{student.action || "None"}</td>
                    <td style={{ color: "#94a3b8", fontSize: "0.8rem" }}>{formattedDate}</td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Mobile Card View */}
      <div className={styles.mobileCardList}>
        {loading ? (
          <div style={{ textAlign: "center", padding: "2rem" }}>Loading student data...</div>
        ) : filteredStudents.length === 0 ? (
          <div style={{ textAlign: "center", padding: "2rem" }}>No matching records found.</div>
        ) : (
          filteredStudents.map((student) => {
            let formattedDate = student.last_interaction;
            try {
               formattedDate = format(new Date(student.last_interaction), "MMM d, h:mm a");
            } catch(e) {}

            return (
              <div key={student.session_id} className={styles.mobileStudentCard}>
                <div className={styles.mobileCardHeader}>
                  <span className={styles.mobileCardId}>{student.fullname !== 'N/A' ? student.fullname : student.session_id.substring(0, 8)}</span>
                  <RiskBadge level={student.highest_risk_level || 0} />
                </div>
                <div className={styles.mobileCardRow}>
                  <span><strong>ID:</strong> {student.student_id !== 'N/A' ? student.student_id : '—'}</span>
                </div>
                <div className={styles.mobileCardRow}>
                  <span><strong>Mood:</strong> {student.latest_mood || "—"}</span>
                  <span style={{ color: student.alert ? "#ef4444" : "#10b981", fontWeight: student.alert ? "bold" : "normal" }}>
                    {student.alert ? "Alert Active" : "No Alert"}
                  </span>
                </div>
                <div className={styles.mobileCardRow}>
                  <span><strong>Action:</strong> {student.action || "None"}</span>
                  <span style={{ fontSize: "0.75rem" }}>{formattedDate}</span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
