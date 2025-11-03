/**
 * Signup Page
 * 사용자 회원가입 페이지 (전문 분야 선택 포함)
 */

import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import './Signup.css';

const SPECIALIZATIONS = [
  '형사 일반',
  '교통사고',
  '성범죄',
  '마약범죄',
  '기업범죄',
  '민사',
];

const Signup: React.FC = () => {
  const navigate = useNavigate();
  const { signup } = useAuth();

  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirmPassword: '',
    full_name: '',
    lawyer_registration_number: '',
    specializations: [] as string[],
  });

  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSpecializationToggle = (spec: string) => {
    setFormData(prev => ({
      ...prev,
      specializations: prev.specializations.includes(spec)
        ? prev.specializations.filter(s => s !== spec)
        : [...prev.specializations, spec],
    }));
  };

  const validate = (): boolean => {
    if (!formData.email || !formData.password || !formData.full_name) {
      setError('필수 항목을 모두 입력해주세요');
      return false;
    }

    if (formData.password.length < 8) {
      setError('비밀번호는 최소 8자 이상이어야 합니다');
      return false;
    }

    if (formData.password !== formData.confirmPassword) {
      setError('비밀번호가 일치하지 않습니다');
      return false;
    }

    if (formData.specializations.length === 0) {
      setError('최소 1개 이상의 전문 분야를 선택해주세요');
      return false;
    }

    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!validate()) {
      return;
    }

    setIsSubmitting(true);

    try {
      await signup({
        email: formData.email,
        password: formData.password,
        full_name: formData.full_name,
        specializations: formData.specializations,
        lawyer_registration_number: formData.lawyer_registration_number || undefined,
      });
      navigate('/app'); // 회원가입 성공 후 앱으로 이동
    } catch (err: any) {
      setError(err.message || '회원가입에 실패했습니다');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="signup-container">
      <div className="signup-box">
        <div className="signup-header">
          <h1>LawLaw 회원가입</h1>
          <p>형사법 전문 AI 어시스턴트를 시작하세요</p>
        </div>

        <form onSubmit={handleSubmit} className="signup-form">
          {error && <div className="signup-error">{error}</div>}

          <div className="form-group">
            <label htmlFor="full_name">이름 *</label>
            <input
              id="full_name"
              name="full_name"
              type="text"
              value={formData.full_name}
              onChange={handleInputChange}
              placeholder="홍길동"
              required
              autoFocus
            />
          </div>

          <div className="form-group">
            <label htmlFor="email">이메일 *</label>
            <input
              id="email"
              name="email"
              type="email"
              value={formData.email}
              onChange={handleInputChange}
              placeholder="lawyer@lawlaw.com"
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">비밀번호 * (8자 이상)</label>
            <input
              id="password"
              name="password"
              type="password"
              value={formData.password}
              onChange={handleInputChange}
              placeholder="비밀번호 입력"
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="confirmPassword">비밀번호 확인 *</label>
            <input
              id="confirmPassword"
              name="confirmPassword"
              type="password"
              value={formData.confirmPassword}
              onChange={handleInputChange}
              placeholder="비밀번호 재입력"
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="lawyer_registration_number">변호사 등록번호 (선택)</label>
            <input
              id="lawyer_registration_number"
              name="lawyer_registration_number"
              type="text"
              value={formData.lawyer_registration_number}
              onChange={handleInputChange}
              placeholder="12345"
            />
          </div>

          <div className="form-group">
            <label>전문 분야 * (1개 이상 선택)</label>
            <div className="specializations-grid">
              {SPECIALIZATIONS.map(spec => (
                <label key={spec} className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={formData.specializations.includes(spec)}
                    onChange={() => handleSpecializationToggle(spec)}
                  />
                  <span>{spec}</span>
                </label>
              ))}
            </div>
          </div>

          <button
            type="submit"
            className="signup-button"
            disabled={isSubmitting}
          >
            {isSubmitting ? '가입 중...' : '회원가입'}
          </button>
        </form>

        <div className="signup-footer">
          <p>
            이미 계정이 있으신가요? <Link to="/login">로그인</Link>
          </p>
        </div>
      </div>
    </div>
  );
};

export default Signup;
