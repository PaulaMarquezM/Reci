# B1 — Batería manual de 20 objetos

Validación física con cámara real, definida en el [roadmap del README](../README.md#roadmap--demo-funcional-semana-pao-2026).
Meta: **≥ 18/20 correctos**.

Los 20 objetos están elegidos a propósito para golpear los puntos débiles conocidos
de vidrio-vs-plástico (ver diagnóstico en el hilo de trabajo): brillo especular
ambiguo, botellas PET de color oscuro que parecen vidrio, y el mismo producto
(Gatorade) existiendo en ambos materiales.

---

## Cómo correr la batería

```bash
python3 scripts/bateria_b1.py
```

El script usa la cámara real (`vision/camera.py`, con triple captura + voto
mayoritario de A5) y para cada objeto de la lista:

1. Pide que coloques el objeto indicado y presiones ENTER.
2. Clasifica con el flujo híbrido completo (TM → API → SE).
3. Te pregunta si el resultado fue correcto.
4. Si fue incorrecto, pide la causa (ver columna **Causa** abajo) para que quede
   registrada — no basta con saber que falló, hay que saber en qué capa.
5. Al final guarda un resumen en `docs/bateria_b1/resultados_<timestamp>.csv`
   y en `docs/bateria_b1/resultados_<timestamp>.md`, y muestra el score total.

`docs/bateria_b1/` **sí se versiona** (a diferencia de `logs/` e `images/capturas/`,
que están en `.gitignore`) para poder comparar el progreso entre sesiones de
validación a lo largo de la semana.

Requiere cámara conectada y `.env` configurado (`VISION_API`, API key). Si la
API falla, el flujo cae automáticamente a TM + heurísticas OpenCV — el script
igual registra el resultado y la causa "fallback" queda visible en el log de
`logs/clasificaciones.jsonl`.

---

## Causas de fallo (para anotar en cada objeto que falle)

| Causa | Significa |
|-------|-----------|
| `captura` | Foto mal encuadrada, objeto fuera de foco, luz muy pobre/con contraluz |
| `api` | Claude/Gemini describió mal un atributo (ej. dijo transparente algo opaco) |
| `opencv` | `refinar_atributos_api` cambió un atributo correcto a uno incorrecto (flip indebido) |
| `se` | El sistema experto concluyó mal a partir de atributos ya correctos (bug de reglas) |
| `umbral` | CF quedó justo debajo del umbral de apertura y rechazó un caso válido |
| `voto` | El voto mayoritario de las 3 fotos dio DESCONOCIDO por inconsistencia entre tomas |

Esta clasificación de causa es la que decide qué tocar después en B2 (ajuste
fino): si la mayoría de fallos son `captura`, el problema es el setup físico
(C1), no el código. Si son `api`/`opencv`, hay que revisar el prompt o
`visual_heuristics.py`. Si son `se`, hay que revisar `knowledge_base.py`.

---

## Lista de 20 objetos

| # | Objeto | Esperado | Por qué está en la lista |
|---|--------|----------|---------------------------|
| 1 | Botella de agua PET transparente (Manantial/Dasani) | PLASTICO | Caso base — debe ser trivial |
| 2 | Botella de gaseosa PET (Coca-Cola/Sprite) | PLASTICO | Caso base con etiqueta de color |
| 3 | Botella Fioravanti (PET ámbar/marrón oscuro) | PLASTICO | Color oscuro de PET que suele confundirse con vidrio |
| 4 | Vaso plástico transparente desechable | PLASTICO | Brillo difuso vs. vidrio nítido — sin cuello de botella |
| 5 | Vaso plástico blanco de cafetería (café/chocolate) | PLASTICO | Ya documentado como confusión con vaso_carton |
| 6 | Funda plástica transparente | PLASTICO | Forma irregular, sin tapa — no debe caer a DESCONOCIDO |
| 7 | Botella Gatorade PET (tapa rosca plástica gruesa) | PLASTICO | Mismo producto que el #14 en vidrio — decide el material, no la marca |
| 8 | Envase de yogur plástico blanco opaco | PLASTICO | Sin transparencia — no debe confundirse con frasco de vidrio blanco |
| 9 | Botella de cerveza de vidrio ámbar (Pilsener) | VIDRIO | Caso base de vidrio |
| 10 | Botella de cerveza de vidrio verde (Club) | VIDRIO | Color verde — probar la señal `green_ratio` |
| 11 | Frasco de vidrio transparente (mermelada/conserva) | VIDRIO | Tapa ancha metálica, no rosca — vidrio transparente puro |
| 12 | Botella de vidrio Mocachino (café frío) | VIDRIO | Caso ya parcheado en KB (R01_B) — confirmar que sigue funcionando |
| 13 | Botella Pony Malta (vidrio ámbar, tapa twist-off) | VIDRIO | Similar a cerveza pero producto distinto — no debe decidir por marca |
| 14 | Botella Gatorade de VIDRIO (473 ml, tapa metálica de color) | VIDRIO | El caso más difícil: mismo producto que #7, solo cambia el material. **Falló en vivo el 20/jul/2026** (`images/prueba17.jpeg`, Gatorade Perform 473ml): TM 99.8% "plastico" y Claude Sonnet también leyó `tapa: rosca_plastico` — ninguna de las dos capas de visión distinguió el material en una foto nítida y bien iluminada. Corregido manualmente con V, fotos guardadas en `fotos_dataset/vidrio/` para reentrenamiento. Ver `logs/correcciones.jsonl`. |
| 15 | Vaso de vidrio / tumbler reutilizable | VIDRIO | Sin cuello de botella — probar que no se confunda con vaso plástico |
| 16 | Botella de vidrio con condensación (recién sacada de nevera/hielo) | VIDRIO | El vaho apaga el brillo especular — es la prueba de estrés real para la señal principal de "vidrio" |
| 17 | Lata de aluminio (Coca-Cola/Red Bull) | LATA (rechazo) | Confusión histórica con botella_gaseosa (ver commit 61a623c) |
| 18 | Papel / servilleta | ORGANICO (rechazo) | No debe caer en PLASTICO por textura lisa brillante |
| 19 | Tetra Pak (Del Valle / Sunny jugo) | ORGANICO (rechazo) | Cartón rectangular — no es vidrio ni plástico aunque tenga tapa de rosca |
| 20 | Cáscara de fruta o resto de comida | ORGANICO (rechazo) | Caso base de residuo orgánico |

**Distribución:** 8 PLASTICO · 8 VIDRIO · 4 rechazo (LATA/ORGANICO) — deliberadamente
cargada hacia vidrio/plástico porque es el eje de la demo. Los pares 7↔14
(Gatorade) y 9↔10 (color de vidrio) son los que más valor dan: si esos dos
fallan, el problema está confirmado en la capa de visión, no en el sistema
experto (que ya tiene reglas dedicadas para ambos, ver `R19_M`–`R19_N` y
`MR16`).

---

## Después de correr B1

1. Si el score es **≥ 18/20**: pasar a B2 (ajuste fino, solo de lo que falló).
2. Si el score es **< 18/20**: revisar `docs/bateria_b1/resultados_<timestamp>.md`,
   agrupar los fallos por columna **Causa**, y atacar primero la causa con más
   fallos.
3. Guardar las fotos de los objetos que fallaron (el script ya las deja en
   `images/capturas/`) para alimentar `RECI_entrenar_automatico.ipynb` si la
   causa fue del modelo TM.
