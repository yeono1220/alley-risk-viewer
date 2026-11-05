# -*- coding: utf-8 -*-
"""Mock data for the Web Viewer, following 국내 생활도로 VLM 평가 벤치마크 및 개발 명세서 (Track 1).
All numbers are fabricated for layout/flow checks. Scoring here mirrors App.A/B rules but the
backend 자동 채점기 is the source of truth."""
import json, os
OUT = os.path.dirname(os.path.abspath(__file__))

ACTIONS = {
    "VERIFY_BEFORE_ADVANCE": "확인 후 진행", "REDUCE_SPEED_IF_MOVING": "이동 중이면 감속",
    "YIELD_IF_OCCUPIED": "점유 시 양보", "HOLD_UNTIL_CLEAR": "해소될 때까지 보류",
    "VERIFY_PASSAGE": "통과 가능성 확인", "MONITOR_AHEAD": "전방 관찰", "ADVANCE_WITH_MONITORING": "관찰하며 진행",
}
CONDITIONS = {
    "no_condition": {"label": "조건 없음", "needs": None},
    "while_corridor_occupied": {"label": "점유 동안", "needs": ("R1", ["P"])},
    "while_actor_near_entrance": {"label": "출입구 주변 Actor 있는 동안", "needs": ("R2", ["P"])},
    "before_entering_occluded_area": {"label": "가려진 영역 진입 전", "needs": ("R3", ["P"])},
    "before_passing_restricted_section": {"label": "좁아진 구간 통과 전", "needs": ("R4", ["P", "U"])},
    "before_resolving_uncertainty": {"label": "불확실성 확인 전", "needs": ("R1R2R3", ["U"])},
}
RELATIONS = {
    "R1": {"label": "점유", "q": "보이는 Actor·Obstacle이 C를 점유하는가"},
    "R2": {"label": "출입구", "q": "C와 이어지는 출입구 주변에 보이는 Actor가 있는가"},
    "R3": {"label": "시야 가림", "q": "진행 판단에 필요한 영역이 가려졌는가"},
    "R4": {"label": "통행 제한", "q": "배치가 C 구간의 통행 공간을 제한하는가"},
}
FAIL = {
    "invalid": "형식 오류", "missing_required": "필요 대응 누락", "forbidden": "금지 대응",
    "unsupported": "근거가 확인되지 않은 대응", "contradiction": "관계 판정과의 모순",
}
DIAG = {
    "evidence": {"label": "근거 정합성", "metrics": "V3 · V4", "desc": "Box 짝짓기(IoU≥0.5) 실패 · 근거 ID 불일치"},
    "bias": {"label": "판단 편향", "metrics": "V6–V9", "desc": "있는 관계 놓침 · 없는 관계 단정 · U 처리"},
    "action": {"label": "대응 결함", "metrics": "V11 · V12", "desc": "필요 대응 누락 · 금지 대응"},
    "explain": {"label": "설명문 환각", "metrics": "V13 · V14", "desc": "근거 없이 단정한 진술"},
}
MODELS = {
    "base": {"id": "google/gemma-4-12b-it", "label": "Base", "desc": "Gemma 4 12B · Zero-shot", "run_id": "run_base_test-v0.1"},
    "tuned": {"id": "team1/gemma-4-12b-alley-lora", "label": "Tuned", "desc": "Gemma 4 12B · LoRA", "run_id": "run_tuned_test-v0.1"},
}
C_DEFAULT = [[0.42, 0.52], [0.58, 0.52], [0.92, 1.0], [0.08, 1.0]]
SCENE_DEFAULT = {"sidewalk_left": "A", "sidewalk_right": "A", "traffic_direction": "Unknown", "direction_match": "Unknown"}

def obj(i, cls, box, placement=None, kind=None):
    k = kind or ("Obstacle" if cls in ("obstacle", "pole", "cone", "construction") else "Actor")
    o = {"id": f"o{i}", "class": cls, "kind": k, "bbox": box}
    if placement: o["placement"] = placement
    return o
def region(i, cls, box): return {"id": f"z{i}", "class": cls, "bbox": box}
def rel(code, state, evidence=None): return {"code": code, "state": state, "evidence": evidence or []}
def act(code, cond, based_on=None): return {"code": code, "condition": cond, "based_on": based_on or []}
def R(r1, r2, r3, r4, ev=None):
    ev = ev or {}
    return [rel("R1", r1, ev.get("R1")), rel("R2", r2, ev.get("R2")), rel("R3", r3, ev.get("R3")), rel("R4", r4, ev.get("R4"))]
def rmap(rels): return {r["code"]: r for r in rels}

# ---------- App.B.2: derive 필요 묶음 / 허용 / 금지 from GT relations ----------
def derive_actions(ref):
    rm = rmap(ref["relations"]); objs = {o["id"]: o for o in ref["objects"]}
    groups, allowed, forbidden = [], set(), set()
    st = {k: rm[k]["state"] for k in rm}
    if ref["scene"].get("direction_match") == "Conflicting":
        return None  # App.B.3: excluded from action evaluation
    if st["R1"] == "P":
        movable = [e for e in rm["R1"]["evidence"] if e in objs and objs[e]["kind"] == "Actor" and objs[e].get("placement") != "roadside"]
        if movable:
            groups.append({"why": "R1=P 움직일 수 있는 Actor 점유", "alts": [["YIELD_IF_OCCUPIED", "while_corridor_occupied"], ["HOLD_UNTIL_CLEAR", "while_corridor_occupied"]]})
            allowed.add(("REDUCE_SPEED_IF_MOVING", "while_corridor_occupied"))
        else:
            groups.append({"why": "R1=P Obstacle·Roadside Vehicle 점유 → R4 행 적용", "alts": [["VERIFY_PASSAGE", "before_passing_restricted_section"]]})
            allowed.add(("HOLD_UNTIL_CLEAR", "while_corridor_occupied"))
    if st["R2"] == "P":
        groups.append({"why": "R2=P", "alts": [["MONITOR_AHEAD", "while_actor_near_entrance"], ["REDUCE_SPEED_IF_MOVING", "while_actor_near_entrance"]]})
    if st["R3"] == "P":
        groups.append({"why": "R3=P", "alts": [["VERIFY_BEFORE_ADVANCE", "before_entering_occluded_area"]]})
        allowed.add(("REDUCE_SPEED_IF_MOVING", "before_entering_occluded_area"))
    if st["R4"] in ("P", "U"):
        g = {"why": "R4=%s" % st["R4"], "alts": [["VERIFY_PASSAGE", "before_passing_restricted_section"]]}
        if not any(x["why"].endswith("R4 행 적용") for x in groups): groups.append(g)
    if any(st[k] == "U" for k in ("R1", "R2", "R3")):
        groups.append({"why": "R1·R2·R3 중 U", "alts": [["VERIFY_BEFORE_ADVANCE", "before_resolving_uncertainty"]]})
    if all(st[k] == "A" for k in ("R1", "R2", "R3", "R4")):
        groups.append({"why": "R1–R4 모두 A", "alts": [["MONITOR_AHEAD", "no_condition"], ["ADVANCE_WITH_MONITORING", "no_condition"]]})
        forbidden.add(("HOLD_UNTIL_CLEAR", "no_condition"))
    else:
        forbidden.add(("ADVANCE_WITH_MONITORING", "no_condition"))
    for g in groups:
        for a in g["alts"]: allowed.add(tuple(a))
    return {"required_groups": groups, "allowed": sorted([list(a) for a in allowed]), "forbidden": sorted([list(f) for f in forbidden])}

# ---------- scenes ----------
scenes = []
def add(sid, cond, scene_desc, objects, rels, preds, regions=None, scene=None, C=None, review="Reviewed", missing=None, group="G1"):
    ref = {"objects": objects, "regions": regions or [], "scene": {**SCENE_DEFAULT, **(scene or {})}, "relations": rels, "source": "사진", "review_status": review}
    ref["actions"] = None if missing else derive_actions(ref)
    scenes.append({"scene_id": sid, "source_group": group, "conditions": cond, "scene": scene_desc, "C": C or C_DEFAULT,
                   "reference": ref, "predictions": preds, "missing": missing})
def pred(objects, rels, actions, explanation, regions=None, scene=None, valid=True, raw=None):
    return {"valid": valid, "objects": objects, "regions": regions or [], "scene": {**SCENE_DEFAULT, **(scene or {})},
            "relations": rels, "actions": actions, "explanation": explanation, "raw_excerpt": raw}

# S-0001 보행자 2명 C 중앙 — both pass
add("S-0001", ["주간", "보도 없음"], "보행자 2명이 통행 경로 중앙을 걷고 있음",
    [obj(1, "pedestrian", [0.44, 0.50, 0.50, 0.72]), obj(2, "pedestrian", [0.51, 0.49, 0.57, 0.71])],
    R("P", "A", "A", "A", {"R1": ["o1", "o2"]}),
    {"base": pred([obj(1, "pedestrian", [0.43, 0.50, 0.51, 0.73]), obj(2, "pedestrian", [0.50, 0.48, 0.58, 0.72])], R("P", "A", "A", "A", {"R1": ["o1", "o2"]}),
                  [act("HOLD_UNTIL_CLEAR", "while_corridor_occupied", ["R1"])], "경로 중앙에 보행자 2명이 있어 해소될 때까지 보류한다."),
     "tuned": pred([obj(1, "pedestrian", [0.44, 0.50, 0.50, 0.72]), obj(2, "pedestrian", [0.51, 0.49, 0.57, 0.71])], R("P", "A", "A", "A", {"R1": ["o1", "o2"]}),
                   [act("YIELD_IF_OCCUPIED", "while_corridor_occupied", ["R1"])], "경로 중앙에 보행자 2명. 점유 동안 양보.")}, group="G1")

# S-0002 길가 차량이 출입구 z1 가림 + 사이로 어린이 — base misses child & R3
add("S-0002", ["주간", "보도 없음"], "우측 길가 차량 두 대가 건물 출입구를 가리고, 그 사이로 어린이 상반신이 보임",
    [obj(1, "vehicle", [0.62, 0.48, 0.80, 0.68], "roadside"), obj(2, "vehicle", [0.80, 0.47, 0.97, 0.66], "roadside"), obj(3, "pedestrian", [0.76, 0.52, 0.81, 0.60])],
    R("A", "A", "P", "P", {"R3": ["o1", "o2", "z1"], "R4": ["o1"]}), regions=[region(1, "occluded_entrance", [0.70, 0.30, 0.86, 0.60])],
    preds={"base": pred([obj(1, "vehicle", [0.61, 0.47, 0.81, 0.69], "roadside"), obj(2, "vehicle", [0.80, 0.46, 0.98, 0.67], "roadside")], R("A", "A", "A", "P", {"R4": ["o1"]}),
                  [act("ADVANCE_WITH_MONITORING", "no_condition")], "양측에 주차 차량이 있으나 통과 폭은 충분하다. 관찰하며 진행."),
     "tuned": pred([obj(1, "vehicle", [0.62, 0.48, 0.80, 0.68], "roadside"), obj(2, "vehicle", [0.80, 0.47, 0.97, 0.66], "roadside"), obj(3, "pedestrian", [0.75, 0.51, 0.82, 0.61])],
                   R("A", "A", "P", "P", {"R3": ["o1", "o2", "z1"], "R4": ["o1"]}), regions=[region(1, "occluded_entrance", [0.70, 0.31, 0.86, 0.60])],
                   actions=[act("VERIFY_BEFORE_ADVANCE", "before_entering_occluded_area", ["R3"]), act("VERIFY_PASSAGE", "before_passing_restricted_section", ["R4"])],
                   explanation="길가 차량 사이에 보행자 일부가 보이고 출입구는 가려져 있다. 가려진 영역 앞에서 확인 후 진행, 좁아진 구간은 통과 가능성 확인.")}, group="G2")

# S-0003 관계는 맞지만 근거 없음 — base explanation error, evidence miss
add("S-0003", ["주간", "보도 없음"], "보행자 1명이 좌측 길가 차량 바깥쪽을 걸어 C와 겹침",
    [obj(1, "vehicle", [0.05, 0.50, 0.26, 0.70], "roadside"), obj(2, "pedestrian", [0.30, 0.50, 0.36, 0.70])],
    R("P", "A", "P", "A", {"R1": ["o2"], "R3": ["o1", "z1"]}), regions=[region(1, "occluded_entrance", [0.02, 0.28, 0.16, 0.55])],
    preds={"base": pred([obj(1, "vehicle", [0.04, 0.49, 0.27, 0.71], "roadside")], R("P", "A", "A", "A", {"R1": ["o1"]}),
                  [act("REDUCE_SPEED_IF_MOVING", "while_corridor_occupied", ["R1"])], "주택가 좁은 골목이라 보행자가 갑자기 나올 수 있어 감속한다."),
     "tuned": pred([obj(1, "vehicle", [0.05, 0.50, 0.26, 0.70], "roadside"), obj(2, "pedestrian", [0.29, 0.50, 0.37, 0.71])], R("P", "A", "P", "A", {"R1": ["o2"], "R3": ["o1", "z1"]}),
                   regions=[region(1, "occluded_entrance", [0.02, 0.28, 0.16, 0.55])],
                   actions=[act("YIELD_IF_OCCUPIED", "while_corridor_occupied", ["R1"]), act("VERIFY_BEFORE_ADVANCE", "before_entering_occluded_area", ["R3"])],
                   explanation="좌측 보행자가 C와 겹친다. 양보. 길가 차량이 출입구를 가려 확인 후 진행.")}, group="G2")

# S-0004 전봇대를 보행자로 — base hallucination
add("S-0004", ["주간", "보도 없음"], "보행자·차량 없음. 전봇대와 화분만 있음",
    [obj(1, "pole", [0.70, 0.30, 0.73, 0.68])], R("A", "A", "A", "A"),
    preds={"base": pred([obj(1, "pedestrian", [0.69, 0.40, 0.74, 0.68])], R("A", "P", "A", "A", {"R2": ["o1"]}),
                  [act("MONITOR_AHEAD", "while_actor_near_entrance", ["R2"])], "우측에 보행자가 서 있어 출입구 주변을 관찰한다."),
     "tuned": pred([], R("A", "A", "A", "A"), [act("ADVANCE_WITH_MONITORING", "no_condition")], "C 안과 출입구 주변에 Actor 없음. 관찰하며 진행.")}, group="G3")

# S-0005 보행자 정면 근거리 — base 감속만 (필요 묶음 누락)
add("S-0005", ["주간", "보도 없음", "일방통행"], "보행자가 C 한가운데 근거리에 정면으로 서 있음",
    [obj(1, "pedestrian", [0.45, 0.46, 0.55, 0.84]), obj(2, "sign_oneway", [0.08, 0.20, 0.12, 0.26], kind="Obstacle")],
    R("P", "A", "A", "A", {"R1": ["o1"]}), scene={"traffic_direction": "One-way", "direction_match": "Consistent"},
    preds={"base": pred([obj(1, "pedestrian", [0.45, 0.46, 0.55, 0.84])], R("P", "A", "A", "A", {"R1": ["o1"]}),
                  [act("REDUCE_SPEED_IF_MOVING", "while_corridor_occupied", ["R1"])], "C 중앙 보행자. 감속.", scene={"traffic_direction": "Unknown"}),
     "tuned": pred([obj(1, "pedestrian", [0.45, 0.46, 0.55, 0.84]), obj(2, "sign_oneway", [0.08, 0.20, 0.12, 0.26], kind="Obstacle")], R("P", "A", "A", "A", {"R1": ["o1"]}),
                   [act("HOLD_UNTIL_CLEAR", "while_corridor_occupied", ["R1"])], "C 중앙 근거리 보행자. 해소될 때까지 보류.", scene={"traffic_direction": "One-way", "direction_match": "Consistent"})}, group="G3")

# S-0006 안전 장면 — both pass
add("S-0006", ["주간", "보도 없음"], "우측 길가 차량 1대, 통행 공간 제한 없음",
    [obj(1, "vehicle", [0.66, 0.50, 0.88, 0.68], "roadside")], R("A", "A", "A", "A"),
    preds={"base": pred([obj(1, "vehicle", [0.65, 0.50, 0.89, 0.69], "roadside")], R("A", "A", "A", "A"), [act("MONITOR_AHEAD", "no_condition")], "우측 길가 차량 1대, 좌측 여유. 전방 관찰."),
     "tuned": pred([obj(1, "vehicle", [0.66, 0.50, 0.88, 0.68], "roadside")], R("A", "A", "A", "A"), [act("ADVANCE_WITH_MONITORING", "no_condition")], "관찰하며 진행.")}, group="G4")

# S-0007 야간 — GT R1=U, R3=P. base A/A, tuned correct
add("S-0007", ["야간", "보도 없음"], "야간. 우측 어두운 영역은 식별 불가, 길가 차량 1대가 영역을 가림",
    [obj(1, "vehicle", [0.64, 0.50, 0.86, 0.68], "roadside")], R("U", "A", "P", "A", {"R3": ["o1", "z1"]}), regions=[region(1, "occluded_area", [0.86, 0.35, 1.0, 0.75])],
    preds={"base": pred([obj(1, "vehicle", [0.63, 0.49, 0.87, 0.69], "roadside")], R("A", "A", "A", "A"), [act("ADVANCE_WITH_MONITORING", "no_condition")], "야간이지만 경로에 장애 없음. 관찰하며 진행."),
     "tuned": pred([obj(1, "vehicle", [0.64, 0.50, 0.86, 0.68], "roadside")], R("U", "A", "P", "A", {"R3": ["o1", "z1"]}), regions=[region(1, "occluded_area", [0.86, 0.35, 1.0, 0.75])],
                   actions=[act("VERIFY_BEFORE_ADVANCE", "before_entering_occluded_area", ["R3"]), act("VERIFY_BEFORE_ADVANCE", "before_resolving_uncertainty", ["R1"])],
                   explanation="조도 부족으로 C 우측 점유 여부를 판정할 수 없고, 길가 차량이 우측 영역을 가린다. 확인 후 진행.")}, group="G5")

# S-0008 — base invalid
add("S-0008", ["주간", "보도 없음"], "맞은편 차량과 길가 차량으로 통행 공간 부족",
    [obj(1, "vehicle", [0.44, 0.47, 0.58, 0.62]), obj(2, "vehicle", [0.08, 0.50, 0.30, 0.70], "roadside")],
    R("P", "A", "A", "P", {"R1": ["o1"], "R4": ["o1", "o2"]}),
    preds={"base": pred([], [], [], None, valid=False, raw='{"objects":[{"id":"o1","class":"vehicle","bbox":[0.44,0.47,0.58'),
     "tuned": pred([obj(1, "vehicle", [0.44, 0.47, 0.58, 0.62]), obj(2, "vehicle", [0.08, 0.50, 0.30, 0.70], "roadside")], R("P", "A", "A", "P", {"R1": ["o1"], "R4": ["o1", "o2"]}),
                   [act("HOLD_UNTIL_CLEAR", "while_corridor_occupied", ["R1"]), act("VERIFY_PASSAGE", "before_passing_restricted_section", ["R4"])], "맞은편 차량이 C를 점유하고 교행 공간이 없다. 보류 후 통과 가능성 확인.")}, group="G4")

# S-0009 양측 주차지만 폭 확보 — base R4 false positive
add("S-0009", ["주간", "보도 없음"], "양측 길가 차량이 있으나 통행 공간 제한 없음",
    [obj(1, "vehicle", [0.04, 0.50, 0.24, 0.69], "roadside"), obj(2, "vehicle", [0.74, 0.50, 0.95, 0.69], "roadside")], R("A", "A", "A", "A"),
    preds={"base": pred([obj(1, "vehicle", [0.04, 0.50, 0.24, 0.69], "roadside"), obj(2, "vehicle", [0.74, 0.50, 0.95, 0.69], "roadside")], R("A", "A", "A", "P", {"R4": ["o1", "o2"]}),
                  [act("VERIFY_PASSAGE", "before_passing_restricted_section", ["R4"])], "양측 주차로 통과 폭이 좁아 통과 가능성 확인."),
     "tuned": pred([obj(1, "vehicle", [0.04, 0.50, 0.24, 0.69], "roadside"), obj(2, "vehicle", [0.74, 0.50, 0.95, 0.69], "roadside")], R("A", "A", "A", "A"),
                   [act("MONITOR_AHEAD", "no_condition")], "양측 길가 차량에도 통행 공간 충분. 전방 관찰.")}, group="G1")

# S-0010 출입구 보행자 (R2) — base misses + hallucinated crosswalk
add("S-0010", ["주간", "보도 없음", "일방통행"], "골목 출입부 우측 모서리에 보행자. 출입구 주변",
    [obj(1, "pedestrian", [0.80, 0.46, 0.86, 0.66]), obj(2, "sign_oneway", [0.90, 0.18, 0.94, 0.24], kind="Obstacle")], R("A", "P", "A", "A", {"R2": ["o1", "z1"]}),
    regions=[region(1, "entrance", [0.74, 0.40, 0.92, 0.66])], scene={"traffic_direction": "One-way", "direction_match": "Consistent"},
    preds={"base": pred([obj(1, "crosswalk", [0.30, 0.70, 0.70, 0.80], kind="Obstacle")], R("A", "A", "A", "A"), [act("ADVANCE_WITH_MONITORING", "no_condition")], "전방 횡단보도에 보행자 없음. 관찰하며 진행."),
     "tuned": pred([obj(1, "pedestrian", [0.79, 0.46, 0.87, 0.67])], R("A", "P", "A", "A", {"R2": ["o1", "z1"]}), regions=[region(1, "entrance", [0.74, 0.40, 0.92, 0.66])],
                   actions=[act("REDUCE_SPEED_IF_MOVING", "while_actor_near_entrance", ["R2"])], explanation="출입구 주변 보행자. 이동 중이면 감속.", scene={"traffic_direction": "One-way", "direction_match": "Consistent"})}, group="G5")

# S-0011 벽에 붙은 보행자, all A — tuned answers an unsupported pair
add("S-0011", ["주간", "보도 없음"], "합류부, 보행자가 벽면에 붙어 C 밖에 서 있음",
    [obj(1, "pedestrian", [0.90, 0.48, 0.95, 0.66])], R("A", "A", "A", "A"),
    preds={"base": pred([obj(1, "pedestrian", [0.90, 0.48, 0.95, 0.66])], R("A", "A", "A", "A"), [act("MONITOR_AHEAD", "no_condition")], "보행자가 벽 옆에 멈춰 서서 차량을 기다리고 있다. 전방 관찰."),
     "tuned": pred([obj(1, "pedestrian", [0.90, 0.48, 0.95, 0.66])], R("A", "A", "A", "A"), [act("YIELD_IF_OCCUPIED", "while_corridor_occupied", ["R1"])], "보행자에게 양보.")}, group="G3")

# S-0012 reference Missing — excluded everywhere
add("S-0012", ["주간", "보도 없음"], "공사 적치물이 우측 절반을 막음. 작업자 유무 불명확",
    [obj(1, "construction", [0.55, 0.45, 0.95, 0.70])], R("A", "A", "U", "P", {"R4": ["o1"]}),
    preds={"base": pred([obj(1, "construction", [0.55, 0.45, 0.95, 0.70])], R("A", "A", "U", "P", {"R4": ["o1"]}), [act("VERIFY_PASSAGE", "before_passing_restricted_section", ["R4"])], "우측 적치물. 통과 가능성 확인."),
     "tuned": pred([obj(1, "construction", [0.55, 0.45, 0.95, 0.70])], R("A", "A", "P", "P", {"R3": ["o1"], "R4": ["o1"]}), [act("VERIFY_BEFORE_ADVANCE", "before_entering_occluded_area", ["R3"]), act("VERIFY_PASSAGE", "before_passing_restricted_section", ["R4"])], "적치물 뒤 확인 후 진행.")},
    review="Draft", missing="정답 검수 미완료 (Draft) — R3 판정 검수자 간 불일치", group="G6")

# S-0013 일방통행 역주행 (Direction Match = Conflicting) — relations scored, actions excluded
add("S-0013", ["주간", "보도 없음", "일방통행"], "일방통행 표지가 진행 방향과 반대. 길가 차량 1대",
    [obj(1, "vehicle", [0.66, 0.50, 0.88, 0.68], "roadside"), obj(2, "sign_oneway_reverse", [0.50, 0.18, 0.54, 0.24], kind="Obstacle")], R("A", "A", "A", "A"),
    scene={"traffic_direction": "One-way", "direction_match": "Conflicting"},
    preds={"base": pred([obj(1, "vehicle", [0.66, 0.50, 0.88, 0.68], "roadside")], R("A", "A", "A", "A"), [act("ADVANCE_WITH_MONITORING", "no_condition")], "관찰하며 진행.", scene={"traffic_direction": "Unknown"}),
     "tuned": pred([obj(1, "vehicle", [0.66, 0.50, 0.88, 0.68], "roadside"), obj(2, "sign_oneway_reverse", [0.50, 0.18, 0.54, 0.24], kind="Obstacle")], R("A", "A", "A", "A"), [act("MONITOR_AHEAD", "no_condition")], "일방통행 표지가 진행 방향과 반대다. 전방 관찰.", scene={"traffic_direction": "One-way", "direction_match": "Conflicting"})}, group="G5")

# ---------- scoring (App.A) ----------
def iou(a, b):
    x1, y1 = max(a[0], b[0]), max(a[1], b[1]); x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    ua = (a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - inter
    return inter / ua if ua else 0

def match_boxes(gt, pr):
    used, matched, missed, extra = set(), [], [], []
    for g in gt:
        best = None
        for p in pr:
            if p["id"] in used or p["class"] != g["class"]: continue
            v = iou(g["bbox"], p["bbox"])
            if v >= 0.5 and (best is None or v > best[1]): best = (p, v)
        if best: used.add(best[0]["id"]); matched.append({"gt": g["id"], "pred": best[0]["id"], "iou": round(best[1], 2)})
        else: missed.append(g["id"])
    extra = [p["id"] for p in pr if p["id"] not in used]
    return matched, missed, extra

def score(sc, p):
    ref = sc["reference"]; out = {"relations": {}, "diag": [], "fail_reasons": [], "evidence_match": {}}
    if not p["valid"]:
        out.update({"pass": False if ref["actions"] else None, "fail_reasons": ["invalid"], "diag": ["action"], "boxes": {"matched": [], "missed": [], "extra": []}, "explain_ok": None, "fail_labels": ["형식 오류"]})
        return out
    grm, prm = rmap(ref["relations"]), rmap(p["relations"])
    # boxes (V3) — objects and regions separately
    mo, so, eo = match_boxes(ref["objects"], p["objects"]); mr, sr, er = match_boxes(ref["regions"], p["regions"])
    out["boxes"] = {"matched": mo + mr, "missed": so + sr, "extra": eo + er}
    if (so and any(o["kind"] == "Actor" for o in ref["objects"] if o["id"] in so)) or eo: out["diag"].append("evidence")
    idmap = {m["pred"]: m["gt"] for m in out["boxes"]["matched"]}
    # relations (V5–V9) + evidence ids (V4)
    for r in ["R1", "R2", "R3", "R4"]:
        g, q = grm[r], prm.get(r)
        ok = q is not None and q["state"] == g["state"]
        out["relations"][r] = {"gt": g["state"], "pred": q["state"] if q else None, "ok": ok, "gt_evidence": g["evidence"], "pred_evidence": q["evidence"] if q else []}
        if not ok: out["diag"].append("bias")
        if g["state"] in ("P", "U") and g["evidence"]:
            mapped = sorted(set(idmap.get(e, "?") for e in (q["evidence"] if q else [])))
            em = mapped == sorted(set(g["evidence"]))
            out["evidence_match"][r] = em
            if not em: out["diag"].append("evidence")
    # actions (V10–V12)
    acts = ref["actions"]
    if acts is None:
        out["pass"] = None; out["fail_labels"] = []
    else:
        S = [(a["code"], a["condition"]) for a in p["actions"]]
        A = set(tuple(x) for x in acts["allowed"]); F = set(tuple(x) for x in acts["forbidden"])
        fr = set()
        for a in p["actions"]:
            cond = CONDITIONS.get(a["condition"]); code = a["code"]
            if code not in ACTIONS or cond is None: fr.add("unsupported"); continue
            if cond["needs"]:
                relc, states = cond["needs"]
                if relc == "R1R2R3":
                    if not all(prm.get(x, {}).get("state") == "U" for x in a["based_on"]) or not a["based_on"]: fr.add("contradiction")
                else:
                    if prm.get(relc, {}).get("state") not in states or relc not in a["based_on"]: fr.add("contradiction")
        for s in S:
            if s in F: fr.add("forbidden")
            elif s not in A: fr.add("unsupported")
        groups_hit = []
        for g in acts["required_groups"]:
            hit = any(tuple(alt) in S for alt in g["alts"]); groups_hit.append(hit)
            if not hit: fr.add("missing_required")
        out["groups_hit"] = groups_hit
        out["fail_reasons"] = sorted(fr); out["pass"] = not fr; out["fail_labels"] = [FAIL[f] for f in out["fail_reasons"]]
        if fr: out["diag"].append("action")
    out["explain_ok"] = True
    return out

EXPLAIN_FAIL = {("S-0003", "base"): "실제 보행자를 관측했다는 진술 없이 장소 상식만으로 판정", ("S-0011", "base"): "'멈춰 서서 기다리고 있다'는 정지 이미지로 관측 불가한 움직임 단정", ("S-0004", "base"): "전봇대를 보행자로 단정"}
for sc in scenes:
    sc["scoring"] = {}
    for m in MODELS:
        s = score(sc, sc["predictions"][m])
        if (sc["scene_id"], m) in EXPLAIN_FAIL: s["explain_ok"] = False; s["explain_note"] = EXPLAIN_FAIL[(sc["scene_id"], m)]; s["diag"].append("explain")
        s["diag"] = sorted(set(s["diag"])); sc["scoring"][m] = s

# ---------- report ----------
rel_scenes = [s for s in scenes if not s["missing"]]
act_scenes = [s for s in rel_scenes if s["reference"]["actions"] is not None]
nR, nA = len(rel_scenes), len(act_scenes)
groups = sorted(set(s["source_group"] for s in rel_scenes))
def v10(m): return sum(1 for s in act_scenes if s["scoring"][m]["pass"]), nA
def v12(m): return sum(1 for s in act_scenes if "forbidden" in s["scoring"][m]["fail_reasons"]), nA
def v11(m):
    tot = hit = 0
    for s in act_scenes:
        gh = s["scoring"][m].get("groups_hit", [False]*len(s["reference"]["actions"]["required_groups"])); tot += len(gh); hit += sum(gh)
    return hit, tot
def v6(m):
    num = den = 0
    for s in rel_scenes:
        for r, v in s["scoring"][m]["relations"].items():
            if v["gt"] == "P": den += 1; num += 1 if v["pred"] == "P" else 0
    return num, den
def v7(m):
    num = den = 0
    for s in rel_scenes:
        for r, v in s["scoring"][m]["relations"].items():
            if v["gt"] == "A": den += 1; num += 1 if v["pred"] == "P" else 0
    return num, den
report = {
    "_note": "가상 데이터. V5·신뢰구간·verdict는 형식 확인용 임의 값(Group Bootstrap 미실행). 화면은 verdict를 계산하지 않고 Report API 값을 그대로 표시한다.",
    "test_version": "test-v0.1 (frozen 2026-11-04)", "label_version": "L0.2", "scorer_commit": "a1b2c3d",
    "n_scenes": len(scenes), "n_relation": nR, "n_action": nA, "n_source_groups": len(groups),
    "excluded": {"relation": {"count": len(scenes) - nR, "reasons": {"정답 검수 미완료 (Draft/Missing)": len(scenes) - nR}},
                 "action": {"count": len(scenes) - nA, "reasons": {"정답 검수 미완료 (Draft/Missing)": len(scenes) - nR, "방향 충돌 (Direction Match = Conflicting)": nR - nA}}},
    "models": MODELS,
    "core": {
        "V5": {"label": "V5 Relation Macro-F1", "n": nR, "base": {"value": 0.58, "ci": [0.45, 0.70]}, "tuned": {"value": 0.87, "ci": [0.78, 0.95]}, "note": "12칸 중 정답 0개 칸 있음 → Supported-class Macro-F1로 보고"},
        "V10": {"label": "V10 Action Pass Rate", "n": nA, "base": {"value": round(v10("base")[0]/nA, 2), "ci": [0.15, 0.61], "k": v10("base")[0]}, "tuned": {"value": round(v10("tuned")[0]/nA, 2), "ci": [0.59, 0.98], "k": v10("tuned")[0]}},
    },
    "comparison": {"V5": {"diff": 0.29, "ci": [0.12, 0.44], "verdict": "improved"},
                   "V10": {"diff": round((v10("tuned")[0] - v10("base")[0]) / nA, 2), "ci": [-0.02, 0.68], "verdict": "not_confirmed"}},
    "diagnostics": {k: {"label": v["label"], "metrics": v["metrics"], "desc": v["desc"],
                        "base": {"fail_scenes": sum(1 for s in rel_scenes if k in s["scoring"]["base"]["diag"])},
                        "tuned": {"fail_scenes": sum(1 for s in rel_scenes if k in s["scoring"]["tuned"]["diag"])}} for k, v in DIAG.items()},
    "diag_scores": {
        "V6": {"label": "V6 Recall for Present", "base": v6("base"), "tuned": v6("tuned")},
        "V7": {"label": "V7 False Positive Rate", "base": v7("base"), "tuned": v7("tuned")},
        "V11": {"label": "V11 Required Action Coverage", "base": v11("base"), "tuned": v11("tuned")},
        "V12": {"label": "V12 Forbidden Action Rate", "base": v12("base"), "tuned": v12("tuned")},
    },
    "conditions": [
        {"label": "야간", "n": sum(1 for s in rel_scenes if "야간" in s["conditions"]), "base": {"v5": 0.25, "ci": [0.0, 0.75]}, "tuned": {"v5": 1.0, "ci": [0.4, 1.0]}},
        {"label": "보도 없음", "n": nR, "base": {"v5": 0.58, "ci": [0.45, 0.70]}, "tuned": {"v5": 0.87, "ci": [0.78, 0.95]}},
        {"label": "일방통행", "n": sum(1 for s in rel_scenes if "일방통행" in s["conditions"]), "base": {"v5": 0.5, "ci": [0.0, 1.0]}, "tuned": {"v5": 1.0, "ci": [0.3, 1.0]}},
    ],
    "exploratory_threshold": 20,
    "runs": [
        {"run_id": MODELS["base"]["run_id"], "model": "base", "status": "done", "requests": len(scenes), "ok": len(scenes)-1, "failed": 1, "V1_schema_valid": round((len(scenes)-1)/len(scenes), 3), "V2_invalid": round(1/len(scenes), 3), "input_condition": "정상 영상", "prompt": "p0.1", "seed": 7, "finished_at": "2026-11-04T21:10:00+09:00"},
        {"run_id": MODELS["tuned"]["run_id"], "model": "tuned", "status": "done", "requests": len(scenes), "ok": len(scenes), "failed": 0, "V1_schema_valid": 1.0, "V2_invalid": 0.0, "input_condition": "정상 영상", "prompt": "p0.1", "seed": 7, "finished_at": "2026-11-04T22:40:00+09:00"},
        {"run_id": "run_base_test-v0.1_noimage", "model": "base", "status": "queued", "requests": len(scenes), "ok": 0, "failed": 0, "input_condition": "영상 없음", "note": "이미지 의존도 보조 실험"},
    ],
}
meta = {"relations": RELATIONS, "actions": ACTIONS, "conditions": {k: v["label"] for k, v in CONDITIONS.items()}, "fail_reasons": FAIL, "diagnostics": DIAG,
        "pau": {"P": "성립 근거 있음", "A": "충분히 확인했고 성립하지 않음", "U": "입력만으로 판정할 수 없음 (정답의 하나, 오류 아님)"},
        "empty_values": {"Invalid": "모델 출력 형식 오류", "Missing": "아직 작성·검수하지 않은 정답", "Not applicable": "해당 장면에 적용되지 않는 질문"},
        "scene_attrs": {"sidewalk_left": "좌 보도", "sidewalk_right": "우 보도", "traffic_direction": "통행 방향", "direction_match": "진행 방향 일치"}}
json.dump(report, open(f"{OUT}/report.json", "w"), ensure_ascii=False, indent=2)
json.dump({"test_version": report["test_version"], "scenes": scenes}, open(f"{OUT}/scenes.json", "w"), ensure_ascii=False, indent=2)
json.dump(meta, open(f"{OUT}/meta.json", "w"), ensure_ascii=False, indent=2)
for s in scenes:
    b, t = s["scoring"]["base"], s["scoring"]["tuned"]
    print(s["scene_id"], "| base", b["pass"], b["fail_labels"], b["diag"], "| tuned", t["pass"], t["fail_labels"], t["diag"])
print("V10", v10("base"), v10("tuned"), "V11", v11("base"), v11("tuned"), "V6", v6("base"), v6("tuned"))
