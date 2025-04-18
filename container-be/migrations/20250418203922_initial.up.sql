-- Add up migration script here
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    forename VARCHAR ( 50 ) NOT NULL,
    surname VARCHAR ( 50 ) NOT NULL,
    password VARCHAR ( 50 ) NOT NULL
);
