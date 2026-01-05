import React from 'react';

/**
 * 면책 문구 컴포넌트
 * 투자 정보 제공 페이지에 표시되는 법적 고지사항
 */
const Disclaimer = ({ type = 'general' }) => {
  const disclaimers = {
    general: {
      title: '⚠️ 투자 유의사항',
      content: [
        '본 서비스에서 제공하는 모든 정보는 투자 참고용으로만 제공되며, 투자 권유나 매매 추천이 아닙니다.',
        '모든 투자 결정은 이용자 본인의 판단과 책임 하에 이루어져야 하며, 투자로 인한 손실에 대해 당사는 법적 책임을 지지 않습니다.',
        '과거 수익률이나 시뮬레이션 결과는 미래의 투자 성과를 보장하지 않습니다.',
        '투자 전에는 반드시 전문가와 상담하시기 바랍니다.'
      ]
    },
    diagnosis: {
      title: '⚠️ 투자 성향 진단 유의사항',
      content: [
        '본 투자 성향 진단은 참고용 정보이며, 실제 금융상품 가입 시 금융기관의 정식 투자자 정보 확인이 필요합니다.',
        '진단 결과는 설문 응답 시점의 개인 상황을 기반으로 하며, 시간이 지남에 따라 변경될 수 있습니다.',
        '진단 결과만으로 투자 결정을 내리지 마시고, 반드시 전문가와 상담하시기 바랍니다.'
      ]
    },
    portfolio: {
      title: '⚠️ 포트폴리오 추천 유의사항',
      content: [
        '제시된 포트폴리오는 알고리즘 기반 참고 자료이며, 개인별 맞춤 투자 전략이 아닙니다.',
        '실제 투자 시에는 개인의 재무 상황, 투자 목적, 위험 감내도를 종합적으로 고려해야 합니다.',
        '포트폴리오에 포함된 종목의 과거 성과는 미래 수익을 보장하지 않습니다.',
        '투자 전 반드시 해당 종목 및 상품의 투자설명서를 확인하시기 바랍니다.'
      ]
    },
    stock: {
      title: '⚠️ 종목 정보 유의사항',
      content: [
        '본 페이지의 종목 정보 및 차트는 참고용이며, 실시간 데이터가 아닐 수 있습니다.',
        '표시된 재무지표 및 수익률은 과거 데이터이며, 미래 성과를 보장하지 않습니다.',
        '투자 결정 전 반드시 최신 공시정보 및 재무제표를 확인하시기 바랍니다.',
        '종목 정보는 정보 제공 목적이며, 특정 종목의 매수/매도를 권유하는 것이 아닙니다.'
      ]
    },
    backtest: {
      title: '⚠️ 백테스트 결과 유의사항',
      content: [
        '백테스트 결과는 과거 데이터를 기반으로 한 시뮬레이션이며, 실제 투자 결과와 다를 수 있습니다.',
        '시뮬레이션에는 거래 비용, 세금, 슬리피지 등이 반영되지 않았을 수 있습니다.',
        '과거의 성과가 미래의 수익을 보장하지 않으며, 실제 투자 시에는 예상치 못한 변수가 발생할 수 있습니다.',
        '백테스트 결과만으로 투자 결정을 내리지 마시고, 충분한 검토와 전문가 상담이 필요합니다.'
      ]
    }
  };

  const selected = disclaimers[type] || disclaimers.general;

  return (
    <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 rounded-md mb-6">
      <div className="flex">
        <div className="flex-1">
          <h3 className="text-sm font-bold text-yellow-800 mb-2">
            {selected.title}
          </h3>
          <ul className="text-xs text-yellow-700 space-y-1">
            {selected.content.map((item, index) => (
              <li key={index} className="flex items-start">
                <span className="mr-2">•</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
};

export default Disclaimer;
