import re
from typing import List, Dict, Any

# Critical failure keywords that impact user acquisition, retention, and revenue
CRITICAL_KEYWORDS = {
    "crash", "crashes", "crashing", "freeze", "freezes", "blank screen", "white screen",
    "cannot log in", "unable to sign in", "login failed", "charged twice", "payment failed",
    "security", "data loss", "corrupt", "unresponsive", "fails immediately", "cannot open",
    "not opening", "deleted all", "lost all", "disappeared", "won't open", "cant open"
}

HIGH_KEYWORDS = {
    "slow", "lag", "latency", "timeout", "reject", "rejected", "invoice", "refund",
    "error", "broken", "failing", "freeze browser", "spam", "spams", "unusable",
    "horrible", "terrible", "worst", "bug", "bugs", "glitch", "costly", "rip off"
}

class IssuePrioritizer:
    def evaluate_severity(
        self, 
        theme_name: str, 
        feedback_texts: List[str], 
        is_feature_request: bool,
        negative_ratio: float = 0.0
    ) -> str:
        """Determines intrinsic severity based on operational impact and sentiment concentration."""
        if is_feature_request:
            return "Low"

        combined = (" ".join(feedback_texts) + " " + theme_name).lower()
        
        crit_hits = sum(1 for kw in CRITICAL_KEYWORDS if kw in combined)
        high_hits = sum(1 for kw in HIGH_KEYWORDS if kw in combined)
        
        if crit_hits >= 1 or (negative_ratio >= 0.85 and high_hits >= 1):
            return "Critical"
        elif high_hits >= 2 or negative_ratio >= 0.70:
            return "High"
        elif high_hits >= 1 or negative_ratio >= 0.40:
            return "Medium"
        return "Low"

    def rank_themes(self, themes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Ranks themes based on frequency, negative ratio, and severity without inflating feature requests."""
        if not themes:
            return []

        max_mentions = max(t.get("mention_count", 1) for t in themes) or 1

        for t in themes:
            mention_count = t.get("mention_count", 0)
            neg_count = t.get("negative_count", 0)
            total = max(1, mention_count)
            neg_ratio = neg_count / total
            is_feature = t.get("is_feature_request", False)

            name = t.get("theme_name") or t.get("name", "General")
            feedback_texts = [it["feedback_text"] for it in t.get("items", [])]
            if not feedback_texts:
                reps = t.get("representative_feedback") or t.get("representative_comments") or []
                feedback_texts = list(reps)
                if t.get("main_complaint"):
                    feedback_texts.append(t["main_complaint"])
                if t.get("summary"):
                    feedback_texts.append(t["summary"])

            severity = self.evaluate_severity(name, feedback_texts, is_feature, negative_ratio=neg_ratio)
            t["severity"] = severity

            # Severity weight
            severity_weights = {
                "Critical": 45.0,
                "High": 30.0,
                "Medium": 15.0,
                "Low": 5.0
            }
            s_weight = severity_weights.get(severity, 10.0)

            # Frequency normalized to [0, 25]
            freq_score = (mention_count / max_mentions) * 25.0

            # Negative sentiment normalized to [0, 40]
            neg_score = neg_ratio * 40.0

            # Base score
            score = neg_score + freq_score + s_weight

            # Feature request dampener: ensure high-frequency feature requests do not displace critical crashes
            if is_feature:
                score *= 0.45

            t["priority_score"] = round(score, 2)

            # Assign priority level
            if score >= 65.0 and severity in ("Critical", "High") and not is_feature:
                p_level = "Critical"
            elif score >= 45.0:
                p_level = "High"
            elif score >= 25.0:
                p_level = "Medium"
            else:
                p_level = "Low"

            t["priority"] = p_level
            t["priority_level"] = p_level

        # Sort descending by priority_score
        themes.sort(key=lambda x: x["priority_score"], reverse=True)

        # Assign 1-based ranks
        for idx, t in enumerate(themes):
            t["priority_rank"] = idx + 1

        return themes

issue_prioritizer = IssuePrioritizer()
