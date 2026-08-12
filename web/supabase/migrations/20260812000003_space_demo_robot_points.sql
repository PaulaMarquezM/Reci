-- Ajusta los puntos de la demo para que se distingan en el mapa del campus.
-- Están alineados de norte a sur; la ruta física sigue siendo simbólica.

update public.robot_points
set lat = -1.0374000, lng = -80.4692000,
    notes = 'Inicio y regreso de RECI.'
where name = 'Base';

update public.robot_points
set lat = -1.0383000, lng = -80.4692000,
    notes = 'Primera parada de la ruta demo.'
where name = 'Parada 1';

update public.robot_points
set lat = -1.0392000, lng = -80.4692000,
    notes = 'Segunda parada de la ruta demo.'
where name = 'Parada 2';
