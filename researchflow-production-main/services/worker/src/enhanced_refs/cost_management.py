"""
Cost Management & Billing Integration for AI Bridge

Enterprise cost control with:
- Real-time cost tracking per user/organization
- Budget management and alerts
- Cost optimization strategies
- Billing integration and reporting
- Cost forecasting and analysis
- Usage-based pricing models

Author: AI Bridge Enhancement Team
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
from decimal import Decimal, ROUND_HALF_UP
from collections import defaultdict, deque
import statistics

logger = logging.getLogger(__name__)

class CostCategory(Enum):
    """Categories of costs."""
    AI_INFERENCE = "ai_inference"         # AI model inference costs
    DATA_PROCESSING = "data_processing"   # Data processing costs
    STORAGE = "storage"                   # Data storage costs
    BANDWIDTH = "bandwidth"               # Network bandwidth costs
    COMPUTE = "compute"                   # Raw compute costs
    API_CALLS = "api_calls"              # External API calls
    PREMIUM_FEATURES = "premium_features" # Premium feature costs

class BillingPeriod(Enum):
    """Billing period types."""
    HOURLY = "hourly"
    DAILY = "daily" 
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"

class CostModel(Enum):
    """Cost calculation models."""
    PAY_PER_USE = "pay_per_use"          # Pay for actual usage
    SUBSCRIPTION = "subscription"         # Fixed subscription
    HYBRID = "hybrid"                    # Combination of both
    FREEMIUM = "freemium"                # Free tier with paid upgrades

@dataclass
class CostEntry:
    """Individual cost entry."""
    entry_id: str
    user_id: str
    organization_id: Optional[str]
    
    # Cost details
    amount_usd: Decimal
    category: CostCategory
    description: str
    
    # Usage details
    units_consumed: int = 0
    unit_type: str = "requests"
    unit_cost: Decimal = Decimal("0.001")
    
    # Timing
    timestamp: datetime = field(default_factory=datetime.utcnow)
    billing_period: Optional[str] = None
    
    # Metadata
    resource_id: Optional[str] = None
    session_id: Optional[str] = None
    endpoint: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "entry_id": self.entry_id,
            "user_id": self.user_id,
            "organization_id": self.organization_id,
            "amount_usd": float(self.amount_usd),
            "category": self.category.value,
            "description": self.description,
            "units_consumed": self.units_consumed,
            "unit_type": self.unit_type,
            "unit_cost": float(self.unit_cost),
            "timestamp": self.timestamp.isoformat(),
            "billing_period": self.billing_period,
            "resource_id": self.resource_id,
            "session_id": self.session_id,
            "endpoint": self.endpoint,
            "metadata": self.metadata
        }

@dataclass
class Budget:
    """Budget configuration for users/organizations."""
    budget_id: str
    name: str
    
    # Budget amounts
    total_budget_usd: Decimal
    spent_usd: Decimal = Decimal("0")
    remaining_usd: Decimal = field(init=False)
    
    # Scope
    user_id: Optional[str] = None
    organization_id: Optional[str] = None
    
    # Period
    billing_period: BillingPeriod = BillingPeriod.MONTHLY
    period_start: datetime = field(default_factory=datetime.utcnow)
    period_end: Optional[datetime] = None
    
    # Alerts
    alert_thresholds: List[float] = field(default_factory=lambda: [0.5, 0.8, 0.9, 1.0])  # 50%, 80%, 90%, 100%
    alerts_sent: List[float] = field(default_factory=list)
    
    # Status
    is_active: bool = True
    auto_renew: bool = True
    
    def __post_init__(self):
        """Calculate remaining budget."""
        self.remaining_usd = self.total_budget_usd - self.spent_usd
    
    def add_cost(self, amount: Decimal) -> bool:
        """Add cost to budget and check if within limits."""
        if not self.is_active:
            return False
        
        new_spent = self.spent_usd + amount
        
        if new_spent <= self.total_budget_usd:
            self.spent_usd = new_spent
            self.remaining_usd = self.total_budget_usd - self.spent_usd
            return True
        
        return False
    
    def get_usage_percentage(self) -> float:
        """Get budget usage percentage."""
        if self.total_budget_usd <= 0:
            return 0.0
        return float(self.spent_usd / self.total_budget_usd * 100)
    
    def should_send_alert(self) -> Optional[float]:
        """Check if a budget alert should be sent."""
        usage_percent = self.get_usage_percentage() / 100
        
        for threshold in self.alert_thresholds:
            if usage_percent >= threshold and threshold not in self.alerts_sent:
                return threshold
        
        return None

@dataclass
class CostOptimizationStrategy:
    """Cost optimization strategy."""
    strategy_id: str
    name: str
    description: str
    
    # Optimization parameters
    enabled: bool = True
    priority: int = 100
    
    # Conditions for activation
    conditions: Dict[str, Any] = field(default_factory=dict)
    
    # Actions to take
    actions: List[Dict[str, Any]] = field(default_factory=list)
    
    # Results tracking
    estimated_savings_usd: Decimal = Decimal("0")
    actual_savings_usd: Decimal = Decimal("0")
    activation_count: int = 0

class CostManagementSystem:
    """
    Comprehensive cost management and billing system.
    
    Features:
    - Real-time cost tracking and analysis
    - Budget management with alerts
    - Cost optimization strategies
    - Usage analytics and reporting
    - Billing integration
    - Cost forecasting
    """
    
    def __init__(self,
                 enable_billing_integration: bool = False,
                 enable_cost_optimization: bool = True):
        self.enable_billing_integration = enable_billing_integration
        self.enable_cost_optimization = enable_cost_optimization
        
        # Cost storage
        self.cost_entries: List[CostEntry] = []
        self.budgets: Dict[str, Budget] = {}
        self.optimization_strategies: Dict[str, CostOptimizationStrategy] = {}
        
        # Usage tracking
        self.usage_analytics: Dict[str, Any] = defaultdict(dict)
        self.cost_history: deque = deque(maxlen=10000)
        
        # Initialize default strategies
        self._setup_default_optimization_strategies()
        
        logger.info("Cost Management System initialized")
    
    def _setup_default_optimization_strategies(self):
        """Setup default cost optimization strategies."""
        strategies = [
            CostOptimizationStrategy(
                strategy_id="cache_optimization",
                name="Aggressive Caching",
                description="Increase cache hit rates to reduce AI processing costs",
                conditions={"cost_per_hour": {"gt": 5.0}},
                actions=[
                    {"type": "increase_cache_ttl", "factor": 2},
                    {"type": "enable_result_caching", "enabled": True}
                ]
            ),
            CostOptimizationStrategy(
                strategy_id="model_optimization", 
                name="Model Selection Optimization",
                description="Use lower-cost models for simple tasks",
                conditions={"avg_request_complexity": {"lt": 0.5}},
                actions=[
                    {"type": "use_cheaper_model", "model": "gpt-3.5-turbo"},
                    {"type": "reduce_max_tokens", "factor": 0.8}
                ]
            ),
            CostOptimizationStrategy(
                strategy_id="batch_processing",
                name="Batch Processing",
                description="Batch similar requests to reduce per-request costs",
                conditions={"queue_size": {"gt": 10}},
                actions=[
                    {"type": "enable_batching", "batch_size": 5},
                    {"type": "batch_timeout_ms", "timeout": 5000}
                ]
            )
        ]
        
        for strategy in strategies:
            self.optimization_strategies[strategy.strategy_id] = strategy
    
    async def record_cost(self,
                         user_id: str,
                         amount_usd: float,
                         category: CostCategory,
                         description: str,
                         organization_id: Optional[str] = None,
                         units_consumed: int = 1,
                         unit_type: str = "requests",
                         endpoint: Optional[str] = None,
                         metadata: Optional[Dict[str, Any]] = None) -> str:
        """Record a cost entry."""
        try:
            entry_id = f"cost_{int(time.time() * 1000)}_{user_id}"
            
            amount_decimal = Decimal(str(amount_usd)).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
            unit_cost = amount_decimal / max(units_consumed, 1)
            
            cost_entry = CostEntry(
                entry_id=entry_id,
                user_id=user_id,
                organization_id=organization_id,
                amount_usd=amount_decimal,
                category=category,
                description=description,
                units_consumed=units_consumed,
                unit_type=unit_type,
                unit_cost=unit_cost,
                endpoint=endpoint,
                metadata=metadata or {}
            )
            
            # Store cost entry
            self.cost_entries.append(cost_entry)
            self.cost_history.append(cost_entry)
            
            # Check budgets
            await self._check_budgets(user_id, organization_id, amount_decimal)
            
            # Update usage analytics
            await self._update_usage_analytics(cost_entry)
            
            # Check for cost optimization opportunities
            if self.enable_cost_optimization:
                await self._check_optimization_opportunities(cost_entry)
            
            logger.debug(f"Cost recorded: ${amount_decimal} for {user_id} ({description})")
            return entry_id
            
        except Exception as e:
            logger.error(f"Error recording cost: {e}")
            raise
    
    async def _check_budgets(self, user_id: str, organization_id: Optional[str], amount: Decimal):
        """Check if cost would exceed budgets and send alerts."""
        try:
            # Check user budgets
            user_budgets = [b for b in self.budgets.values() if b.user_id == user_id]
            for budget in user_budgets:
                if budget.add_cost(amount):
                    # Within budget
                    alert_threshold = budget.should_send_alert()
                    if alert_threshold:
                        await self._send_budget_alert(budget, alert_threshold)
                        budget.alerts_sent.append(alert_threshold)
                else:
                    # Budget exceeded
                    logger.warning(f"Budget exceeded for user {user_id}: {budget.name}")
                    await self._handle_budget_exceeded(budget)
            
            # Check organization budgets
            if organization_id:
                org_budgets = [b for b in self.budgets.values() if b.organization_id == organization_id]
                for budget in org_budgets:
                    if budget.add_cost(amount):
                        alert_threshold = budget.should_send_alert()
                        if alert_threshold:
                            await self._send_budget_alert(budget, alert_threshold)
                            budget.alerts_sent.append(alert_threshold)
                    else:
                        logger.warning(f"Organization budget exceeded: {organization_id}")
                        await self._handle_budget_exceeded(budget)
            
        except Exception as e:
            logger.error(f"Error checking budgets: {e}")
    
    async def _send_budget_alert(self, budget: Budget, threshold: float):
        """Send budget alert (mock implementation)."""
        logger.warning(f"Budget alert: {budget.name} at {threshold*100:.0f}% usage")
        # In production, integrate with notification system
    
    async def _handle_budget_exceeded(self, budget: Budget):
        """Handle budget exceeded scenario."""
        logger.error(f"Budget exceeded: {budget.name}")
        # In production, could disable features or send notifications
    
    async def _update_usage_analytics(self, cost_entry: CostEntry):
        """Update usage analytics with new cost entry."""
        try:
            # User-level analytics
            user_key = f"user:{cost_entry.user_id}"
            if user_key not in self.usage_analytics:
                self.usage_analytics[user_key] = {
                    "total_cost": Decimal("0"),
                    "request_count": 0,
                    "categories": defaultdict(Decimal),
                    "endpoints": defaultdict(int),
                    "first_usage": cost_entry.timestamp,
                    "last_usage": cost_entry.timestamp
                }
            
            analytics = self.usage_analytics[user_key]
            analytics["total_cost"] += cost_entry.amount_usd
            analytics["request_count"] += 1
            analytics["categories"][cost_entry.category.value] += cost_entry.amount_usd
            if cost_entry.endpoint:
                analytics["endpoints"][cost_entry.endpoint] += 1
            analytics["last_usage"] = cost_entry.timestamp
            
            # Organization-level analytics
            if cost_entry.organization_id:
                org_key = f"org:{cost_entry.organization_id}"
                if org_key not in self.usage_analytics:
                    self.usage_analytics[org_key] = {
                        "total_cost": Decimal("0"),
                        "request_count": 0,
                        "user_count": set(),
                        "categories": defaultdict(Decimal),
                        "first_usage": cost_entry.timestamp,
                        "last_usage": cost_entry.timestamp
                    }
                
                org_analytics = self.usage_analytics[org_key]
                org_analytics["total_cost"] += cost_entry.amount_usd
                org_analytics["request_count"] += 1
                org_analytics["user_count"].add(cost_entry.user_id)
                org_analytics["categories"][cost_entry.category.value] += cost_entry.amount_usd
                org_analytics["last_usage"] = cost_entry.timestamp
            
        except Exception as e:
            logger.error(f"Error updating usage analytics: {e}")
    
    async def _check_optimization_opportunities(self, cost_entry: CostEntry):
        """Check for cost optimization opportunities."""
        try:
            # Simple optimization checks
            recent_costs = [entry for entry in self.cost_history if 
                          entry.timestamp > datetime.utcnow() - timedelta(hours=1)]
            
            if len(recent_costs) >= 10:  # Need some data for analysis
                hourly_cost = sum(float(entry.amount_usd) for entry in recent_costs)
                
                for strategy in self.optimization_strategies.values():
                    if strategy.enabled and self._should_activate_strategy(strategy, hourly_cost):
                        await self._activate_optimization_strategy(strategy)
            
        except Exception as e:
            logger.error(f"Error checking optimization opportunities: {e}")
    
    def _should_activate_strategy(self, strategy: CostOptimizationStrategy, hourly_cost: float) -> bool:
        """Check if optimization strategy should be activated."""
        conditions = strategy.conditions
        
        # Check cost-per-hour condition
        if "cost_per_hour" in conditions:
            cost_condition = conditions["cost_per_hour"]
            if "gt" in cost_condition and hourly_cost <= cost_condition["gt"]:
                return False
            if "lt" in cost_condition and hourly_cost >= cost_condition["lt"]:
                return False
        
        # Check other conditions (simplified)
        return True
    
    async def _activate_optimization_strategy(self, strategy: CostOptimizationStrategy):
        """Activate a cost optimization strategy."""
        try:
            strategy.activation_count += 1
            logger.info(f"Activating cost optimization strategy: {strategy.name}")
            
            # Execute optimization actions (mock implementation)
            for action in strategy.actions:
                await self._execute_optimization_action(action, strategy)
            
        except Exception as e:
            logger.error(f"Error activating optimization strategy: {e}")
    
    async def _execute_optimization_action(self, action: Dict[str, Any], strategy: CostOptimizationStrategy):
        """Execute a specific optimization action."""
        action_type = action.get("type")
        
        if action_type == "increase_cache_ttl":
            logger.info(f"Optimization: Increasing cache TTL by factor {action.get('factor', 2)}")
            # In production, would update cache configuration
            
        elif action_type == "use_cheaper_model":
            logger.info(f"Optimization: Switching to cheaper model {action.get('model')}")
            # In production, would update model selection
            
        elif action_type == "enable_batching":
            logger.info(f"Optimization: Enabling batch processing (size: {action.get('batch_size')})")
            # In production, would enable batch processing
        
        # Estimate savings (mock calculation)
        estimated_savings = Decimal("0.50")  # $0.50 per activation
        strategy.estimated_savings_usd += estimated_savings
    
    async def get_cost_summary(self,
                              user_id: Optional[str] = None,
                              organization_id: Optional[str] = None,
                              start_date: Optional[datetime] = None,
                              end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Get comprehensive cost summary."""
        try:
            # Filter cost entries
            filtered_entries = self._filter_cost_entries(user_id, organization_id, start_date, end_date)
            
            if not filtered_entries:
                return {
                    "total_cost_usd": 0.0,
                    "entry_count": 0,
                    "period": self._format_period(start_date, end_date)
                }
            
            # Calculate summary statistics
            total_cost = sum(entry.amount_usd for entry in filtered_entries)
            
            # Category breakdown
            category_costs = defaultdict(Decimal)
            for entry in filtered_entries:
                category_costs[entry.category.value] += entry.amount_usd
            
            # Endpoint breakdown
            endpoint_costs = defaultdict(Decimal)
            endpoint_counts = defaultdict(int)
            for entry in filtered_entries:
                if entry.endpoint:
                    endpoint_costs[entry.endpoint] += entry.amount_usd
                    endpoint_counts[entry.endpoint] += 1
            
            # Time-based analysis
            daily_costs = defaultdict(Decimal)
            for entry in filtered_entries:
                day_key = entry.timestamp.strftime("%Y-%m-%d")
                daily_costs[day_key] += entry.amount_usd
            
            # Trends
            costs_list = list(daily_costs.values())
            if len(costs_list) > 1:
                trend = "increasing" if costs_list[-1] > costs_list[0] else "decreasing"
                trend_magnitude = float(abs(costs_list[-1] - costs_list[0]) / costs_list[0] * 100) if costs_list[0] > 0 else 0
            else:
                trend = "stable"
                trend_magnitude = 0.0
            
            return {
                "total_cost_usd": float(total_cost),
                "entry_count": len(filtered_entries),
                "period": self._format_period(start_date, end_date),
                "category_breakdown": {k: float(v) for k, v in category_costs.items()},
                "endpoint_breakdown": {
                    "costs": {k: float(v) for k, v in endpoint_costs.items()},
                    "counts": dict(endpoint_counts)
                },
                "daily_costs": {k: float(v) for k, v in daily_costs.items()},
                "trends": {
                    "direction": trend,
                    "magnitude_percent": trend_magnitude
                },
                "average_cost_per_request": float(total_cost / len(filtered_entries)) if filtered_entries else 0.0
            }
            
        except Exception as e:
            logger.error(f"Error getting cost summary: {e}")
            return {"error": str(e)}
    
    def _filter_cost_entries(self,
                            user_id: Optional[str],
                            organization_id: Optional[str], 
                            start_date: Optional[datetime],
                            end_date: Optional[datetime]) -> List[CostEntry]:
        """Filter cost entries based on criteria."""
        filtered = self.cost_entries
        
        if user_id:
            filtered = [e for e in filtered if e.user_id == user_id]
        
        if organization_id:
            filtered = [e for e in filtered if e.organization_id == organization_id]
        
        if start_date:
            filtered = [e for e in filtered if e.timestamp >= start_date]
        
        if end_date:
            filtered = [e for e in filtered if e.timestamp <= end_date]
        
        return filtered
    
    def _format_period(self, start_date: Optional[datetime], end_date: Optional[datetime]) -> str:
        """Format time period for display."""
        if start_date and end_date:
            return f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        elif start_date:
            return f"Since {start_date.strftime('%Y-%m-%d')}"
        elif end_date:
            return f"Until {end_date.strftime('%Y-%m-%d')}"
        else:
            return "All time"
    
    async def create_budget(self,
                           name: str,
                           total_budget_usd: float,
                           user_id: Optional[str] = None,
                           organization_id: Optional[str] = None,
                           billing_period: BillingPeriod = BillingPeriod.MONTHLY) -> str:
        """Create a new budget."""
        try:
            budget_id = f"budget_{int(time.time())}_{user_id or organization_id or 'global'}"
            
            budget = Budget(
                budget_id=budget_id,
                name=name,
                total_budget_usd=Decimal(str(total_budget_usd)),
                user_id=user_id,
                organization_id=organization_id,
                billing_period=billing_period
            )
            
            self.budgets[budget_id] = budget
            
            logger.info(f"Budget created: {name} (${total_budget_usd})")
            return budget_id
            
        except Exception as e:
            logger.error(f"Error creating budget: {e}")
            raise
    
    async def get_budget_status(self, budget_id: str) -> Optional[Dict[str, Any]]:
        """Get budget status and usage."""
        try:
            if budget_id not in self.budgets:
                return None
            
            budget = self.budgets[budget_id]
            
            return {
                "budget_id": budget_id,
                "name": budget.name,
                "total_budget_usd": float(budget.total_budget_usd),
                "spent_usd": float(budget.spent_usd),
                "remaining_usd": float(budget.remaining_usd),
                "usage_percentage": budget.get_usage_percentage(),
                "billing_period": budget.billing_period.value,
                "period_start": budget.period_start.isoformat(),
                "period_end": budget.period_end.isoformat() if budget.period_end else None,
                "is_active": budget.is_active,
                "alerts_sent": budget.alerts_sent,
                "alert_thresholds": budget.alert_thresholds
            }
            
        except Exception as e:
            logger.error(f"Error getting budget status: {e}")
            return None
    
    async def get_cost_forecast(self,
                               user_id: Optional[str] = None,
                               organization_id: Optional[str] = None,
                               days_ahead: int = 30) -> Dict[str, Any]:
        """Generate cost forecast based on historical usage."""
        try:
            # Get recent cost data (last 30 days)
            start_date = datetime.utcnow() - timedelta(days=30)
            recent_entries = self._filter_cost_entries(user_id, organization_id, start_date, None)
            
            if not recent_entries:
                return {
                    "forecast_period_days": days_ahead,
                    "estimated_cost_usd": 0.0,
                    "confidence": "no_data"
                }
            
            # Calculate daily costs
            daily_costs = defaultdict(Decimal)
            for entry in recent_entries:
                day_key = entry.timestamp.strftime("%Y-%m-%d")
                daily_costs[day_key] += entry.amount_usd
            
            # Simple forecast based on average
            costs_list = [float(cost) for cost in daily_costs.values()]
            
            if len(costs_list) >= 7:  # Need at least a week of data
                # Calculate trend
                recent_avg = statistics.mean(costs_list[-7:])  # Last week
                
                # Project forward
                forecasted_cost = recent_avg * days_ahead
                
                # Calculate confidence based on variance
                variance = statistics.variance(costs_list) if len(costs_list) > 1 else 0
                confidence = "high" if variance < recent_avg * 0.2 else "medium" if variance < recent_avg * 0.5 else "low"
                
                return {
                    "forecast_period_days": days_ahead,
                    "estimated_cost_usd": round(forecasted_cost, 4),
                    "daily_average_usd": round(recent_avg, 4),
                    "confidence": confidence,
                    "data_points": len(costs_list),
                    "variance": round(variance, 4),
                    "trend": "increasing" if len(costs_list) > 1 and costs_list[-1] > costs_list[0] else "stable"
                }
            else:
                # Not enough data for good forecast
                simple_avg = statistics.mean(costs_list)
                return {
                    "forecast_period_days": days_ahead,
                    "estimated_cost_usd": round(simple_avg * days_ahead, 4),
                    "daily_average_usd": round(simple_avg, 4),
                    "confidence": "low",
                    "data_points": len(costs_list),
                    "note": "Insufficient data for reliable forecast"
                }
            
        except Exception as e:
            logger.error(f"Error generating cost forecast: {e}")
            return {"error": str(e)}

# Global cost management system
_cost_manager: Optional[CostManagementSystem] = None

def get_cost_manager() -> CostManagementSystem:
    """Get global cost management system instance."""
    global _cost_manager
    if _cost_manager is None:
        _cost_manager = CostManagementSystem()
    return _cost_manager

# Utility functions for FastAPI integration
async def record_request_cost(user_id: str,
                             endpoint: str,
                             processing_time_seconds: float,
                             tokens_used: int = 0,
                             organization_id: Optional[str] = None) -> str:
    """Record cost for an API request."""
    cost_manager = get_cost_manager()
    
    # Calculate cost based on processing time and tokens
    base_cost = 0.001  # Base cost per request
    time_cost = processing_time_seconds * 0.0001  # $0.0001 per second
    token_cost = tokens_used * 0.00001  # $0.00001 per token
    
    total_cost = base_cost + time_cost + token_cost
    
    return await cost_manager.record_cost(
        user_id=user_id,
        amount_usd=total_cost,
        category=CostCategory.AI_INFERENCE,
        description=f"API request to {endpoint}",
        organization_id=organization_id,
        units_consumed=1,
        unit_type="requests",
        endpoint=endpoint,
        metadata={
            "processing_time_seconds": processing_time_seconds,
            "tokens_used": tokens_used
        }
    )