create table if not exists hm_responses (
    id text primary key,
    "timestamp" timestamptz,
    community text not null check (community in ('GC', 'TC', 'Other')),
    topic_id text not null,
    issue text not null,
    negotiation_restart integer,
    governance integer,
    security integer,
    territory integer,
    property integer,
    text text not null,
    is_seed boolean not null default false
);

create table if not exists hm_statement_rounds (
    round_id text primary key,
    "timestamp" timestamptz,
    scope text not null,
    topic_id text not null,
    issue text not null,
    statement_a text,
    statement_b text,
    statement_c text,
    statement_d text,
    key_tensions text,
    raw_output text,
    winning_statement text,
    refined_statement text
);

create table if not exists hm_rankings (
    ranking_id text primary key,
    "timestamp" timestamptz,
    round_id text not null references hm_statement_rounds(round_id) on delete cascade,
    participant_community text not null check (participant_community in ('GC', 'TC', 'Other')),
    rank_a integer,
    rank_b integer,
    rank_c integer,
    rank_d integer,
    acceptable_statements text,
    critique text
);

create index if not exists hm_responses_topic_idx on hm_responses(topic_id);
create index if not exists hm_statement_rounds_topic_idx on hm_statement_rounds(topic_id);
create index if not exists hm_rankings_round_idx on hm_rankings(round_id);
