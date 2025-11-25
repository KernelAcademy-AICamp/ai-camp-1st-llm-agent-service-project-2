import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import Layout from './components/Layout/Layout';
import Landing from './pages/Landing/Landing';
import Home from './pages/Home/Home';
import LegalResearch from './pages/LegalResearch/LegalResearch';
import CaseManagement from './pages/CaseManagement/CaseManagement';
import DocumentEditor from './pages/DocumentEditor/DocumentEditor';
import RecentPrecedents from './pages/RecentPrecedents/RecentPrecedents';
import Documents from './pages/Documents';
import DocumentDetail from './pages/DocumentDetail';
import Organizations from './pages/Organizations';
import Projects from './pages/Projects';
import RiskAnalysisDashboard from './pages/RiskAnalysisDashboard';
import Login from './pages/Login/Login';
import Signup from './pages/Signup/Signup';
import ModelComparison from './pages/ModelComparison/ModelComparison';
import './App.css';

// Analysis Landing Page Component
const AnalysisLanding: React.FC = () => (
  <div style={{ padding: '24px' }}>
    <h1>분석 도구</h1>
    <p>리스크 분석과 모델 비교 기능을 이용하실 수 있습니다.</p>
    <div style={{ display: 'flex', gap: '16px', marginTop: '24px' }}>
      <a href="/risk-dashboard" style={{
        padding: '16px 24px',
        backgroundColor: '#3b82f6',
        color: 'white',
        borderRadius: '8px',
        textDecoration: 'none',
        fontWeight: 500
      }}>
        리스크 대시보드
      </a>
      <a href="/analysis/model-comparison" style={{
        padding: '16px 24px',
        backgroundColor: '#10b981',
        color: 'white',
        borderRadius: '8px',
        textDecoration: 'none',
        fontWeight: 500
      }}>
        모델 비교
      </a>
    </div>
  </div>
);

function App() {
  return (
    <Router>
      <AuthProvider>
        <Routes>
          {/* Public routes */}
          <Route path="/" element={<Landing />} />
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
          <Route path="/app" element={
            <Layout>
              <Home />
            </Layout>
          } />

          {/* Feature routes - publicly accessible for demo */}
          <Route path="/research/cases" element={
            <Layout>
              <RecentPrecedents />
            </Layout>
          } />
          <Route path="/research/*" element={
            <Layout>
              <LegalResearch />
            </Layout>
          } />
          <Route path="/cases/*" element={
            <Layout>
              <CaseManagement />
            </Layout>
          } />
          <Route path="/docs/*" element={
            <Layout>
              <DocumentEditor />
            </Layout>
          } />
          <Route path="/documents" element={
            <Layout>
              <Documents />
            </Layout>
          } />
          <Route path="/documents/:documentId" element={
            <Layout>
              <DocumentDetail />
            </Layout>
          } />
          <Route path="/organizations" element={
            <Layout>
              <Organizations />
            </Layout>
          } />
          <Route path="/projects" element={
            <Layout>
              <Projects />
            </Layout>
          } />
          <Route path="/risk-dashboard" element={
            <Layout>
              <RiskAnalysisDashboard />
            </Layout>
          } />

          {/* Analysis routes */}
          <Route path="/analysis" element={
            <Layout>
              <AnalysisLanding />
            </Layout>
          } />
          <Route path="/analysis/model-comparison" element={
            <Layout>
              <ModelComparison />
            </Layout>
          } />

          {/* Legacy redirect: /settings/model-comparison -> /analysis/model-comparison */}
          <Route path="/settings/model-comparison" element={<Navigate to="/analysis/model-comparison" replace />} />

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </Router>
  );
}

export default App;