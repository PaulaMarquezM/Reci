-- ============================================================
-- Reci · Despacho de llamadas hacia el robot (Fase 7)
-- ============================================================
-- Cierra el Flujo B: hasta ahora `call_requests` se llenaba desde
-- la app y nadie la leía nunca. El robot ahora consulta y actualiza
-- sus llamadas vía /api/robot/calls/*.
--
-- Dos cambios:
--   1. robot_positions.point_id — posición simbólica (no hay GPS).
--   2. Realtime en call_requests — la app ve "voy" / "llegué".
-- ============================================================

-- ------------------------------------------------------------
-- 1. Posición simbólica
-- ------------------------------------------------------------
-- El robot no tiene GPS: solo se mueve entre puntos fijos. Reporta
-- en qué punto está (o hacia cuál va) y la API resuelve lat/lng
-- desde robot_points. lat/lng siguen siendo NOT NULL y se llenan
-- igual que antes, así que el mapa y el Realtime no cambian.

alter table public.robot_positions
  add column point_id uuid references public.robot_points(id) on delete set null;

comment on column public.robot_positions.point_id is
  'Punto del campus al que corresponde esta posición. Con status=moving es el punto DESTINO, no dónde está el robot ahora.';

-- ------------------------------------------------------------
-- 2. Realtime en call_requests
-- ------------------------------------------------------------
-- Para que la pantalla de Llamar reaccione cuando el robot pasa la
-- llamada a in_progress ("Reci aceptó") y a resolved ("Reci llegó").
-- La policy "Llamadas: leer propias" (auth.uid() = user_id) del
-- schema v1 ya limita cada usuario a sus propias filas, y Realtime
-- respeta RLS: nadie ve las llamadas de otro.

alter publication supabase_realtime add table public.call_requests;

-- ------------------------------------------------------------
-- 3. Índice para el polling del robot
-- ------------------------------------------------------------
-- El robot pega a /api/robot/calls/next cada ~3s y esa query filtra
-- por status y ordena por created_at. Ya existe el índice
-- (status, created_at) del schema v1, así que no hace falta uno nuevo.
