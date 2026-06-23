# app/confidence.py
#
# Real confidence scoring for Pelican Risk.
# Replaces fake "high/medium/low" strings with a 0.0–1.0 float
# that reflects actual signal strength.
#
# Score thresholds:
#   0.85 – 1.00 → HIGH         → auto-confirmed, no review needed
#   0.60 – 0.84 → MEDIUM       → recommended for human review
#   0.00 – 0.59 → LOW          → required human review
#   None        → UNCLASSIFIED → no match, must be manually coded
#   1.00 locked → CONFIRMED    → human reviewed and signed off

REVIEW_THRESHOLD = 0.60
HIGH_THRESHOLD   = 0.85
CONFIRMED_SCORE  = 1.00


def score_keyword_match(keyword, all_matches, is_generic):
    conflict_detected = False
    base_score = 0.0

    word_count = len(keyword.split())
    if word_count >= 3:
        base_score = 0.90
    elif word_count == 2:
        base_score = 0.82
    else:
        base_score = 0.72

    if is_generic:
        base_score = min(base_score, 0.55)

    if len(all_matches) > 1:
        codes = set(m["naics_code"] for m in all_matches)
        if len(codes) == 1:
            base_score = min(base_score + 0.07, 0.97)
        else:
            base_score = max(base_score - 0.20, 0.35)
            conflict_detected = True

    score = round(base_score, 2)
    tier = score_to_tier(score)
    return score, tier, conflict_detected


def score_llm_result(llm_confidence=None):
    if llm_confidence == "high":
        score = 0.72
    elif llm_confidence == "medium":
        score = 0.62
    else:
        score = 0.52
    return score, score_to_tier(score)


def score_to_tier(score):
    if score is None:
        return "unclassified"
    if score >= HIGH_THRESHOLD:
        return "high"
    if score >= REVIEW_THRESHOLD:
        return "medium"
    return "low"


def needs_human_review(score):
    return score < HIGH_THRESHOLD


def build_reasoning(keyword, all_matches, conflict_detected, score, method):
    if method == "keyword":
        reasoning = f'Matched keyword "{keyword}" in business name.'
        if len(all_matches) > 1:
            others = [m["match_keyword"] for m in all_matches if m["match_keyword"] != keyword]
            reasoning += f' Additional matches: {", ".join(repr(k) for k in others)}.'
        if conflict_detected:
            codes = list(set(m["naics_code"] for m in all_matches))
            reasoning += f' CONFLICT: keywords map to different codes ({", ".join(codes)}). Human review required.'
        else:
            reasoning += f' Confidence score: {score}.'
    elif method == "llm_assist":
        reasoning = f'No keyword match. LLM-assisted classification. Score: {score}. Human review recommended.'
    elif method == "manual":
        reasoning = "Manually classified by reviewer. Human-confirmed."
    else:
        reasoning = "Classification method unknown."
    return reasoning