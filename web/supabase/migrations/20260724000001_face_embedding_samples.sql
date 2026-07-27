-- Varias muestras por usuario reducen la variación entre cámaras sin guardar fotos.
create table public.face_embedding_samples (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  embedding_ciphertext text not null,
  model text not null,
  created_at timestamptz not null default now()
);

create index face_embedding_samples_user_id_idx on public.face_embedding_samples(user_id);

alter table public.face_embedding_samples enable row level security;

create policy "Muestras faciales: leer propias"
on public.face_embedding_samples for select using (auth.uid() = user_id);

create policy "Muestras faciales: insertar propias"
on public.face_embedding_samples for insert with check (auth.uid() = user_id);

create policy "Muestras faciales: eliminar propias"
on public.face_embedding_samples for delete using (auth.uid() = user_id);

comment on table public.face_embedding_samples is
  'Muestras faciales cifradas con AES-256-GCM. No contiene fotografías.';
