import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout/Layout';
import Home from './pages/Home/Home';
import LegalResearch from './pages/LegalResearch/LegalResearch';
import CaseManagement from './pages/CaseManagement/CaseManagement';
import DocumentEditor from './pages/DocumentEditor/DocumentEditor';
import './App.css';

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/research/*" element={<LegalResearch />} />
          <Route path="/cases/*" element={<CaseManagement />} />
          <Route path="/docs/*" element={<DocumentEditor />} />
        </Routes>
      </Layout>
    </Router>
  );
}

export default App;