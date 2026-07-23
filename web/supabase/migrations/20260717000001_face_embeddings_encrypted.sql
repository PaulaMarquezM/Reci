-- Reci · embeddings faciales reales y cifrados en la capa de aplicación.
-- La foto original ya no se conserva tras generar el vector.

alter table public.face_embeddings
  alter column storage_path drop not null,
  add column if not exists embedding_ciphertext text,
  add column if not exists model text,
  add column if not exists embedding_version integer not null default 1;

comment on column public.face_embeddings.embedding_ciphertext is
  'Embedding facial cifrado con AES-256-GCM por el backend; nunca se expone al cliente ni al robot.';

comment on column public.face_embeddings.model is
  'Modelo que generó el embedding, por ejemplo Facenet512.';
