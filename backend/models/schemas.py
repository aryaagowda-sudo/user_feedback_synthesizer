from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import date, datetime

class FeedbackInput(BaseModel):
    feedback: str = Field(..., description="The raw feedback text submitted by the user")
    rating: Optional[int] = Field(None, ge=1, le=5, description="Optional 1-5 rating")
    date: Optional[str] = Field(None, description="Optional date in YYYY-MM-DD or ISO format")
    source: Optional[str] = Field("Web App", description="Feedback origin e.g. iOS, Web, Support")

class BatchAnalyzeRequest(BaseModel):
    items: Optional[List[FeedbackInput]] = None
    raw_text: Optional[str] = None  # For manual text input (e.g. newline-separated feedback)
    dataset_name: Optional[str] = "Manual Ingestion"
    user_id: Optional[str] = None

class SentimentBreakdown(BaseModel):
    positive: int = 0
    neutral: int = 0
    negative: int = 0
    positive_pct: float = 0.0
    neutral_pct: float = 0.0
    negative_pct: float = 0.0

class FeedbackRecord(BaseModel):
    id: str
    analysis_id: Optional[str] = None
    user_id: Optional[str] = None
    feedback_text: str
    rating: Optional[int] = None
    sentiment: str  # 'Positive', 'Negative', 'Neutral'
    sentiment_confidence: float = 0.9
    confidence: Optional[float] = None
    theme_id: Optional[str] = None
    theme_name: Optional[str] = None
    source: str = "Web App"
    date: str
    created_at: Optional[str] = None

class ThemeRecord(BaseModel):
    id: str
    analysis_id: Optional[str] = None
    user_id: Optional[str] = None
    theme_name: str
    name: Optional[str] = None  # Alias for backward compatibility
    ai_summary: str
    summary: Optional[str] = None  # Alias for backward compatibility
    mention_count: int
    positive_count: int = 0
    neutral_count: int = 0
    negative_count: int = 0
    positive_percentage: float = 0.0
    negative_percentage: float = 0.0
    neutral_percentage: float = 0.0
    sentiment_distribution: Optional[SentimentBreakdown] = None
    main_complaint: str = ""
    key_observations: List[str] = []
    representative_feedback: List[str] = []
    representative_comments: Optional[List[str]] = None  # Alias
    severity: str = "Low"  # 'Critical', 'High', 'Medium', 'Low'
    priority: str = "Medium"  # 'Critical', 'High', 'Medium', 'Low'
    priority_level: Optional[str] = None  # Alias
    priority_rank: int = 99
    priority_score: float = 0.0
    recommendation: str = ""
    suggested_action: Optional[str] = None  # Alias
    is_feature_request: bool = False
    created_at: Optional[str] = None

class SentimentTrendPoint(BaseModel):
    date: str
    positive: int
    negative: int
    neutral: int
    total: int

class AnalyticsResponse(BaseModel):
    total_feedback: int
    positive_percentage: float
    neutral_percentage: float
    negative_percentage: float
    total_issues_identified: int
    sentiment_donut: List[Dict[str, Any]]
    sentiment_trend: List[SentimentTrendPoint]
    top_themes: List[Dict[str, Any]]
    top_complaints: List[Dict[str, Any]]
    most_requested_features: List[Dict[str, Any]]
    priority_issues: List[Dict[str, Any]]
    recent_feedback: List[FeedbackRecord]

class AIInsightItem(BaseModel):
    title: str
    description: str
    impact: str  # 'High', 'Medium', 'Low'
    category: str  # 'Complaint', 'Emerging', 'Feature', 'Pattern'
    supporting_evidence: List[str]
    suggested_action: str

class InsightsResponse(BaseModel):
    summary: str
    most_common_complaints: List[AIInsightItem]
    emerging_problems: List[AIInsightItem]
    feature_requests: List[AIInsightItem]
    sentiment_patterns: List[AIInsightItem]
    actionable_recommendations: List[AIInsightItem]

class ChatRequest(BaseModel):
    message: str
    analysis_id: Optional[str] = None

class ChatResponse(BaseModel):
    answer: str
    sources: List[str] = []
    suggested_questions: List[str] = []
    supporting_quotes: Optional[List[str]] = None  # Alias
    relevant_themes: Optional[List[str]] = None  # Alias
    confidence: float = 0.95

class AnalysisHistoryItem(BaseModel):
    id: str
    user_id: Optional[str] = None
    analysis_name: str
    total_feedback: int
    positive_count: int
    negative_count: int
    neutral_count: int
    positive_percentage: float = 0.0
    negative_percentage: float = 0.0
    neutral_percentage: float = 0.0
    themes_count: int = 0
    created_at: str

class SummarizeRequest(BaseModel):
    analysis_id: Optional[str] = None
    theme_ids: Optional[List[str]] = None
