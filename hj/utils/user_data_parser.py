import json
import pandas as pd
from typing import Dict, List

class AppleWatchDataParser:
    """Apple Watch 데이터를 파싱하고 분석하는 클래스"""
    
    def __init__(self, json_file_path: str):
        self.json_file_path = json_file_path
        self.data = None
        self.df = None
        
    def load_data(self) -> Dict:
        """JSON 파일에서 Apple Watch 데이터를 로드합니다."""
        try:
            with open(self.json_file_path, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            return self.data
        except Exception as e:
            print(f"데이터 로드 중 오류 발생: {e}")
            return {}
    
    def to_dataframe(self) -> pd.DataFrame:
        """JSON 데이터를 pandas DataFrame으로 변환합니다."""
        if not self.data:
            self.load_data()
        
        if not self.data or 'data' not in self.data:
            return pd.DataFrame()
        
        self.df = pd.DataFrame(self.data['data'])
        self.df['timestamp'] = pd.to_datetime(self.df['timestamp'])
        return self.df
    
    def get_summary_stats(self) -> Dict:
        """데이터의 요약 통계를 계산합니다."""
        if self.df is None:
            self.to_dataframe()
        
        if self.df.empty:
            return {}
        
        summary = {
            'user_id': self.data.get('user_id', 'Unknown'),
            'date': self.data.get('date', 'Unknown'),
            'duration_minutes': len(self.df) * 0.5,  # 30초 간격
            'total_steps': self.df['step_count'].max() - self.df['step_count'].min(),
            'avg_heart_rate': round(self.df['heart_rate'].mean(), 1),
            'min_heart_rate': self.df['heart_rate'].min(),
            'max_heart_rate': self.df['heart_rate'].max(),
            'heart_rate_variability': round(self.df['heart_rate'].std(), 1),
            'step_rate_per_minute': round((self.df['step_count'].max() - self.df['step_count'].min()) / (len(self.df) * 0.5), 1)
        }
        
        return summary
    
    def get_activity_periods(self) -> List[Dict]:
        """활동 구간을 식별합니다 (걸음 수 증가 구간)."""
        if self.df is None:
            self.to_dataframe()
        
        if self.df.empty:
            return []
        
        # 걸음 수 변화량 계산
        self.df['step_diff'] = self.df['step_count'].diff().fillna(0)
        
        # 활동 구간 식별 (걸음 수가 증가하는 구간)
        active_periods = []
        current_period = None
        
        for idx, row in self.df.iterrows():
            if row['step_diff'] > 0:  # 걸음 수 증가
                if current_period is None:
                    current_period = {
                        'start_time': row['timestamp'],
                        'start_steps': row['step_count'],
                        'start_hr': row['heart_rate']
                    }
                current_period['end_time'] = row['timestamp']
                current_period['end_steps'] = row['step_count']
                current_period['end_hr'] = row['heart_rate']
            else:  # 걸음 수 변화 없음
                if current_period is not None:
                    # 활동 구간 종료
                    duration = (current_period['end_time'] - current_period['start_time']).total_seconds() / 60
                    if duration >= 1:  # 1분 이상인 활동만 기록
                        current_period['duration_minutes'] = round(duration, 1)
                        current_period['steps_taken'] = current_period['end_steps'] - current_period['start_steps']
                        current_period['avg_hr'] = round((current_period['start_hr'] + current_period['end_hr']) / 2, 1)
                        active_periods.append(current_period)
                    current_period = None
        
        return active_periods
    
    def format_for_llm(self) -> str:
        """LLM이 이해하기 쉬운 형태로 데이터를 포맷팅합니다."""
        summary = self.get_summary_stats()
        activity_periods = self.get_activity_periods()
        
        if not summary:
            return "Apple Watch 데이터를 로드할 수 없습니다."
        
        # 기본 정보
        formatted_text = f"""## Apple Watch 데이터 분석 결과

### 기본 정보
- 사용자 ID: {summary['user_id']}
- 측정 날짜: {summary['date']}
- 측정 시간: {summary['duration_minutes']}분간 (30초 간격 측정)

### 활동 요약
- 총 걸음 수: {summary['total_steps']}보
- 분당 평균 걸음 수: {summary['step_rate_per_minute']}보/분

### 심박수 분석
- 평균 심박수: {summary['avg_heart_rate']} bpm
- 최저 심박수: {summary['min_heart_rate']} bpm
- 최고 심박수: {summary['max_heart_rate']} bpm
- 심박수 변동성: {summary['heart_rate_variability']} bpm (표준편차)

"""
        
        # 활동 구간 정보
        if activity_periods:
            formatted_text += "### 주요 활동 구간\n"
            for i, period in enumerate(activity_periods, 1):
                formatted_text += f"""
**구간 {i}**
- 시간: {period['start_time'].strftime('%H:%M:%S')} ~ {period['end_time'].strftime('%H:%M:%S')}
- 지속시간: {period['duration_minutes']}분
- 걸음 수: {period['steps_taken']}보
- 평균 심박수: {period['avg_hr']} bpm
"""
        else:
            formatted_text += "### 활동 구간\n- 특별한 활동 구간이 감지되지 않았습니다.\n"
        
        return formatted_text

def parse_apple_watch_data(json_file_path: str) -> str:
    """Apple Watch 데이터를 파싱하여 LLM용 텍스트로 반환하는 편의 함수"""
    parser = AppleWatchDataParser(json_file_path)
    return parser.format_for_llm() 