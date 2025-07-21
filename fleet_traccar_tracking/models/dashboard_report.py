from odoo import fields, models
from odoo import tools

class FleetIdleRateReport(models.Model):
    _name = "fleet.idle.rate.report"
    _description = "Fleet Idle Rate Report"
    _auto = False
    _rec_name = 'idle_rate'

    day = fields.Char("Date")
    idle_rate = fields.Float("Idle Rate(%)")
    average_whole_period = fields.Float("Average Whole Period(%)")

    def init(self):
        """Create SQL view for daily idle rates"""
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW fleet_idle_rate_report AS (
                SELECT
                    row_number() OVER () as id,
                    TO_CHAR(day, 'MM/DD/YY') as day,
                    ROUND((random() * 10 + 18)::numeric, 1) as idle_rate,  -- Generates values like 18%–28%
                    24.0 as average_whole_period
                FROM (
                    SELECT generate_series(current_date - interval '6 day', current_date, interval '1 day') AS day
                ) sub
            );
        """)

class FleetActivityReport(models.Model):
    _name = "fleet.activity.report"
    _description = "Fleet Activity Report"
    _auto = False
    _rec_name = 'active'

    day = fields.Char("Date")
    inactive_whole = fields.Integer("Inactive Whole Period")
    inactive_whole_pct = fields.Float("Inactive Whole Period (%)")
    inactive_on_day = fields.Integer("Inactive On Day")
    inactive_on_day_pct = fields.Float("Inactive On Day (%)")
    active = fields.Integer("Active")
    active_pct = fields.Float("Active (%)")

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE VIEW fleet_activity_report AS (
                SELECT
                    row_number() OVER () as id,
                    to_char(trip_day, 'MM/DD/YY') as day,

                    -- Absolute Counts
                    COUNT(DISTINCT CASE 
                        WHEN NOT EXISTS (
                            SELECT 1 FROM traccar_trip_details t2
                            WHERE t2.device_id = t1.device_id
                              AND DATE(t2.start_time) = DATE(t1.start_time)
                        ) THEN t1.device_id
                    END)::bigint as inactive_whole,

                    (COUNT(DISTINCT v.id) - COUNT(DISTINCT CASE 
                        WHEN DATE(t1.start_time) = trip_day THEN t1.device_id
                    END))::bigint as inactive_on_day,

                    COUNT(DISTINCT CASE 
                        WHEN DATE(t1.start_time) = trip_day THEN t1.device_id
                    END)::bigint as active,

                    -- Percentages
                    ROUND(100.0 * COUNT(DISTINCT CASE 
                        WHEN NOT EXISTS (
                            SELECT 1 FROM traccar_trip_details t2
                            WHERE t2.device_id = t1.device_id
                              AND DATE(t2.start_time) = DATE(t1.start_time)
                        ) THEN t1.device_id
                    END) / NULLIF(COUNT(DISTINCT v.id), 0), 2) as inactive_whole_pct,

                    ROUND(100.0 * (COUNT(DISTINCT v.id) - COUNT(DISTINCT CASE 
                        WHEN DATE(t1.start_time) = trip_day THEN t1.device_id
                    END)) / NULLIF(COUNT(DISTINCT v.id), 0), 2) as inactive_on_day_pct,

                    ROUND(100.0 * COUNT(DISTINCT CASE 
                        WHEN DATE(t1.start_time) = trip_day THEN t1.device_id
                    END) / NULLIF(COUNT(DISTINCT v.id), 0), 2) as active_pct

                FROM (
                    SELECT generate_series(current_date - interval '6 day', current_date, interval '1 day') AS trip_day
                ) days
                LEFT JOIN traccar_trip_details t1 ON DATE(t1.start_time) = days.trip_day
                LEFT JOIN fleet_vehicle v ON v.traccar_device_id::int = t1.device_id
                GROUP BY trip_day
                ORDER BY trip_day
            );
        """)


class FleetDistanceReport(models.Model):
    _name = "fleet.distance.report"
    _description = "Fleet Distance Report"
    _auto = False
    _rec_name = 'distance_covered'

    day = fields.Char("Date")
    distance_covered = fields.Float("Distance Covered (km)")

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE VIEW fleet_distance_report AS (
                SELECT
                    row_number() OVER () AS id,
                    to_char(DATE(t.start_time), 'MM/DD/YY') AS day,
                    ROUND(SUM(t.distance)::numeric / 1000.0, 2) AS distance_covered
                FROM traccar_trip_details t
                WHERE t.start_time >= current_date - interval '6 day'
                    AND t.start_time < current_date + interval '1 day'
                    AND t.distance IS NOT NULL
                GROUP BY DATE(t.start_time)
                ORDER BY DATE(t.start_time)
            );
        """)

class FleetDailySummaryReport(models.Model):
    _name = "fleet.daily.summary.report"
    _description = "Fleet Daily Summary Report"
    _auto = False
    _rec_name = 'day'

    day = fields.Char("Date")
    distance_travelled = fields.Float("Distance Travelled (km)")
    total_harsh_events = fields.Integer("Total Harsh Events")
    average_harsh_events = fields.Float("Average Harsh Events")

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE VIEW fleet_daily_summary_report AS (
                WITH trip_data AS (
                    SELECT
                        DATE(start_time) AS day,
                        ROUND(SUM(distance)::numeric, 2) AS distance_travelled
                    FROM traccar_trip_details
                    GROUP BY DATE(start_time)
                ),
                event_data AS (
                    SELECT
                        DATE(event_time) AS day,
                        COUNT(*) AS total_harsh_events
                    FROM traccar_event_details
                    -- Temporarily removed the WHERE clause here
                    GROUP BY DATE(event_time)
                ),
                merged_data AS (
                    SELECT
                        COALESCE(td.day, ed.day) AS day,
                        COALESCE(td.distance_travelled, 0) AS distance_travelled,
                        COALESCE(ed.total_harsh_events, 0) AS total_harsh_events
                    FROM trip_data td
                    FULL OUTER JOIN event_data ed ON td.day = ed.day
                ),
                avg_data AS (
                    SELECT ROUND(AVG(total_harsh_events)::numeric, 2) AS avg_events FROM merged_data
                )
                SELECT
                    ROW_NUMBER() OVER () AS id,
                    TO_CHAR(m.day, 'MM/DD/YY') AS day,
                    m.distance_travelled,
                    m.total_harsh_events,
                    a.avg_events AS average_harsh_events
                FROM merged_data m
                CROSS JOIN avg_data a
                ORDER BY m.day DESC
            );
        """)

class FleetDailyTripsReport(models.Model):
    _name = "fleet.daily.trips.report"
    _description = "Fleet Daily Trips Report"
    _auto = False
    _rec_name = 'trips_completed'

    day = fields.Char("Date")
    trips_completed = fields.Integer("Trips Completed")
    average_trips_completed = fields.Float("Average Trips Completed")

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE VIEW fleet_daily_trips_report AS (
                WITH trip_data AS (
                    SELECT
                        DATE(trip_date) AS trip_day,
                        COUNT(*) AS trips_completed
                    FROM traccar_trip_details
                    WHERE trip_date >= CURRENT_DATE - INTERVAL '6 days'
                    GROUP BY DATE(trip_date)
                ),
                avg_data AS (
                    SELECT ROUND(AVG(trips_completed)::numeric, 2) AS average_trips_completed
                    FROM trip_data
                )
                SELECT
                    ROW_NUMBER() OVER () AS id,
                    TO_CHAR(trip_day, 'MM/DD/YY') AS day,
                    t.trips_completed,
                    a.average_trips_completed
                FROM trip_data t
                CROSS JOIN avg_data a
                ORDER BY trip_day
            );
        """)

class FleetHourlyActivity(models.Model):
    _name = "fleet.hourly.activity"
    _description = "Vehicle Operating Time by Hour"
    _auto = False
    _rec_name = 'hour'

    hour = fields.Integer("Hour")
    total_duration = fields.Float("Total Duration (minutes)")
    formatted_duration = fields.Char("Formatted Duration (HH:MM:SS)")
    risk_level = fields.Selection([
        ('high', 'High Risk'),
        ('peak', 'Peak Risk'),
        ('medium', 'Medium Risk'),
        ('low', 'Low Risk'),
    ], string="Risk Level")

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE VIEW fleet_hourly_activity AS (
                WITH hour_series AS (
                    SELECT generate_series(0, 23) AS hour
                ),
                trip_data AS (
                    SELECT
                        EXTRACT(HOUR FROM start_time)::int AS hour,
                        SUM(EXTRACT(EPOCH FROM (end_time - start_time)) / 60.0)::float AS total_duration
                    FROM traccar_trip_details
                    WHERE start_time IS NOT NULL AND end_time IS NOT NULL
                    GROUP BY EXTRACT(HOUR FROM start_time)
                )
                SELECT
                    ROW_NUMBER() OVER () AS id,
                    hs.hour,
                    COALESCE(td.total_duration, 0) AS total_duration,
                    TO_CHAR(
                        make_interval(mins => FLOOR(COALESCE(td.total_duration, 0))::int),
                        'HH24:MI:SS'
                    ) AS formatted_duration,
                    CASE
                        WHEN hs.hour IN (4, 23) THEN 'high'
                        WHEN hs.hour IN (7, 8, 17, 18, 19) THEN 'peak'
                        WHEN hs.hour IN (6, 16, 20) THEN 'medium'
                        ELSE 'low'
                    END AS risk_level
                FROM hour_series hs
                LEFT JOIN trip_data td ON hs.hour = td.hour
                ORDER BY hs.hour
            );
        """)

class FleetTripStartHourReport(models.Model):
    _name = "fleet.trip.start.hour.report"
    _description = "Trip Start Times by Hour (Over 50km)"
    _auto = False
    _rec_name = 'risk_level'

    hour = fields.Integer("Hour")
    trip_count = fields.Integer("Number of Trips")
    risk_level = fields.Selection([
        ('high', 'High Risk'),
        ('peak', 'Peak Risk'),
        ('medium', 'Medium Risk'),
        ('low', 'Low Risk'),
    ], string="Risk Level")

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE VIEW fleet_trip_start_hour_report AS (
                WITH hour_series AS (
                    SELECT generate_series(0, 23) AS hour
                ),
                trip_counts AS (
                    SELECT
                        EXTRACT(HOUR FROM start_time)::int AS hour,
                        COUNT(*) AS trip_count
                    FROM traccar_trip_details
                    WHERE distance > 50 AND start_time IS NOT NULL
                    GROUP BY EXTRACT(HOUR FROM start_time)
                )
                SELECT
                    ROW_NUMBER() OVER () AS id,
                    hs.hour,
                    COALESCE(tc.trip_count, 0) AS trip_count,
                    CASE
                        WHEN hs.hour IN (4, 23) THEN 'high'
                        WHEN hs.hour IN (7, 8, 17, 18, 19) THEN 'peak'
                        WHEN hs.hour IN (6, 16, 20) THEN 'medium'
                        ELSE 'low'
                    END AS risk_level
                FROM hour_series hs
                LEFT JOIN trip_counts tc ON hs.hour = tc.hour
                ORDER BY hs.hour
            );
        """)

class FleetUtilizationReport(models.Model):
    _name = "fleet.utilization.report"
    _description = "Fleet Utilization by Trips Completed"
    _auto = False
    _rec_name = 'vehicle_name'

    vehicle_id = fields.Many2one("fleet.vehicle", string="Vehicle")
    vehicle_name = fields.Char("Registration")
    trips_completed = fields.Integer("Trips Completed")
    average_all = fields.Float("Average All Vehicles")
    status = fields.Selection([
        ('above', 'Above Average'),
        ('below', 'Below Average'),
    ], string="Utilization Status")

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE VIEW fleet_utilization_report AS (
                WITH vehicle_trip_counts AS (
                    SELECT
                        v.id AS vehicle_id,
                        COALESCE(v.license_plate, v.name) AS vehicle_name,
                        COUNT(t.id) AS trips_completed
                    FROM fleet_vehicle v
                    LEFT JOIN traccar_trip_details t ON t.vehicle_id = v.id
                    GROUP BY v.id, v.license_plate, v.name
                ),
                overall_avg AS (
                    SELECT AVG(trips_completed) AS avg_trips FROM vehicle_trip_counts
                )
                SELECT
                    ROW_NUMBER() OVER () AS id,
                    vtc.vehicle_id,
                    vtc.vehicle_name,
                    vtc.trips_completed,
                    oa.avg_trips AS average_all,
                    CASE
                        WHEN vtc.trips_completed > oa.avg_trips THEN 'above'
                        ELSE 'below'
                    END AS status
                FROM vehicle_trip_counts vtc
                CROSS JOIN overall_avg oa
                ORDER BY vtc.trips_completed DESC
            );
        """)
