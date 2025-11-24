import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { apiClient } from '../api/client';
import { Membership, MemberRole } from '../types';
import './MemberManagement.css';

interface MemberManagementProps {
  organizationId: string;
  onMembersChange?: () => void;
}

const MemberManagement: React.FC<MemberManagementProps> = ({
  organizationId,
  onMembersChange
}) => {
  const { token } = useAuth();
  const [members, setMembers] = useState<Membership[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [newMemberEmail, setNewMemberEmail] = useState('');
  const [newMemberRole, setNewMemberRole] = useState<MemberRole>('VIEWER');
  const [adding, setAdding] = useState(false);

  useEffect(() => {
    loadMembers();
  }, [organizationId, token]);

  const loadMembers = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiClient.getOrganizationMembers(
        organizationId,
        token || undefined
      );
      setMembers(response.results);
    } catch (err: any) {
      setError(err.message || 'Failed to load members');
      console.error('Load members error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleAddMember = async () => {
    if (!newMemberEmail.trim()) {
      setError('Email is required');
      return;
    }

    try {
      setAdding(true);
      setError(null);
      await apiClient.addMember(
        organizationId,
        { user_email: newMemberEmail.trim(), role: newMemberRole },
        token || undefined
      );
      setShowAddModal(false);
      setNewMemberEmail('');
      setNewMemberRole('VIEWER');
      await loadMembers();
      if (onMembersChange) {
        onMembersChange();
      }
    } catch (err: any) {
      setError(err.message || 'Failed to add member');
      console.error('Add member error:', err);
    } finally {
      setAdding(false);
    }
  };

  const handleUpdateRole = async (userId: string, newRole: MemberRole) => {
    try {
      setError(null);
      await apiClient.updateMemberRole(
        organizationId,
        userId,
        { role: newRole },
        token || undefined
      );
      await loadMembers();
      if (onMembersChange) {
        onMembersChange();
      }
    } catch (err: any) {
      setError(err.message || 'Failed to update role');
      console.error('Update role error:', err);
    }
  };

  const handleRemoveMember = async (userId: string, userEmail: string) => {
    if (!window.confirm(`Are you sure you want to remove ${userEmail} from this organization?`)) {
      return;
    }

    try {
      setError(null);
      await apiClient.removeMember(organizationId, userId, token || undefined);
      await loadMembers();
      if (onMembersChange) {
        onMembersChange();
      }
    } catch (err: any) {
      setError(err.message || 'Failed to remove member');
      console.error('Remove member error:', err);
    }
  };

  const getRoleBadgeClass = (role: MemberRole): string => {
    switch (role) {
      case 'ADMIN':
        return 'role-badge admin';
      case 'EDITOR':
        return 'role-badge editor';
      case 'VIEWER':
        return 'role-badge viewer';
      default:
        return 'role-badge';
    }
  };

  if (loading) {
    return <div className="member-management loading">Loading members...</div>;
  }

  return (
    <div className="member-management">
      <div className="members-header">
        <h3>Members ({members.length})</h3>
        <button
          className="btn-primary"
          onClick={() => setShowAddModal(true)}
        >
          Add Member
        </button>
      </div>

      {error && (
        <div className="error-message">
          {error}
          <button onClick={() => setError(null)} className="close-btn">×</button>
        </div>
      )}

      <div className="members-table">
        {members.length === 0 ? (
          <div className="empty-state">
            <p>No members in this organization yet.</p>
          </div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Email</th>
                <th>Role</th>
                <th>Permissions</th>
                <th>Joined</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {members.map(member => (
                <tr key={member.id}>
                  <td>{member.user_email}</td>
                  <td>
                    <span className={getRoleBadgeClass(member.role)}>
                      {member.role_display}
                    </span>
                  </td>
                  <td className="permissions">
                    {member.is_admin && <span className="perm-tag">Admin</span>}
                    {member.can_edit && <span className="perm-tag">Edit</span>}
                    <span className="perm-tag">View</span>
                  </td>
                  <td>
                    {new Date(member.joined_at).toLocaleDateString()}
                  </td>
                  <td className="actions">
                    <select
                      value={member.role}
                      onChange={(e) => handleUpdateRole(member.user, e.target.value as MemberRole)}
                      className="role-select"
                    >
                      <option value="ADMIN">Admin</option>
                      <option value="EDITOR">Editor</option>
                      <option value="VIEWER">Viewer</option>
                    </select>
                    <button
                      className="btn-danger-small"
                      onClick={() => handleRemoveMember(member.user, member.user_email)}
                      title="Remove member"
                    >
                      Remove
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showAddModal && (
        <div className="modal-overlay">
          <div className="modal">
            <div className="modal-header">
              <h2>Add Member</h2>
              <button
                className="close-btn"
                onClick={() => {
                  setShowAddModal(false);
                  setNewMemberEmail('');
                  setNewMemberRole('VIEWER');
                  setError(null);
                }}
              >
                ×
              </button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label htmlFor="memberEmail">Email *</label>
                <input
                  id="memberEmail"
                  type="email"
                  value={newMemberEmail}
                  onChange={(e) => setNewMemberEmail(e.target.value)}
                  placeholder="Enter member email"
                  autoFocus
                />
              </div>
              <div className="form-group">
                <label htmlFor="memberRole">Role *</label>
                <select
                  id="memberRole"
                  value={newMemberRole}
                  onChange={(e) => setNewMemberRole(e.target.value as MemberRole)}
                >
                  <option value="VIEWER">Viewer (Read-only)</option>
                  <option value="EDITOR">Editor (Can edit)</option>
                  <option value="ADMIN">Admin (Full access)</option>
                </select>
              </div>
            </div>
            <div className="modal-footer">
              <button
                className="btn-secondary"
                onClick={() => {
                  setShowAddModal(false);
                  setNewMemberEmail('');
                  setNewMemberRole('VIEWER');
                  setError(null);
                }}
                disabled={adding}
              >
                Cancel
              </button>
              <button
                className="btn-primary"
                onClick={handleAddMember}
                disabled={adding || !newMemberEmail.trim()}
              >
                {adding ? 'Adding...' : 'Add Member'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default MemberManagement;
