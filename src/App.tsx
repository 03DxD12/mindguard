import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';
import { Layout } from './components/Layout';
import { ProtectedRoute } from './components/ProtectedRoute';
import { StaffRoute } from './components/StaffRoute';
import { SuperAdminRoute } from './components/SuperAdminRoute';

// Student Pages
import { Landing } from './pages/Landing';
import { Login } from './pages/Login';
import { Signup } from './pages/Signup';
import { ForgotPassword } from './pages/ForgotPassword';
import { Dashboard } from './pages/Dashboard';
import { Chat } from './pages/Chat';
import { Wellness } from './pages/Wellness';
import { Profile } from './pages/Profile';
import { Groups } from './pages/Groups';
import { Booking } from './pages/Booking';
import { Journal } from './pages/Journal';
import { ResourceLibrary } from './pages/ResourceLibrary';
import { Emergency } from './pages/Emergency';
import { Affirmations } from './pages/Affirmations';

// Staff Dashboard (renamed from Admin)
import { AdminLayout as StaffLayout } from './pages/admin/layout/AdminLayout';
import AdminHome from './pages/admin/AdminHome';
import MoodAnalytics from './pages/admin/MoodAnalytics';
import RiskMonitoring from './pages/admin/RiskMonitoring';
import StudentOverview from './pages/admin/StudentOverview';

import Reports from './pages/admin/Reports';

// Admin (Super Admin) Dashboard
import { AdminDashboardLayout } from './pages/superadmin/AdminDashboardLayout';
import AdminDashboardHome from './pages/superadmin/AdminDashboardHome';
import ManageStaff from './pages/superadmin/ManageStaff';
import SystemLogs from './pages/superadmin/SystemLogs';

const MobileLayout = () => (
  <div className="app-container">
    <Outlet />
  </div>
);

function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <Router basename="/mindguard">
          <Routes>
            {/* Student and Public Routes - wrapped in mobile container */}
            <Route element={<MobileLayout />}>
              <Route path="/" element={<Landing />} />
              <Route path="/login" element={<Login />} />
              <Route path="/signup" element={<Signup />} />
              <Route path="/forgot-password" element={<ForgotPassword />} />

              <Route path="/dashboard" element={<ProtectedRoute><Layout><Dashboard /></Layout></ProtectedRoute>} />
              <Route path="/chat" element={<ProtectedRoute><Layout><Chat /></Layout></ProtectedRoute>} />
              <Route path="/wellness" element={<ProtectedRoute><Layout><Wellness /></Layout></ProtectedRoute>} />
              <Route path="/groups" element={<ProtectedRoute><Layout><Groups /></Layout></ProtectedRoute>} />
              <Route path="/journal" element={<ProtectedRoute><Layout><Journal /></Layout></ProtectedRoute>} />
              <Route path="/booking" element={<ProtectedRoute><Layout><Booking /></Layout></ProtectedRoute>} />
              <Route path="/profile" element={<ProtectedRoute><Layout><Profile /></Layout></ProtectedRoute>} />
              <Route path="/resources" element={<ProtectedRoute><Layout><ResourceLibrary /></Layout></ProtectedRoute>} />
              <Route path="/emergency" element={<ProtectedRoute><Layout><Emergency /></Layout></ProtectedRoute>} />
              <Route path="/affirmations" element={<ProtectedRoute><Layout><Affirmations /></Layout></ProtectedRoute>} />
            </Route>

              {/* Staff Dashboard (staff and admin can both view) */}
              <Route path="/staff" element={<StaffRoute><StaffLayout /></StaffRoute>}>
                <Route index element={<Navigate to="dashboard" replace />} />
                <Route path="dashboard" element={<AdminHome />} />
                <Route path="mood-analytics" element={<MoodAnalytics />} />
                <Route path="risk-monitoring" element={<RiskMonitoring />} />
                <Route path="student-overview" element={<StudentOverview />} />
                <Route path="reports" element={<Reports />} />
              </Route>

              {/* Admin (Super Admin) Dashboard — admin only */}
              <Route path="/superadmin" element={<SuperAdminRoute><AdminDashboardLayout /></SuperAdminRoute>}>
                <Route index element={<Navigate to="dashboard" replace />} />
                <Route path="dashboard" element={<AdminDashboardHome />} />
                <Route path="manage-staff" element={<ManageStaff />} />
                <Route path="system-logs" element={<SystemLogs />} />
              </Route>

              {/* Legacy /admin redirect to /staff */}
              <Route path="/admin/*" element={<Navigate to="/staff" replace />} />

              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
        </Router>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;
