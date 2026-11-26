import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/Button';
import { Input } from '../components/Input';
import { useAuth } from '../context/AuthContext';
import styles from './Auth.module.css'; // Shared styles for Auth

export const Login: React.FC = () => {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { user } = useAuth(); // Need user state to check role after login

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      const loggedInUser = await login(email, password);
      
      if (loggedInUser.role === 'admin') {
        navigate('/superadmin/dashboard');
      } else if (loggedInUser.role === 'staff') {
        navigate('/staff/dashboard');
      } else {
        navigate('/dashboard');
      }
    } catch (err: any) {
      setError(err.message || 'Failed to login');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.card}>
        <h2 className={styles.title}>Welcome Back</h2>
        <p className={styles.subtitle}>Log in to continue your journey</p>

        <form onSubmit={handleSubmit}>
          <Input
            label="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="email@lspu.edu.ph"
            required
            fullWidth
          />
          <Input
            label="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Enter your password"
            required
            fullWidth
          />

          {error && <div className={styles.error}>{error}</div>}


          <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "0.5rem", marginBottom: "1rem" }}>
            <button
              type="button"
              onClick={() => navigate('/forgot-password')}
              style={{
                background: "none",
                border: "none",
                padding: "4px 2px",
                fontSize: "0.875rem",
                color: "#0f766e",
                cursor: "pointer",
                fontWeight: 500
              }}
            >
              Forgot Password?
            </button>
          </div>

          <Button type="submit" variant="primary" size="lg" isLoading={isLoading} className="w-full">
            Log In
          </Button>
        </form>

        <div className={styles.footer}>
          <p>Don't have an account? <span className={styles.link} onClick={() => navigate('/signup')}>Sign Up</span></p>
          <p className="mt-2"><span className={styles.link} onClick={() => navigate('/')}>Back to Home</span></p>
        </div>
      </div>
    </div>
  );
};
