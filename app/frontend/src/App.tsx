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
import Login from './pages/Login/Login';
import Signup from './pages/Signup/Signup';
import './App.css';

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

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </Router>
  );
}

export default App;