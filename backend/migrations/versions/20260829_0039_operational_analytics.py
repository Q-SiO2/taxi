"""Add privacy-bounded operational analytics projections.

Revision ID: 20260829_0039
Revises: 20260829_0038
Create Date: 2026-08-29
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260829_0039"
down_revision = "20260829_0038"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "operational_supply_snapshots_hourly",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "city_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "operator_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("operators.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("service_type", sa.String(length=20), nullable=False),
        sa.Column("zone_code", sa.String(length=32), nullable=False),
        sa.Column("bucket_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("available_driver_count", sa.Integer(), nullable=False),
        sa.Column("eligible_driver_count", sa.Integer(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("retention_until", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "service_type IN ('ON_DEMAND', 'FIXED_ROUTE')",
            name="operational_supply_service_type",
        ),
        sa.CheckConstraint(
            "zone_code = 'CITY_WIDE'",
            name="operational_supply_coarse_zone",
        ),
        sa.CheckConstraint(
            "available_driver_count >= 0 AND eligible_driver_count >= available_driver_count",
            name="operational_supply_counts_valid",
        ),
        sa.CheckConstraint(
            "retention_until > bucket_start",
            name="operational_supply_retention_after_bucket",
        ),
        sa.UniqueConstraint(
            "city_id",
            "operator_id",
            "service_type",
            "zone_code",
            "bucket_start",
            name="operational_supply_bucket_scope",
        ),
    )
    op.create_index(
        "ix_operational_supply_city_bucket",
        "operational_supply_snapshots_hourly",
        ["city_id", "bucket_start"],
    )

    # This view is the allowlist. It deliberately contains no account IDs,
    # coordinates, notes, documents, contact data, provider references, or
    # arbitrary JSON. Internal event keys support reconciliation only and are
    # never selected by the analyst API.
    op.execute(
        sa.schema.DDL(
        """
        CREATE VIEW operational_domain_events_v1 AS
        SELECT
          'ride_event:' || re.id::text AS event_key,
          CASE
            WHEN re.event_type::text = 'CREATED' THEN 'RIDE_REQUESTED'
            WHEN re.new_status::text = 'ACCEPTED' THEN 'RIDE_ACCEPTED'
            WHEN re.new_status::text = 'DRIVER_EN_ROUTE' THEN 'DRIVER_EN_ROUTE'
            WHEN re.new_status::text = 'DRIVER_ARRIVED' THEN 'DRIVER_ARRIVED'
            WHEN re.new_status::text = 'IN_PROGRESS' THEN 'RIDE_STARTED'
            WHEN re.new_status::text = 'COMPLETED' THEN 'RIDE_COMPLETED'
            WHEN re.new_status::text = 'CANCELLED' THEN 'RIDE_CANCELLED'
            WHEN re.new_status::text = 'UNMATCHED' THEN 'RIDE_UNMATCHED'
          END::varchar(48) AS event_type,
          re.created_at AS occurred_at,
          re.created_at AS recorded_at,
          r.city_id,
          r.operator_id,
          r.service_type::text::varchar(20) AS service_type,
          COALESCE(fs.booking_type::text, CASE WHEN r.scheduled_booking_id IS NULL THEN 'IMMEDIATE' ELSE 'SCHEDULED' END)::varchar(16) AS booking_type,
          r.fixed_route_direction_id,
          fs.pricing_rule_id,
          fs.operator_fee_policy_id,
          fs.scheduling_policy_id,
          NULL::varchar(32) AS matching_algorithm_version,
          re.new_status::text::varchar(48) AS outcome_code,
          NULL::varchar(3) AS currency,
          NULL::numeric(14,2) AS amount,
          CASE
            WHEN re.new_status::text = 'ACCEPTED' THEN EXTRACT(EPOCH FROM (r.accepted_at - r.created_at))::bigint
            WHEN re.new_status::text = 'DRIVER_ARRIVED' THEN EXTRACT(EPOCH FROM (r.arrived_at - r.accepted_at))::bigint
            WHEN re.new_status::text = 'COMPLETED' THEN EXTRACT(EPOCH FROM (r.completed_at - r.started_at))::bigint
          END AS duration_seconds,
          NULL::bigint AS distance_meters,
          NULL::varchar(64) AS category_code
        FROM ride_events re
        JOIN rides r ON r.id = re.ride_id
        LEFT JOIN ride_financial_snapshots fs ON fs.ride_id = r.id
        WHERE re.event_type::text IN ('CREATED', 'STATUS_CHANGED', 'CANCELLED', 'MATCHING_FAILED')
          AND (
            re.event_type::text = 'CREATED'
            OR re.new_status::text IN ('ACCEPTED', 'DRIVER_EN_ROUTE', 'DRIVER_ARRIVED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED', 'UNMATCHED')
          )

        UNION ALL

        SELECT
          'ride_offer:' || ro.id::text || ':created',
          'RIDE_OFFERED'::varchar(48), ro.created_at, ro.created_at,
          r.city_id, r.operator_id, r.service_type::text::varchar(20),
          COALESCE(fs.booking_type::text, 'IMMEDIATE')::varchar(16),
          r.fixed_route_direction_id, fs.pricing_rule_id, fs.operator_fee_policy_id,
          fs.scheduling_policy_id, ro.matching_algorithm_version,
          'PENDING'::varchar(48), NULL::varchar(3), NULL::numeric(14,2),
          ro.estimated_pickup_time_seconds::bigint,
          ro.estimated_pickup_distance_meters::bigint, NULL::varchar(64)
        FROM ride_offers ro
        JOIN rides r ON r.id = ro.ride_id
        LEFT JOIN ride_financial_snapshots fs ON fs.ride_id = r.id

        UNION ALL

        SELECT
          'ride_offer:' || ro.id::text || ':response',
          ('RIDE_OFFER_' || ro.status::text)::varchar(48), ro.responded_at, ro.responded_at,
          r.city_id, r.operator_id, r.service_type::text::varchar(20),
          COALESCE(fs.booking_type::text, 'IMMEDIATE')::varchar(16),
          r.fixed_route_direction_id, fs.pricing_rule_id, fs.operator_fee_policy_id,
          fs.scheduling_policy_id, ro.matching_algorithm_version,
          ro.status::text::varchar(48), NULL::varchar(3), NULL::numeric(14,2),
          EXTRACT(EPOCH FROM (ro.responded_at - ro.created_at))::bigint,
          ro.estimated_pickup_distance_meters::bigint, NULL::varchar(64)
        FROM ride_offers ro
        JOIN rides r ON r.id = ro.ride_id
        LEFT JOIN ride_financial_snapshots fs ON fs.ride_id = r.id
        WHERE ro.responded_at IS NOT NULL AND ro.status::text <> 'PENDING'

        UNION ALL

        SELECT
          'scheduled_event:' || se.id::text,
          ('SCHEDULED_' || se.event_type::text)::varchar(48), se.created_at, se.created_at,
          sb.city_id, sb.operator_id, sb.service_type::text::varchar(20),
          'SCHEDULED'::varchar(16), sb.fixed_route_direction_id,
          sb.pricing_rule_id, sb.operator_fee_policy_id, sb.scheduling_policy_id,
          NULL::varchar(32), se.new_status::text::varchar(48),
          sb.currency::varchar(3),
          CASE WHEN se.event_type::text = 'CREATED' THEN sb.passenger_total_amount ELSE NULL END,
          CASE
            WHEN se.event_type::text = 'CREATED' THEN EXTRACT(EPOCH FROM (sb.scheduled_for - sb.created_at))::bigint
            WHEN se.event_type::text = 'DRIVER_COMMITTED' THEN EXTRACT(EPOCH FROM (sb.committed_at - sb.created_at))::bigint
            WHEN se.event_type::text = 'LIVE_RIDE_CREATED' THEN EXTRACT(EPOCH FROM (sb.live_ride_created_at - sb.scheduled_for))::bigint
          END,
          NULL::bigint, NULL::varchar(64)
        FROM scheduled_booking_events se
        JOIN scheduled_bookings sb ON sb.id = se.booking_id

        UNION ALL

        SELECT
          'driver_application:' || a.id::text || ':created',
          'DRIVER_APPLICATION_CREATED'::varchar(48), a.created_at, a.created_at,
          a.city_id, NULL::uuid, NULL::varchar(20), NULL::varchar(16), NULL::uuid,
          NULL::uuid, NULL::uuid, NULL::uuid, NULL::varchar(32),
          'NOT_STARTED'::varchar(48), NULL::varchar(3), NULL::numeric(14,2),
          NULL::bigint, NULL::bigint, NULL::varchar(64)
        FROM driver_city_applications a

        UNION ALL

        SELECT
          'driver_application:' || a.id::text || ':submitted',
          'DRIVER_APPLICATION_SUBMITTED'::varchar(48), a.submitted_at, a.updated_at,
          a.city_id, NULL::uuid, NULL::varchar(20), NULL::varchar(16), NULL::uuid,
          NULL::uuid, NULL::uuid, NULL::uuid, NULL::varchar(32),
          'SUBMITTED'::varchar(48), NULL::varchar(3), NULL::numeric(14,2),
          NULL::bigint, NULL::bigint, NULL::varchar(64)
        FROM driver_city_applications a WHERE a.submitted_at IS NOT NULL

        UNION ALL

        SELECT
          'driver_application_decision:' || d.id::text,
          'DRIVER_APPLICATION_DECIDED'::varchar(48), d.created_at, d.created_at,
          a.city_id, NULL::uuid, NULL::varchar(20), NULL::varchar(16), NULL::uuid,
          NULL::uuid, NULL::uuid, NULL::uuid, NULL::varchar(32),
          d.decision::text::varchar(48), NULL::varchar(3), NULL::numeric(14,2),
          EXTRACT(EPOCH FROM (d.created_at - a.submitted_at))::bigint,
          NULL::bigint, NULL::varchar(64)
        FROM driver_application_decisions d
        JOIN driver_city_applications a ON a.id = d.application_id

        UNION ALL

        SELECT
          'payment:' || p.id::text || ':completed',
          'PAYMENT_COMPLETED'::varchar(48), p.completed_at, p.completed_at,
          r.city_id, r.operator_id, r.service_type::text::varchar(20),
          COALESCE(fs.booking_type::text, 'IMMEDIATE')::varchar(16),
          r.fixed_route_direction_id, fs.pricing_rule_id, fs.operator_fee_policy_id,
          fs.scheduling_policy_id, NULL::varchar(32), p.method::text::varchar(48),
          p.currency::varchar(3), p.amount::numeric(14,2),
          EXTRACT(EPOCH FROM (p.completed_at - p.created_at))::bigint,
          NULL::bigint, p.method::text::varchar(64)
        FROM payments p
        JOIN rides r ON r.id = p.ride_id
        LEFT JOIN ride_financial_snapshots fs ON fs.ride_id = r.id
        WHERE p.completed_at IS NOT NULL

        UNION ALL

        SELECT
          'payment_refund:' || pr.id::text,
          'PAYMENT_REFUNDED'::varchar(48), pr.refunded_at, pr.refunded_at,
          r.city_id, r.operator_id, r.service_type::text::varchar(20),
          COALESCE(fs.booking_type::text, 'IMMEDIATE')::varchar(16),
          r.fixed_route_direction_id, fs.pricing_rule_id, fs.operator_fee_policy_id,
          fs.scheduling_policy_id, NULL::varchar(32), pr.reason::text::varchar(48),
          pr.currency::varchar(3), pr.amount::numeric(14,2), NULL::bigint,
          NULL::bigint, pr.reason::text::varchar(64)
        FROM payment_refunds pr
        JOIN payments p ON p.id = pr.payment_id
        JOIN rides r ON r.id = p.ride_id
        LEFT JOIN ride_financial_snapshots fs ON fs.ride_id = r.id

        UNION ALL

        SELECT
          'support_ticket:' || st.id::text,
          'SUPPORT_TICKET_CREATED'::varchar(48), st.created_at, st.created_at,
          r.city_id, r.operator_id, r.service_type::text::varchar(20),
          COALESCE(fs.booking_type::text, 'IMMEDIATE')::varchar(16),
          r.fixed_route_direction_id, fs.pricing_rule_id, fs.operator_fee_policy_id,
          fs.scheduling_policy_id, NULL::varchar(32), st.priority::text::varchar(48),
          NULL::varchar(3), NULL::numeric(14,2), NULL::bigint, NULL::bigint,
          st.category::text::varchar(64)
        FROM support_tickets st
        JOIN rides r ON r.id = st.ride_id
        LEFT JOIN ride_financial_snapshots fs ON fs.ride_id = r.id
        WHERE st.ride_id IS NOT NULL

        UNION ALL

        SELECT
          'safety_report:' || sr.id::text,
          'SAFETY_REPORT_CREATED'::varchar(48), sr.created_at, sr.created_at,
          r.city_id, r.operator_id, r.service_type::text::varchar(20),
          COALESCE(fs.booking_type::text, 'IMMEDIATE')::varchar(16),
          r.fixed_route_direction_id, fs.pricing_rule_id, fs.operator_fee_policy_id,
          fs.scheduling_policy_id, NULL::varchar(32), sr.priority::text::varchar(48),
          NULL::varchar(3), NULL::numeric(14,2), NULL::bigint, NULL::bigint,
          sr.category::text::varchar(64)
        FROM safety_reports sr
        JOIN rides r ON r.id = sr.ride_id
        LEFT JOIN ride_financial_snapshots fs ON fs.ride_id = r.id
        """
        )
    )

    op.execute(
        sa.schema.DDL(
        """
        CREATE MATERIALIZED VIEW operational_metric_facts_hourly_v1 AS
        WITH driver_work_counts AS (
          SELECT
            date_trunc('hour', r.accepted_at) AS bucket_start,
            r.city_id,
            r.operator_id,
            r.service_type::text::varchar(20) AS service_type,
            COALESCE(fs.booking_type::text, 'IMMEDIATE')::varchar(16) AS booking_type,
            r.fixed_route_direction_id,
            fs.pricing_rule_id,
            fs.operator_fee_policy_id,
            fs.scheduling_policy_id,
            r.driver_id,
            count(*)::bigint AS assignment_count,
            max(r.updated_at) AS source_watermark
          FROM rides r
          LEFT JOIN ride_financial_snapshots fs ON fs.ride_id = r.id
          WHERE r.driver_id IS NOT NULL
            AND r.accepted_at IS NOT NULL
            AND r.accepted_at >= now() - interval '730 days'
          GROUP BY
            date_trunc('hour', r.accepted_at), r.city_id, r.operator_id,
            r.service_type, fs.booking_type, r.fixed_route_direction_id,
            fs.pricing_rule_id, fs.operator_fee_policy_id,
            fs.scheduling_policy_id, r.driver_id
        ),
        driver_work_ranked AS (
          SELECT
            dw.*,
            row_number() OVER (
              PARTITION BY bucket_start, city_id, operator_id, service_type,
                booking_type, fixed_route_direction_id, pricing_rule_id,
                operator_fee_policy_id, scheduling_policy_id
              ORDER BY assignment_count, driver_id
            )::bigint AS assignment_rank,
            count(*) OVER (
              PARTITION BY bucket_start, city_id, operator_id, service_type,
                booking_type, fixed_route_direction_id, pricing_rule_id,
                operator_fee_policy_id, scheduling_policy_id
            )::bigint AS driver_count,
            sum(assignment_count) OVER (
              PARTITION BY bucket_start, city_id, operator_id, service_type,
                booking_type, fixed_route_direction_id, pricing_rule_id,
                operator_fee_policy_id, scheduling_policy_id
            )::bigint AS total_assignments
          FROM driver_work_counts dw
        )
        SELECT
          date_trunc('hour', occurred_at) AS bucket_start,
          city_id,
          operator_id,
          service_type,
          booking_type,
          fixed_route_direction_id,
          pricing_rule_id,
          operator_fee_policy_id,
          scheduling_policy_id,
          matching_algorithm_version,
          event_type AS metric_code,
          outcome_code,
          category_code,
          currency,
          count(*)::bigint AS sample_count,
          count(*)::bigint AS integer_value,
          sum(duration_seconds)::bigint AS duration_seconds_sum,
          sum(distance_meters)::bigint AS distance_meters_sum,
          sum(amount)::numeric(16,2) AS amount_sum,
          NULL::numeric(20,6) AS numeric_value_sum,
          NULL::bigint AS minimum_per_entity,
          NULL::bigint AS maximum_per_entity,
          NULL::numeric(12,6) AS distribution_gini,
          max(recorded_at) AS source_watermark,
          now() AS computed_at
        FROM operational_domain_events_v1
        WHERE occurred_at >= now() - interval '730 days'
          AND event_type IS NOT NULL
        GROUP BY
          date_trunc('hour', occurred_at), city_id, operator_id, service_type,
          booking_type, fixed_route_direction_id, pricing_rule_id,
          operator_fee_policy_id, scheduling_policy_id,
          matching_algorithm_version, event_type, outcome_code, category_code, currency

        UNION ALL

        SELECT
          date_trunc('hour', ro.created_at), r.city_id, r.operator_id,
          r.service_type::text::varchar(20),
          COALESCE(fs.booking_type::text, 'IMMEDIATE')::varchar(16),
          r.fixed_route_direction_id, fs.pricing_rule_id,
          fs.operator_fee_policy_id, fs.scheduling_policy_id,
          ro.matching_algorithm_version,
          'MATCHING_FAIRNESS_SCORE'::varchar(48), NULL::varchar(48),
          NULL::varchar(64), NULL::varchar(3),
          count(*)::bigint, count(*)::bigint,
          NULL::bigint, NULL::bigint, NULL::numeric(16,2),
          sum(ro.fairness_score)::numeric(20,6),
          NULL::bigint, NULL::bigint, NULL::numeric(12,6),
          max(ro.created_at), now()
        FROM ride_offers ro
        JOIN rides r ON r.id = ro.ride_id
        LEFT JOIN ride_financial_snapshots fs ON fs.ride_id = r.id
        WHERE ro.fairness_score IS NOT NULL
          AND ro.created_at >= now() - interval '730 days'
        GROUP BY
          date_trunc('hour', ro.created_at), r.city_id, r.operator_id,
          r.service_type, fs.booking_type, r.fixed_route_direction_id,
          fs.pricing_rule_id, fs.operator_fee_policy_id,
          fs.scheduling_policy_id, ro.matching_algorithm_version

        UNION ALL

        SELECT
          date_trunc('hour', p.completed_at), r.city_id, r.operator_id,
          r.service_type::text::varchar(20),
          COALESCE(fs.booking_type::text, 'IMMEDIATE')::varchar(16),
          r.fixed_route_direction_id, fs.pricing_rule_id,
          fs.operator_fee_policy_id, fs.scheduling_policy_id,
          NULL::varchar(32), component.metric_code::varchar(48),
          'SETTLED'::varchar(48), p.method::text::varchar(64),
          p.currency::varchar(3), count(*)::bigint, count(*)::bigint,
          NULL::bigint, NULL::bigint,
          sum(component.amount)::numeric(16,2),
          NULL::numeric(20,6), NULL::bigint, NULL::bigint,
          NULL::numeric(12,6), max(p.completed_at), now()
        FROM driver_earnings de
        JOIN payments p ON p.id = de.payment_id
        JOIN rides r ON r.id = de.ride_id
        LEFT JOIN ride_financial_snapshots fs ON fs.ride_id = r.id
        CROSS JOIN LATERAL (
          VALUES
            ('FINANCIAL_PASSENGER_TOTAL', p.amount),
            ('FINANCIAL_TRANSPORT_FARE', de.transport_fare_amount),
            ('FINANCIAL_SCHEDULING_SURCHARGE', de.scheduling_surcharge_amount),
            ('FINANCIAL_OPERATOR_FEE', de.operator_fee_amount),
            ('FINANCIAL_OPERATOR_ALLOCATION', de.operator_allocation_amount),
            ('FINANCIAL_DRIVER_NET', de.net_amount)
        ) AS component(metric_code, amount)
        WHERE p.completed_at IS NOT NULL
          AND p.completed_at >= now() - interval '730 days'
        GROUP BY
          date_trunc('hour', p.completed_at), r.city_id, r.operator_id,
          r.service_type, fs.booking_type, r.fixed_route_direction_id,
          fs.pricing_rule_id, fs.operator_fee_policy_id,
          fs.scheduling_policy_id, component.metric_code, p.method, p.currency

        UNION ALL

        SELECT
          bucket_start, city_id, operator_id, service_type, booking_type,
          fixed_route_direction_id, pricing_rule_id, operator_fee_policy_id,
          scheduling_policy_id, NULL::varchar(32),
          'DRIVER_WORK_DISTRIBUTION'::varchar(48),
          'ASSIGNED'::varchar(48), NULL::varchar(64), NULL::varchar(3),
          max(driver_count)::bigint, max(total_assignments)::bigint,
          NULL::bigint, NULL::bigint, NULL::numeric(16,2),
          max(total_assignments)::numeric(20,6),
          min(assignment_count)::bigint, max(assignment_count)::bigint,
          CASE
            WHEN max(total_assignments) = 0 THEN 0::numeric(12,6)
            ELSE (
              sum((2 * assignment_rank - driver_count - 1) * assignment_count)::numeric
              / (max(driver_count) * max(total_assignments))::numeric
            )::numeric(12,6)
          END,
          max(source_watermark), now()
        FROM driver_work_ranked
        GROUP BY
          bucket_start, city_id, operator_id, service_type, booking_type,
          fixed_route_direction_id, pricing_rule_id, operator_fee_policy_id,
          scheduling_policy_id

        UNION ALL

        SELECT
          bucket_start, city_id, operator_id, service_type,
          NULL::varchar(16), NULL::uuid, NULL::uuid, NULL::uuid, NULL::uuid,
          NULL::varchar(32), supply.metric_code::varchar(48),
          zone_code::varchar(48), zone_code::varchar(64), NULL::varchar(3),
          supply.driver_count::bigint, supply.driver_count::bigint,
          NULL::bigint, NULL::bigint, NULL::numeric(16,2),
          NULL::numeric(20,6), NULL::bigint, NULL::bigint,
          NULL::numeric(12,6), observed_at, now()
        FROM operational_supply_snapshots_hourly
        CROSS JOIN LATERAL (
          VALUES
            ('SUPPLY_AVAILABLE', available_driver_count),
            ('SUPPLY_ELIGIBLE', eligible_driver_count)
        ) AS supply(metric_code, driver_count)
        WHERE retention_until > now()
        """
        )
    )
    op.execute(
        "CREATE INDEX ix_operational_metric_facts_city_bucket "
        "ON operational_metric_facts_hourly_v1 (city_id, bucket_start)"
    )
    op.execute(
        "CREATE INDEX ix_operational_metric_facts_metric_bucket "
        "ON operational_metric_facts_hourly_v1 (metric_code, bucket_start)"
    )


def downgrade() -> None:
    op.execute("DROP MATERIALIZED VIEW IF EXISTS operational_metric_facts_hourly_v1")
    op.execute("DROP VIEW IF EXISTS operational_domain_events_v1")
    op.drop_index("ix_operational_supply_city_bucket", table_name="operational_supply_snapshots_hourly")
    op.drop_table("operational_supply_snapshots_hourly")
