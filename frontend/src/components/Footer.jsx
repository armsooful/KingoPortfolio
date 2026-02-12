import React from 'react';
import '../styles/Footer.css';

/**
 * 공통 푸터 컴포넌트
 * 저작권 및 법적 고지사항 표시
 */
const Footer = () => {
  return (
    <footer className="footer">
      <div className="footer-inner">
        {/* 법적 고지사항 */}
        <div className="footer-legal">
          <p className="footer-legal-title">⚠️ 법적 고지사항</p>
          <p className="footer-legal-item">
            • 본 서비스는 투자 정보 제공을 목적으로 하며, 투자 권유나 매매 추천이 아닙니다.
          </p>
          <p className="footer-legal-item">
            • 모든 투자 결정은 이용자의 판단과 책임 하에 이루어지며, 투자 손실에 대해 당사는 책임을 지지 않습니다.
          </p>
          <p className="footer-legal-item">
            • 과거 수익률은 미래 수익을 보장하지 않습니다. 투자 전 전문가와 상담하시기 바랍니다.
          </p>
        </div>

        {/* 저작권 */}
        <div className="footer-copyright">
          <p>
            © 2026 Foresto Compass. All rights reserved.
          </p>
          <p className="footer-copyright-sub">
            본 서비스는 교육 및 연구 목적으로 제작되었습니다.
          </p>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
