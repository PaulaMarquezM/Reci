-- Reci · Códigos QR de reclamo para reciclajes sin usuario identificado.
--
-- Cuando la ESP32-CAM clasifica un objeto y no hay user_id conocido (sin
-- reconocimiento facial o sin match), el evento se guarda igual pero no
-- suma puntos todavía. Se genera un claim_code corto que el robot muestra
-- como QR en el OLED; quien lo escanea desde la app (ya autenticado) queda
-- vinculado al evento y ahí sí se otorgan los puntos.

alter table public.recycle_events
  add column if not exists claim_code text,
  add column if not exists claim_expires_at timestamptz,
  add column if not exists claimed_at timestamptz;

create unique index if not exists recycle_events_claim_code_key
  on public.recycle_events (claim_code)
  where claim_code is not null;

comment on column public.recycle_events.claim_code is
  'Código corto (8 caracteres) mostrado como QR en el OLED de Reci. Null si el evento ya nació con user_id conocido.';
comment on column public.recycle_events.claim_expires_at is
  'El código deja de ser válido después de esta hora (evita que alguien reclame un evento viejo ajeno).';
comment on column public.recycle_events.claimed_at is
  'Cuándo se reclamó el código. Null mientras esté pendiente.';

-- El trigger original solo corría en INSERT y asumía user_id ya conocido.
-- Ahora también corre en UPDATE, para el momento en que se reclama el QR
-- (user_id pasa de null a un uuid). Se evita duplicar puntos si el evento
-- ya tenía user_id desde el insert original.
create or replace function public.handle_recycle_event()
returns trigger language plpgsql security definer
set search_path = public
as $$
declare
  pts integer;
begin
  if new.user_id is null then
    return new;
  end if;

  if tg_op = 'UPDATE' and old.user_id is not null then
    return new;
  end if;

  pts := case new.material
    when 'vidrio'   then 10
    when 'plastico' then 10
    else 0
  end;

  if pts > 0 then
    insert into public.points_ledger (user_id, delta, reason, event_id)
    values (new.user_id, pts, 'recycle:' || new.material::text, new.id);

    update public.profiles
    set total_points = total_points + pts,
        updated_at   = now()
    where id = new.user_id;

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

drop trigger if exists on_recycle_event_created on public.recycle_events;
create trigger on_recycle_event_user_known
  after insert or update on public.recycle_events
  for each row execute procedure public.handle_recycle_event();
