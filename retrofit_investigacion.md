# Retrofit del planar IBM ThinkPad X31 — investigación de plausibilidad

Fecha: 2026-09-02. Basado en `ibm_thinkpad_x31_tokyo-3_rev_2.00_sch.pdf` (hojas 26, 59,
68, 71, 72), `IBM X31 Boardview/Tokyo2 Dv.LST` y `THINKPAD-X30_-X31.pdf` (HMM).

Objetivo del proyecto: reemplazar el planar Tokyo-2/Tokyo-3 por una placa moderna,
conservando carcasa, teclado original (con su conector intacto), pantalla (bezel/chasis)
y — en la medida de lo posible — la batería original.

## 1. Pantalla (LCD)

- Panel: **12.1" XGA (1024×768), TFT, 16M colores, backlight CCFL** (confirmado en HMM,
  sección "Product overview" y "LCD FRUs"). No hay part number de panel específico en la
  documentación — hay que leerlo de la etiqueta física en la parte trasera del panel
  (candidatos típicos de la época: Toshiba LTM12C275, Samsung LTN121XJ, LG.Philips
  LP121X08, Hydis, Sharp — no asumir cuál sin ver la etiqueta).
- Conector en el planar: **J9**, P/N IBM `61P6347`, footprint `917852_3`, **50 pines**,
  lado top, hoja 26 del esquemático. No es sólo LVDS: por el mismo conector/cable pasan
  también las antenas WiFi (`WIRELESS_GRNP/GRNN`), señales de LEDs de estado en la tapa
  (`-LEDSUS`, `-LEDFUEL0/1`), un botón/LED de la tapa (`-BDC_PWRBTN`, `BDC_LED`), el ID
  del panel (`-LCDID0/1`) y el control/alimentación del inversor CCFL (`VBL16`,
  `VBL_DRV`, `BACKLIGHT_ON`) — es decir, es un cable "combo" LCD+antena+LEDs, no un LVDS
  puro. Esto es irrelevante si se reemplaza el driver del panel (no se va a reusar J9),
  pero si se preservan antenas/LEDs de la tapa hay que rutearlos aparte.
- LVDS: single-channel, 3 pares de datos (`TXOUT_L0/L1/L2 P/N`) + 1 par de clock
  (`TXCLK_LP/LN`) → tal cual un panel XGA 6-bit típico de la época.
- **Plausibilidad: alta.** El supuesto del usuario es correcto: existen placas
  controladoras "universales" LVDS→VGA/HDMI/(algunas) USB-C en AliExpress/eBay que
  todavía cubren específicamente paneles XGA 12.1" **con CCFL** (ej. kits para
  HT12X12-100, LT121SU, familias LTN133/B133 con opción "1CCFL"). El punto crítico NO es
  encontrar el driver — es que:
  1. La mayoría de las placas "universales" modernas asumen backlight **LED**, no CCFL.
     Hay que buscar específicamente el modelo que declare **inversor CCFL incluido**
     (son menos, pero existen — ver listados de referencia más abajo).
  2. Confirmar el pinout exacto del conector propio del panel (no el de J9) leyendo la
     etiqueta del panel o contactando al vendedor del kit con ese part number.
  3. Encaje mecánico del driver board + inversor dentro de la tapa (espacio detrás del
     bezel) — hay que medir.

## 2. Teclado

- Conector: **J1**, P/N IBM `04N7715`, footprint `KX14_40K5D1` (**JAE KX14 series**,
  conector board-to-board de 0.8mm pitch, 40 posiciones), altura de stack **H=5.4mm**,
  lado top, hoja 59. Al ser una familia **board-to-board tipo plug/socket** (no un ZIF de
  presión sobre FPC desnudo), **es no-destructivo por diseño**: se puede fabricar un
  adaptador que usa el conector macho/hembra complementario (buscar en JAE la contraparte
  de `KX14-40...`, variantes `K5D`/`K11D`/etc.) para acoplarse al conector original del
  teclado sin tocarlo ni modificarlo. Esto resuelve directamente la restricción del
  usuario ("no pienso hacer cambios irreversibles en el conector").
- Matriz: confirmada por esquemático — **16 líneas DRV<15..0> (columnas/drive) × 8 líneas
  SENSE<7..0> (filas/sense)** = hasta 128 posiciones, escaneadas directo por pines GPIO
  del EC (H8S/2169A, hoja 53). Es una matriz resistiva pasiva pura — **no hay chip en el
  teclado que hable un protocolo serie** (a diferencia de teclados USB modernos). Esto es
  bueno: cualquier microcontrolador (Teensy, Pi Pico, ATmega/AVR con QMK/TMK/ZMK, etc.)
  puede escanear la matriz directamente sin necesitar imitar un protocolo propietario.
  Mapeo pin→bit DRV/SENSE está en la hoja 59 (asignación física de J1 pin 1-40 a cada
  índice).
  - **Lo que NO está en ningún esquemático ni documentación pública**: qué tecla física
    cae en cada intersección DRV×SENSE (eso vive en la membrana del teclado mismo, no en
    el planar). Confirmado por búsqueda: no hay schematics públicos de teclados
    ThinkPad — la comunidad (deskthority, thinkpads forum) siempre reconstruye esta tabla
    a mano por continuidad (multímetro en modo diodo, tecla por tecla, sobre los 40 pines
    del conector). Para ~85-87 teclas reales sobre 128 posiciones posibles es un trabajo
    de un par de horas, tedioso pero totalmente factible y bien documentado como método
    (ver hilo "Rebuilding and Redesigning a Classic Thinkpad Keyboard" en deskthority).
  - Señales extra en el mismo conector J1: `-HOTKEY`, `-PWRSWITCH` (botón de power),
    `KBDID0/1/2` (ID de layout/idioma del teclado, 3 bits), y **`IPDCLK`/`IPDDATA`** =
    interfaz del TrackPoint.
- TrackPoint: confirmado que el X31 **no tiene chip conversor en el teclado** — el EC
  habla directo un protocolo tipo **PS/2 (clock+data, 2 hilos)** con el controlador del
  TrackPoint (`IPDDATA`/`IPDCLK` van directo a hoja 53, el H8S). Esto es exactamente el
  mismo caso que proyectos ya documentados (ej. "IBM Thinkpad 380ED Keyboard/Trackpoint
  to USB" en Hackaday.io): un microcontrolador puede emular el lado host de PS/2 para el
  TrackPoint (librerías PS/2 para QMK/TMK/Arduino ya existen) totalmente separado del
  escaneo de matriz del teclado.
- **Plausibilidad: alta**, con trabajo manual de reverse-engineering de la matriz física
  como único paso no trivial (pero bien acotado y sin ambigüedad de método).

## 3. Batería

- Conector: **J18**, P/N IBM `61P6349`, footprint `1565548_1`, **10 pines**, H=6.05mm
  (conector tipo header/wafer, no FPC), lado top, hoja 71.
- Pack original: **Li-Ion 6 celdas, 10.8V nominal, 4.4 Ah** (HMM: "6-cell Li-Ion battery
  pack (4.4 AH)"; el checkout guide del HMM valida "menos de +11.0V ⇒ reemplazar" lo que
  confirma ~10.8V nominal de un 3S2P). FRUs de fábrica: Panasonic `08K8039` / Sanyo
  `08K8040`.
- Protocolo: **SMBus real, System Management Bus / Smart Battery System (SBS)**
  confirmado en hoja 71 (`I2C_CLK_BT0`/`I2C_DATA_BT0`) y hoja 68 (el EC, H8S, es el
  master SMBus vía un mux `PI3B3253`; hay un segundo canal `BT1` para una batería de bahía
  que en el X31 **no está poblado** — `NO_ASM` en varios pasivos de esa rama, es
  compartido con otro modelo Tokyo-3 que sí tenía bahía). Además del bus digital hay un
  **termistor analógico dedicado** (`M_TEMP`) y un **divisor resistivo de voltaje directo**
  a un ADC del EC (hoja 72, fórmula `VOUT = 0.264×(VBAT−5)`) como respaldo/seguridad fuera
  de banda del SMBus — típico de diseño ThinkPad de esa época.
- Esto significa: **la "inteligencia" vive dentro del pack removible**, no en el planar.
  El planar sólo es un master SMBus + monitor analógico de respaldo. Es el escenario
  ideal para preservar autenticidad:
  1. Abrir el shell original, reemplazar las celdas 18650 (o el formato que tenga,
     verificar físicamente) manteniendo la config 3S2P, **sin desconectar nunca la placa
     interna del pack de una fuente de energía** (alimentar con una fuente auxiliar de
     respaldo vía resistor durante el cambio de celdas) para no perder la calibración del
     fuel gauge — es el método estándar documentado (Battery University BU-911,
     hackspherelabs wiki "Laptop Battery Rebuild").
  2. Si la placa interna del pack sigue viva, se puede re-celdar conservándola tal cual
     (mejor opción de autenticidad). Si está muerta, reemplazar por una placa BMS/fuel
     gauge SMBus genérica compatible (bq2060 y clones/equivalentes siguen circulando en
     el mercado de rebuild de baterías) reprogramada con los parámetros correctos
     (capacidad, código de fabricante) — existe un ecosistema entero de foros/negocios de
     "chip reset" de baterías laptop (laptopu.ro, elektroda) para esto.
  3. **El punto que decide el nivel real de autenticidad no es la batería sino la placa
     nueva**: para que el pack siga reportando como "smart battery" real, la placa
     madre de reemplazo tiene que tener un cargador que espere un SBS real por SMBus (lo
     cual es el comportamiento normal de CUALQUIER laptop x86 moderno con batería
     Smart — así que si el reemplazo es una placa de laptop real o un diseño con un IC
     cargador tipo bq24725/bq25xxx, funciona de fábrica). Si el reemplazo es un SBC
     genérico sin gestión de batería nativa (ej. una placa pensada para alimentarse sólo
     por DC-in), se pierde la parte "smart" y el pack original queda reducido a ser sólo
     una carcasa con celdas — sigue teniendo sentido por estética/peso, pero ya no es
     "auténtico" en función.

## 4. La placa madre en sí (dimensión no preguntada explícitamente, pero crítica)

- El planar original mide, según cabecera del boardview (`$A30 = 9000 4000` mils), **~228.6
  × 101.6 mm** de huella — angosto y alargado, típico de un ultraportátil de 2003. No hay
  en el boardview un layer de mounting holes explícito para tornillos (no decodificado),
  así que la huella exacta de anclaje hay que sacarla midiendo el planar real o el HMM
  (sección de desarme).
- **No existe ningún "donor board" moderno pensado para esta carcasa.** La comunidad
  FrankenPad (foro thinkpads.com, 51nb.com) sí tiene un ecosistema maduro de trasplantes
  de placas — pero está anclado a la generación **T60/T61/X60/X61/X200/X201** en
  adelante (chasis 4:3 de 14"/15" o el "clásico teclado de 7 filas" compartido entre esos
  modelos, y ahora las placas custom X210/X2100/X210Ai de 51nb). El X31 es una generación
  entera anterior y de un chasis más chico/angosto: **no hay compatibilidad mecánica
  directa con ningún donor board conocido**. Esto no mata el proyecto, pero cambia la
  naturaleza: no es "meter una placa de otro ThinkPad", es **diseñar/adaptar un SBC
  genérico** (tipo LattePanda, UP board, Raspberry Pi CM4 + carrier custom, o un mini-PC
  N100 desarmado) y resolver a medida cada interfaz (teclado, trackpoint, pantalla,
  batería, USB, red) con adaptadores propios — mucho más parecido a los proyectos
  "vintage laptop + mini-ITX/SBC" documentados en la escena maker que a un FrankenPad
  clásico.
- Restricción física más dura de verificar: **la altura disponible** (grosor entre la
  base inferior y el plano del teclado) en un ultraportátil de 2003 suele ser muy ajustada
  (varios mm, no cm) — hay que medirla en el equipo real antes de elegir SBC candidato;
  la mayoría de SBCs x86 "pequeños" (LattePanda, UP) tienen más altura de componentes
  (conectores, disipador) de la que suele haber libre bajo el teclado de un X31.

## Referencias externas citadas

- FrankenPad / 51nb: https://forum.thinkpads.com/viewtopic.php?t=119588 ,
  https://hackaday.com/2021/11/27/replacement-motherboard-brings-new-lease-of-life-to-classic-thinkpads/ ,
  https://forum.thinkpads.com/viewtopic.php?t=125094
- Teclado/TrackPoint a USB: https://hackaday.io/project/171439-ibm-thinkpad-380ed-keyboardtrackpoint-to-usb ,
  https://github.com/JohSchneider/ps2trackpoint-attiny85-vusb ,
  https://deskthority.net/viewtopic.php?t=6181
- Rebuild de batería SBS: https://batteryuniversity.com/index.php/learn/article/how_to_repair_a_laptop_battery ,
  https://wiki.hackspherelabs.com/index.php?title=Laptop_Battery_Rebuild ,
  https://www.laptopu.ro/community/laptop-battery-chip-reset-and-repair/bq2060a-atmlh744/
- Conector KX14 (JAE): https://www.digikey.com/en/products/detail/jae-electronics/KX14-20K2DE/1283373 ,
  https://www.jae.com/en/topics/detail/id=1711
- Driver LVDS 12.1" XGA CCFL: https://www.aliexpress.com/i/32998337953.html ,
  https://www.ebay.com/itm/133708774654
