-- ============================================================
-- Reci · Habilitar Realtime para la posición del robot
-- ============================================================
-- La pantalla del mapa (Fase 6) se suscribe a INSERTs en
-- robot_positions vía Supabase Realtime. Para que los cambios se
-- transmitan, la tabla debe estar en la publicación supabase_realtime.
--
-- La lectura ya está permitida por la policy "Posición robot: leer"
-- (select using true) creada en el schema v1.
-- ============================================================

alter publication supabase_realtime add table public.robot_positions;
