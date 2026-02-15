"""
Shortage Alerting Service

Handles:
- Predictive shortage detection
- Multi-level alert management
- Alert lifecycle (create, acknowledge, escalate, resolve)
- Notification management
- Shortage analytics
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, update
from sqlalchemy.orm import selectinload

from models.alerts import (
    ShortageAlert, AlertHistory, AlertSubscription, AlertAction,
    AlertLevel, AlertType, AlertStatus
)
from models.inventory import FoodInventory, FoodCategory, ConsumptionPattern
from models.agricultural import Region, HarvestForecast
from models.distribution import RouteDisruption
from schemas.alerts import (
    ShortageAlertCreate, ShortageAlertUpdate, ShortageAlertResponse,
    AlertHistoryCreate, AlertHistoryResponse,
    AlertSubscriptionCreate, AlertSubscriptionUpdate, AlertSubscriptionResponse,
    AlertActionCreate, AlertActionUpdate, AlertActionResponse,
    AlertDashboard, AlertAnalytics, AlertSummary,
    PredictedShortage, ShortageRiskAssessment
)
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ShortageAlertingService:
    """Service for predictive shortage alerting."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ==================== Alert Management ====================

    async def create_alert(self, data: ShortageAlertCreate) -> ShortageAlert:
        """Create a new shortage alert."""
        alert_data = data.model_dump()
        alert_data["alert_code"] = f"SA-{uuid.uuid4().hex[:8].upper()}"

        alert = ShortageAlert(**alert_data)
        self.db.add(alert)
        await self.db.flush()
        await self.db.refresh(alert)

        # Create initial history record
        await self._record_history(
            alert_id=alert.id,
            new_level=alert.alert_level,
            new_status=AlertStatus.ACTIVE,
            change_reason="Alert created"
        )

        # Trigger notifications
        await self._send_notifications(alert)

        logger.warning(
            f"Alert created: {alert.alert_code} - {alert.title} "
            f"(Level: {alert.alert_level.value})"
        )
        return alert

    async def get_alert(self, alert_id: int) -> Optional[ShortageAlert]:
        """Get alert by ID."""
        result = await self.db.execute(
            select(ShortageAlert)
            .options(selectinload(ShortageAlert.history))
            .where(ShortageAlert.id == alert_id)
        )
        return result.scalar_one_or_none()

    async def get_alert_by_code(self, alert_code: str) -> Optional[ShortageAlert]:
        """Get alert by code."""
        result = await self.db.execute(
            select(ShortageAlert).where(ShortageAlert.alert_code == alert_code)
        )
        return result.scalar_one_or_none()

    async def update_alert(
        self,
        alert_id: int,
        data: ShortageAlertUpdate,
        changed_by: Optional[str] = None
    ) -> Optional[ShortageAlert]:
        """Update an alert."""
        alert = await self.get_alert(alert_id)
        if not alert:
            return None

        update_data = data.model_dump(exclude_unset=True)
        previous_level = alert.alert_level
        previous_status = alert.status

        for field, value in update_data.items():
            setattr(alert, field, value)

        # Record status/level change in history
        if "alert_level" in update_data or "status" in update_data:
            await self._record_history(
                alert_id=alert.id,
                previous_level=previous_level if "alert_level" in update_data else None,
                new_level=alert.alert_level if "alert_level" in update_data else None,
                previous_status=previous_status if "status" in update_data else None,
                new_status=alert.status if "status" in update_data else None,
                changed_by=changed_by,
                change_reason="Alert updated"
            )

        # Handle resolution
        if alert.status == AlertStatus.RESOLVED:
            alert.resolved_at = datetime.utcnow()
            alert.is_active = False

        await self.db.flush()
        await self.db.refresh(alert)

        logger.info(f"Alert updated: {alert.alert_code}")
        return alert

    async def acknowledge_alert(
        self,
        alert_id: int,
        acknowledged_by: str
    ) -> Optional[ShortageAlert]:
        """Acknowledge an alert."""
        return await self.update_alert(
            alert_id=alert_id,
            data=ShortageAlertUpdate(status=AlertStatus.ACKNOWLEDGED),
            changed_by=acknowledged_by
        )

    async def escalate_alert(
        self,
        alert_id: int,
        escalate_to: List[str],
        escalated_by: str,
        reason: Optional[str] = None
    ) -> Optional[ShortageAlert]:
        """Escalate an alert to higher authorities."""
        alert = await self.get_alert(alert_id)
        if not alert:
            return None

        alert.status = AlertStatus.ESCALATED
        alert.escalation_level = (alert.escalation_level or 0) + 1
        alert.escalated_to = escalate_to

        await self._record_history(
            alert_id=alert.id,
            previous_status=alert.status,
            new_status=AlertStatus.ESCALATED,
            changed_by=escalated_by,
            change_reason=reason or "Alert escalated"
        )

        # Send escalation notifications
        await self._send_escalation_notifications(alert, escalate_to)

        await self.db.flush()
        await self.db.refresh(alert)

        logger.warning(f"Alert escalated: {alert.alert_code} to {escalate_to}")
        return alert

    async def resolve_alert(
        self,
        alert_id: int,
        resolved_by: str,
        resolution_notes: Optional[str] = None
    ) -> Optional[ShortageAlert]:
        """Resolve an alert."""
        alert = await self.get_alert(alert_id)
        if not alert:
            return None

        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = datetime.utcnow()
        alert.is_active = False

        await self._record_history(
            alert_id=alert.id,
            previous_status=alert.status,
            new_status=AlertStatus.RESOLVED,
            changed_by=resolved_by,
            change_reason=resolution_notes or "Alert resolved"
        )

        await self.db.flush()
        await self.db.refresh(alert)

        logger.info(f"Alert resolved: {alert.alert_code}")
        return alert

    # ==================== Alert History ====================

    async def _record_history(
        self,
        alert_id: int,
        previous_level: Optional[AlertLevel] = None,
        new_level: Optional[AlertLevel] = None,
        previous_status: Optional[AlertStatus] = None,
        new_status: Optional[AlertStatus] = None,
        changed_by: Optional[str] = None,
        change_reason: Optional[str] = None
    ) -> AlertHistory:
        """Record alert history entry."""
        history = AlertHistory(
            alert_id=alert_id,
            changed_at=datetime.utcnow(),
            changed_by=changed_by,
            previous_level=previous_level,
            new_level=new_level,
            previous_status=previous_status,
            new_status=new_status,
            change_reason=change_reason
        )
        self.db.add(history)
        await self.db.flush()
        return history

    async def get_alert_history(self, alert_id: int) -> List[AlertHistory]:
        """Get history for an alert."""
        result = await self.db.execute(
            select(AlertHistory)
            .where(AlertHistory.alert_id == alert_id)
            .order_by(AlertHistory.changed_at.desc())
        )
        return list(result.scalars().all())

    # ==================== Alert Queries ====================

    async def list_alerts(
        self,
        region_id: Optional[int] = None,
        alert_type: Optional[AlertType] = None,
        alert_level: Optional[AlertLevel] = None,
        status: Optional[AlertStatus] = None,
        is_active: Optional[bool] = True,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[ShortageAlert], int]:
        """List alerts with filters."""
        query = select(ShortageAlert)

        if region_id:
            query = query.where(ShortageAlert.region_id == region_id)
        if alert_type:
            query = query.where(ShortageAlert.alert_type == alert_type)
        if alert_level:
            query = query.where(ShortageAlert.alert_level == alert_level)
        if status:
            query = query.where(ShortageAlert.status == status)
        if is_active is not None:
            query = query.where(ShortageAlert.is_active == is_active)

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar()

        query = query.order_by(ShortageAlert.created_at.desc())
        query = query.offset(offset).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def get_critical_alerts(
        self,
        region_id: Optional[int] = None
    ) -> List[ShortageAlert]:
        """Get all critical active alerts."""
        query = select(ShortageAlert).where(
            and_(
                ShortageAlert.alert_level == AlertLevel.CRITICAL,
                ShortageAlert.is_active == True
            )
        )

        if region_id:
            query = query.where(ShortageAlert.region_id == region_id)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ==================== Predictive Alerting ====================

    async def detect_shortages(
        self,
        region_id: Optional[int] = None
    ) -> List[PredictedShortage]:
        """Detect potential shortages across regions."""
        predictions = []

        # Get regions to analyze
        if region_id:
            regions = [(region_id,)]
        else:
            result = await self.db.execute(
                select(Region.id).where(Region.is_active == True)
            )
            regions = result.all()

        for (rid,) in regions:
            region_predictions = await self._analyze_region_shortages(rid)
            predictions.extend(region_predictions)

        # Sort by urgency (days to shortage)
        predictions.sort(
            key=lambda x: x.days_of_supply if x.days_of_supply else float('inf')
        )

        return predictions

    async def _analyze_region_shortages(
        self,
        region_id: int
    ) -> List[PredictedShortage]:
        """Analyze shortage risks for a specific region."""
        predictions = []

        # Get region info
        region_result = await self.db.execute(
            select(Region).where(Region.id == region_id)
        )
        region = region_result.scalar_one_or_none()
        if not region:
            return []

        # Get current inventory levels
        inventory_result = await self.db.execute(
            select(FoodInventory)
            .options(selectinload(FoodInventory.category))
            .where(FoodInventory.region_id == region_id)
            .order_by(FoodInventory.recorded_at.desc())
        )
        inventories = inventory_result.scalars().all()

        # Analyze each category
        seen_categories = set()
        for inv in inventories:
            if inv.category_id in seen_categories:
                continue
            seen_categories.add(inv.category_id)

            # Check if shortage predicted
            if inv.days_of_supply and inv.days_of_supply < settings.shortage_warning_days:
                # Calculate shortage date
                shortage_date = datetime.utcnow() + timedelta(
                    days=inv.days_of_supply
                )

                # Get risk factors
                risk_factors = await self._identify_risk_factors(
                    region_id, inv.category_id
                )

                # Calculate confidence based on data quality
                confidence = self._calculate_prediction_confidence(inv)

                predictions.append(PredictedShortage(
                    region_id=region_id,
                    region_name=region.name,
                    category_id=inv.category_id,
                    category_name=inv.category.name if inv.category else f"Category {inv.category_id}",
                    current_inventory_tonnes=inv.quantity_tonnes,
                    days_of_supply=inv.days_of_supply,
                    predicted_shortage_date=shortage_date,
                    confidence_score=confidence,
                    risk_factors=risk_factors,
                    recommended_actions=self._generate_shortage_recommendations(
                        inv.days_of_supply, risk_factors
                    )
                ))

        return predictions

    async def _identify_risk_factors(
        self,
        region_id: int,
        category_id: int
    ) -> List[str]:
        """Identify risk factors contributing to potential shortage."""
        factors = []

        # Check for harvest forecast issues
        forecast_result = await self.db.execute(
            select(HarvestForecast)
            .where(
                and_(
                    HarvestForecast.region_id == region_id,
                    HarvestForecast.target_date > datetime.utcnow(),
                    HarvestForecast.is_active == True
                )
            )
            .order_by(HarvestForecast.target_date)
            .limit(1)
        )
        forecast = forecast_result.scalar_one_or_none()

        if forecast:
            if forecast.deviation_percentage and forecast.deviation_percentage < -20:
                factors.append(
                    f"Harvest forecast {abs(forecast.deviation_percentage):.0f}% below normal"
                )
            if forecast.weather_risk and forecast.weather_risk > 0.5:
                factors.append("High weather-related risk")
            if forecast.labor_risk and forecast.labor_risk > 0.5:
                factors.append("Labor shortage affecting production")

        # Check for distribution disruptions
        disruption_result = await self.db.execute(
            select(RouteDisruption)
            .where(
                and_(
                    RouteDisruption.region_id == region_id,
                    RouteDisruption.is_active == True
                )
            )
        )
        disruptions = disruption_result.scalars().all()

        if disruptions:
            factors.append(f"{len(disruptions)} active distribution disruptions")

        # Check consumption anomalies
        consumption_result = await self.db.execute(
            select(ConsumptionPattern)
            .where(
                and_(
                    ConsumptionPattern.region_id == region_id,
                    ConsumptionPattern.category_id == category_id,
                    ConsumptionPattern.anomaly_detected == True
                )
            )
            .order_by(ConsumptionPattern.period_start.desc())
            .limit(1)
        )
        consumption = consumption_result.scalar_one_or_none()

        if consumption and consumption.anomaly_detected:
            factors.append("Abnormal consumption pattern detected (possible panic buying)")

        if not factors:
            factors.append("Standard seasonal variation")

        return factors

    def _calculate_prediction_confidence(self, inventory: FoodInventory) -> float:
        """Calculate confidence score for shortage prediction."""
        confidence = 0.7  # Base confidence

        # Adjust based on data freshness
        if inventory.recorded_at:
            hours_old = (datetime.utcnow() - inventory.recorded_at).total_seconds() / 3600
            if hours_old < 24:
                confidence += 0.1
            elif hours_old > 72:
                confidence -= 0.1

        # Adjust based on consumption rate data
        if inventory.consumption_rate_tonnes_per_day:
            confidence += 0.1

        return min(0.95, max(0.3, confidence))

    def _generate_shortage_recommendations(
        self,
        days_of_supply: float,
        risk_factors: List[str]
    ) -> List[str]:
        """Generate recommended actions based on shortage prediction."""
        recommendations = []

        if days_of_supply < 7:
            recommendations.extend([
                "Activate emergency food reserves",
                "Request emergency food aid",
                "Implement rationing protocols",
                "Coordinate with military logistics"
            ])
        elif days_of_supply < 15:
            recommendations.extend([
                "Emergency procurement from alternative sources",
                "Begin ration distribution planning",
                "Communicate with public about conservation",
                "Prepare distribution centers"
            ])
        elif days_of_supply < 30:
            recommendations.extend([
                "Notify government food agencies",
                "Activate contingency sourcing agreements",
                "Review and optimize distribution routes",
                "Monitor consumption patterns closely"
            ])

        # Add factor-specific recommendations
        for factor in risk_factors:
            if "distribution disruption" in factor.lower():
                recommendations.append("Identify and activate alternative routes")
            if "panic buying" in factor.lower():
                recommendations.append("Implement purchase limits at retail")
            if "harvest" in factor.lower():
                recommendations.append("Coordinate with agricultural ministry")

        return list(dict.fromkeys(recommendations))  # Remove duplicates

    async def auto_generate_alerts(self) -> List[ShortageAlert]:
        """Automatically generate alerts based on shortage predictions."""
        predictions = await self.detect_shortages()
        new_alerts = []

        for prediction in predictions:
            # Check if alert already exists
            existing = await self.db.execute(
                select(ShortageAlert)
                .where(
                    and_(
                        ShortageAlert.region_id == prediction.region_id,
                        ShortageAlert.category_id == prediction.category_id,
                        ShortageAlert.is_active == True
                    )
                )
            )
            if existing.scalar_one_or_none():
                continue  # Alert already exists

            # Determine alert level
            if prediction.days_of_supply < settings.shortage_critical_days:
                level = AlertLevel.CRITICAL
            elif prediction.days_of_supply < settings.shortage_imminent_days:
                level = AlertLevel.IMMINENT
            else:
                level = AlertLevel.WARNING

            # Create alert
            alert_data = ShortageAlertCreate(
                region_id=prediction.region_id,
                category_id=prediction.category_id,
                alert_type=AlertType.SHORTAGE,
                alert_level=level,
                title=f"Food Shortage Alert: {prediction.category_name}",
                description=(
                    f"Predicted shortage in {prediction.region_name}. "
                    f"Current supply: {prediction.days_of_supply:.1f} days."
                ),
                predicted_shortage_date=prediction.predicted_shortage_date,
                days_until_shortage=int(prediction.days_of_supply),
                current_inventory_tonnes=prediction.current_inventory_tonnes,
                current_days_supply=prediction.days_of_supply,
                confidence_score=prediction.confidence_score,
                model_name="shortage_predictor_v1",
                recommended_actions=[
                    {"action": rec, "priority": i + 1}
                    for i, rec in enumerate(prediction.recommended_actions[:5])
                ]
            )

            alert = await self.create_alert(alert_data)
            new_alerts.append(alert)

        return new_alerts

    # ==================== Subscriptions ====================

    async def create_subscription(
        self,
        data: AlertSubscriptionCreate
    ) -> AlertSubscription:
        """Create an alert subscription."""
        subscription = AlertSubscription(**data.model_dump())
        subscription.verification_token = uuid.uuid4().hex
        self.db.add(subscription)
        await self.db.flush()
        await self.db.refresh(subscription)

        logger.info(
            f"Created subscription for {data.subscriber_name} "
            f"({data.subscriber_email})"
        )
        return subscription

    async def list_subscriptions(
        self,
        is_active: bool = True
    ) -> List[AlertSubscription]:
        """List active subscriptions."""
        result = await self.db.execute(
            select(AlertSubscription).where(
                AlertSubscription.is_active == is_active
            )
        )
        return list(result.scalars().all())

    async def _send_notifications(self, alert: ShortageAlert) -> None:
        """Send notifications for a new alert."""
        subscriptions = await self.list_subscriptions()

        for sub in subscriptions:
            # Check if subscription matches alert criteria
            if not self._subscription_matches_alert(sub, alert):
                continue

            # Queue notification (in production, use message queue)
            logger.info(
                f"Notification queued: {alert.alert_code} -> {sub.subscriber_email}"
            )

            # Update subscription stats
            sub.last_notification_at = datetime.utcnow()
            sub.notifications_sent = (sub.notifications_sent or 0) + 1

    async def _send_escalation_notifications(
        self,
        alert: ShortageAlert,
        escalate_to: List[str]
    ) -> None:
        """Send escalation notifications."""
        for contact in escalate_to:
            logger.warning(
                f"Escalation notification: {alert.alert_code} -> {contact}"
            )

    def _subscription_matches_alert(
        self,
        subscription: AlertSubscription,
        alert: ShortageAlert
    ) -> bool:
        """Check if subscription criteria match the alert."""
        # Check minimum level
        level_order = {
            AlertLevel.NORMAL: 0,
            AlertLevel.WARNING: 1,
            AlertLevel.IMMINENT: 2,
            AlertLevel.CRITICAL: 3
        }
        if level_order.get(alert.alert_level, 0) < level_order.get(
            subscription.minimum_alert_level, 0
        ):
            return False

        # Check region filter
        if subscription.region_ids and alert.region_id not in subscription.region_ids:
            return False

        # Check category filter
        if subscription.category_ids and alert.category_id not in subscription.category_ids:
            return False

        # Check alert type filter
        if subscription.alert_types:
            alert_type_values = [t.value if hasattr(t, 'value') else t for t in subscription.alert_types]
            if alert.alert_type.value not in alert_type_values:
                return False

        return True

    # ==================== Analytics ====================

    async def get_dashboard(self) -> AlertDashboard:
        """Get alert dashboard data."""
        # Active alerts by level
        level_counts = await self.db.execute(
            select(ShortageAlert.alert_level, func.count())
            .where(ShortageAlert.is_active == True)
            .group_by(ShortageAlert.alert_level)
        )
        by_level = {row[0].value: row[1] for row in level_counts.all()}

        # Active alerts by type
        type_counts = await self.db.execute(
            select(ShortageAlert.alert_type, func.count())
            .where(ShortageAlert.is_active == True)
            .group_by(ShortageAlert.alert_type)
        )
        by_type = {row[0].value: row[1] for row in type_counts.all()}

        # By region
        region_counts = await self.db.execute(
            select(ShortageAlert.region_id, func.count())
            .where(ShortageAlert.is_active == True)
            .group_by(ShortageAlert.region_id)
        )
        by_region = {str(row[0]): row[1] for row in region_counts.all()}

        # Total active
        total_active = sum(by_level.values())

        # Critical alerts
        critical, _ = await self.list_alerts(
            alert_level=AlertLevel.CRITICAL,
            is_active=True,
            limit=10
        )

        # Recent alerts (last 24 hours)
        recent_cutoff = datetime.utcnow() - timedelta(hours=24)
        recent_result = await self.db.execute(
            select(ShortageAlert)
            .where(ShortageAlert.created_at >= recent_cutoff)
            .order_by(ShortageAlert.created_at.desc())
            .limit(10)
        )
        recent = recent_result.scalars().all()

        # 7-day trend
        trend_data = {}
        for i in range(7):
            date = datetime.utcnow().date() - timedelta(days=i)
            start = datetime.combine(date, datetime.min.time())
            end = datetime.combine(date, datetime.max.time())

            count_result = await self.db.execute(
                select(func.count())
                .select_from(ShortageAlert)
                .where(
                    and_(
                        ShortageAlert.created_at >= start,
                        ShortageAlert.created_at <= end
                    )
                )
            )
            trend_data[date.isoformat()] = count_result.scalar() or 0

        # Build alert summaries
        def to_summary(alert: ShortageAlert) -> AlertSummary:
            return AlertSummary(
                id=alert.id,
                alert_code=alert.alert_code,
                region_id=alert.region_id,
                region_name=f"Region {alert.region_id}",
                alert_type=alert.alert_type,
                alert_level=alert.alert_level,
                status=alert.status,
                title=alert.title,
                days_until_shortage=alert.days_until_shortage,
                created_at=alert.created_at
            )

        return AlertDashboard(
            total_active_alerts=total_active,
            alerts_by_level=by_level,
            alerts_by_type=by_type,
            alerts_by_region=by_region,
            critical_alerts=[to_summary(a) for a in critical],
            recent_alerts=[to_summary(a) for a in recent],
            trend_7_days=trend_data
        )

    async def get_risk_assessment(self, region_id: int) -> ShortageRiskAssessment:
        """Get comprehensive shortage risk assessment for a region."""
        predictions = await self._analyze_region_shortages(region_id)

        # Categorize by risk level
        categories_at_risk = []
        for pred in predictions:
            risk_level = "critical" if pred.days_of_supply < 7 else \
                         "high" if pred.days_of_supply < 15 else \
                         "medium" if pred.days_of_supply < 30 else "low"

            categories_at_risk.append({
                "category_id": pred.category_id,
                "category_name": pred.category_name,
                "days_of_supply": pred.days_of_supply,
                "risk_level": risk_level
            })

        # Aggregate contributing factors
        all_factors = []
        for pred in predictions:
            all_factors.extend(pred.risk_factors)

        # Count factor occurrences
        factor_counts = {}
        for factor in all_factors:
            factor_counts[factor] = factor_counts.get(factor, 0) + 1

        contributing_factors = [
            {"factor": factor, "frequency": count}
            for factor, count in sorted(
                factor_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )
        ]

        # Calculate overall risk
        if any(p.days_of_supply < 7 for p in predictions):
            overall_risk = 0.9
        elif any(p.days_of_supply < 15 for p in predictions):
            overall_risk = 0.7
        elif any(p.days_of_supply < 30 for p in predictions):
            overall_risk = 0.5
        elif predictions:
            overall_risk = 0.3
        else:
            overall_risk = 0.1

        # Generate recommendations
        all_recommendations = []
        for pred in predictions:
            all_recommendations.extend(pred.recommended_actions)

        # Deduplicate and prioritize
        unique_recommendations = list(dict.fromkeys(all_recommendations))

        mitigation_recommendations = [
            {"action": rec, "priority": i + 1}
            for i, rec in enumerate(unique_recommendations[:10])
        ]

        return ShortageRiskAssessment(
            region_id=region_id,
            assessment_date=datetime.utcnow(),
            overall_risk=overall_risk,
            categories_at_risk=categories_at_risk,
            contributing_factors=contributing_factors,
            mitigation_recommendations=mitigation_recommendations,
            monitoring_indicators=[
                "Daily inventory levels",
                "Consumption rate changes",
                "Distribution disruption status",
                "Harvest forecast updates"
            ]
        )
