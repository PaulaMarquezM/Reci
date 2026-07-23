-- Recursos necesarios para Ajustes: avatar público, foto facial privada y
-- actualizaciones idempotentes de suscripciones/consentimiento.

insert into storage.buckets (id, name, public)
values ('avatars', 'avatars', true), ('face-embeddings', 'face-embeddings', false)
on conflict (id) do update set public = excluded.public;

create policy "Avatar: lectura pública"
on storage.objects for select
using (bucket_id = 'avatars');

create policy "Avatar: subir propio"
on storage.objects for insert to authenticated
with check (bucket_id = 'avatars' and (storage.foldername(name))[1] = auth.uid()::text);

create policy "Avatar: actualizar propio"
on storage.objects for update to authenticated
using (bucket_id = 'avatars' and (storage.foldername(name))[1] = auth.uid()::text);

create policy "Avatar: borrar propio"
on storage.objects for delete to authenticated
using (bucket_id = 'avatars' and (storage.foldername(name))[1] = auth.uid()::text);

create policy "Rostro: subir propio"
on storage.objects for insert to authenticated
with check (bucket_id = 'face-embeddings' and (storage.foldername(name))[2] = auth.uid()::text);

create policy "Rostro: borrar propio"
on storage.objects for delete to authenticated
using (bucket_id = 'face-embeddings' and (storage.foldername(name))[2] = auth.uid()::text);

create policy "Facial: actualizar propio"
on public.face_embeddings for update
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

create policy "Push: actualizar propios"
on public.push_tokens for update
using (auth.uid() = user_id)
with check (auth.uid() = user_id);
