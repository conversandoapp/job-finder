-- Schema para el almacenamiento del backend en Supabase Postgres.
--
-- Correr una sola vez en el SQL Editor del proyecto de Supabase ya usado
-- para auth (Project → SQL Editor → pegar y ejecutar).
--
-- RLS queda deshabilitado a propósito: el frontend solo usa el cliente de
-- Supabase para auth (login/sesión), nunca consulta estas tablas
-- directamente. Toda la autorización (dueño de la sesión vs. admin) la
-- hace el backend en Python (ver backend/services/auth.py:
-- ensure_owner_or_admin, require_admin) usando la service_role key, que
-- ignora RLS de todas formas.

create table if not exists sessions (
  session_id        uuid primary key default gen_random_uuid(),
  created_at        timestamptz not null default now(),
  candidate_name    text,
  linkedin_url      text,
  pais              text not null default 'Peru',
  user_id           uuid,
  user_email        text,
  cv_status         text not null default 'pending'
                      check (cv_status in ('pending', 'ready', 'error')),
  jobs_status       text not null default 'not_requested'
                      check (jobs_status in ('not_requested', 'pending', 'ready', 'error')),
  cv_requested_at   timestamptz,
  cv_ready_at       timestamptz,
  jobs_requested_at timestamptz,
  jobs_ready_at     timestamptz,
  cv_drive_link     text,
  notes             text,
  -- Reemplazan cv_scores.json / vacantes.json (antes un archivo por sesión).
  cv_scores         jsonb,
  vacantes          jsonb,
  -- Sugerencias automáticas de roles por palabras clave (primer filtro,
  -- generado sin intervención humana en /api/analyze). No reemplaza el
  -- análisis del admin en cv_scores.roles_objetivo.
  roles_sugeridos   jsonb,
  -- Key exacta del objeto en el bucket "cv-files" de Supabase Storage.
  cv_original_path    text,
  cv_optimizado_path  text
);

create index if not exists sessions_user_id_idx on sessions (user_id);
create index if not exists sessions_created_at_idx on sessions (created_at desc);

create table if not exists notifications (
  id         bigint generated always as identity primary key,
  created_at timestamptz not null default now(),
  subject    text not null,
  body       text not null
);

create index if not exists notifications_created_at_idx on notifications (created_at desc);

-- Almacén genérico clave/valor. Usos actuales:
--   'drive_token'               -> credenciales OAuth de Google Drive (ver
--                                  backend/services/drive_oauth.py)
--   'drive_oauth_pending_state' -> state pendiente entre /authorize y
--                                  /oauth2callback del flujo de Drive
create table if not exists app_settings (
  key        text primary key,
  value      jsonb not null,
  updated_at timestamptz not null default now()
);

-- Cambios incrementales aplicados a mano sobre una DB ya existente (el
-- "create table if not exists" de arriba no los aplica solo):
--   alter table sessions add column if not exists roles_sugeridos jsonb;
