import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { apiClient } from '../api/client';
import {
  Project,
  Organization,
  CreateProjectRequest,
  UpdateProjectRequest
} from '../types';
import './Projects.css';

const Projects: React.FC = () => {
  const { token } = useAuth();
  const [projects, setProjects] = useState<Project[]>([]);
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [selectedOrgFilter, setSelectedOrgFilter] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [formData, setFormData] = useState({
    organization: '',
    name: '',
    description: ''
  });
  const [creating, setCreating] = useState(false);
  const [updating, setUpdating] = useState(false);

  useEffect(() => {
    loadOrganizations();
  }, [token]);

  useEffect(() => {
    loadProjects();
  }, [selectedOrgFilter, token]);

  const loadOrganizations = async () => {
    try {
      const response = await apiClient.getOrganizations(token || undefined);
      setOrganizations(response.results);
    } catch (err: any) {
      console.error('Load organizations error:', err);
    }
  };

  const loadProjects = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiClient.getProjects(
        selectedOrgFilter || undefined,
        token || undefined
      );
      setProjects(response.results);
    } catch (err: any) {
      setError(err.message || 'Failed to load projects');
      console.error('Load projects error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateProject = async () => {
    if (!formData.name.trim() || !formData.organization) {
      setError('Project name and organization are required');
      return;
    }

    try {
      setCreating(true);
      setError(null);
      const data: CreateProjectRequest = {
        organization: formData.organization,
        name: formData.name.trim(),
        description: formData.description.trim()
      };
      await apiClient.createProject(data, token || undefined);
      setShowCreateModal(false);
      setFormData({ organization: '', name: '', description: '' });
      await loadProjects();
    } catch (err: any) {
      setError(err.message || 'Failed to create project');
      console.error('Create project error:', err);
    } finally {
      setCreating(false);
    }
  };

  const handleUpdateProject = async () => {
    if (!selectedProject || !formData.name.trim()) {
      setError('Project name is required');
      return;
    }

    try {
      setUpdating(true);
      setError(null);
      const data: UpdateProjectRequest = {
        name: formData.name.trim(),
        description: formData.description.trim()
      };
      await apiClient.updateProject(selectedProject.id, data, token || undefined);
      setShowEditModal(false);
      setFormData({ organization: '', name: '', description: '' });
      setSelectedProject(null);
      await loadProjects();
    } catch (err: any) {
      setError(err.message || 'Failed to update project');
      console.error('Update project error:', err);
    } finally {
      setUpdating(false);
    }
  };

  const handleDeleteProject = async (projectId: string, projectName: string) => {
    if (!window.confirm(`Are you sure you want to delete project "${projectName}"? This action cannot be undone.`)) {
      return;
    }

    try {
      setError(null);
      await apiClient.deleteProject(projectId, token || undefined);
      setProjects(projects.filter(proj => proj.id !== projectId));
      if (selectedProject?.id === projectId) {
        setSelectedProject(null);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to delete project');
      console.error('Delete project error:', err);
    }
  };

  const openEditModal = (project: Project) => {
    setSelectedProject(project);
    setFormData({
      organization: project.organization,
      name: project.name,
      description: project.description
    });
    setShowEditModal(true);
  };

  const openCreateModal = () => {
    setFormData({
      organization: selectedOrgFilter || (organizations[0]?.id || ''),
      name: '',
      description: ''
    });
    setShowCreateModal(true);
  };

  if (loading) {
    return (
      <div className="projects-container">
        <div className="loading">프로젝트 목록을 불러오는 중...</div>
      </div>
    );
  }

  return (
    <div className="projects-container">
      <div className="projects-header">
        <h1>프로젝트 관리</h1>
        <button
          className="btn-primary"
          onClick={openCreateModal}
          disabled={organizations.length === 0}
        >
          프로젝트 생성
        </button>
      </div>

      {organizations.length === 0 && (
        <div className="warning-message">
          프로젝트를 생성하려면 먼저 조직을 만들어야 합니다.
        </div>
      )}

      {error && (
        <div className="error-message">
          {error}
          <button onClick={() => setError(null)} className="close-btn">×</button>
        </div>
      )}

      <div className="projects-filters">
        <label htmlFor="orgFilter">조직별 필터:</label>
        <select
          id="orgFilter"
          value={selectedOrgFilter}
          onChange={(e) => setSelectedOrgFilter(e.target.value)}
        >
          <option value="">모든 조직</option>
          {organizations.map(org => (
            <option key={org.id} value={org.id}>
              {org.name}
            </option>
          ))}
        </select>
      </div>

      <div className="projects-grid">
        {projects.length === 0 ? (
          <div className="empty-state">
            <p>프로젝트가 없습니다. 새 프로젝트를 생성해 주세요!</p>
          </div>
        ) : (
          projects.map(project => (
            <div key={project.id} className="project-card">
              <div className="project-card-header">
                <h3>{project.name}</h3>
                <span className="org-badge">{project.organization_name}</span>
              </div>
              <div className="project-card-body">
                <p className="project-description">
                  {project.description || '설명 없음'}
                </p>
                <div className="project-stats">
                  <div className="stat">
                    <span className="stat-label">문서</span>
                    <span className="stat-value">{project.document_count}</span>
                  </div>
                  <div className="stat">
                    <span className="stat-label">케이스</span>
                    <span className="stat-value">{project.case_count}</span>
                  </div>
                </div>
              </div>
              <div className="project-card-footer">
                <span className="project-date">
                  생성일: {new Date(project.created_at).toLocaleDateString()}
                </span>
                <div className="project-actions">
                  <button
                    className="btn-secondary-small"
                    onClick={() => openEditModal(project)}
                  >
                    수정
                  </button>
                  <button
                    className="btn-danger-small"
                    onClick={() => handleDeleteProject(project.id, project.name)}
                  >
                    삭제
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {showCreateModal && (
        <div className="modal-overlay">
          <div className="modal">
            <div className="modal-header">
              <h2>프로젝트 생성</h2>
              <button
                className="close-btn"
                onClick={() => {
                  setShowCreateModal(false);
                  setFormData({ organization: '', name: '', description: '' });
                  setError(null);
                }}
              >
                ×
              </button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label htmlFor="projectOrg">조직 *</label>
                <select
                  id="projectOrg"
                  value={formData.organization}
                  onChange={(e) => setFormData({ ...formData, organization: e.target.value })}
                >
                  <option value="">조직을 선택하세요</option>
                  {organizations.map(org => (
                    <option key={org.id} value={org.id}>
                      {org.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label htmlFor="projectName">프로젝트 이름 *</label>
                <input
                  id="projectName"
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="프로젝트 이름을 입력하세요"
                />
              </div>
              <div className="form-group">
                <label htmlFor="projectDesc">설명</label>
                <textarea
                  id="projectDesc"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="프로젝트 설명을 입력하세요 (선택)"
                  rows={4}
                />
              </div>
            </div>
            <div className="modal-footer">
              <button
                className="btn-secondary"
                onClick={() => {
                  setShowCreateModal(false);
                  setFormData({ organization: '', name: '', description: '' });
                  setError(null);
                }}
                disabled={creating}
              >
                취소
              </button>
              <button
                className="btn-primary"
                onClick={handleCreateProject}
                disabled={creating || !formData.name.trim() || !formData.organization}
              >
                {creating ? '생성 중...' : '생성'}
              </button>
            </div>
          </div>
        </div>
      )}

      {showEditModal && selectedProject && (
        <div className="modal-overlay">
          <div className="modal">
            <div className="modal-header">
              <h2>프로젝트 수정</h2>
              <button
                className="close-btn"
                onClick={() => {
                  setShowEditModal(false);
                  setFormData({ organization: '', name: '', description: '' });
                  setSelectedProject(null);
                  setError(null);
                }}
              >
                ×
              </button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label>조직</label>
                <input
                  type="text"
                  value={selectedProject.organization_name}
                  disabled
                  className="disabled-input"
                />
              </div>
              <div className="form-group">
                <label htmlFor="editProjectName">프로젝트 이름 *</label>
                <input
                  id="editProjectName"
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="프로젝트 이름을 입력하세요"
                />
              </div>
              <div className="form-group">
                <label htmlFor="editProjectDesc">설명</label>
                <textarea
                  id="editProjectDesc"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="프로젝트 설명을 입력하세요 (선택)"
                  rows={4}
                />
              </div>
            </div>
            <div className="modal-footer">
              <button
                className="btn-secondary"
                onClick={() => {
                  setShowEditModal(false);
                  setFormData({ organization: '', name: '', description: '' });
                  setSelectedProject(null);
                  setError(null);
                }}
                disabled={updating}
              >
                취소
              </button>
              <button
                className="btn-primary"
                onClick={handleUpdateProject}
                disabled={updating || !formData.name.trim()}
              >
                {updating ? '수정 중...' : '수정'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Projects;
