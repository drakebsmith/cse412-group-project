-- Run against a new database: psql -v ON_ERROR_STOP=1 -d YOUR_DATABASE -f sql/updated_schema.sql
BEGIN;

CREATE TABLE IF NOT EXISTS circuits (
    circuitId INTEGER PRIMARY KEY,
    circuitRef TEXT NOT NULL UNIQUE,
    "name" TEXT NOT NULL,
    "location" TEXT,
    country TEXT
);

CREATE TABLE IF NOT EXISTS drivers (
    driverId INTEGER PRIMARY KEY,
    driverRef TEXT NOT NULL UNIQUE,
    "number" INTEGER CHECK ("number" >= 0),
    code VARCHAR(3),
    forename TEXT NOT NULL,
    surname TEXT NOT NULL,
    dob DATE,
    nationality TEXT
);

CREATE TABLE IF NOT EXISTS constructors (
    constructorId INTEGER PRIMARY KEY,
    constructorRef TEXT NOT NULL UNIQUE,
    "name" TEXT NOT NULL,
    nationality TEXT
);

CREATE TABLE IF NOT EXISTS statuses (
    statusId INTEGER PRIMARY KEY,
    "status" TEXT NOT NULL -- Descriptive label added to the diagram's ID-only entity.
);

CREATE TABLE IF NOT EXISTS races (
    raceId INTEGER PRIMARY KEY,
    "year" INTEGER NOT NULL CHECK ("year" >= 1950),
    round INTEGER NOT NULL CHECK (round > 0),
    "name" TEXT NOT NULL,
    "date" DATE NOT NULL,
    "time" TIME, -- Source time of day; retain source timezone convention.
    circuitId INTEGER NOT NULL REFERENCES circuits(circuitId),
    UNIQUE ("year", round)
);

CREATE TABLE IF NOT EXISTS results (
    resultId INTEGER PRIMARY KEY,
    raceId INTEGER NOT NULL REFERENCES races(raceId),
    driverId INTEGER NOT NULL REFERENCES drivers(driverId),
    constructorId INTEGER NOT NULL REFERENCES constructors(constructorId),
    statusId INTEGER NOT NULL REFERENCES statuses(statusId),
    "number" INTEGER CHECK ("number" >= 0),
    grid INTEGER CHECK (grid >= 0),
    positionOrder INTEGER NOT NULL CHECK (positionOrder > 0),
    points NUMERIC(8,3) NOT NULL CHECK (points >= 0),
    laps INTEGER CHECK (laps >= 0),
    "time" INTERVAL CHECK ("time" >= INTERVAL '0 seconds'),
    fastestLapTime INTERVAL CHECK (fastestLapTime > INTERVAL '0 seconds'),
    fastestLapSpeed NUMERIC(8,3) CHECK (fastestLapSpeed > 0) -- km/h assumption
);

-- Weak entities: parent result ID plus the partial key from the ER diagram.
CREATE TABLE IF NOT EXISTS pit_stops (
    resultId INTEGER NOT NULL REFERENCES results(resultId),
    "stop" INTEGER NOT NULL CHECK ("stop" > 0),
    lap INTEGER NOT NULL CHECK (lap >= 0),
    "time" TIME,
    duration INTERVAL CHECK (duration >= INTERVAL '0 seconds'),
    PRIMARY KEY (resultId, "stop")
);

CREATE TABLE IF NOT EXISTS lap_times (
    resultId INTEGER NOT NULL REFERENCES results(resultId),
    lap INTEGER NOT NULL CHECK (lap > 0),
    position INTEGER CHECK (position > 0),
    "time" INTERVAL CHECK ("time" > INTERVAL '0 seconds'),
    PRIMARY KEY (resultId, lap)
);

COMMIT;