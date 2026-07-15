-- Supabase schema for LLMOps MVP

create extension if not exists "pgcrypto";

create table if not exists llm_logs (
    id uuid primary key default gen_random_uuid(),
    user_id text,
    input text not null,
    output text not null,
    model text not null,
    tokens integer default 0,
    prompt_tokens integer default 0,
    completion_tokens integer default 0,
    latency integer default 0,
    created_at timestamptz default now()
);

create table if not exists documents (
    id uuid primary key default gen_random_uuid(),
    content text not null,
    source text not null default 'upload',
    created_at timestamptz default now()
);

create table if not exists chunks (
    id uuid primary key default gen_random_uuid(),
    document_id uuid references documents(id) on delete cascade,
    chunk_text text not null,
    embedding_version text not null default 'v1',
    created_at timestamptz default now()
);

-- Product-side model catalogue. This stores non-secret connection metadata only;
-- Xinference remains responsible for loading and managing model processes.
create table if not exists model_configs (
    id uuid primary key default gen_random_uuid(),
    model_key text not null unique,
    display_name text not null,
    model_type text not null check (model_type in ('chat', 'embedding', 'vision')),
    provider text not null,
    model_name text not null,
    endpoint text,
    dimension integer check (dimension is null or dimension > 0),
    enabled boolean not null default true,
    is_active boolean not null default false,
    notes text not null default '',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_llm_logs_created_at on llm_logs(created_at desc);
create index if not exists idx_chunks_document_id on chunks(document_id);
create index if not exists idx_documents_created_at on documents(created_at desc);
create index if not exists idx_model_configs_type on model_configs(model_type);
create unique index if not exists idx_model_configs_one_active_per_type
    on model_configs(model_type) where is_active;

-- 已有库升级（可单独执行）
alter table llm_logs add column if not exists prompt_tokens integer default 0;
alter table llm_logs add column if not exists completion_tokens integer default 0;
alter table model_configs add column if not exists is_active boolean not null default false;
