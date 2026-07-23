-- ============================================================
-- Reci · Schema v1
-- Migración inicial: todas las tablas del plan maestro
-- ============================================================

-- Habilitar extensiones necesarias
create extension if not exists "uuid-ossp";
create extension if not exists "pgcrypto";

-- ============================================================
-- ENUMS
-- ============================================================

create type material_type as enum ('vidrio', 'plastico', 'desconocido');
create type robot_status as enum ('idle', 'moving', 'charging');
create type call_status as enum ('pending', 'in_progress', 'resolved', 'cancelled');

-- ============================================================
-- TABLA: profiles
-- Extiende auth.users con datos públicos del usuario
-- ============================================================

create table public.profiles (
  id            uuid primary key references auth.users(id) on delete cascade,
  display_name  text,
  avatar_url    text,
  facial_opt_in boolean not null default false,
  total_points  integer not null default 0,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);

-- ============================================================
-- TABLA: robot_points
-- Puntos fijos del campus donde Reci puede ir
-- ============================================================

create table public.robot_points (
  id         uuid primary key default uuid_generate_v4(),
  name       text not null,
  lat        numeric(10, 7) not null,
  lng        numeric(10, 7) not null,
  notes      text,
  active     boolean not null default true,
  created_at timestamptz not null default now()
);

-- ============================================================
-- TABLA: recycle_events
-- Cada reciclaje registrado por la IA
-- ============================================================

create table public.recycle_events (
  id             uuid primary key default uuid_generate_v4(),
  user_id        uuid references public.profiles(id) on delete set null,
  material       material_type not null,
  confidence     numeric(5, 4) check (confidence between 0 and 1),
  robot_point_id uuid references public.robot_points(id) on delete set null,
  created_at     timestamptz not null default now()
);

-- ============================================================
-- TABLA: points_ledger
-- Puntos por evento (append-only para auditoría)
-- ============================================================

create table public.points_ledger (
  id         uuid primary key default uuid_generate_v4(),
  user_id    uuid not null references public.profiles(id) on delete cascade,
  delta      integer not null,
  reason     text not null,
  event_id   uuid references public.recycle_events(id) on delete set null,
  created_at timestamptz not null default now()
);

-- ============================================================
-- TABLA: streaks
-- Racha actual del usuario
-- ============================================================

create table public.streaks (
  user_id          uuid primary key references public.profiles(id) on delete cascade,
  current_streak   integer not null default 0,
  longest_streak   integer not null default 0,
  last_recycle_at  timestamptz,
  updated_at       timestamptz not null default now()
);

-- ============================================================
-- TABLA: coupons
-- Catálogo de cupones canjeables
-- ============================================================

create table public.coupons (
  id           uuid primary key default uuid_generate_v4(),
  title        text not null,
  description  text,
  cost_points  integer not null check (cost_points > 0),
  stock        integer not null default 0 check (stock >= 0),
  active       boolean not null default true,
  created_at   timestamptz not null default now()
);

-- ============================================================
-- TABLA: coupon_redemptions
-- Canjes realizados
-- ============================================================

create table public.coupon_redemptions (
  id          uuid primary key default uuid_generate_v4(),
  user_id     uuid not null references public.profiles(id) on delete cascade,
  coupon_id   uuid not null references public.coupons(id) on delete restrict,
  code        text not null unique default encode(gen_random_bytes(6), 'hex'),
  redeemed_at timestamptz not null default now()
);

-- ============================================================
-- TABLA: robot_positions
-- Tracking de posición de Reci (snapshot por ciclo)
-- ============================================================

create table public.robot_positions (
  id          uuid primary key default uuid_generate_v4(),
  robot_id    text not null default 'reci-01',
  lat         numeric(10, 7) not null,
  lng         numeric(10, 7) not null,
  status      robot_status not null default 'idle',
  recorded_at timestamptz not null default now()
);

-- ============================================================
-- TABLA: compartments
-- Estado de los dos compartimentos del robot
-- ============================================================

create table public.compartments (
  id             text primary key check (id in ('vidrio', 'plastico')),
  fill_percent   integer not null default 0 check (fill_percent between 0 and 100),
  last_updated   timestamptz not null default now(),
  last_emptied_at timestamptz
);

-- Seed: crear los dos compartimentos
insert into public.compartments (id) values ('vidrio'), ('plastico');

-- ============================================================
-- TABLA: call_requests
-- Solicitudes "llama a Reci a este punto"
-- ============================================================

create table public.call_requests (
  id          uuid primary key default uuid_generate_v4(),
  user_id     uuid not null references public.profiles(id) on delete cascade,
  point_id    uuid not null references public.robot_points(id) on delete restrict,
  status      call_status not null default 'pending',
  created_at  timestamptz not null default now(),
  resolved_at timestamptz
);

-- ============================================================
-- TABLA: face_embeddings
-- Embeddings faciales cifrados (opt-in)
-- ============================================================

create table public.face_embeddings (
  user_id           uuid primary key references public.profiles(id) on delete cascade,
  storage_path      text not null,
  consent_signed_at timestamptz not null default now()
);

-- ============================================================
-- TABLA: push_tokens
-- Tokens Web Push por dispositivo
-- ============================================================

create table public.push_tokens (
  id         uuid primary key default uuid_generate_v4(),
  user_id    uuid not null references public.profiles(id) on delete cascade,
  endpoint   text not null unique,
  keys       jsonb not null,
  created_at timestamptz not null default now()
);

-- ============================================================
-- ÍNDICES
-- ============================================================

create index on public.recycle_events (user_id, created_at desc);
create index on public.recycle_events (created_at desc);
create index on public.points_ledger (user_id, created_at desc);
create index on public.robot_positions (recorded_at desc);
create index on public.call_requests (user_id, status);
create index on public.call_requests (status, created_at);
create index on public.coupon_redemptions (user_id);

-- ============================================================
-- TRIGGER: crear profile automáticamente al registrarse
-- ============================================================

create or replace function public.handle_new_user()
returns trigger language plpgsql security definer
set search_path = public
as $$
begin
  insert into public.profiles (id, display_name, avatar_url)
  values (
    new.id,
    coalesce(new.raw_user_meta_data->>'full_name', split_part(new.email, '@', 1)),
    new.raw_user_meta_data->>'avatar_url'
  );

  insert into public.streaks (user_id)
  values (new.id);

  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();

-- ============================================================
-- TRIGGER: sumar puntos al registrar un reciclaje
-- ============================================================

create or replace function public.handle_recycle_event()
returns trigger language plpgsql security definer
set search_path = public
as $$
declare
  pts integer;
begin
  -- Puntos según material (desconocido no suma)
  pts := case new.material
    when 'vidrio'   then 10
    when 'plastico' then 10
    else 0
  end;

  if pts > 0 and new.user_id is not null then
    -- Registrar en el ledger
    insert into public.points_ledger (user_id, delta, reason, event_id)
    values (new.user_id, pts, 'recycle:' || new.material::text, new.id);

    -- Actualizar total en el perfil
    update public.profiles
    set total_points = total_points + pts,
        updated_at   = now()
    where id = new.user_id;

    -- Actualizar racha
    update public.streaks
    set
      current_streak  = case
        when last_recycle_at is null
          or last_recycle_at < now() - interval '2 days' then 1
        when date_trunc('day', last_recycle_at) < date_trunc('day', now()) then current_streak + 1
        else current_streak
      end,
      longest_streak  = greatest(
        longest_streak,
        case
          when last_recycle_at is null
            or last_recycle_at < now() - interval '2 days' then 1
          when date_trunc('day', last_recycle_at) < date_trunc('day', now()) then current_streak + 1
          else current_streak
        end
      ),
      last_recycle_at = now(),
      updated_at      = now()
    where user_id = new.user_id;
  end if;

  return new;
end;
$$;

create trigger on_recycle_event_created
  after insert on public.recycle_events
  for each row execute procedure public.handle_recycle_event();

-- ============================================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================================

-- Habilitar RLS en todas las tablas con datos de usuario
alter table public.profiles          enable row level security;
alter table public.recycle_events    enable row level security;
alter table public.points_ledger     enable row level security;
alter table public.streaks           enable row level security;
alter table public.coupon_redemptions enable row level security;
alter table public.call_requests     enable row level security;
alter table public.face_embeddings   enable row level security;
alter table public.push_tokens       enable row level security;

-- Tablas públicas (lectura libre)
alter table public.robot_points      enable row level security;
alter table public.robot_positions   enable row level security;
alter table public.compartments      enable row level security;
alter table public.coupons           enable row level security;

-- ---- profiles ----
create policy "Perfil propio: leer"   on public.profiles for select using (auth.uid() = id);
create policy "Perfil propio: editar" on public.profiles for update using (auth.uid() = id);
-- Service role puede leer/escribir todo (para triggers y API routes)

-- ---- recycle_events ----
create policy "Eventos: leer propios" on public.recycle_events for select using (auth.uid() = user_id);
-- Insertar solo desde service role (lo hace la IA / API route autenticada como service)

-- ---- points_ledger ----
create policy "Ledger: leer propio" on public.points_ledger for select using (auth.uid() = user_id);

-- ---- streaks ----
create policy "Racha: leer propia" on public.streaks for select using (auth.uid() = user_id);

-- ---- coupon_redemptions ----
create policy "Canjes: leer propios" on public.coupon_redemptions for select using (auth.uid() = user_id);

-- ---- call_requests ----
create policy "Llamadas: leer propias"  on public.call_requests for select using (auth.uid() = user_id);
create policy "Llamadas: insertar"      on public.call_requests for insert with check (auth.uid() = user_id);
create policy "Llamadas: cancelar"      on public.call_requests for update using (auth.uid() = user_id and status = 'pending');

-- ---- face_embeddings ----
create policy "Facial: leer propio"    on public.face_embeddings for select using (auth.uid() = user_id);
create policy "Facial: insertar"       on public.face_embeddings for insert with check (auth.uid() = user_id);
create policy "Facial: eliminar"       on public.face_embeddings for delete using (auth.uid() = user_id);

-- ---- push_tokens ----
create policy "Push: leer propios"   on public.push_tokens for select using (auth.uid() = user_id);
create policy "Push: insertar"       on public.push_tokens for insert with check (auth.uid() = user_id);
create policy "Push: eliminar"       on public.push_tokens for delete using (auth.uid() = user_id);

-- ---- tablas públicas (lectura libre para usuarios autenticados) ----
create policy "Puntos campus: leer"   on public.robot_points    for select using (true);
create policy "Posición robot: leer"  on public.robot_positions for select using (true);
create policy "Compartimentos: leer"  on public.compartments    for select using (true);
create policy "Cupones: leer activos" on public.coupons         for select using (active = true);
