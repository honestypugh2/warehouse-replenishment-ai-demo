-- 01_min_max_candidates.sql
-- Databricks SQL Warehouse pattern that produces the daily min-max candidates.
-- Databricks is the system of intelligence: this query owns the candidate logic.
-- The FastAPI Databricks client (app/services/databricks_client.py) reads the
-- result of a query shaped like this. In MOCK_MODE the same shape is served from
-- data/candidates.json.

-- Inputs (Unity Catalog tables, illustrative names):
--   main.replen.shipments_daily      -- historical shipments per SKU/facility
--   main.replen.inventory_snapshot   -- on-hand by location
--   main.replen.location_capacity    -- slot capacity / class
--   main.replen.stocking_limits      -- current min/max (mirrored from D365)

WITH velocity AS (
  SELECT
    sku,
    facility,
    AVG(units_shipped)                               AS avg_daily_velocity,
    STDDEV(units_shipped)                            AS stddev_velocity,
    -- 14-day trailing growth vs. prior 14 days
    (SUM(CASE WHEN ship_date >= DATEADD(DAY, -14, CURRENT_DATE) THEN units_shipped END)
     - SUM(CASE WHEN ship_date >= DATEADD(DAY, -28, CURRENT_DATE)
                 AND ship_date <  DATEADD(DAY, -14, CURRENT_DATE) THEN units_shipped END))
      / NULLIF(SUM(CASE WHEN ship_date >= DATEADD(DAY, -28, CURRENT_DATE)
                 AND ship_date <  DATEADD(DAY, -14, CURRENT_DATE) THEN units_shipped END), 0)
                                                      AS velocity_growth_14d
  FROM main.replen.shipments_daily
  WHERE ship_date >= DATEADD(DAY, -28, CURRENT_DATE)
  GROUP BY sku, facility
),

current_limits AS (
  SELECT sku, facility, location, current_min, current_max
  FROM main.replen.stocking_limits
)

SELECT
  v.sku,
  v.facility,
  cl.location,
  cl.current_min,
  cl.current_max,
  -- Recommended min: ~3 days of demand plus a safety buffer.
  CAST(CEIL(v.avg_daily_velocity * 3 + 1.5 * v.stddev_velocity) AS INT)  AS recommended_min,
  -- Recommended max: bounded by slot capacity.
  LEAST(
    CAST(CEIL(v.avg_daily_velocity * 9 + 2.0 * v.stddev_velocity) AS INT),
    cap.max_units
  )                                                                       AS recommended_max,
  CONCAT('Velocity growth ', ROUND(v.velocity_growth_14d * 100, 0), '% (14d).') AS rationale,
  -- Confidence inversely related to volatility.
  ROUND(GREATEST(0.5, LEAST(0.95, 1 - (v.stddev_velocity / NULLIF(v.avg_daily_velocity, 0)))), 2)
                                                                          AS confidence
FROM velocity v
JOIN current_limits cl
  ON cl.sku = v.sku AND cl.facility = v.facility
JOIN main.replen.location_capacity cap
  ON cap.location = cl.location
ORDER BY v.facility, v.sku;
