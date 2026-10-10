"""Single source of truth for API/data contracts shared across all backend
modules (analytics, forecast, simulate, recommend, copilot) and mirrored to
the frontend via generated OpenAPI types.

Do not duplicate these shapes elsewhere -- import from here.
"""
from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Domain enums
# ---------------------------------------------------------------------------


class AccountType(str, Enum):
    checking = "checking"
    savings = "savings"
    credit_card = "credit_card"
    loan = "loan"
    investment = "investment"


class TxnCategory(str, Enum):
    income = "income"
    rent_housing = "rent_housing"
    emi_loan = "emi_loan"
    groceries = "groceries"
    dining = "dining"
    transport = "transport"
    utilities = "utilities"
    subscriptions = "subscriptions"
    shopping = "shopping"
    healthcare = "healthcare"
    entertainment = "entertainment"
    investment_sip = "investment_sip"
    credit_card_payment = "credit_card_payment"
    transfer = "transfer"
    fees_interest = "fees_interest"
    other = "other"


class RecurrenceFrequency(str, Enum):
    weekly = "weekly"
    biweekly = "biweekly"
    monthly = "monthly"
    quarterly = "quarterly"
    annual = "annual"
    irregular = "irregular"


class ActionType(str, Enum):
    cancel_subscription = "cancel_subscription"
    reduce_category_spend = "reduce_category_spend"
    prepay_debt = "prepay_debt"
    increase_sip = "increase_sip"
    build_emergency_fund = "build_emergency_fund"
    refinance_debt = "refinance_debt"
    affordability_check = "affordability_check"
    shift_payment_date = "shift_payment_date"


# ---------------------------------------------------------------------------
# Core entities (mirror DB models, used at the API boundary)
# ---------------------------------------------------------------------------


class Account(BaseModel):
    id: str
    user_id: str
    name: str
    type: AccountType
    balance: float
    credit_limit: Optional[float] = None
    interest_rate_apr: Optional[float] = None
    currency: str = "INR"


class ReviewStatus(str, Enum):
    pending = "pending"
    reviewed = "reviewed"
    skipped = "skipped"


class RuleMatchType(str, Enum):
    contains = "contains"
    exact = "exact"
    starts_with = "starts_with"
    regex = "regex"


class Transaction(BaseModel):
    id: str
    user_id: str
    account_id: str
    date: date
    amount: float  # positive = inflow, negative = outflow
    merchant: str
    category: TxnCategory
    description: Optional[str] = None
    is_recurring: bool = False
    recurring_group_id: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    notes: Optional[str] = None
    review_status: str = "pending"
    reviewed_at: Optional[datetime] = None


class Debt(BaseModel):
    id: str
    user_id: str
    account_id: str
    principal: float
    interest_rate_apr: float
    minimum_payment: float
    due_day_of_month: int


class Income(BaseModel):
    id: str
    user_id: str
    source: str
    amount: float
    frequency: RecurrenceFrequency
    next_date: date


class RecurringObligation(BaseModel):
    group_id: str
    merchant: str
    category: TxnCategory
    amount: float
    frequency: RecurrenceFrequency
    next_expected_date: date
    confidence: float = Field(ge=0, le=1)


class Goal(BaseModel):
    """Mirrors models.GoalRow. Added by analytics-agent for goal-progress
    projection (app.analytics.goals) -- new shape, does not alter any
    existing contract."""

    id: str
    user_id: str
    name: str
    target_amount: float
    target_date: Optional[date] = None
    current_amount: float = 0
    cover_key: str = "general"
    funding_account_id: Optional[str] = None
    auto_track: bool = False



# ---------------------------------------------------------------------------
# Health score
# ---------------------------------------------------------------------------


class SubScore(BaseModel):
    name: str
    score: float = Field(ge=0, le=100)
    weight: float
    detail: str


class HealthScore(BaseModel):
    overall: float = Field(ge=0, le=100)
    sub_scores: list[SubScore]
    computed_at: datetime
    trend_30d: Optional[float] = None  # delta vs 30 days ago


# ---------------------------------------------------------------------------
# Forecast
# ---------------------------------------------------------------------------


class ForecastPoint(BaseModel):
    date: date
    p10: float
    p50: float
    p90: float
    is_gap_risk: bool = False


class CashFlowForecast(BaseModel):
    generated_at: datetime
    horizon_days: int
    points: list[ForecastPoint]
    first_gap_date: Optional[date] = None
    confidence: float = Field(ge=0, le=1)
    basis: str  # human-readable explanation of method/data used


# ---------------------------------------------------------------------------
# The Answer Contract -- facts / predictions / recommendations
# This is the core differentiator: every insight & copilot response uses it.
# ---------------------------------------------------------------------------


class Fact(BaseModel):
    """An observed, verifiable statement grounded in the user's own data."""

    text: str
    value: Optional[float] = None
    source_txn_ids: list[str] = Field(default_factory=list)


class Prediction(BaseModel):
    """A model-derived statement about the future or an inferred pattern."""

    text: str
    value: Optional[float] = None
    range_low: Optional[float] = None
    range_high: Optional[float] = None
    confidence: float = Field(ge=0, le=1)
    basis: str  # what the prediction is derived from


class ImpactEstimate(BaseModel):
    metric: str  # e.g. "monthly free cash flow", "health score"
    before: float
    after: float
    delta: float
    horizon: str  # e.g. "next 30 days", "12 months"


class Recommendation(BaseModel):
    action: ActionType
    text: str
    rationale: str
    impact: ImpactEstimate
    confidence: float = Field(ge=0, le=1)
    action_params: dict = Field(default_factory=dict)


class DataGap(BaseModel):
    text: str
    what_would_help: str


class NextStep(BaseModel):
    """One concrete thing the user should do next, in priority order."""

    title: str  # imperative, e.g. "Cancel the duplicate Netflix charge"
    why: str  # one sentence tying it to the user's own data
    when: Optional[str] = None  # e.g. "this week", "before 15 Dec 2026"
    link: Optional[str] = None  # in-app route ("/budgets") or an official https URL


class Source(BaseModel):
    """A web page the answer used. Only set when live web search ran."""

    title: str
    url: str


class AnswerContract(BaseModel):
    """The shape every /chat, /recommendations and dashboard-insight response
    conforms to. Frontend renders three lanes (Observed / Predicted /
    Recommended) directly from this."""

    query: Optional[str] = None
    facts: list[Fact] = Field(default_factory=list)
    predictions: list[Prediction] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)
    data_gaps: list[DataGap] = Field(default_factory=list)
    narrative: str = ""  # short natural-language summary tying it together
    nugen_narrative: Optional[str] = None  # second opinion from Nugen, when configured and reachable
    nugen_confidence: Optional[float] = None  # 0-100, only on Nugen-aligned models
    source: Optional[str] = None  # which engine wrote this answer, shown in the UI
    next_steps: list[NextStep] = Field(default_factory=list)  # prioritised "what to do next", 1-4 items
    sources: list[Source] = Field(default_factory=list)  # web pages used (empty when no web search ran)


# ---------------------------------------------------------------------------
# Simulation (what-if)
# ---------------------------------------------------------------------------


class SimulationRequest(BaseModel):
    action: ActionType
    action_params: dict = Field(default_factory=dict)


class SimulationResult(BaseModel):
    request: SimulationRequest
    health_score_before: float
    health_score_after: float
    forecast_before: CashFlowForecast
    forecast_after: CashFlowForecast
    impact: ImpactEstimate
    confidence: float = Field(ge=0, le=1)
    # Added by simulate-upgrades-agent: explicit minimum-balance guard (upgrade 1).
    # `breaches_minimum_balance` is True when `forecast_after`'s P50 path dips
    # below the caller's `ForecastInputs.minimum_balance_to_keep` at any point
    # in the horizon. Defaults to False/None for every existing action type
    # and every existing caller that doesn't configure a buffer.
    breaches_minimum_balance: bool = False
    min_balance_date: Optional[date] = None
    # Added by simulate-upgrades-agent: multi-strategy affordability (upgrade 2).
    # Populated only for the `affordability_check` action; every other action
    # type leaves this None. Each dict has the shape produced by
    # `app.simulate.engine.evaluate_affordability_strategies`.
    affordability_strategies: Optional[list[dict]] = None


# ---------------------------------------------------------------------------
# Dashboard aggregate + recompute diff (for the /timeline "what changed" view)
# ---------------------------------------------------------------------------


class DashboardSnapshot(BaseModel):
    user_id: str
    health_score: HealthScore
    net_worth: float
    monthly_income: float
    monthly_expenses: float
    savings_rate: float
    recurring_obligations: list[RecurringObligation]
    debts: list[Debt]
    forecast: CashFlowForecast
    insights: AnswerContract
    generated_at: datetime
    # False for a real signed-in user who hasn't added any accounts yet --
    # the snapshot is then an all-zero placeholder, not demo data.
    has_data: bool = True


class CreateAccountRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    type: AccountType
    balance: float = 0
    credit_limit: Optional[float] = None
    interest_rate_apr: Optional[float] = None


class CopilotAction(BaseModel):
    label: str
    href: str


class CopilotInsight(BaseModel):
    id: str
    created_at: datetime
    txn_id: Optional[str] = None
    severity: Literal["info", "positive", "warning", "critical"]
    title: str = Field(max_length=60)
    body: str
    action: Optional[CopilotAction] = None


class RecomputeDiff(BaseModel):
    """Returned after a new event/transaction is added, so the UI can
    animate exactly what changed and why."""

    trigger: str  # e.g. "added transaction", "new income source"
    health_score_before: float
    health_score_after: float
    forecast_first_gap_before: Optional[date] = None
    forecast_first_gap_after: Optional[date] = None
    new_recommendations: list[Recommendation] = Field(default_factory=list)
    removed_recommendation_actions: list[ActionType] = Field(default_factory=list)
    narrative: str
    insights: list[CopilotInsight] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------


class HistoryTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    # Additive, backward-compatible: defaults to the demo persona so existing
    # callers that don't send it keep working unchanged.
    user_id: str = "demo-priya"
    # Privacy preference (Security page toggle): when true, never call the
    # AI service for this message, regardless of whether a key is configured.
    force_offline: bool = False
    # FinPilot engine preference: auto | deep | fast | alt (brand names, never the vendor model)
    model: str = "auto"
    history: list[HistoryTurn] = Field(default_factory=list)  # earlier turns of this chat, oldest first


ChatRole = Literal["user", "assistant"]


class ChatMessage(BaseModel):
    role: ChatRole
    content: str
    answer: Optional[AnswerContract] = None
    created_at: datetime


# ---------------------------------------------------------------------------
# Transactions ledger + budgets (added by ledger-budgets-backend-agent).
# Additive only -- does not alter any existing contract above.
# ---------------------------------------------------------------------------


class TransactionPage(BaseModel):
    """Paginated response for GET /api/transactions/{user_id}."""

    items: list[Transaction]
    total: int
    page: int
    page_size: int


class TransactionUpdate(BaseModel):
    """Body for PATCH /api/transactions/{user_id}/{transaction_id}.
    All fields optional -- only the fields provided are updated."""

    category: Optional[TxnCategory] = None
    merchant: Optional[str] = None
    tags: Optional[list[str]] = None
    notes: Optional[str] = None
    review_status: Optional[str] = None


class ReviewQueueResponse(BaseModel):
    pending_count: int
    items: list[Transaction]


class ReviewAction(str, Enum):
    confirm = "confirm"
    recategorize = "recategorize"
    skip = "skip"


class ReviewTransactionRequest(BaseModel):
    action: ReviewAction
    category: Optional[TxnCategory] = None
    tags: Optional[list[str]] = None
    notes: Optional[str] = None
    create_rule: bool = False
    rule_pattern: Optional[str] = None


class CategorizationRule(BaseModel):
    id: str
    user_id: str
    match_type: RuleMatchType = RuleMatchType.contains
    pattern: str
    category: TxnCategory
    tags: list[str] = Field(default_factory=list)
    created_at: datetime


class CategorizationRuleCreate(BaseModel):
    match_type: RuleMatchType = RuleMatchType.contains
    pattern: str
    category: TxnCategory
    tags: list[str] = Field(default_factory=list)
    apply_to_existing: bool = False


class CategorizationRuleList(BaseModel):
    items: list[CategorizationRule]
    total: int


class Budget(BaseModel):
    """Mirrors models.BudgetRow."""

    id: str
    user_id: str
    category: TxnCategory
    monthly_limit: float
    rollover_enabled: bool = False
    rollover_cap: Optional[float] = None


class BudgetCreateRequest(BaseModel):
    category: TxnCategory
    monthly_limit: float
    rollover_enabled: bool = False
    rollover_cap: Optional[float] = None


class BudgetUpdateRequest(BaseModel):
    monthly_limit: Optional[float] = None
    rollover_enabled: Optional[bool] = None
    rollover_cap: Optional[float] = None


BudgetHealth = Literal["under", "near", "over"]


class BudgetStatus(BaseModel):
    category: TxnCategory
    monthly_limit: float
    spent_so_far: float
    remaining: float
    percent_used: float
    status: BudgetHealth
    rollover_amount: float = 0.0
    total_available: float = 0.0
    rollover_enabled: bool = False
    rollover_cap: Optional[float] = None


class SafeToSpend(BaseModel):
    amount: float
    basis: str  # human-readable explanation of the formula/data used
    as_of_date: date


# ---------------------------------------------------------------------------
# Goals (added by goals-networth-backend-agent -- wraps
# app.analytics.goals.project_goal's dict output in a typed shape, and
# request bodies for the goals CRUD routes).
# ---------------------------------------------------------------------------


class GoalCreateRequest(BaseModel):
    name: str
    target_amount: float
    target_date: Optional[date] = None
    current_amount: float = 0
    cover_key: str = "general"
    funding_account_id: Optional[str] = None
    auto_track: bool = False


class GoalUpdateRequest(BaseModel):
    """All fields optional -- PATCH semantics (only provided fields change)."""

    current_amount: Optional[float] = None
    target_amount: Optional[float] = None
    target_date: Optional[date] = None
    name: Optional[str] = None
    cover_key: Optional[str] = None
    funding_account_id: Optional[str] = None
    auto_track: Optional[bool] = None


class GoalProgress(BaseModel):
    goal: Goal
    monthly_contribution: float
    projected_completion_date: Optional[date] = None
    on_track: bool
    months_remaining: Optional[float] = None
    required_monthly: float = 0.0



# ---------------------------------------------------------------------------
# Net worth over time (added by goals-networth-backend-agent -- reconstructed
# live from Account + Transaction history, not a stored table).
# ---------------------------------------------------------------------------


class NetWorthPoint(BaseModel):
    date: date
    net_worth: float


class NetWorthHistory(BaseModel):
    points: list[NetWorthPoint]
    current: float


# ---------------------------------------------------------------------------
# Notifications feed (added by goals-networth-backend-agent -- live-computed
# merge of anomalies / recommendations / upcoming bills / cash-flow gaps /
# over-budget alerts, not persisted).
# ---------------------------------------------------------------------------

NotificationType = Literal["anomaly", "recommendation", "upcoming_bill", "cash_flow_gap", "over_budget"]
NotificationSeverity = Literal["info", "warning", "critical"]


class NotificationItem(BaseModel):
    id: str
    type: NotificationType
    severity: NotificationSeverity
    text: str
    date: date
    source_ref: Optional[str] = None


# ---------------------------------------------------------------------------
# Indian Income Tax Regime & Deductions Optimizer
# ---------------------------------------------------------------------------


class TaxSlabBreakdown(BaseModel):
    slab_label: str
    rate_pct: float
    taxable_amount_in_slab: float
    tax_amount: float


class TaxDeductionsBreakdown(BaseModel):
    standard_deduction: float
    section_80c: float
    section_80c_limit: float = 150000.0
    section_80d: float
    section_80d_limit: float = 75000.0
    section_80ccd_1b_nps: float
    section_80ccd_1b_limit: float = 50000.0
    section_24b_home_loan_interest: float
    section_24b_limit: float = 200000.0
    hra_exemption: float = 0.0
    other_deductions: float = 0.0
    total_deductions: float


class TaxRegimeCalculation(BaseModel):
    regime: Literal["new", "old"]
    gross_income: float
    total_deductions: float
    taxable_income: float
    slabs: list[TaxSlabBreakdown]
    tax_before_rebate: float
    rebate_87a: float
    tax_after_rebate: float
    cess_4pct: float
    net_tax_payable: float
    effective_tax_rate_pct: float
    monthly_take_home: float
    deductions_applied: TaxDeductionsBreakdown


class DetectedDeductions(BaseModel):
    section_80c_detected: float
    section_80d_detected: float
    home_loan_interest_detected: float
    rent_paid_detected: float


class TaxOptimizationAnalysis(BaseModel):
    user_id: str
    gross_annual_income: float
    new_regime: TaxRegimeCalculation
    old_regime: TaxRegimeCalculation
    recommended_regime: Literal["new", "old"]
    annual_tax_savings: float
    monthly_take_home_delta: float
    recommendation_rationale: str
    break_even_deductions_needed: float
    detected_deductions: DetectedDeductions


class TaxCalculationRequest(BaseModel):
    gross_annual_income: Optional[float] = None
    section_80c: Optional[float] = None
    section_80d: Optional[float] = None
    section_80ccd_1b_nps: Optional[float] = None
    section_24b_home_loan: Optional[float] = None
    hra_exemption: Optional[float] = None
    other_deductions: Optional[float] = None


# ---------------------------------------------------------------------------
# Household & Co-Piloting Collaboration (Pillar 5D)
# ---------------------------------------------------------------------------


class HouseholdRole(str, Enum):
    owner = "owner"
    editor = "editor"
    viewer = "viewer"


class InviteStatus(str, Enum):
    pending = "pending"
    accepted = "accepted"
    revoked = "revoked"
    expired = "expired"


class Household(BaseModel):
    id: str
    name: str
    owner_user_id: str
    created_at: datetime


class HouseholdMember(BaseModel):
    id: str
    household_id: str
    user_id: str
    role: HouseholdRole
    joined_at: datetime
    display_name: Optional[str] = None
    avatar_letter: Optional[str] = None
    net_worth: Optional[float] = None


class HouseholdInvite(BaseModel):
    id: str
    household_id: str
    invited_email: str
    role: HouseholdRole
    status: InviteStatus
    created_at: datetime
    expires_at: datetime
    invite_link: Optional[str] = None
    token: Optional[str] = None


class CreateHouseholdRequest(BaseModel):
    name: str


class CreateInviteRequest(BaseModel):
    email: str
    role: HouseholdRole = HouseholdRole.editor


class AcceptInviteRequest(BaseModel):
    token: str


class MemberWealthContribution(BaseModel):
    user_id: str
    display_name: str
    role: str
    assets: float
    liabilities: float
    net_worth: float
    pct_of_household: float


class HouseholdNetWorthSummary(BaseModel):
    total_net_worth: float
    total_assets: float
    total_liabilities: float
    members_breakdown: list[MemberWealthContribution]


class HouseholdSummary(BaseModel):
    household: Household
    members: list[HouseholdMember]
    invites: list[HouseholdInvite]
    net_worth_summary: HouseholdNetWorthSummary
    user_role: HouseholdRole


