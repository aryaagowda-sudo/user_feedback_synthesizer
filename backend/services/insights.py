import re
import numpy as np
from typing import List, Dict, Any, Optional
from backend.services.clustering import semantic_clusterer

class InsightsAndChatEngine:
    def generate_insights(self, themes: List[Dict[str, Any]], feedback_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generates evidence-backed AI insights for the AI Insights page."""
        complaints = []
        emerging = []
        feature_requests = []
        patterns = []
        recommendations = []

        # 1. Identify Complaints from Critical & High priority themes
        for t in themes:
            name = t.get("theme_name") or t.get("name", "General")
            summary = t.get("ai_summary") or t.get("summary", "")
            prio = t.get("priority") or t.get("priority_level", "Medium")
            action = t.get("recommendation") or t.get("suggested_action", "")
            reps = t.get("representative_feedback") or t.get("representative_comments") or []
            
            neg_items = [it["feedback_text"] for it in t.get("items", []) if it.get("sentiment") == "Negative"]
            if not neg_items:
                neg_items = reps

            if (t.get("negative_count", 0) > 0 or t.get("negative_percentage", 0) > 40) and prio in ("Critical", "High") and not t.get("is_feature_request"):
                complaints.append({
                    "title": name,
                    "description": summary,
                    "impact": prio,
                    "category": "Complaint",
                    "supporting_evidence": neg_items[:3],
                    "suggested_action": action
                })

        # 2. Emerging problems (critical failure terms across dataset)
        crit_quotes = [
            it["feedback_text"] for it in feedback_records 
            if any(w in it["feedback_text"].lower() for w in ["crash", "freeze", "blank screen", "charged twice", "timeout", "failed"])
        ]
        if crit_quotes:
            emerging.append({
                "title": "System Stability Alert: Platform Reliability",
                "description": f"Multiple customer submissions reported acute blockers preventing normal platform usage ({len(crit_quotes)} critical blocker records).",
                "impact": "High",
                "category": "Emerging",
                "supporting_evidence": crit_quotes[:3],
                "suggested_action": "Audit server logs, inspect Sentry trace alerts, and deploy an immediate stability hotfix."
            })

        # 3. Feature requests
        for t in themes:
            name = t.get("theme_name") or t.get("name", "General")
            summary = t.get("ai_summary") or t.get("summary", "")
            reps = t.get("representative_feedback") or t.get("representative_comments") or []
            action = t.get("recommendation") or t.get("suggested_action", "")

            if t.get("is_feature_request"):
                feature_requests.append({
                    "title": name,
                    "description": summary,
                    "impact": "Medium",
                    "category": "Feature",
                    "supporting_evidence": reps[:3],
                    "suggested_action": action or "Evaluate API partner roadmap and prioritize integrations for upcoming sprint."
                })

        if not feature_requests:
            feat_items = [
                it["feedback_text"] for it in feedback_records 
                if any(w in it["feedback_text"].lower() for w in ["add", "integration", "support", "webhook", "zapier", "export", "jira", "would love", "dark mode"])
            ]
            if feat_items:
                feature_requests.append({
                    "title": "Workflow Integrations & Ecosystem Expansion",
                    "description": f"Customer requests for workflow connectors, webhooks, and export formats ({len(feat_items)} total mentions).",
                    "impact": "Medium",
                    "category": "Feature",
                    "supporting_evidence": feat_items[:3],
                    "suggested_action": "Prioritize high-demand integration connectors (e.g. Slack, Zapier, Webhooks)."
                })

        # 4. Sentiment patterns across channels
        sources = {}
        for it in feedback_records:
            src = it.get("source", "Web App")
            sent = it.get("sentiment", "Neutral")
            sources.setdefault(src, {"Positive": 0, "Negative": 0, "Neutral": 0, "Total": 0})
            sources[src][sent] += 1
            sources[src]["Total"] += 1

        pattern_evidence = []
        for src, stats in sources.items():
            if stats["Total"] >= 2:
                neg_rate = round((stats["Negative"] / stats["Total"]) * 100, 1)
                pattern_evidence.append(f"{src}: {neg_rate}% negative rate ({stats['Negative']} of {stats['Total']} reports)")

        patterns.append({
            "title": "Channel Sentiment Variance",
            "description": "Noticeable variance in satisfaction across client touchpoints, with mobile and web reporting distinct obstacle profiles.",
            "impact": "Medium",
            "category": "Pattern",
            "supporting_evidence": pattern_evidence[:4],
            "suggested_action": "Conduct targeted platform audits for channels displaying higher negative ratios."
        })

        # 5. Actionable recommendations
        if themes:
            top_theme = themes[0]
            top_name = top_theme.get("theme_name") or top_theme.get("name")
            top_prio = top_theme.get("priority") or top_theme.get("priority_level", "Critical")
            top_reps = top_theme.get("representative_feedback") or top_theme.get("representative_comments") or []
            top_act = top_theme.get("recommendation") or top_theme.get("suggested_action", "Implement engineering sprint focus.")

            recommendations.append({
                "title": f"Priority 1: Resolve {top_name}",
                "description": f"Ranked #{top_theme.get('priority_rank', 1)} urgency due to {top_theme.get('negative_count', 0)} negative reports and {top_theme.get('severity', 'High')} severity.",
                "impact": top_prio,
                "category": "Recommendation",
                "supporting_evidence": top_reps[:2],
                "suggested_action": top_act
            })

            if len(themes) > 1 and not themes[1].get("is_feature_request"):
                second_theme = themes[1]
                s_name = second_theme.get("theme_name") or second_theme.get("name")
                s_prio = second_theme.get("priority") or second_theme.get("priority_level", "High")
                s_reps = second_theme.get("representative_feedback") or second_theme.get("representative_comments") or []
                s_act = second_theme.get("recommendation") or second_theme.get("suggested_action", "Optimize API response times and caching.")

                recommendations.append({
                    "title": f"Priority 2: Stabilize {s_name}",
                    "description": f"Addressing this will eliminate friction for {second_theme.get('mention_count', 0)} active user touchpoints.",
                    "impact": s_prio,
                    "category": "Recommendation",
                    "supporting_evidence": s_reps[:2],
                    "suggested_action": s_act
                })

        first_name = (themes[0].get("theme_name") or themes[0].get("name")) if themes else "technical stability"
        summary_text = (
            f"Synthesized analysis of {len(feedback_records)} customer records across {len(themes)} distinct themes. "
            f"The primary driver of user dissatisfaction is {first_name}, "
            f"while strong satisfaction is maintained in core platform utility and AI analysis speed."
        )

        return {
            "summary": summary_text,
            "most_common_complaints": complaints,
            "emerging_problems": emerging,
            "feature_requests": feature_requests,
            "sentiment_patterns": patterns,
            "actionable_recommendations": recommendations
        }

insights_engine = InsightsAndChatEngine()
