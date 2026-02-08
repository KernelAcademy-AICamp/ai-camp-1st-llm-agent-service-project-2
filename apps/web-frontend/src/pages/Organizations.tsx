import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { apiClient } from '../api/client';
import {
  Organization,
  OrganizationDetail,
  CreateOrganizationRequest
} from '../types';
import MemberManagement from '../components/MemberManagement';
import './Organizations.css';

const Organizations: React.FC = () => {
  const { token } = useAuth();
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [selectedOrg, setSelectedOrg] = useState<OrganizationDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [newOrgName, setNewOrgName] = useState('');
  const [editOrgName, setEditOrgName] = useState('');
  const [creating, setCreating] = useState(false);
  const [updating, setUpdating] = useState(false);

  useEffect(() => {
    loadOrganizations();
  }, [token]);

  const loadOrganizations = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiClient.getOrganizations(token || undefined);
      setOrganizations(response.results);
    } catch (err: any) {
      setError(err.message || 'Failed to load organizations');
      console.error('Load organizations error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectOrganization = async (orgId: string) => {
    try {
      setError(null);
      const detail = await apiClient.getOrganization(orgId, token || undefined);
      setSelectedOrg(detail);
    } catch (err: any) {
      setError(err.message || 'Failed to load organization details');
      console.error('Load organization detail error:', err);
    }
  };

  const handleCreateOrganization = async () => {
    if (!newOrgName.trim()) {
      setError('Organization name is required');
      return;
    }

    try {
      setCreating(true);
      setError(null);
      const data: CreateOrganizationRequest = {
        name: newOrgName.trim(),
        settings: {}
      };
      const newOrg = await apiClient.createOrganization(data, token || undefined);
      setOrganizations([...organizations, newOrg]);
      setShowCreateModal(false);
      setNewOrgName('');
      setSelectedOrg(null);
      await loadOrganizations();
    } catch (err: any) {
      setError(err.message || 'Failed to create organization');
      console.error('Create organization error:', err);
    } finally {
      setCreating(false);
    }
  };

  const handleUpdateOrganization = async () => {
    if (!selectedOrg || !editOrgName.trim()) {
      setError('Organization name is required');
      return;
    }

    try {
      setUpdating(true);
      setError(null);
      const updated = await apiClient.updateOrganization(
        selectedOrg.id,
        { name: editOrgName.trim() },
        token || undefined
      );
      setOrganizations(organizations.map(org =>
        org.id === updated.id ? updated : org
      ));
      setSelectedOrg({ ...selectedOrg, name: updated.name });
      setShowEditModal(false);
      setEditOrgName('');
    } catch (err: any) {
      setError(err.message || 'Failed to update organization');
      console.error('Update organization error:', err);
    } finally {
      setUpdating(false);
    }
  };

  const handleDeleteOrganization = async (orgId: string) => {
    if (!window.confirm('Are you sure you want to delete this organization? This action cannot be undone.')) {
      return;
    }

    try {
      setError(null);
      await apiClient.deleteOrganization(orgId, token || undefined);
      setOrganizations(organizations.filter(org => org.id !== orgId));
      if (selectedOrg?.id === orgId) {
        setSelectedOrg(null);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to delete organization');
      console.error('Delete organization error:', err);
    }
  };

  const openEditModal = () => {
    if (selectedOrg) {
      setEditOrgName(selectedOrg.name);
      setShowEditModal(true);
    }
  };

  if (loading) {
    return (
      <div className="organizations-container">
        <div className="loading">조직 목록을 불러오는 중...</div>
      </div>
    );
  }

  return (
    <div className="organizations-container">
      <div className="organizations-header">
        <h1>조직 관리</h1>
        <button
          className="btn-primary"
          onClick={() => setShowCreateModal(true)}
        >
          조직 생성
        </button>
      </div>

      {error && (
        <div className="error-message">
          {error}
          <button onClick={() => setError(null)} className="close-btn">×</button>
        </div>
      )}

      <div className="organizations-content">
        <div className="organizations-list">
          <h2>내 조직 ({organizations.length})</h2>
          {organizations.length === 0 ? (
            <div className="empty-state">
              <p>조직이 없습니다. 새 조직을 생성해 주세요!</p>
            </div>
          ) : (
            <div className="org-cards">
              {organizations.map(org => (
                <div
                  key={org.id}
                  className={`org-card ${selectedOrg?.id === org.id ? 'active' : ''}`}
                  onClick={() => handleSelectOrganization(org.id)}
                >
                  <div className="org-card-header">
                    <h3>{org.name}</h3>
                    <span className="member-count">{org.member_count}명</span>
                  </div>
                  <div className="org-card-footer">
                    <span className="org-date">
                      생성일: {new Date(org.created_at).toLocaleDateString()}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {selectedOrg && (
          <div className="organization-detail">
            <div className="detail-header">
              <h2>{selectedOrg.name}</h2>
              <div className="detail-actions">
                <button
                  className="btn-secondary"
                  onClick={openEditModal}
                >
                  수정
                </button>
                <button
                  className="btn-danger"
                  onClick={() => handleDeleteOrganization(selectedOrg.id)}
                >
                  삭제
                </button>
              </div>
            </div>

            <div className="detail-info">
              <div className="info-item">
                <label>멤버:</label>
                <span>{selectedOrg.member_count}명</span>
              </div>
              <div className="info-item">
                <label>생성일:</label>
                <span>{new Date(selectedOrg.created_at).toLocaleString()}</span>
              </div>
            </div>

            <MemberManagement
              organizationId={selectedOrg.id}
              onMembersChange={() => handleSelectOrganization(selectedOrg.id)}
            />
          </div>
        )}
      </div>

      {showCreateModal && (
        <div className="modal-overlay">
          <div className="modal">
            <div className="modal-header">
              <h2>조직 생성</h2>
              <button
                className="close-btn"
                onClick={() => {
                  setShowCreateModal(false);
                  setNewOrgName('');
                  setError(null);
                }}
              >
                ×
              </button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label htmlFor="orgName">조직 이름 *</label>
                <input
                  id="orgName"
                  type="text"
                  value={newOrgName}
                  onChange={(e) => setNewOrgName(e.target.value)}
                  placeholder="조직 이름을 입력하세요"
                  autoFocus
                />
              </div>
            </div>
            <div className="modal-footer">
              <button
                className="btn-secondary"
                onClick={() => {
                  setShowCreateModal(false);
                  setNewOrgName('');
                  setError(null);
                }}
                disabled={creating}
              >
                취소
              </button>
              <button
                className="btn-primary"
                onClick={handleCreateOrganization}
                disabled={creating || !newOrgName.trim()}
              >
                {creating ? '생성 중...' : '생성'}
              </button>
            </div>
          </div>
        </div>
      )}

      {showEditModal && selectedOrg && (
        <div className="modal-overlay">
          <div className="modal">
            <div className="modal-header">
              <h2>조직 수정</h2>
              <button
                className="close-btn"
                onClick={() => {
                  setShowEditModal(false);
                  setEditOrgName('');
                  setError(null);
                }}
              >
                ×
              </button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label htmlFor="editOrgName">조직 이름 *</label>
                <input
                  id="editOrgName"
                  type="text"
                  value={editOrgName}
                  onChange={(e) => setEditOrgName(e.target.value)}
                  placeholder="조직 이름을 입력하세요"
                  autoFocus
                />
              </div>
            </div>
            <div className="modal-footer">
              <button
                className="btn-secondary"
                onClick={() => {
                  setShowEditModal(false);
                  setEditOrgName('');
                  setError(null);
                }}
                disabled={updating}
              >
                취소
              </button>
              <button
                className="btn-primary"
                onClick={handleUpdateOrganization}
                disabled={updating || !editOrgName.trim()}
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

export default Organizations;
