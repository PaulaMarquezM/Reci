-- ============================================================
-- RECI · Puntos fijos para la demostracion de ruta circular
-- ============================================================
-- La ruta fisica del prototipo es BASE -> P1 -> P2 -> BASE.
-- Estas coordenadas solo ubican los marcadores en el mapa de la app;
-- el Mega se mueve por tiempos calibrados, no por GPS.

insert into public.robot_points (name, lat, lng, notes, active)
select 'Base', -1.0374000, -80.4692000, 'Inicio y regreso de RECI.', true
where not exists (
  select 1 from public.robot_points where name = 'Base'
);

insert into public.robot_points (name, lat, lng, notes, active)
select 'Parada 1', -1.0383000, -80.4692000, 'Primera parada de la ruta demo.', true
where not exists (
  select 1 from public.robot_points where name = 'Parada 1'
);

insert into public.robot_points (name, lat, lng, notes, active)
select 'Parada 2', -1.0392000, -80.4692000, 'Segunda parada de la ruta demo.', true
where not exists (
  select 1 from public.robot_points where name = 'Parada 2'
);
