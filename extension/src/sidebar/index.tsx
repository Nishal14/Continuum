/**
 * Entry point for Continuum sidebar popup
 */

import React from 'react';
import { createRoot } from 'react-dom/client';
import Sidebar from './Sidebar';

// Render the Sidebar component
const container = document.getElementById('root');
if (container) {
  const root = createRoot(container);
  root.render(
    <React.StrictMode>
      <Sidebar />
    </React.StrictMode>
  );
}
