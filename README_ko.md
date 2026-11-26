# ExamRAG

[![tests](https://github.com/huiren789/exam-rag/actions/workflows/tests.yml/badge.svg)](https://github.com/huiren789/exam-rag/actions/workflows/tests.yml)
![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue)
![MIT](https://img.shields.io/badge/license-MIT-green)
[![Live demo](https://img.shields.io/badge/demo-live-green)](https://examrag-demo.app.workbuddy.host/?sharecode=YTW7YFIS3R)

<div align="center">

<img src="assets/demo.png" alt="ExamRAG 데모: 질문, 검색, 출처" width="880">

**근거를 확인할 수 있는 학습 도우미**

**의존성 없음 · 출처 표시 · 교재 교체 가능** — 검색은 로컬에서 수행하고 선택된 자료만 LLM에 전달합니다. 모든 답변에는 근거가 표시되어 원문으로 돌아가 확인할 수 있습니다.

[온라인 데모(API 키 불필요)](https://examrag-demo.app.workbuddy.host/?sharecode=YTW7YFIS3R) ·
[해결하는 문제](#해결하는-문제) ·
[30초 만에 내 과목으로 바꾸기](#30초-만에-내-과목으로-바꾸기)

</div>

**언어**：[中文](README.md) · [English](README_en.md) · [日本語](README_ja.md) · **한국어** · [Español](README_es.md)

> 포함된 「교육 측정」 자료는 예시입니다. `data/material.txt`를 바꾸면 **모든 과목에 사용할 수 있습니다**. 검색 핵심은 Python 표준 라이브러리만 사용합니다. 작성자가 첫 실제 사용자로 자기 학습에 활용하고 자체 평가 세트로 4회 개선했습니다.

## 해결하는 문제

LLM에 바로 물어보면 그럴듯하지만 만들어낸 답변이 나올 수 있습니다. 교재를 직접 읽으면 필요한 부분을 찾기 어렵습니다.

ExamRAG는 「자료 찾기」를 로컬에서 수행합니다. 검색은 오프라인·무료·결과가 보입니다. 선택된 자료 블록만 모델에 보내고, 그 자료만 사용할 것·출처를 적을 것·자료에 없으면 「자료에 없음」이라고 답할 것을 프롬프트로 요구합니다.

## 30초 만에 내 과목으로 바꾸기

포함된 자료는 예시일 뿐입니다. 내 노트를 다음 형식의 일반 텍스트로 정리하면 됩니다:

```text
【숙달·개념 이름】한 문단으로 개념을 설명하는 본문.
【이해·다른 개념】……
【파악·세 번째 개념】……
```

세 라벨(숙달 / 이해 / 파악)이 출제 가중치를 결정합니다. 그다음:

```bash
python -m examrag -q "내 질문" --material my.txt
```

또는 `EXAMRAG_MATERIAL=my.txt`를 한 번 설정하면 됩니다. 검색·출처·가중 출제·웹 UI가 그대로 동작합니다. **특정 과목 전용 도구와의 결정적 차이입니다**.

## 주요 기능

- 로컬 어휘 검색(bigram 빈도, 제목 가중, 목차·요약 감점) — 표준 라이브러리만
- 선택적 TF-IDF 의미 검색(`--semantic`) — 오프라인·의존성 없음
- 선택적 embedding 벡터 검색(`--vector`) — 캐시 지원
- 문장 단위 근거 표시 — 웹 UI에서 출처 문장으로 원문 이동
- 가중 출제(숙달 ×3 / 이해 ×2 / 파악 ×1)
- 질문 재작성, 핵심 요약, 병렬 개념 분리 검색
- 오프라인 dry-run(`--dry-run`) — 키 없이 검색 결과와 프롬프트 표시
- 웹 UI 및 FastAPI(5개 엔드포인트, Swagger 자동 생성)
- 89개 오프라인 테스트, CI(Python 3.8 / 3.11 / 3.13 + ruff)

## 빠른 시작

```bash
git clone https://github.com/huiren789/exam-rag.git
cd exam-rag
python -m examrag -q "난이도란" --dry-run   # 오프라인, 키 불필요
python -m examrag                             # 대화형 모드
```

실제 모델을 호출하려면 `.env.example`을 `.env`로 복사하고 `SILICONFLOW_API_KEY`를 설정하세요. 웹 UI는 WorkBuddy Cloud를 사용하므로 [데모](https://examrag-demo.app.workbuddy.host/?sharecode=YTW7YFIS3R)는 키가 필요 없습니다.

## 제한 사항

- 기본 검색은 어휘 매칭입니다. TF-IDF는 표현 차이를 완화하고, 동의어 수준의 검색에는 embedding이 필요합니다.
- 근거 문장은 중국어 문장부호 휴리스틱을 사용합니다. 매우 긴 문장이나 여러 문장에 걸친 표현은 정확도가 떨어집니다.
- 자료는 수동으로 정리해야 합니다(PDF / Word 가져오기 미지원).
- 대화 문맥은 유지하지 않습니다. 각 질문이 독립적으로 검색합니다.

## 문서

[中文 전체 문서](README.md) · [English](README_en.md) · [設計 판단](docs/adr) · [변경 이력](CHANGELOG.md)

## 라이선스

[MIT](LICENSE) © 2026 huiren789
