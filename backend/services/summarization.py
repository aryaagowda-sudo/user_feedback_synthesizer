import os
import re
import json
import logging
import httpx
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("feedbackiq.summarization")

LLM_API_KEY = os.getenv("LLM_API_KEY", "").strip()
LLM_MODEL = os.getenv("LLM_MODEL", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

# Determine effective API key and provider
EFFECTIVE_API_KEY = LLM_API_KEY or GEMINI_API_KEY or OPENAI_API_KEY
IS_OPENAI = bool(OPENAI_API_KEY or (LLM_API_KEY and LLM_API_KEY.startswith("sk-")))

class ThemeSummarizer:
    def __init__(self):
        self.has_llm = bool(
            EFFECTIVE_API_KEY and 
            not EFFECTIVE_API_KEY.startswith("your_") and 
            len(EFFECTIVE_API_KEY) > 10
        )
        self.model = LLM_MODEL or ("gpt-4o-mini" if IS_OPENAI else "gemini-1.5-flash")

    def _call_llm_api(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Invokes Gemini or OpenAI REST API with structured JSON output enforcement."""
        if not self.has_llm:
            return None

        # Try Gemini API if not OpenAI
        if not IS_OPENAI and (GEMINI_API_KEY or LLM_API_KEY):
            api_key = LLM_API_KEY or GEMINI_API_KEY
            model_name = self.model if "gemini" in self.model else "gemini-1.5-flash"
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.2,
                    "maxOutputTokens": 600,
                    "responseMimeType": "application/json"
                }
            }
            try:
                with httpx.Client(timeout=12.0) as client:
                    resp = client.post(url, json=payload)
                    resp.raise_for_status()
                    res = resp.json()
                    text_content = res["candidates"][0]["content"]["parts"][0]["text"].strip()
                    cleaned = re.sub(r"^```(?:json)?|```$", "", text_content.strip(), flags=re.MULTILINE).strip()
                    return json.loads(cleaned)
            except Exception as e:
                logger.warning(f"Gemini API request failed ({e}), attempting fallback.")

        # Try OpenAI API
        if IS_OPENAI or OPENAI_API_KEY:
            api_key = OPENAI_API_KEY or LLM_API_KEY
            model_name = self.model if ("gpt" in self.model) else "gpt-4o-mini"
            url = "https://api.openai.com/v1/chat/completions"
            payload = {
                "model": model_name,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a senior product feedback intelligence analyst. Generate strictly evidence-based, factual JSON summaries from customer feedback without hallucinating statistics or issues."
                    },
                    {"role": "user", "content": prompt}
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.2,
                "max_tokens": 600
            }
            try:
                headers = {"Authorization": f"Bearer {api_key}"}
                with httpx.Client(timeout=12.0) as client:
                    resp = client.post(url, json=payload, headers=headers)
                    resp.raise_for_status()
                    res = resp.json()
                    text_content = res["choices"][0]["message"]["content"].strip()
                    cleaned = re.sub(r"^```(?:json)?|```$", "", text_content.strip(), flags=re.MULTILINE).strip()
                    return json.loads(cleaned)
            except Exception as e:
                logger.warning(f"OpenAI API request failed ({e}), attempting fallback.")

        return None

    def _fallback_deterministic_synthesis(
        self, 
        theme_name: str, 
        feedback_texts: List[str], 
        neg_pct: float, 
        pos_pct: float, 
        total: int,
        severity: str
    ) -> Dict[str, Any]:
        """Evidence-based extractive and deterministic synthesis when LLM API is unavailable."""
        sample_quotes = sorted(feedback_texts, key=lambda s: len(s), reverse=True)
        top_quotes = sample_quotes[:3]
        longest_quote = top_quotes[0] if top_quotes else "Feedback reports collected."

        # Derive main complaint
        if neg_pct >= 50.0:
            main_complaint = f"Frequent blockers and errors reported: '{longest_quote[:90]}...'" if len(longest_quote) > 90 else f"Blockers reported: '{longest_quote}'"
        elif pos_pct >= 50.0:
            main_complaint = f"Minimal negative friction reported; users emphasize workflow satisfaction."
        else:
            main_complaint = f"Mixed customer experiences with usability friction: '{longest_quote[:90]}...'"

        # Derive key observations
        key_observations = []
        if len(feedback_texts) >= 1:
            key_observations.append(f"Primary user comment: \"{feedback_texts[0]}\"")
        if len(feedback_texts) >= 2:
            key_observations.append(f"Secondary report: \"{feedback_texts[1]}\"")
        if total > 2:
            key_observations.append(f"Represents {total} customer submissions with {neg_pct}% negative sentiment concentration.")

        # Build ai_summary
        if neg_pct >= 60.0:
            ai_summary = (
                f"Users report acute, recurring dissatisfaction regarding {theme_name.lower()}. "
                f"Negative sentiment stands at {neg_pct}% across {total} reports, indicating friction in core user workflows. "
                f"Key concerns center around reports such as: \"{longest_quote}\"."
            )
            recommendation = f"Audit server endpoints and UX workflows for {theme_name.lower()}, add telemetry instrumentation, and deploy a stability hotfix."
        elif pos_pct >= 60.0:
            ai_summary = (
                f"Strong positive reception observed for {theme_name.lower()}, with {pos_pct}% positive feedback across {total} mentions. "
                f"Users express high satisfaction with efficiency and features, highlighting: \"{longest_quote}\"."
            )
            recommendation = f"Document customer success patterns around {theme_name.lower()} and consider featuring testimonials in product onboarding."
        else:
            ai_summary = (
                f"Analysis shows mixed sentiment across {total} mentions regarding {theme_name.lower()} ({neg_pct}% negative, {pos_pct}% positive). "
                f"Feedback combines actionable usability adjustments with functional praise. Representative note: \"{longest_quote}\"."
            )
            recommendation = f"Conduct a UX audit for {theme_name.lower()} to eliminate specific edge-case friction while preserving popular capabilities."

        return {
            "ai_summary": ai_summary,
            "main_complaint": main_complaint,
            "key_observations": key_observations,
            "recommendation": recommendation
        }

    def summarize_theme(self, theme_name: str, items: List[Dict[str, Any]], severity: str = "Medium") -> Dict[str, Any]:
        """
        Generates structured, evidence-based theme summaries and metrics.
        Computes exact counts and percentages programmatically, then synthesizes
        main complaint, key observations, AI summary, and recommendations.
        """
        feedback_texts = [it["feedback_text"] for it in items]
        total = len(items)
        pos = sum(1 for it in items if it.get("sentiment") == "Positive")
        neg = sum(1 for it in items if it.get("sentiment") == "Negative")
        neu = sum(1 for it in items if it.get("sentiment") == "Neutral")

        pos_pct = round((pos / total) * 100, 1) if total > 0 else 0.0
        neg_pct = round((neg / total) * 100, 1) if total > 0 else 0.0
        neu_pct = round((neu / total) * 100, 1) if total > 0 else 0.0

        sentiment_distribution = {
            "positive": pos,
            "neutral": neu,
            "negative": neg,
            "positive_pct": pos_pct,
            "neutral_pct": neu_pct,
            "negative_pct": neg_pct,
        }

        # Select diverse representative feedback comments (up to 4 items)
        rep_comments = []
        neg_samples = [it["feedback_text"] for it in items if it.get("sentiment") == "Negative"]
        pos_samples = [it["feedback_text"] for it in items if it.get("sentiment") == "Positive"]
        neu_samples = [it["feedback_text"] for it in items if it.get("sentiment") == "Neutral"]

        if neg_samples:
            rep_comments.append(neg_samples[0])
        if pos_samples:
            rep_comments.append(pos_samples[0])
        if len(neg_samples) > 1:
            rep_comments.append(neg_samples[1])
        elif neu_samples:
            rep_comments.append(neu_samples[0])

        if not rep_comments and feedback_texts:
            rep_comments = feedback_texts[:3]

        # Deduplicate representative feedback
        seen = set()
        dedup_rep = []
        for c in rep_comments:
            if c not in seen:
                seen.add(c)
                dedup_rep.append(c)

        # Attempt LLM synthesis if key configured
        llm_data = None
        if self.has_llm:
            prompt = f"""You are an executive product intelligence analyst analyzing customer feedback.
Theme Name: {theme_name}
Total Mentions: {total}
Negative Sentiment: {neg_pct}% | Positive Sentiment: {pos_pct}% | Neutral Sentiment: {neu_pct}%
Customer feedback comments:
{chr(10).join(f"- {t}" for t in feedback_texts[:10])}

Task:
Generate grounded, evidence-based synthesis strictly supported by these customer comments.
Return a valid JSON object with EXACTLY the following keys:
1. "ai_summary": A professional 2-3 sentence executive summary explaining what customers are experiencing.
2. "main_complaint": A 1-sentence statement describing the primary friction or root complaint (or "No major complaints" if positive).
3. "key_observations": A JSON list of 2 to 3 concise, concrete bullet points citing specific user behaviors or feedback patterns.
4. "recommendation": A concrete, actionable engineering or product recommendation to resolve the friction or enhance the feature.

Do not invent numbers, quotes, or issues not present in the customer comments. Return ONLY valid JSON."""
            llm_res = self._call_llm_api(prompt)
            if llm_res and isinstance(llm_res, dict):
                ai_sum = llm_res.get("ai_summary", "")
                main_comp = llm_res.get("main_complaint", "")
                key_obs = llm_res.get("key_observations", [])
                rec = llm_res.get("recommendation", "")
                if ai_sum and rec:
                    llm_data = {
                        "ai_summary": str(ai_sum),
                        "main_complaint": str(main_comp),
                        "key_observations": [str(o) for o in key_obs] if isinstance(key_obs, list) else [str(key_obs)],
                        "recommendation": str(rec)
                    }

        # Fallback if LLM unavailable or failed
        if not llm_data:
            llm_data = self._fallback_deterministic_synthesis(
                theme_name=theme_name,
                feedback_texts=feedback_texts,
                neg_pct=neg_pct,
                pos_pct=pos_pct,
                total=total,
                severity=severity
            )

        calc_priority = "P1" if (severity == "High" or neg_pct >= 60.0) else ("P2" if (severity == "Medium" or neg_pct >= 30.0) else "P3")

        return {
            "theme_name": theme_name,
            "name": theme_name,  # Alias
            "ai_summary": llm_data["ai_summary"],
            "summary": llm_data["ai_summary"],  # Alias
            "main_complaint": llm_data["main_complaint"],
            "key_observations": llm_data["key_observations"],
            "severity": severity,
            "priority": calc_priority,
            "recommendation": llm_data["recommendation"],
            "suggested_action": llm_data["recommendation"],  # Alias
            "mention_count": total,
            "positive_count": pos,
            "neutral_count": neu,
            "negative_count": neg,
            "positive_percentage": pos_pct,
            "negative_percentage": neg_pct,
            "neutral_percentage": neu_pct,
            "sentiment_distribution": sentiment_distribution,
            "representative_feedback": dedup_rep,
            "representative_comments": dedup_rep  # Alias
        }

theme_summarizer = ThemeSummarizer()
