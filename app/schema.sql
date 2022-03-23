drop table if exists clients;
drop table if exists global_model;

create table clients (
    id integer primary key AUTOINCREMENT,
    name varchar(50) not null,
    weights BLOB not null,
    score real not null
);

create table global_model (
    id integer primary key AUTOINCREMENT,
    client_1_name varchar(50) not null,
    client_2_name varchar(50) not null,
    model BLOB not null,
    client_count integer not null default 0
);