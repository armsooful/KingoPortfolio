from .user import User
from .securities import KrxTimeSeries
from .portfolio import Portfolio, PortfolioHistory, SimulationCache
from .simulation import SimulationRun, SimulationPath, SimulationSummary
from .scenario import ScenarioDefinition, PortfolioModel, PortfolioAllocation
from .rebalancing import RebalancingRule, RebalancingEvent, RebalancingCostModel
# app/models.py의 모델들을 직접 import하지 않고 lazy import 허용

__all__ = ['User', 'KrxTimeSeries', 'Portfolio', 'PortfolioHistory', 'SimulationCache',
           'SimulationRun', 'SimulationPath', 'SimulationSummary',
           'ScenarioDefinition', 'PortfolioModel', 'PortfolioAllocation',
           'RebalancingRule', 'RebalancingEvent', 'RebalancingCostModel']
# models.py에서 추가 모델 import
import sys
import os

# 상위 디렉토리의 models.py 직접 로드
models_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models.py')
if os.path.exists(models_file):
    import importlib.util
    spec = importlib.util.spec_from_file_location("_models", models_file)
    _models = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(_models)
    
    Diagnosis = _models.Diagnosis
    DiagnosisAnswer = _models.DiagnosisAnswer
    SurveyQuestion = _models.SurveyQuestion

    __all__ = ['User', 'KrxTimeSeries', 'Portfolio', 'PortfolioHistory', 'SimulationCache', 'Diagnosis', 'DiagnosisAnswer', 'SurveyQuestion']
