# alley-risk-viewer

보도 없는 생활도로 VLM 평가 Benchmark의 **Web Viewer** (프론트엔드). 명세서(Role_Frontend) 기준.
점수 → 실패 장면 → 판단 근거로 내려가는 흐름을 제공하고, 정답과 예측을 구분해 **근거 Object → 관계 판정(R1–R4) → 대응**의 연결을 보여 준다.

> 현재 상태: 가상(mock) 데이터로 F1–F5와 상태 화면이 동작하는 단일 HTML 프로토타입. 기본 모델은 Gemma 4(명세 §4.5). React 구현은 2주차 Schema 확정 후.

## 화면

| 화면 | 답하는 질문 | 보여 주는 것 |
|---|---|---|
| F1 평가 실행 | 어떤 모델·Test Version으로 실행하는가 | HF 모델 ID, Test Version(frozen), 입력 조건(정상/영상 없음), 진행률, 성공·실패 수, V1·V2 |
| F2 결과 Report | Base 대비 개선되었는가 | V5·V10 + 분모 + 95% CI, 차이 구간과 판정(improved / not_confirmed), 진단 지표군 4개, 조건별 점수(탐색적 표시) |
| F3 오류 목록 | 어떤 장면에서 어떤 종류로 틀렸는가 | 진단 지표군·관계·조건 필터, 실패 사유 이름표(형식 오류/필요 대응 누락/금지 대응/등록되지 않은 대응/관계 모순) |
| F4 모델 비교 | 같은 장면에서 두 모델이 어떻게 다른가 | Base/Tuned 관계 판정과 대응 나란히, 통과/실패 |
| F5 장면 상세 | 이 판단의 근거는 무엇인가 | C·정답 Box(실선)·예측 Box(점선) 레이어, GT 체인 / 예측 체인, Box 짝짓기(IoU), 정답 출처·검수 상태 |

상태 화면: 평가 전(→F1) · 실행 중(진행률·남은 요청) · 실행 오류(실패 수·재실행) · Invalid 장면 · 필터 결과 없음(초기화).

## 표시 규칙 (명세 §5)

- 정답 Box·C는 사람이 작성, 예측 Box는 모델 출력. 선 모양과 범례로 구분. C는 모델에 제공되지 않음을 범례에 명시.
- **P/A/U**: P 성립, A 충분히 확인했고 불성립, U 입력만으로 판정 불가. U는 정답의 하나이므로 오류 색을 쓰지 않는다.
- 빈 값: **Invalid**(출력 형식 오류) / **Missing**(검수 전 정답) / **Not applicable** 을 서로 다른 표기로.
- 실패 사유는 색만이 아니라 이름표와 함께.
- 점수는 분모와 95% CI를 함께. 개선은 차이 구간 하한 > 0일 때만 "개선", 아니면 "차이를 확인하지 못함". 판정 값은 Report API를 그대로 따른다.
- 분모가 작은 조건별 점수는 "탐색적 결과".

## 파일

`prototype/build.py` 가 `template.html` + `mock/*.json` → `index.html` 로 합친다 (`cd prototype && python3 build.py`). mock은 `python3 mock/gen.py` 로 재생성.

| 경로 | 내용 |
|---|---|
| `prototype/index.html` | 단일 HTML 프로토타입 (GitHub Pages 배포 가능) |
| `mock/report.json` | Report API 응답 제안 — core(V5·V10), comparison(verdict), diag_scores(V6·V7·V11·V12), diagnostics, conditions, excluded(relation/action), runs |
| `mock/scenes.json` | 장면별 reference(objects·regions·scene·relations[code,state,evidence]·actions{required_groups,allowed,forbidden})·predictions(App.B.4 Schema)·scoring |
| `mock/meta.json` | 관계 R1–R4·대응 Code 7종·조건 Code 6종·실패 사유 5종·진단 지표군 enum |
| `mock/gen.py` | mock 생성 스크립트. App.B.2 규칙으로 GT 관계 → 필요 묶음/허용/금지 도출, App.A 채점(V3 IoU 짝짓기·V4 근거 ID·V10 일관성/허용/금지/묶음) 구현. 백엔드 자동 채점기가 기준이며 이건 화면 검토용 |
| `docs/plan-draft-2026-11-01.md` | 11/1 구현 계획 초안 |

## 백엔드 요구 (초안)

```
GET  /tests                                   frozen Test Version 목록
POST /runs                                    { model_id, test_version, input_condition, prompt_version, schema_version }
GET  /runs/{run_id}                           status, progress, V1, V2, failures[]
POST /runs/{run_id}/retry                     실패 요청만 재실행
GET  /reports?test=&base=&target=             core, comparison(verdict), diagnostics, conditions, excluded
GET  /runs/{run_id}/scenes?status=fail&diag=&relation=&condition=
GET  /scenes/{scene_id}?run=|runs=a,b         reference, prediction(s), scoring
```

## 다음 단계

1. 2주차: 위 필드 목록을 백엔드와 확정
2. 3주차: React + Vite + TS로 F1–F5·상태 화면 구현 (필터는 URL 쿼리, mock → API 교체)
3. 4주차: 실제 Base·Tuned 결과 연결, 정답·예측 Box와 근거–관계–대응 연결 표시
