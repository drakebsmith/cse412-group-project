-- Executed by database_import.py after COPY staging. No psql commands.
-- Choose and reorder only the target columns. Source-only metadata remains in staging.
INSERT INTO circuits (circuit_id, circuit_ref, name, location, country)
SELECT circuitId::integer, circuitRef, name, location, country FROM stage_circuits;

INSERT INTO drivers (driver_id, driver_ref, number, code, forename, surname, dob, nationality)
SELECT driverId::integer, driverRef, number::integer, code, forename, surname,
       dob::date, nationality FROM stage_drivers;

INSERT INTO constructors (constructor_id, constructor_ref, name, nationality)
SELECT constructorId::integer, constructorRef, name, nationality FROM stage_constructors;

INSERT INTO statuses (status_id, status)
SELECT statusId::integer, status FROM stage_status;

INSERT INTO races (race_id, year, round, name, race_date, start_time, circuit_id)
SELECT raceId::integer, year::integer, round::integer, name, date::date,
       time::time, circuitId::integer FROM stage_races;

INSERT INTO results (
    result_id, race_id, driver_id, constructor_id, status_id, number, grid,
    position_order, points, laps, elapsed_time, fastest_lap_time, fastest_lap_speed
)
SELECT resultId::integer, raceId::integer, driverId::integer, constructorId::integer,
       statusId::integer, number::integer, grid::integer, positionOrder::integer,
       points::numeric, laps::integer,
       milliseconds::double precision * INTERVAL '1 millisecond',
       -- Source fastestLapTime is minutes:seconds, not hours:minutes.
       CASE WHEN fastestLapTime IS NULL THEN NULL
            ELSE (split_part(fastestLapTime, ':', 1)::double precision * 60
                + split_part(fastestLapTime, ':', 2)::double precision)
                * INTERVAL '1 second' END,
       fastestLapSpeed::numeric
FROM stage_results;

CREATE INDEX IF NOT EXISTS results_race_driver_import_idx ON results (race_id, driver_id);

-- Historical race/driver pairs are not globally unique. Every staged child
-- must match EXACTLY one result; abort instead of dropping or duplicating rows.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM stage_pit_stops s
        WHERE (SELECT count(*) FROM results r
               WHERE r.race_id = s.raceId::integer
                 AND r.driver_id = s.driverId::integer) <> 1
    ) THEN
        RAISE EXCEPTION 'Pit-stop CSV has missing or ambiguous result matches; import rolled back';
    END IF;
    IF EXISTS (
        SELECT 1 FROM stage_lap_times s
        WHERE (SELECT count(*) FROM results r
               WHERE r.race_id = s.raceId::integer
                 AND r.driver_id = s.driverId::integer) <> 1
    ) THEN
        RAISE EXCEPTION 'Lap-time CSV has missing or ambiguous result matches; import rolled back';
    END IF;
END $$;

INSERT INTO pit_stops (result_id, stop, lap, stop_time, duration)
SELECT r.result_id, s.stop::integer, s.lap::integer, s.time::time,
       s.milliseconds::double precision * INTERVAL '1 millisecond'
FROM stage_pit_stops s
JOIN results r ON r.race_id = s.raceId::integer AND r.driver_id = s.driverId::integer;

INSERT INTO lap_times (result_id, lap, position, lap_time)
SELECT r.result_id, s.lap::integer, s.position::integer,
       s.milliseconds::double precision * INTERVAL '1 millisecond'
FROM stage_lap_times s
JOIN results r ON r.race_id = s.raceId::integer AND r.driver_id = s.driverId::integer;

-- Verify all staged rows reached their target before committing.
DO $$
BEGIN

    IF (SELECT count(*) FROM circuits) <> (SELECT count(*) FROM stage_circuits) THEN
        RAISE EXCEPTION 'Row count mismatch for circuits';
    END IF;

    IF (SELECT count(*) FROM drivers) <> (SELECT count(*) FROM stage_drivers) THEN
        RAISE EXCEPTION 'Row count mismatch for drivers';
    END IF;

    IF (SELECT count(*) FROM constructors) <> (SELECT count(*) FROM stage_constructors) THEN
        RAISE EXCEPTION 'Row count mismatch for constructors';
    END IF;

    IF (SELECT count(*) FROM statuses) <> (SELECT count(*) FROM stage_status) THEN
        RAISE EXCEPTION 'Row count mismatch for statuses';
    END IF;

    IF (SELECT count(*) FROM races) <> (SELECT count(*) FROM stage_races) THEN
        RAISE EXCEPTION 'Row count mismatch for races';
    END IF;

    IF (SELECT count(*) FROM results) <> (SELECT count(*) FROM stage_results) THEN
        RAISE EXCEPTION 'Row count mismatch for results';
    END IF;

    IF (SELECT count(*) FROM pit_stops) <> (SELECT count(*) FROM stage_pit_stops) THEN
        RAISE EXCEPTION 'Row count mismatch for pit_stops';
    END IF;

    IF (SELECT count(*) FROM lap_times) <> (SELECT count(*) FROM stage_lap_times) THEN
        RAISE EXCEPTION 'Row count mismatch for lap_times';
    END IF;

END $$;
