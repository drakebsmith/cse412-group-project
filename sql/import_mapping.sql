
INSERT INTO circuits (circuitId, circuitRef, name, location, country)
SELECT circuitId::integer, circuitRef, name, location, country FROM stage_circuits;

INSERT INTO drivers (driverId, driverRef, number, code, forename, surname, dob, nationality)
SELECT driverId::integer, driverRef, number::integer, code, forename, surname,
       dob::date, nationality FROM stage_drivers;

INSERT INTO constructors (constructorId, constructorRef, name, nationality)
SELECT constructorId::integer, constructorRef, name, nationality FROM stage_constructors;

INSERT INTO statuses (statusId, status)
SELECT statusId::integer, status FROM stage_statuses;

INSERT INTO races (raceId, year, round, name, date, time, circuitId)
SELECT raceId::integer, year::integer, round::integer, name, date::date,
       time::time, circuitId::integer FROM stage_races;

INSERT INTO results (
    resultId, raceId, driverId, constructorId, statusId, number, grid,
    positionOrder, points, laps, time, fastestLapTime, fastestLapSpeed
)
SELECT resultId::integer, raceId::integer, driverId::integer, constructorId::integer,
       statusId::integer, number::integer, grid::integer, positionOrder::integer,
       points::numeric, laps::integer,
       milliseconds::double precision * INTERVAL '1 millisecond',
       CASE WHEN fastestLapTime IS NULL THEN NULL
            ELSE (split_part(fastestLapTime, ':', 1)::double precision * 60
                + split_part(fastestLapTime, ':', 2)::double precision)
                * INTERVAL '1 second' END,
       fastestLapSpeed::numeric
FROM stage_results;

-- Historical pairs can repeat. Require exactly one match for every child;
-- MIN is used only after checking that the group has one result.
CREATE TEMP TABLE race_detail_result_map ON COMMIT DROP AS
SELECT raceId, driverId, MIN(resultId) AS resultId, COUNT(*) AS matches
FROM results GROUP BY raceId, driverId;
CREATE UNIQUE INDEX ON race_detail_result_map (raceId, driverId);
ANALYZE race_detail_result_map;
ANALYZE stage_pit_stops;
ANALYZE stage_lap_times;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM stage_pit_stops s
        LEFT JOIN race_detail_result_map r
          ON r.raceId = s.raceId::integer AND r.driverId = s.driverId::integer
        WHERE COALESCE(r.matches, 0) <> 1
    ) THEN
        RAISE EXCEPTION 'Pit-stop row has a missing or ambiguous result; import rolled back';
    END IF;
    IF EXISTS (
        SELECT 1 FROM stage_lap_times s
        LEFT JOIN race_detail_result_map r
          ON r.raceId = s.raceId::integer AND r.driverId = s.driverId::integer
        WHERE COALESCE(r.matches, 0) <> 1
    ) THEN
        RAISE EXCEPTION 'Lap-time row has a missing or ambiguous result; import rolled back';
    END IF;
END $$;

INSERT INTO pit_stops (resultId, stop, lap, time, duration)
SELECT r.resultId, s.stop::integer, s.lap::integer, s.time::time,
       s.milliseconds::double precision * INTERVAL '1 millisecond'
FROM stage_pit_stops s JOIN race_detail_result_map r
  ON r.raceId = s.raceId::integer AND r.driverId = s.driverId::integer;

INSERT INTO lap_times (resultId, lap, position, time)
SELECT r.resultId, s.lap::integer, s.position::integer,
       s.milliseconds::double precision * INTERVAL '1 millisecond'
FROM stage_lap_times s JOIN race_detail_result_map r
  ON r.raceId = s.raceId::integer AND r.driverId = s.driverId::integer;
