import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { MdPeople, MdWarning, MdHistory, MdShield } from 'react-icons/md';
import layoutStyles from './AdminDashboardLayout.module.css';

const cardStyle: React.CSSProperties = {
  background: '#fff',
  borderRadius: '12px',
  padding: '24px',
  boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
  display: 'flex',
  alignItems: 'center',
  gap: '20px',
};

const iconBoxStyle = (color: string): React.CSSProperties => ({
  width: 52,
  height: 52,
  borderRadius: '12px',
  background: color,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  flexShrink: 0,
});

export default function AdminDashboardHome() {
  const [staffCount, setStaffCount] = useState(0);
  const [logsCount, setLogsCount] = useState(0);

  useEffect(() => {
    axios.get('/api/admin/staff').then(r => setStaffCount(r.data.length)).catch(() => {});
    axios.get('/api/admin/system-logs').then(r => setLogsCount(r.data.length)).catch(() => {});
  }, []);

  const stats = [
    { label: 'Total Staff', value: staffCount, icon: <MdPeople size={26} color="#fff" />, color: '#6366f1', bg: 'rgba(99,102,241,0.1)' },
    { label: 'Audit Log Entries', value: logsCount, icon: <MdHistory size={26} color="#fff" />, color: '#0f766e', bg: 'rgba(15,118,110,0.1)' },
    { label: 'Active Role', value: 'Admin', icon: <MdShield size={26} color="#fff" />, color: '#d946ef', bg: 'rgba(217,70,239,0.1)' },
  ];

  return (
    <div>
      <div style={{ marginBottom: '32px' }}>
        <h2 style={{ fontSize: '1.5rem', fontWeight: 700, color: '#1e293b', margin: 0 }}>System Overview</h2>
        <p style={{ color: '#64748b', fontSize: '0.875rem', marginTop: '4px' }}>Real-time admin control panel summary</p>
      </div>

      <div className={layoutStyles.kpiGrid}>
        {stats.map((s, i) => (
          <div key={i} style={cardStyle}>
            <div style={iconBoxStyle(s.color)}>
              {s.icon}
            </div>
            <div>
              <div style={{ color: '#64748b', fontSize: '0.8rem', fontWeight: 500, marginBottom: '4px' }}>{s.label}</div>
              <div style={{ fontSize: '1.75rem', fontWeight: 800, color: '#1e293b' }}>{s.value}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Quick Links */}
      <div style={{ background: '#fff', borderRadius: '12px', padding: '24px', boxShadow: '0 1px 3px rgba(0,0,0,0.08)' }}>
        <h3 style={{ margin: '0 0 16px', fontSize: '1rem', fontWeight: 600, color: '#1e293b' }}>Quick Actions</h3>
        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
          <a href="#/superadmin/manage-staff" style={{ padding: '10px 20px', background: '#6366f1', color: '#fff', borderRadius: '8px', textDecoration: 'none', fontSize: '0.875rem', fontWeight: 600 }}>
            + Add Staff Member
          </a>
          <a href="#/superadmin/system-logs" style={{ padding: '10px 20px', background: '#f1f5f9', color: '#1e293b', borderRadius: '8px', textDecoration: 'none', fontSize: '0.875rem', fontWeight: 600 }}>
            View Audit Logs
          </a>
        </div>
      </div>

      <div style={{ marginTop: '24px', padding: '16px', background: '#fef9c3', borderRadius: '10px', border: '1px solid #fde68a', fontSize: '0.8rem', color: '#92400e' }}>
        <MdWarning size={16} style={{ verticalAlign: 'middle', marginRight: '6px' }} />
        As the system administrator, you have full control over staff accounts. Use this power responsibly.
      </div>
    </div>
  );
}
