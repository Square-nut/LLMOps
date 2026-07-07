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

create index if not exists idx_llm_logs_created_at on llm_logs(created_at desc);
create index if not exists idx_chunks_document_id on chunks(document_id);
create index if not exists idx_documents_created_at on documents(created_at desc);

-- 已有库升级（可单独执行）
alter table llm_logs add column if not exists prompt_tokens integer default 0;
alter table llm_logs add column if not exists completion_tokens integer default 0;
