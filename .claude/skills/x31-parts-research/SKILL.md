---
name: x31-parts-research
description: Investiga componentes de hardware para reparar o modificar/mejorar el IBM ThinkPad X31 — busca datasheets, especificaciones, pinout/footprint, reemplazos o equivalentes compatibles, y dónde conseguirlos (proveedores, precio, disponibilidad/stock). Úsala cuando pidan buscar un reemplazo o equivalente de un componente, el datasheet de un IC, dónde comprar una pieza, precio o stock de algo, evaluar si un componente moderno es compatible con el X31 (ej. módulo WiFi mini-PCI, adaptador CF/mSATA, batería, pantalla LCD, RAM), o investigación de mods/upgrades en general. Combínala con x31-schematics (para confirmar la red/pinout real) y x31-boardview (para confirmar footprint/espacio físico) antes de dar una pieza por compatible.
---

# Investigación de componentes — IBM ThinkPad X31

Esta skill es para el objetivo de **investigación de mods/mejoras** y para conseguir
repuestos de reparación. Nunca afirmes una especificación, precio o compatibilidad sin
haberla buscado — si la búsqueda no da un resultado claro, decilo explícitamente en vez
de completar con un valor plausible.

## ICs clave ya identificados en la documentación (punto de partida, no reemplaza el datasheet)

De los esquemáticos y el power net diagram (ver `x31-schematics`):

| Referencia funcional | Parte | Rol |
|---|---|---|
| CPU | Intel Pentium M "Banias"/"Dothan", Socket 479 | Procesador |
| North bridge | Intel 855GME ("Odem") | Memoria DDR, AGP interno |
| South bridge | Intel ICH4-M | I/O, USB, IDE |
| GPU | ATI Mobility Radeon "Rage M9" | Video (integrado en el planar, no reemplazable suelto) |
| CardBus/SD | Ricoh R5C554 | Controlador CardBus |
| Audio codec | AD1981B (rev 2.00) / AD1981A (TK2 w/TK3RC) | Codec AC97 — **la revisión de placa importa**, no son intercambiables a ciegas |
| Ampli audio | BA7787 | |
| Embedded controller | Renesas/Hitachi H8S/2169A | Teclado, power management |
| Super I/O | PC87392 | Puerto serie/paralelo |
| DC-DC 5V/3.3V | MAX1631AEAI | |
| DC-DC ×3 (2.5V/1.25V, 1.2V/1.05V, 1.8V/1.5V) | MAX1845EEI (x3 instancias) | |
| DC-DC núcleo CPU | ADP3205 | VID de la CPU, 1.436V nominal |
| Cargador de batería | ADP3806-12.5 | Li-Ion 12.6V |
| LDO PLL | MAX8873TEUK | |
| LDO mic | LP3985IM5-4.7 | |
| LDO Gigabit Ethernet | MAX1818EUT25 | |

Antes de dar cualquiera de estos por "el componente correcto" para una reparación,
confirmá la referencia (ej. U-algo) y la hoja en el esquemático real (`x31-schematics`)
— esta tabla es un resumen, no sustituye leer la hoja.

## Método de investigación

1. **Identificar la pieza exacta** — refdes + P/N si viene del `.LST` de boardview
   (`x31-boardview`), o el nombre del IC en el esquemático (`x31-schematics`).
2. **Datasheet**: buscar `"<part number>" datasheet filetype:pdf` (WebSearch/WebFetch).
   Preferir el sitio del fabricante (Analog Devices/Maxim para ADP*/MAX*, Intel para
   chipset/CPU, Renesas para el EC) sobre reuploads de terceros.
3. **Disponibilidad y precio**: para partes electrónicas activas/discretas actuales,
   agregadores como Octopart y distribuidores como Mouser, DigiKey, LCSC dan stock y
   precio en tiempo real. Para partes IBM propietarias descontinuadas hace 20 años
   (planares, bisagras, pantallas, teclados con FRU IBM), lo realista es eBay,
   AliExpress, foros de reparación de ThinkPads clásicos (ej. Lenovo/ThinkPad
   retro-computing forums) — dejar claro cuando la única fuente es "mercado de segunda
   mano", no un distribuidor con garantía de autenticidad.
4. **Compatibilidad real, no de marketing**: un listado que diga "compatible con X31" no
   alcanza. Antes de recomendar comprar algo:
   - Voltajes y pinout deben coincidir con lo que dice el esquemático real (no con lo que
     dice el listado del vendedor).
   - Para conectores/footprints, cruzar con `x31-boardview` (huella, espacio disponible,
     cara de la placa).
   - Si hay ambigüedad entre datasheet y lo que muestra el esquemático, señalarlo — no
     resolverlo por conjetura.

## Consideraciones específicas para mods/upgrades típicos del X31 (2003, plataforma Banias/855GME)

- **WiFi**: el slot es **Mini-PCI** (no Mini-PCI Express) — los módulos WiFi modernos
  (M.2/mPCIe) no entran físicamente ni eléctricamente. Buscar módulos Mini-PCI type IIIA/B
  de época o adaptadores Mini-PCI→Mini-PCIe si se evalúa ese camino (agrega problemas de
  espacio físico, cruzar con boardview).
- **Almacenamiento**: el X31 usa IDE (PATA) de 1.8" o 2.5" según config — no SATA nativo.
  Adaptadores CF→IDE o mSATA/SD→IDE existen en el mercado; verificar el modo del
  controlador IDE (PIO/UDMA) contra el esquemático (hoja "HDD CONNECTOR", #56) antes de
  asumir compatibilidad total.
- **Pantalla/LCD**: el conector LCD del X31 es un pinout LVDS propietario de la época —
  antes de evaluar un panel "compatible", confirmar el pinout real en la hoja "GFX:LCD
  CONNECTOR" (#26) del esquemático, no fiarse de que el conector físico encastre.
- **RAM**: DDR SO-DIMM según hoja "MEMORY:DUAL DDR DIMM" (#13) — confirmar ahí la
  velocidad/voltaje soportado (probablemente DDR-266/333, no asumir JEDEC moderno).

## Formato de salida sugerido

Para cualquier pieza investigada, resumir así:

| Componente | Specs clave | Reemplazo/equivalente propuesto | Proveedor | Precio aprox. | Disponibilidad | Fuente |
|---|---|---|---|---|---|---|
| ... | ... | ... | ... | ... | ... | link |

Marcar con ⚠️ cualquier fila donde la compatibilidad no esté confirmada contra el
esquemático/boardview real, y con ❓ cualquier dato de precio/stock que no se haya podido
verificar en el momento de la búsqueda (los precios de stock cambian; no reportarlos como
definitivos sin fecha de consulta).
