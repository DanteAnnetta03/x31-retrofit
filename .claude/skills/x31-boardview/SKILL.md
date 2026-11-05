---
name: x31-boardview
description: Trabaja con los archivos boardview del planar del IBM ThinkPad X31, en "IBM X31 Boardview/" (Tokyo2 Dv.CST, Tokyo2 Dv.LST, CORDOBA-CASTW.EXE), para ubicar componentes físicamente en la placa real, saber en qué cara están (top/bottom), su footprint, sus coordenadas, y cruzarlos con la hoja de esquemático correspondiente. Úsala cuando pidan "dónde está X en la placa", "de qué lado está", "footprint/huella de X", "coordenadas de X", "abrir/ver el boardview", localizar un componente para reparación (retrabajo, resoldado, bodge wire), o planear una modificación física de la placa (mods, upgrades, puntos de prueba). No interpreta el contenido eléctrico del esquemático en sí — para eso usa x31-schematics.
---

# Boardview del planar IBM ThinkPad X31

Carpeta: `IBM X31 Boardview/`. Contiene tres archivos que van juntos:

| Archivo | Tipo | Rol |
|---|---|---|
| `Tokyo2 Dv.LST` | **Texto plano ASCII** | BOM + posición + orientación + **hoja de esquemático** de cada componente. Se puede grepear directo, sin ninguna herramienta especial. |
| `Tokyo2 Dv.CST` | Binario propietario | Datos gráficos del boardview (siluetas, pistas visibles) para el visor. |
| `CORDOBA-CASTW.EXE` | Ejecutable Win32 (PE32, GUI, muy antiguo — target Windows 4.00 / Win9x) | Visor que abre el `.CST` para inspección visual interactiva. |

Metadatos de cabecera del LST: `$ASM = 30L3093`, `$EC = H33439A`,
`TOKYO-2 DV PLANAR Config-4 (LOGIC VER 0.22)`. **Estos números de EC/ASM no usan el
mismo formato que el "EC NO." de los esquemáticos** (J18444 / J18095 / J18095A), así que
no se pueden comparar directo como texto — si hace falta confirmar que el boardview
corresponde exactamente a una revisión de esquemático dada, verificarlo por el número de
página cruzado (ver abajo) y avisar si algo no calza, en vez de asumir que coinciden.

## El `.LST` es la herramienta principal (no hace falta abrir el `.CST` para casi nada)

Formato de cada línea de componente (ancho fijo, ver cabecera del propio archivo con
`head -10`):

```
CODE   P/N       DESCRIPTION            PNBR  LEAD-L1(x y)  LEAD-L2(x y)  SPACE  CENTER POS(x y)  L2-ORI  COMMENT(footprint)              CDB NAME        PAGE
 U4    #CR3065   ODEM rev.A1            1     ????? ?????                       5200  4410        —       PBGA593_127_01 H=2.89           ODEM-ASM        11
```

- **CODE**: referencia (U4, C233, R950, J21, Y5, …) — la misma que en el esquemático.
- **P/N**: número de parte IBM/proveedor (o `NO_ASM` si no se instala en esa config).
- **PNBR**: cantidad de pines/terminales.
- **LEAD-L1 / LEAD-L2 / CENTER POS**: coordenadas en mils (0.001") de los pines 1 y 2 y
  del centro del componente — sirven para ubicarlo dentro del sistema de coordenadas de
  la placa y planear acceso físico (bodge wire, punta de prueba, resoldado).
- **SPACE**: separación entre pads, en mils.
- **L2 ORI (orientación)**: `T/B/R/L` = hacia dónde apunta el pin 2 visto desde la cara
  frontal (top).
- **COMMENT**: nombre del footprint (ej. `PBGA593_127_01`, `CAP1005R_AUS_02`, `QFP100_1414_500_05`) y a veces altura máxima (`H=`).
- **PAGE**: **número de hoja del esquemático** (coincide 1:1 con las hojas descritas en
  la skill `x31-schematics`) — esto es lo que permite saltar del componente físico al
  esquemático sin buscar a mano.

Cara de la placa (nota literal al final del archivo):
```
PLANE NBR 1  = COMPONENT SIDE (FRONT / TOP)
PLANE NBR 10 = SOLDER SIDE (BACK / BOTTOM)
```
El campo **PNBR** en cada línea es justamente ese "plane number" — 1 = componente montado
arriba, 10 = montado abajo. Revisalo siempre antes de decirle a alguien "date vuelta la
placa" o "es el chip de arriba".

## Recetas de uso

```bash
cd "IBM X31 Boardview"

# Ubicar un componente por referencia exacta (ojo con los espacios: el campo CODE
# está alineado a la izquierda con padding, por eso el patrón "^ U4 " con espacios)
grep -n "^ U4 " "Tokyo2 Dv.LST"
grep -n "^ C233 " "Tokyo2 Dv.LST"

# Buscar por descripción o P/N cuando no se sabe la referencia
grep -in "BANIAS\|ODEM\|RAGE M9\|H8S" "Tokyo2 Dv.LST"

# Ver qué componentes caen en una hoja de esquemático dada (ej. hoja 74, DCDC:VCC3M/5M)
awk '{ if ($NF == 74) print }' "Tokyo2 Dv.LST"

# Ver la leyenda de columnas y las notas finales
head -10 "Tokyo2 Dv.LST"
tail -10 "Tokyo2 Dv.LST"
```

Después de identificar la hoja (`PAGE`), abrir esa hoja puntual en el esquemático
correspondiente (ver `x31-schematics`) para ver el contexto eléctrico completo.

## Visor gráfico del `.CST` (cuando el texto no alcanza)

`CORDOBA-CASTW.EXE` es un binario de Windows antiguo — no corre nativo en Linux. Opciones,
en orden de preferencia:

1. **Wine**: `wine "CORDOBA-CASTW.EXE"` desde la carpeta del boardview (necesita el
   `.CST` en el mismo directorio). Al ser software de la era Win9x/2000, si falla probar
   `winecfg` y forzar versión de Windows más vieja (Windows 98 o 2000) antes de reintentar.
2. Si Wine no está disponible o el visor no abre en este entorno, **no asumir** que el
   `.CST` es compatible con visores modernos tipo OpenBoardView (su formato binario no
   está confirmado como uno de los que soporta) — probarlo es válido, pero si falla,
   decirlo explícitamente en vez de reportar datos inventados. En la gran mayoría de los
   casos el `.LST` en texto plano ya alcanza para ubicar y cruzar componentes; recurrir al
   `.CST` sólo cuando hace falta ver trazas/serigrafía real que el texto no describe.

## Visualización interactiva local (`board_viewer.html`)

Ya existe un visor propio, generado a partir del `.LST` **y del `.CST`**, que reemplaza lo
que antes requería el `.exe`: `IBM X31 Boardview/board_viewer.html`. Es un archivo **HTML
autocontenido y 100% local** (no se publica nada — la documentación está marcada IBM
CONFIDENTIAL) con pan/zoom (librería `svg-pan-zoom` vía CDN), estilo tipo PCB real
(colores por categoría de componente, contorno de placa, pistas de cobre reales) y
resaltado de componentes.

Se regenera con:

```bash
python3 tools/lst_to_board_viewer.py
```

Hace falta si cambia el `.LST` o el `.CST` — si no, el HTML ya generado sirve tal cual.

**Cómo usarlo cuando te pidan ubicar un componente puntual**: no hay que regenerar nada.
El visor lee el parámetro `find` de la URL y resalta directo al cargar — decile al
usuario que abra (o refresque) esa URL, con `file://` directo o desde el Simple Browser
de VSCode:

```
file:///home/dante/Desktop/dante/x31/IBM X31 Boardview/board_viewer.html?find=U4
file:///home/dante/Desktop/dante/x31/IBM X31 Boardview/board_viewer.html?find=U2,U4,C233
```

Esto centra la vista, dibuja un recuadro ajustado al tamaño/posición real del componente
con una flecha, y muestra en el panel lateral su P/N, footprint, cara (top/bottom), la
**hoja de esquemático** correspondiente (para abrirla con `x31-schematics`), y sus **pines
reales con la red (net) de cada uno** si están disponibles. También se puede buscar a mano
en el campo de texto del visor.

### El `.CST` fue reverseado a fondo — no es sólo la tabla de posiciones

El binario tiene 5 secciones marcadas con tags de 4 letras (`CDev`, `CVia`, `CPad`,
`CLin`, `CSha`), confirmados contra los strings del propio `CORDOBA-CASTW.EXE`
("reading DEVICE/PAD/LINE/SHAPE data"). Decodificadas y en uso, todas validadas por
regresión contra las coordenadas reales del `.LST` (no es una interpretación a ojo):

- **`CDev`** (posición de componentes) — cruce de verificación: cada componente queda
  marcado `✓ coincide`, `⚠ discrepancia` (pasó en 20 de 2239 casos reales — se dibujan con
  **borde rojo**, y el panel de detalle muestra la posición alternativa) o `sin registro`.
  Ante una discrepancia, no asumir cuál archivo tiene razón — avisar y, si hace falta,
  confirmar con multímetro sobre la placa real.
- **`CPad`** (posición real de cada pin + su red/net) — reemplaza la caja heurística por
  cantidad de pines por la nube de pines real cuando hay 3+ pines asignados a un
  componente (pasa en los BGA/QFP grandes: ODEM, BANIAS, RAGE M9, etc. — 22 de 24 cajas
  que antes eran aproximadas ahora son geometría real). Cada pin muestra su red al pasar
  el mouse.
- **`CLin`** (segmentos de pista de cobre reales, ~84.600) — se dibujan como pistas de
  cobre de verdad entre componentes, no decoración. **Limitación real: no se distingue
  capa** (top/bottom copper) — todas las pistas se superponen en el dibujo aunque estén en
  capas físicas distintas, así que no asumir que dos pistas que se cruzan visualmente
  están conectadas entre sí.
- `CVia` y `CSha` (vías y librería de formas de pad) — **no decodificadas**, quedaron
  fuera de alcance. No asumir que hay datos de vías o de forma exacta de pad disponibles.

No hace falta el `.exe` ni Wine para nada de esto — se probó levantar
`CORDOBA-CASTW.EXE` con Wine en esta máquina (Wine 11.15 sí está instalado) y arranca,
pero la sesión gráfica es Wayland: no hay forma confiable de automatizar/capturar esa
ventana desde acá, así que quedó descartado como parte del flujo interactivo. Si en algún
momento hace falta cotejar visualmente contra la serigrafía real, se puede lanzar
manualmente (`wine "CORDOBA-CASTW.EXE"` desde la carpeta del boardview) — es un paso
manual del usuario, no algo que se pueda disparar automáticamente desde acá.

## Para modificaciones de PCB (mods/upgrades)

No hay gerbers ni stack-up de capas reales (cuántas capas de cobre tiene el planar, en qué
orden) — eso sigue sin estar disponible. Lo que sí hay ahora es posición real de pines,
su red, y trazado real de pistas (sin separar por capa), que ya alcanza para evaluar con
mucha más confianza si hay lugar para un bodge wire sin puentear algo. Cualquier
modificación física sigue planteándose a nivel de **bodge wire / rework**, nunca como
rediseño de capas internas. Antes de proponer un mod:

1. Confirmar en el esquemático (`x31-schematics`) la red exacta a modificar/interceptar.
2. Ubicar el componente/pad en el visor (cara, footprint, pines reales y su red) para
   evaluar si hay lugar físico para soldar sin puentear pads o pistas vecinas — recordando
   que el dibujo de pistas no distingue capa, así que una pista que "pasa cerca" en el
   dibujo puede estar en otra capa físicamente inaccesible desde ese lado.
3. Si el mod implica un componente nuevo (ej. adaptador mSATA/CF, módulo WiFi), pasar a
   la skill `x31-parts-research` para validar pinout/voltajes reales antes de comprar nada.
