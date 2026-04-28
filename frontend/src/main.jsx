/**
 * main.jsx — React entry point
 */
import 'leaflet/dist/leaflet.css';
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'

try {
  console.log('[Main] Initializing React app...');
  const rootElement = document.getElementById('root');
  if (!rootElement) {
    throw new Error('Root element not found! Check index.html');
  }

  ReactDOM.createRoot(rootElement).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>,
  );
  console.log('[Main] React app rendered successfully');
} catch (error) {
  console.error('[Main] Critical Render Error:', error);
  document.body.innerHTML = `<div style="padding: 20px; color: red; font-family: sans-serif;">
    <h1>Critical Render Error</h1>
    <pre>${error.stack}</pre>
  </div>`;
}
