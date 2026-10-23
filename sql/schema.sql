-- Group 43: ER-to-relational transformation, PostgreSQL.
-- Run against a new database: psql -v ON_ERROR_STOP=1 -d YOUR_DATABASE -f sql/schema.sql
-- IDs are supplied by the source dataset.
-- Convert CSV missing markers to NULL and duration values to INTERVAL before import.
-- Match lap/pit CSV (raceId, driverId) pairs to results to obtain result_id.
BEGIN;

CREATE TABLE IF NOT EXISTS circuits (
    circuit_id INTEGER PRIMARY KEY,
    circuit_ref TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    location TEXT,
    country TEXT
);

CREATE TABLE IF NOT EXISTS drivers (
    driver_id INTEGER PRIMARY KEY,
    driver_ref TEXT NOT NULL UNIQUE,
    number INTEGER CHECK (number >= 0),
    code VARCHAR(3),
    forename TEXT NOT NULL,
    surname TEXT NOT NULL,
    dob DATE,
    nationality TEXT
);

CREATE TABLE IF NOT EXISTS constructors (
    constructor_id INTEGER PRIMARY KEY,
    constructor_ref TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    nationality TEXT
);

CREATE TABLE IF NOT EXISTS statuses (
    status_id INTEGER PRIMARY KEY,
    status TEXT NOT NULL -- Descriptive label added to the diagram's ID-only entity.
);

CREATE TABLE IF NOT EXISTS races (
    race_id INTEGER PRIMARY KEY,
    year INTEGER NOT NULL CHECK (year >= 1950),
    round INTEGER NOT NULL CHECK (round > 0),
    name TEXT NOT NULL,
    race_date DATE NOT NULL,
    start_time TIME, -- Source time of day; retain source timezone convention.
    circuit_id INTEGER NOT NULL REFERENCES circuits(circuit_id),
    UNIQUE (year, round)
);

CREATE TABLE IF NOT EXISTS results (
    result_id INTEGER PRIMARY KEY,
    race_id INTEGER NOT NULL REFERENCES races(race_id),
    driver_id INTEGER NOT NULL REFERENCES drivers(driver_id),
    constructor_id INTEGER NOT NULL REFERENCES constructors(constructor_id),
    status_id INTEGER NOT NULL REFERENCES statuses(status_id),
    number INTEGER CHECK (number >= 0),
    grid INTEGER CHECK (grid >= 0),
    position_order INTEGER NOT NULL CHECK (position_order > 0),
    points NUMERIC(8,3) NOT NULL CHECK (points >= 0),
    laps INTEGER CHECK (laps >= 0),
    elapsed_time INTERVAL CHECK (elapsed_time >= INTERVAL '0 seconds'),
    fastest_lap_time INTERVAL CHECK (fastest_lap_time > INTERVAL '0 seconds'),
    fastest_lap_speed NUMERIC(8,3) CHECK (fastest_lap_speed > 0) -- km/h assumption
);

-- Weak entities: parent result ID plus the partial key from the ER diagram.
CREATE TABLE IF NOT EXISTS pit_stops (
    result_id INTEGER NOT NULL REFERENCES results(result_id),
    stop INTEGER NOT NULL CHECK (stop > 0),
    lap INTEGER NOT NULL CHECK (lap >= 0),
    stop_time TIME,
    duration INTERVAL CHECK (duration >= INTERVAL '0 seconds'),
    PRIMARY KEY (result_id, stop)
);

CREATE TABLE IF NOT EXISTS lap_times (
    result_id INTEGER NOT NULL REFERENCES results(result_id),
    lap INTEGER NOT NULL CHECK (lap > 0),
    position INTEGER CHECK (position > 0),
    lap_time INTERVAL CHECK (lap_time > INTERVAL '0 seconds'),
    PRIMARY KEY (result_id, lap)
);

COMMIT;
