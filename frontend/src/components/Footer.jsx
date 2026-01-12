import React from 'react';

/**
 * 공통 푸터 컴포넌트
 * 저작권 및 법적 고지사항 표시
 */
const Footer = () => {
  return (
    <footer style={{
      marginTop: '64px',
      padding: '32px 24px',
      background: '#f8f9fa',
      borderTop: '1px solid #e0e0e0',
      textAlign: 'center'
    }}>
      <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
        {/* 법적 고지사항 */}
        <div style={{
          fontSize: '0.75rem',
          color: '#666',
          lineHeight: '1.6',
          marginBottom: '16px',
          textAlign: 'left'
        }}>
          <p style={{ marginBottom: '8px', fontWeight: '600' }}>⚠️ 법적 고지사항</p>
          <p style={{ marginBottom: '4px' }}>
            • 본 서비스는 투자 정보 제공을 목적으로 하며, 투자 권유나 매매 추천이 아닙니다.
          </p>
          <p style={{ marginBottom: '4px' }}>
            • 모든 투자 결정은 이용자의 판단과 책임 하에 이루어지며, 투자 손실에 대해 당사는 책임을 지지 않습니다.
          </p>
          <p>
            • 과거 수익률은 미래 수익을 보장하지 않습니다. 투자 전 전문가와 상담하시기 바랍니다.
          </p>
        </div>

        {/* 저작권 */}
        <div style={{
          paddingTop: '16px',
          borderTop: '1px solid #e0e0e0',
          fontSize: '0.875rem',
          color: '#999'
        }}>
          <p style={{ margin: 0 }}>
            © 2026 Foresto Compass. All rights reserved.
          </p>
          <p style={{ margin: '4px 0 0', fontSize: '0.75rem' }}>
            본 서비스는 교육 및 연구 목적으로 제작되었습니다.
          </p>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
