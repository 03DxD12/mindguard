import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './styles/global.css';
import { initDemoInterceptors } from './services/demoFallback';

// Initialize portfolio demo fallback for GitHub Pages
initDemoInterceptors();

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
