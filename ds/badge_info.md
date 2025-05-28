# 산별 달성 목표

- **정상 도달**: 산의 정상에 도달하는 것을 목표로 합니다.
- **시간 기록**: 특정 시간 내에 정상에 도달하는 것을 목표로 합니다.
- **경로 탐색**: 새로운 경로를 탐색하거나, 특정 경로를 따라 등산하는 것을 목표로 합니다.
- **자연 관찰**: 산의 자연 경관을 관찰하고 사진을 찍는 것을 목표로 합니다.

# 전체 목표

- **등반 횟수**: 총 등반 횟수를 기록하고 목표를 설정합니다.
- **난이도별 등반 횟수**: 난이도에 따라 등반 횟수를 기록하고 목표를 설정합니다.
  - **산꼬마**: 초보자 난이도의 등반 횟수를 기록합니다. (산을 처음 만나는 귀여운 꼬마)
  - **산사나이**: 중급자 난이도의 등반 횟수를 기록합니다. (산을 정복하는 진정한 사나이)
  - **산신령**: 고급자 난이도의 등반 횟수를 기록합니다. (산의 신령처럼 자유롭게)

# 데이터베이스 구조

## 산 정보 (Mountains)
- **mountain_id**: 산 고유 식별자
- **name**: 산 이름
- **height**: 높이 (m)
- **location**: 위치 (시/도, 구/군)
- **difficulty**: 난이도 (1-5)
- **estimated_time**: 예상 소요 시간
- **main_route**: 주요 등산로
- **description**: 산 설명
- **image_url**: 산 이미지 URL

## 개인 등반 기록 (Climbing_Records)
- **record_id**: 기록 고유 식별자
- **user_id**: 사용자 고유 식별자
- **mountain_id**: 산 고유 식별자
- **climb_date**: 등반 날짜
- **start_time**: 시작 시간
- **end_time**: 종료 시간
- **route_taken**: 선택한 등산로
- **weather**: 날씨
- **temperature**: 기온
- **completion**: 완등 여부
- **notes**: 메모
- **photos**: 사진 URL 배열
- **rating**: 만족도 (1-5)

## 사용자 정보 (Users)
- **user_id**: 사용자 고유 식별자
- **username**: 사용자 이름
- **join_date**: 가입일
- **total_climbs**: 총 등반 횟수
- **current_level**: 현재 레벨 (산꼬마/산사나이/산신령)
- **achievements**: 달성한 업적 목록
- **favorite_mountains**: 즐겨찾기한 산 목록

# 더미 데이터

## 산 정보
```json
{
  "mountains": [
    {
      "mountain_id": 1,
      "name": "북한산",
      "height": 836,
      "location": "서울시 강북구",
      "difficulty": 3,
      "estimated_time": "3시간",
      "main_route": "북한산성 코스",
      "description": "서울의 대표적인 산으로, 도심에서 쉽게 접근할 수 있습니다."
    },
    {
      "mountain_id": 2,
      "name": "관악산",
      "height": 632,
      "location": "서울시 관악구",
      "difficulty": 2,
      "estimated_time": "2시간",
      "main_route": "관악산 정상 코스",
      "description": "서울 남부의 대표적인 산으로, 등산로가 잘 정비되어 있습니다."
    },
    {
      "mountain_id": 3,
      "name": "지리산",
      "height": 1915,
      "location": "전라남도 구례군",
      "difficulty": 5,
      "estimated_time": "8시간",
      "main_route": "천왕봉 코스",
      "description": "남부지방의 대표적인 산으로, 장거리 등산이 가능합니다."
    }
  ]
}
```

## 사용자 정보
```json
{
  "users": [
    {
      "user_id": 1,
      "username": "산사랑",
      "join_date": "2024-01-01",
      "total_climbs": 5,
      "current_level": "산꼬마",
      "achievements": ["정상 도달 x3", "시간 기록 달성"],
      "favorite_mountains": [1, 2]
    }
  ]
}
```

## 등반 기록
```json
{
  "climbing_records": [
    {
      "record_id": 1,
      "user_id": 1,
      "mountain_id": 1,
      "climb_date": "2024-03-15",
      "start_time": "09:00",
      "end_time": "12:00",
      "route_taken": "북한산성 코스",
      "weather": "맑음",
      "temperature": 15,
      "completion": true,
      "notes": "날씨가 좋아서 정상에서 서울 전경을 잘 볼 수 있었다.",
      "rating": 5
    },
    {
      "record_id": 2,
      "user_id": 1,
      "mountain_id": 2,
      "climb_date": "2024-03-20",
      "start_time": "10:00",
      "end_time": "11:30",
      "route_taken": "관악산 정상 코스",
      "weather": "흐림",
      "temperature": 12,
      "completion": true,
      "notes": "안개가 자욱해서 정상에서의 전망은 좋지 않았다.",
      "rating": 4
    }
  ]
}
```

## 뱃지 시스템
```json
{
  "mountain_badges": {
    "정상 도달": {
      "description": "산의 정상에 도달",
      "condition": "completion == true"
    },
    "스피드 등반": {
      "description": "예상 시간의 80% 이내로 등반 완료",
      "condition": "total_time <= estimated_time * 0.8"
    },
    "경로 탐색": {
      "description": "새로운 등산로 탐색",
      "condition": "route_taken != main_route"
    },
    "자연 관찰": {
      "description": "등반 중 사진 촬영",
      "condition": "photos.length > 0"
    }
  },
  "total_badges": {
    "등반 횟수": {
      "초보 등반가": {
        "description": "총 10회 등반 달성",
        "condition": "total_climbs >= 10"
      },
      "중급 등반가": {
        "description": "총 50회 등반 달성",
        "condition": "total_climbs >= 50"
      },
      "고급 등반가": {
        "description": "총 100회 등반 달성",
        "condition": "total_climbs >= 100"
      }
    },
    "산 정복자": {
      "description": "한 산의 모든 등산로 완등",
      "condition": "all_routes_completed == true"
    },
    "계절 등반가": {
      "description": "한 계절에 5회 이상 등반",
      "condition": "season_climbs >= 5"
    },
    "날씨 도전자": {
      "description": "비나 눈이 오는 날 등반 완료",
      "condition": "weather in ['rain', 'snow'] && completion == true"
    }
  }
}
``` 