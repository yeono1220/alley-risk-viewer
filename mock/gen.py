# -*- coding: utf-8 -*-
"""Mock data for the Web Viewer (Role_Frontend spec). All values are fabricated for layout/flow checks."""
import json, os
OUT = os.path.dirname(os.path.abspath(__file__))

ACTIONS = {
    "HOLD": "보류", "PROCEED_AFTER_CHECK": "확인 후 진행", "CHECK_PASSABILITY": "통과 가능성 확인",
    "SLOW": "서행", "PASS": "통과",
}
RELATIONS = {
    "R1": {"label": "점유", "q": "C 안에 대상이 있는가"},
    "R2": {"label": "출입구", "q": "C와 이어지는 출입구 주변에 Actor가 있는가"},
    "R3": {"label": "시야 가림", "q": "필요한 영역이 가려졌는가"},
    "R4": {"label": "통행 제한", "q": "통행 공간이 좁아졌는가"},
}
FAIL = {
    "invalid": "형식 오류", "missing_required": "필요 대응 누락", "forbidden": "금지 대응",
    "unregistered": "등록되지 않은 대응", "contradiction": "관계 판정과의 모순",
}
DIAG = {
    "evidence": {"label": "근거", "metrics": "V3 · V4", "desc": "근거 Object 누락 · 없는 Object 단정"},
    "bias": {"label": "판단 편향", "metrics": "V6–V9", "desc": "관계 판정 오류 (P↔A, U 처리)"},
    "action": {"label": "대응 결함", "metrics": "V11 · V12", "desc": "필요 대응 누락 · 금지 대응"},
    "explain": {"label": "설명 오류", "metrics": "V13 · V14", "desc": "관측 불가 사실 단정 · 근거-판정 불연결"},
}

MODELS = {
    "base": {"id": "Qwen/Qwen3-VL-8B-Instruct", "label": "Base", "desc": "미세조정 전", "run_id": "run_base_test-v0.1"},
    "tuned": {"id": "team1/qwen3-vl-8b-alley-lora", "label": "Tuned", "desc": "LoRA 미세조정", "run_id": "run_tuned_test-v0.1"},
}

def obj(i, label, kind, box):
    return {"id": f"o{i}", "label": label, "kind": kind, "box": box}

def rel(v, targets=None):
    return {"value": v, "targets": targets or []}

C_DEFAULT = [[0.42, 0.52], [0.58, 0.52], [0.92, 1.0], [0.08, 1.0]]

# 12 scenes. ref = human annotation. pred[base|tuned] = model output.
scenes = []

def add(sid, cond, scene, ref, preds, source="사진", review="Reviewed", C=None, excluded=None):
    scenes.append({"scene_id": sid, "conditions": cond, "scene": scene, "C": C or C_DEFAULT,
                   "reference": ref, "predictions": preds, "source": source, "review_status": review,
                   "excluded": excluded})

# helper for prediction
def pred(objects, rels, actions, explanation, valid=True, raw=None):
    return {"valid": valid, "objects": objects, "relations": rels, "actions": actions,
            "explanation": explanation, "raw_excerpt": raw}

# --- S-01 보행자 2명 C 중앙 (TP both) ---
add("S-0001", ["주간", "보도 없음"], "보행자 2명이 통행 경로 중앙을 걷고 있음",
    {"objects": [obj(1, "보행자", "Actor", [0.44, 0.50, 0.50, 0.72]), obj(2, "보행자", "Actor", [0.51, 0.49, 0.57, 0.71])],
     "relations": {"R1": rel("P", ["o1", "o2"]), "R2": rel("A"), "R3": rel("A"), "R4": rel("A")},
     "actions": {"required": [["HOLD", "R1"]], "allowed": [["SLOW", "R1"]], "forbidden": [["PASS", "R1"]]}},
    {"base": pred([obj(1, "보행자", "Actor", [0.43, 0.50, 0.51, 0.73]), obj(2, "보행자", "Actor", [0.50, 0.48, 0.58, 0.72])],
                  {"R1": rel("P", ["o1", "o2"]), "R2": rel("A"), "R3": rel("A"), "R4": rel("A")},
                  [["HOLD", "R1"]], "경로 중앙에 보행자 2명이 있어 보류한다."),
     "tuned": pred([obj(1, "보행자", "Actor", [0.44, 0.50, 0.50, 0.72]), obj(2, "보행자", "Actor", [0.51, 0.49, 0.57, 0.71])],
                   {"R1": rel("P", ["o1", "o2"]), "R2": rel("A"), "R3": rel("A"), "R4": rel("A")},
                   [["HOLD", "R1"]], "경로 중앙에 보행자 2명. 보류.")})

# --- S-02 주차 차량 사이 어린이 (base misses, tuned catches) ---
add("S-0002", ["주간", "보도 없음"], "우측 주차 차량 두 대 사이로 어린이 상반신이 보임",
    {"objects": [obj(1, "주차 차량", "Roadside Vehicle", [0.62, 0.48, 0.80, 0.68]), obj(2, "주차 차량", "Roadside Vehicle", [0.80, 0.47, 0.97, 0.66]),
                 obj(3, "어린이", "Actor", [0.76, 0.52, 0.81, 0.60])],
     "relations": {"R1": rel("A"), "R2": rel("A"), "R3": rel("P", ["o1", "o2"]), "R4": rel("P", ["o1"])},
     "actions": {"required": [["PROCEED_AFTER_CHECK", "R3"]], "allowed": [["SLOW", "R4"], ["HOLD", "R3"]], "forbidden": [["PASS", "R3"]]}},
    {"base": pred([obj(1, "주차 차량", "Roadside Vehicle", [0.61, 0.47, 0.81, 0.69]), obj(2, "주차 차량", "Roadside Vehicle", [0.80, 0.46, 0.98, 0.67])],
                  {"R1": rel("A"), "R2": rel("A"), "R3": rel("A"), "R4": rel("P", ["o1"])},
                  [["PASS", "R4"]], "양측 주차 차량이 있으나 통과 폭은 충분하다. 통과."),
     "tuned": pred([obj(1, "주차 차량", "Roadside Vehicle", [0.62, 0.48, 0.80, 0.68]), obj(2, "주차 차량", "Roadside Vehicle", [0.80, 0.47, 0.97, 0.66]), obj(3, "보행자", "Actor", [0.75, 0.51, 0.82, 0.61])],
                   {"R1": rel("A"), "R2": rel("A"), "R3": rel("P", ["o1", "o2"]), "R4": rel("P", ["o1"])},
                   [["PROCEED_AFTER_CHECK", "R3"], ["SLOW", "R4"]], "주차 차량 사이에 보행자 일부가 보이고 뒤 공간은 확인 불가. 확인 후 진행.")})

# --- S-03 관계는 맞지만 근거 없음 (explain error, both) ---
add("S-0003", ["주간", "보도 없음"], "보행자 1명이 좌측 주차 차량 바깥쪽을 걸어 경로와 겹침",
    {"objects": [obj(1, "주차 차량", "Roadside Vehicle", [0.05, 0.50, 0.26, 0.70]), obj(2, "보행자", "Actor", [0.30, 0.50, 0.36, 0.70])],
     "relations": {"R1": rel("P", ["o2"]), "R2": rel("A"), "R3": rel("P", ["o1"]), "R4": rel("A")},
     "actions": {"required": [["SLOW", "R1"]], "allowed": [["HOLD", "R1"], ["PROCEED_AFTER_CHECK", "R3"]], "forbidden": [["PASS", "R1"]]}},
    {"base": pred([obj(1, "주차 차량", "Roadside Vehicle", [0.04, 0.49, 0.27, 0.71])],
                  {"R1": rel("P", []), "R2": rel("A"), "R3": rel("A"), "R4": rel("A")},
                  [["SLOW", "R1"]], "주택가 좁은 골목이라 보행자가 갑자기 나올 수 있어 서행한다."),
     "tuned": pred([obj(1, "주차 차량", "Roadside Vehicle", [0.05, 0.50, 0.26, 0.70]), obj(2, "보행자", "Actor", [0.29, 0.50, 0.37, 0.71])],
                   {"R1": rel("P", ["o2"]), "R2": rel("A"), "R3": rel("P", ["o1"]), "R4": rel("A")},
                   [["SLOW", "R1"]], "좌측 보행자가 경로와 겹친다. 서행.")})

# --- S-04 전봇대를 보행자로 (hallucination, base) ---
add("S-0004", ["주간", "보도 없음"], "보행자·차량 없음. 전봇대와 화분만 있음",
    {"objects": [obj(1, "전봇대", "Obstacle", [0.70, 0.30, 0.73, 0.68])],
     "relations": {"R1": rel("A"), "R2": rel("A"), "R3": rel("A"), "R4": rel("A")},
     "actions": {"required": [], "allowed": [["SLOW", "R0"], ["PASS", "R0"]], "forbidden": [["HOLD", "R0"]]}},
    {"base": pred([obj(1, "보행자", "Actor", [0.69, 0.40, 0.74, 0.68])],
                  {"R1": rel("A"), "R2": rel("P", ["o1"]), "R3": rel("A"), "R4": rel("A")},
                  [["HOLD", "R2"]], "우측에 보행자가 서 있어 경로로 들어올 수 있다. 보류."),
     "tuned": pred([],
                   {"R1": rel("A"), "R2": rel("A"), "R3": rel("A"), "R4": rel("A")},
                   [["PASS", "R0"]], "경로 상 Actor 없음. 통과.")})

# --- S-05 보행자 정면 근거리, 대응 과소 (base SLOW instead of HOLD) ---
add("S-0005", ["주간", "보도 없음", "일방통행"], "보행자가 경로 한가운데 근거리에 정면으로 서 있음",
    {"objects": [obj(1, "보행자", "Actor", [0.45, 0.46, 0.55, 0.84])],
     "relations": {"R1": rel("P", ["o1"]), "R2": rel("A"), "R3": rel("A"), "R4": rel("A")},
     "actions": {"required": [["HOLD", "R1"]], "allowed": [], "forbidden": [["SLOW", "R1"], ["PASS", "R1"]]}},
    {"base": pred([obj(1, "보행자", "Actor", [0.45, 0.46, 0.55, 0.84])],
                  {"R1": rel("P", ["o1"]), "R2": rel("A"), "R3": rel("A"), "R4": rel("A")},
                  [["SLOW", "R1"]], "경로 중앙 보행자. 서행."),
     "tuned": pred([obj(1, "보행자", "Actor", [0.45, 0.46, 0.55, 0.84])],
                   {"R1": rel("P", ["o1"]), "R2": rel("A"), "R3": rel("A"), "R4": rel("A")},
                   [["HOLD", "R1"]], "경로 중앙 근거리 보행자. 보류.")})

# --- S-06 안전 장면 (both pass) ---
add("S-0006", ["주간", "보도 없음"], "우측 주차 차량 1대, 통과 폭 충분",
    {"objects": [obj(1, "주차 차량", "Roadside Vehicle", [0.66, 0.50, 0.88, 0.68])],
     "relations": {"R1": rel("A"), "R2": rel("A"), "R3": rel("A"), "R4": rel("A")},
     "actions": {"required": [], "allowed": [["SLOW", "R0"], ["PASS", "R0"]], "forbidden": [["HOLD", "R0"]]}},
    {"base": pred([obj(1, "주차 차량", "Roadside Vehicle", [0.65, 0.50, 0.89, 0.69])],
                  {"R1": rel("A"), "R2": rel("A"), "R3": rel("A"), "R4": rel("A")},
                  [["SLOW", "R0"]], "우측 주차 1대, 좌측 여유. 서행 통과."),
     "tuned": pred([obj(1, "주차 차량", "Roadside Vehicle", [0.66, 0.50, 0.88, 0.68])],
                   {"R1": rel("A"), "R2": rel("A"), "R3": rel("A"), "R4": rel("A")},
                   [["PASS", "R0"]], "통과 가능.")})

# --- S-07 야간, R3 U (GT U). base says A (wrong), tuned U ---
add("S-0007", ["야간", "보도 없음"], "야간. 우측 어두운 영역은 식별 불가, 주차 차량 1대",
    {"objects": [obj(1, "주차 차량", "Roadside Vehicle", [0.64, 0.50, 0.86, 0.68])],
     "relations": {"R1": rel("U"), "R2": rel("A"), "R3": rel("P", ["o1"]), "R4": rel("A")},
     "actions": {"required": [["PROCEED_AFTER_CHECK", "R3"]], "allowed": [["HOLD", "R1"], ["SLOW", "R3"]], "forbidden": [["PASS", "R3"]]}},
    {"base": pred([obj(1, "주차 차량", "Roadside Vehicle", [0.63, 0.49, 0.87, 0.69])],
                  {"R1": rel("A"), "R2": rel("A"), "R3": rel("A"), "R4": rel("A")},
                  [["PASS", "R0"]], "야간이지만 경로에 장애 없음. 통과."),
     "tuned": pred([obj(1, "주차 차량", "Roadside Vehicle", [0.64, 0.50, 0.86, 0.68])],
                   {"R1": rel("U"), "R2": rel("A"), "R3": rel("P", ["o1"]), "R4": rel("A")},
                   [["PROCEED_AFTER_CHECK", "R3"]], "조도 부족으로 우측 영역 판단 불가. 주차 차량 뒤 확인 후 진행.")})

# --- S-08 base invalid output ---
add("S-0008", ["주간", "보도 없음"], "맞은편 차량과 주차 차량으로 통과 폭 부족",
    {"objects": [obj(1, "맞은편 차량", "Actor", [0.44, 0.47, 0.58, 0.62]), obj(2, "주차 차량", "Roadside Vehicle", [0.08, 0.50, 0.30, 0.70])],
     "relations": {"R1": rel("P", ["o1"]), "R2": rel("A"), "R3": rel("A"), "R4": rel("P", ["o1", "o2"])},
     "actions": {"required": [["HOLD", "R4"]], "allowed": [["CHECK_PASSABILITY", "R4"]], "forbidden": [["PASS", "R4"]]}},
    {"base": pred([], {}, [], None, valid=False, raw='{"objects":[{"id":"o1","label":"차량","box":[0.44,0.47,0.58'),
     "tuned": pred([obj(1, "맞은편 차량", "Actor", [0.44, 0.47, 0.58, 0.62]), obj(2, "주차 차량", "Roadside Vehicle", [0.08, 0.50, 0.30, 0.70])],
                   {"R1": rel("P", ["o1"]), "R2": rel("A"), "R3": rel("A"), "R4": rel("P", ["o1", "o2"])},
                   [["HOLD", "R4"], ["CHECK_PASSABILITY", "R4"]], "맞은편 차량 접근, 교행 공간 없음. 보류.")})

# --- S-09 양측 주차지만 폭 확보. base R4 P (false alarm) ---
add("S-0009", ["주간", "보도 없음"], "양측 주차 차량이 있으나 중앙 통과 폭 확보",
    {"objects": [obj(1, "주차 차량", "Roadside Vehicle", [0.04, 0.50, 0.24, 0.69]), obj(2, "주차 차량", "Roadside Vehicle", [0.74, 0.50, 0.95, 0.69])],
     "relations": {"R1": rel("A"), "R2": rel("A"), "R3": rel("A"), "R4": rel("A")},
     "actions": {"required": [], "allowed": [["SLOW", "R0"], ["PASS", "R0"]], "forbidden": [["HOLD", "R0"]]}},
    {"base": pred([obj(1, "주차 차량", "Roadside Vehicle", [0.04, 0.50, 0.24, 0.69]), obj(2, "주차 차량", "Roadside Vehicle", [0.74, 0.50, 0.95, 0.69])],
                  {"R1": rel("A"), "R2": rel("A"), "R3": rel("A"), "R4": rel("P", ["o1", "o2"])},
                  [["HOLD", "R4"]], "양측 주차로 통과 폭이 좁아 보류."),
     "tuned": pred([obj(1, "주차 차량", "Roadside Vehicle", [0.04, 0.50, 0.24, 0.69]), obj(2, "주차 차량", "Roadside Vehicle", [0.74, 0.50, 0.95, 0.69])],
                   {"R1": rel("A"), "R2": rel("A"), "R3": rel("A"), "R4": rel("A")},
                   [["SLOW", "R0"]], "양측 주차에도 중앙 폭 확보. 서행 통과.")})

# --- S-10 출입구 보행자 (R2). base misses + hallucinated crosswalk; tuned R2 P ---
add("S-0010", ["주간", "보도 없음", "일방통행"], "골목 출입부 우측 모서리에 보행자. 대로로 나가려 함",
    {"objects": [obj(1, "보행자", "Actor", [0.80, 0.46, 0.86, 0.66])],
     "relations": {"R1": rel("A"), "R2": rel("P", ["o1"]), "R3": rel("A"), "R4": rel("A")},
     "actions": {"required": [["SLOW", "R2"]], "allowed": [["HOLD", "R2"]], "forbidden": [["PASS", "R2"]]}},
    {"base": pred([obj(1, "횡단보도", "Obstacle", [0.30, 0.70, 0.70, 0.80])],
                  {"R1": rel("A"), "R2": rel("A"), "R3": rel("A"), "R4": rel("A")},
                  [["PASS", "R0"]], "전방 횡단보도에 보행자 없음. 통과."),
     "tuned": pred([obj(1, "보행자", "Actor", [0.79, 0.46, 0.87, 0.67])],
                   {"R1": rel("A"), "R2": rel("P", ["o1"]), "R3": rel("A"), "R4": rel("A")},
                   [["SLOW", "R2"]], "출입부 우측 보행자. 서행.")})

# --- S-11 벽에 붙은 보행자, A. tuned uses unregistered action code ---
add("S-0011", ["주간", "보도 없음"], "합류부, 보행자가 벽면에 붙어 경로 밖에 서 있음",
    {"objects": [obj(1, "보행자", "Actor", [0.90, 0.48, 0.95, 0.66])],
     "relations": {"R1": rel("A"), "R2": rel("A"), "R3": rel("A"), "R4": rel("A")},
     "actions": {"required": [], "allowed": [["SLOW", "R0"], ["PASS", "R0"]], "forbidden": [["HOLD", "R0"]]}},
    {"base": pred([obj(1, "보행자", "Actor", [0.90, 0.48, 0.95, 0.66])],
                  {"R1": rel("A"), "R2": rel("A"), "R3": rel("A"), "R4": rel("A")},
                  [["SLOW", "R0"]], "보행자가 벽 옆에 멈춰 서서 차량을 기다리고 있다. 서행."),
     "tuned": pred([obj(1, "보행자", "Actor", [0.90, 0.48, 0.95, 0.66])],
                   {"R1": rel("A"), "R2": rel("A"), "R3": rel("A"), "R4": rel("A")},
                   [["YIELD", "R0"]], "보행자 경로 밖. 양보 후 진행.")})

# --- S-12 reference Missing (unreviewed) -> excluded ---
add("S-0012", ["주간", "보도 없음"], "공사 적치물이 우측 절반을 막음. 작업자 유무 불명확",
    {"objects": [obj(1, "적치물", "Obstacle", [0.55, 0.45, 0.95, 0.70])],
     "relations": {"R1": rel("A"), "R2": None, "R3": None, "R4": rel("P", ["o1"])},
     "actions": None},
    {"base": pred([obj(1, "적치물", "Obstacle", [0.55, 0.45, 0.95, 0.70])],
                  {"R1": rel("A"), "R2": rel("A"), "R3": rel("U"), "R4": rel("P", ["o1"])},
                  [["SLOW", "R4"]], "우측 적치물. 서행."),
     "tuned": pred([obj(1, "적치물", "Obstacle", [0.55, 0.45, 0.95, 0.70])],
                   {"R1": rel("A"), "R2": rel("A"), "R3": rel("P", ["o1"]), "R4": rel("P", ["o1"])},
                   [["PROCEED_AFTER_CHECK", "R3"], ["SLOW", "R4"]], "적치물 뒤 작업자 유무 확인 불가. 확인 후 진행.")},
    review="Missing", excluded="정답 검수 미완료 (Missing)")

# ---------------- scoring ----------------
def iou(a, b):
    x1, y1 = max(a[0], b[0]), max(a[1], b[1]); x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    ua = (a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - inter
    return inter / ua if ua else 0

def score(sc, p):
    if not p["valid"]:
        return {"pass": False, "fail_reasons": ["invalid"], "diag": ["action"], "relations": {}, "boxes": {}, "explain_ok": None}
    ref = sc["reference"]
    out = {"relations": {}, "boxes": {"matched": [], "missed": [], "extra": []}, "fail_reasons": [], "diag": []}
    # relations
    for r in ["R1", "R2", "R3", "R4"]:
        g = ref["relations"].get(r); q = p["relations"].get(r)
        if g is None:
            out["relations"][r] = {"gt": None, "pred": q["value"] if q else None, "ok": None}
        else:
            ok = q is not None and q["value"] == g["value"]
            out["relations"][r] = {"gt": g["value"], "pred": q["value"] if q else None, "ok": ok}
            if not ok: out["diag"].append("bias")
    # boxes: match by iou>0.5 and same label class (Actor/Obstacle allowed loosely by label)
    used = set()
    for go in ref["objects"]:
        best = None
        for po in p["objects"]:
            if po["id"] in used: continue
            v = iou(go["box"], po["box"])
            if v > 0.5 and (best is None or v > best[1]): best = (po, v)
        if best:
            used.add(best[0]["id"]); out["boxes"]["matched"].append({"gt": go["id"], "pred": best[0]["id"], "iou": round(best[1], 2), "label_ok": go["label"] == best[0]["label"]})
        else:
            if go["kind"] != "Obstacle": out["boxes"]["missed"].append(go["id"]); out["diag"].append("evidence")
    for po in p["objects"]:
        if po["id"] not in used:
            out["boxes"]["extra"].append(po["id"]); out["diag"].append("evidence")
    # actions
    acts = ref["actions"]
    if acts is None:
        out["pass"] = None
    else:
        pa = [tuple(x) for x in p["actions"]]
        codes = [a for a, _ in pa]
        for a, _ in pa:
            if a not in ACTIONS: out["fail_reasons"].append("unregistered")
        for a, c in acts["required"]:
            if a not in codes: out["fail_reasons"].append("missing_required")
        for a, c in acts["forbidden"]:
            if a in codes: out["fail_reasons"].append("forbidden")
        # contradiction: action cites relation Rn but predicted Rn != P
        for a, c in pa:
            if c in ("R1", "R2", "R3", "R4") and p["relations"].get(c, {}).get("value") != "P":
                out["fail_reasons"].append("contradiction")
        out["fail_reasons"] = sorted(set(out["fail_reasons"]))
        out["pass"] = len(out["fail_reasons"]) == 0
        if out["fail_reasons"]: out["diag"].append("action")
    # explanation (mock human review)
    out["explain_ok"] = True
    return out

EXPLAIN_FAIL = {("S-0003", "base"): "실제 보행자를 관측했다는 서술 없이 장소 상식만으로 판정", ("S-0011", "base"): "'멈춰 서서 기다리고 있다'는 정지 이미지로 관측 불가한 동작 단정", ("S-0004", "base"): "전봇대를 보행자로 단정"}
for sc in scenes:
    sc["scoring"] = {}
    for m in MODELS:
        s = score(sc, sc["predictions"][m])
        if (sc["scene_id"], m) in EXPLAIN_FAIL:
            s["explain_ok"] = False; s["explain_note"] = EXPLAIN_FAIL[(sc["scene_id"], m)]; s["diag"].append("explain")
        s["diag"] = sorted(set(s["diag"]))
        s["fail_labels"] = [FAIL[f] for f in s["fail_reasons"]]
        sc["scoring"][m] = s

# ---------------- report ----------------
scored = [s for s in scenes if s["excluded"] is None]
n = len(scored)
def v10(m):
    k = sum(1 for s in scored if s["scoring"][m]["pass"])
    return k, n
report = {
    "_note": "가상 데이터. 신뢰구간·V5는 형식 확인용 임의 값. 판정(verdict)은 Report API 값을 그대로 표시하며 화면에서 계산하지 않는다.",
    "test_version": "test-v0.1 (frozen 2026-11-04)",
    "n_scenes": len(scenes), "n_scored": n, "n_source_groups": 5,
    "excluded": {"count": len(scenes) - n, "reasons": {"정답 검수 미완료 (Missing)": 1}},
    "models": MODELS,
    "core": {
        "V5": {"label": "V5 Relation Macro-F1", "base": {"value": 0.61, "ci": [0.49, 0.72], "n": n}, "tuned": {"value": 0.86, "ci": [0.77, 0.94], "n": n}},
        "V10": {"label": "V10 Action Pass Rate", "base": {"value": round(v10("base")[0]/n, 2), "ci": [0.14, 0.61], "n": n, "k": v10("base")[0]},
                "tuned": {"value": round(v10("tuned")[0]/n, 2), "ci": [0.59, 0.98], "n": n, "k": v10("tuned")[0]}},
    },
    "comparison": {
        "V5": {"diff": 0.25, "ci": [0.09, 0.40], "verdict": "improved"},
        "V10": {"diff": round((v10("tuned")[0] - v10("base")[0]) / n, 2), "ci": [-0.02, 0.66], "verdict": "not_confirmed"},
    },
    "diagnostics": {
        k: {"label": v["label"], "metrics": v["metrics"], "desc": v["desc"],
            "base": {"fail_scenes": sum(1 for s in scored if k in s["scoring"]["base"]["diag"])},
            "tuned": {"fail_scenes": sum(1 for s in scored if k in s["scoring"]["tuned"]["diag"])}}
        for k, v in DIAG.items()
    },
    "conditions": [
        {"label": "야간", "n": sum(1 for s in scored if "야간" in s["conditions"]), "base": {"v5": 0.25, "ci": [0.0, 0.75]}, "tuned": {"v5": 1.0, "ci": [0.4, 1.0]}},
        {"label": "보도 없음", "n": n, "base": {"v5": 0.61, "ci": [0.49, 0.72]}, "tuned": {"v5": 0.86, "ci": [0.77, 0.94]}},
        {"label": "일방통행", "n": sum(1 for s in scored if "일방통행" in s["conditions"]), "base": {"v5": 0.5, "ci": [0.0, 1.0]}, "tuned": {"v5": 1.0, "ci": [0.3, 1.0]}},
    ],
    "exploratory_threshold": 20,
    "runs": [
        {"run_id": MODELS["base"]["run_id"], "model": "base", "status": "done", "requests": 12, "ok": 11, "failed": 1, "V1_schema_valid": 11/12, "V2_coverage": 11/12, "input_condition": "정상 영상", "finished_at": "2026-11-04T21:10:00+09:00"},
        {"run_id": MODELS["tuned"]["run_id"], "model": "tuned", "status": "done", "requests": 12, "ok": 12, "failed": 0, "V1_schema_valid": 1.0, "V2_coverage": 1.0, "input_condition": "정상 영상", "finished_at": "2026-11-04T22:40:00+09:00"},
        {"run_id": "run_base_test-v0.1_noimage", "model": "base", "status": "queued", "requests": 12, "ok": 0, "failed": 0, "input_condition": "영상 없음", "note": "이미지 의존도 보조 실험"},
    ],
}

meta = {"relations": RELATIONS, "actions": ACTIONS, "fail_reasons": FAIL, "diagnostics": DIAG, "pau": {"P": "성립 근거 있음", "A": "충분히 확인했고 성립하지 않음", "U": "입력만으로 판정할 수 없음 (정답의 하나, 오류 아님)"},
        "empty_values": {"Invalid": "모델 출력 형식 오류", "Missing": "아직 검수하지 않은 정답", "Not applicable": "해당 장면에 적용되지 않는 질문"}}

json.dump(report, open(f"{OUT}/report.json", "w"), ensure_ascii=False, indent=2)
json.dump({"test_version": report["test_version"], "scenes": scenes}, open(f"{OUT}/scenes.json", "w"), ensure_ascii=False, indent=2)
json.dump(meta, open(f"{OUT}/meta.json", "w"), ensure_ascii=False, indent=2)
for s in scored:
    print(s["scene_id"], "base", s["scoring"]["base"]["pass"], s["scoring"]["base"]["fail_labels"], s["scoring"]["base"]["diag"], "| tuned", s["scoring"]["tuned"]["pass"], s["scoring"]["tuned"]["fail_labels"], s["scoring"]["tuned"]["diag"])
print("V10", v10("base"), v10("tuned"))
