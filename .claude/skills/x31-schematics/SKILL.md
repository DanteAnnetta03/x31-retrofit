---
name: x31-schematics
description: Localiza e interpreta la documentación electrónica del IBM ThinkPad X31 (esquemáticos de PCB, diagrama de alimentación DC-DC, y el Hardware Maintenance Manual) para diagnóstico y reparación. Úsala cuando pidan diagnosticar una falla del X31 (no enciende, no carga batería, no da video, no hay audio/USB/red, se apaga solo, etc.), trazar una señal o red (ej. VCC3M, -EXTPWR), ubicar en qué hoja del esquemático está un componente por su referencia (ej. U4, C233, R950, J21), entender un riel de alimentación o secuencia de encendido, buscar el número de FRU/parte de IBM, o pidan explícitamente "ver el esquemático", "abrir la hoja N", o consultar el manual de mantenimiento (HMM). No cubre la ubicación física en la placa ni el footprint/lado del componente — para eso usa la skill x31-boardview.
---

# Documentación electrónica del IBM ThinkPad X31

Este directorio contiene la documentación ya depurada (sin duplicados, sin idiomas
redundantes, sin documentos ajenos) del planar del ThinkPad X31. Antes de buscar nada
"a ciegas" con grep en 80+ páginas, usá este mapa.

## Mapa de archivos

| Archivo | Qué es | Cuándo usarlo |
|---|---|---|
| `ibm_thinkpad_x31_tokyo-3_rev_2.00_sch.pdf` | Esquemático completo del planar **TOKYO-3 SVT**, rev **2.00** (12/jun/2003), PN 93P4047, 83 hojas | Esquemático **de referencia principal** para el X31 estándar. Úsalo por defecto. |
| `ibm_thinkpad_x31_tokyo-2_planar_w_tokyo-3_rawcard_sch.pdf` | Esquemático **TOKYO-2 PLANAR w/ TOKYO-3 RAW CARD**, rev 5.01 (27/may/2003), PN 93P3976, 83 hojas | Variante de placa (raw card TK2 con TK3). Misma plantilla/numeración de hojas que el anterior; difiere sobre todo en el códec de audio (AD1981A en vez de AD1981B) y algunos detalles de config. Consultalo si el equipo real no calza con el esquemático principal, o si el archivo de boardview referencia esta variante. |
| `ibm_thinkpad_x31_tokyo-2_power_net_diagram_rev0.1.pdf` | **1 sola hoja**: diagrama de bloques de alimentación DC-DC y power net completo (TOKYO-2 DC-DC & Power Net Diagram, Rev 0.1, 2002MAY23) | Vista rápida de **todos los rieles** (VCC5B, VCC3M, VCC1R8M, etc.), sus corrientes máximas, y qué IC los genera. Es el mejor punto de partida para cualquier falla de alimentación/carga/encendido antes de ir al esquemático hoja por hoja. |
| `THINKPAD-X30_-X31.pdf` | Hardware Maintenance Manual oficial IBM (inglés), cubre X30/X31 MT 2672/2673, 176 páginas | Desarme/rearme, Symptom-to-FRU index, checkout guide, ubicación de conectores, **lista de FRUs con número de parte**. |
| `obsoleto/...rev_1.01...pdf` | Esquemático TOKYO-3 **rev 1.01** (15/abr/2003), revisión **anterior y superada** por la 2.00 | **No usar** como fuente de verdad salvo que se pida explícitamente comparar el historial de cambios entre revisiones. Si se usa, avisar siempre que es una revisión obsoleta y que los valores pueden no coincidir con la 2.00. |

## Índice de hojas (aplica a ambos esquemáticos de 83 páginas)

Los dos esquemáticos completos comparten la misma plantilla de 83 hojas — el índice de
la página 1 (`pdftotext -f 1 -l 1 -layout <archivo>`) siempre es este:

```
 1. TITLE PAGE                    41. CDC CONNECTOR(BMDC)
 2. EC HISTORY                    42. PCI BUS SWITCH(1/2)
 3. CONFIG MATRIX                 43. PCI BUS SWITCH(2/2)
 4. CPU:BANIAS (1/3)              44. DOCKING CONNECTOR
 5. CPU:BANIAS (2/3)              45. AUDIO:AD1981B  (AD1981A en el esq. TK2 w/TK3RC)
 6. CPU:BANIAS (3/3)              46. AUDIO:INT MIC
 7. CPU:ITP                       47. AUDIO:HP/LINE-IN CONN
 8. CPU:DECAP(VCCCPUCORE)         48. AUDIO:EXT MIC
 9. NORTH:ODEM(1/4)               49. AUDIO MISC(1/2)
10. NORTH:ODEM(2/4)               50. AUDIO MISC(2/2)
11. NORTH:ODEM(3/4)               51. AUDIO:BA7787
12. NORTH:ODEM(4/4)               52. LPC:FWH&RTC BATTERY
13. MEMORY:DUAL DDR DIMM          53. LPC:H8S/2169A
14. MEMORY:TERMINATION            54. LPC:MISC GA(PMH-4)
15. MEMORY:DECOUPLING             55. LPC:PC87392
16. MEMORY:RESERVE                56. HDD CONNECTOR
17. CLOCK GENERATOR:CK-408        57. USB CONNECTOR
18. GFX:RAGE M9(1/6)              58. USB POWER
19. GFX:RAGE M9(2/6)              59. KEYBOARD
20. GFX:RAGE M9(3/6)              60. SERIAL DRIVER
21. GFX:RAGE M9(4/6)              61. PARALLEL CONNECTOR
22. GFX:RAGE M9(5/6)              62. SUBCARD CONNECTOR
23. GFX:RAGE M9(6/6)              63. FAN CONNECTOR AND LED / GND PTH
24. GFX:CLK MODULATOR             64. INTENTIONAL BLANK
25. GFX:EXT CRT CONNECTOR         65. POWER ON LOGIC
26. GFX:LCD CONNECTOR             66. SLICE SUPPORT
27. GFX:RESERVE                   67. THERMAL SENSOR
28. SOUTH:ICH4(1/3)               68. I2CBUS/SMBUS
29. SOUTH:ICH4(2/3)               69. DCDC:DC-IN AND CHARGER
30. SOUTH:ICH4(3/3)               70. DCDC:CHARGER SELECT
31. CARDBUS:R5C554(1/2)           71. DCDC:BATTERY INPUT
32. CARDBUS:R5C554(2/2)           72. DCDC:BATTERY MONITOR
33. CARDBUS:POWER CONTROL         73. DCDC:POWER SEQUENCE
34. CARDBUS:PCMCIA SLOT           74. DCDC:VCC3M/5M
35. CARDBUS:COMPACT FLASH         75. DCDC:VCCCPUCORE
36. ETHERNET:GIGABIT(1/2)         76. DCDC:VCC1R2M & VCCCPUIO
37. ETHERNET:GIGABIT(2/2)         77. DCDC:VCC2R5A & VCC1R25B
38. ETHERNET:MAGNETICS            78. DCDC:VCC1R8M & VCCVIDEOCORE
39. ETHERNET:RJ11/45 CONN         79. DCDC:VCC1R5M/A/B/AUX
40. MINIPCI CONNECTOR             80. DCDC:TSURUMAI
                                   81. DCDC:VCC FOR GIGABIT ETHER
                                   82. DCDC:LOAD SW
                                   83. DCDC:MAX POWER CONTROL
```

⚠️ El número de hoja **es literalmente el número de página del PDF** (hoja 1 = página 1
del archivo). No hace falta recalcular offsets.

## Rieles de alimentación (del power net diagram, 1 página)

Referencia rápida — IC que genera cada riel, y a qué alimenta:

| Riel | Genera | Alimenta | Notas |
|---|---|---|---|
| VCC5M / VCC3M | MAX1631AEAI | Lógica general 5V/3.3V | 5.0V/4.0A y 3.3V/3.5A |
| VCC2R5A / VCC1R25B | MAX1845EEI | Norte/DDR | 2.5V/7.8A, 1.25V/2.4A |
| VCCCPUCORE | ADP3205 | Núcleo CPU (Banias/Dothan) | 1.436V nominal (VID), 24A |
| VCC1R2M / VCCCPUIO | MAX1845EEI | CPU I/O | 1.2V/2A, 1.05V/2.4A |
| VCC1R8M / VCCVIDEOCORE | MAX1845EEI | GPU Rage M9 | 1.8V/3A, 1.5V(M7)/3A |
| VCC1R8B_PLL | MAX8873TEUK (LDO desde VCC3B) | PLL | |
| MICVCC | LP3985IM5-4.7 (LDO) | Micrófono | |
| VCCCOREAUX/VCC1R8M/VCCGBEIOAUX | MAX1818EUT25 (LDO 2.5V) | Gigabit Ethernet | bloque "for Gigabit Rther" |
| Carga de batería | ADP3806-12.5 | Li-Ion 12.6V/2.6A con trickle | BAT_CRG, M_TRCL, S_TRCL |

Para trazar una falla de "no enciende/no carga": abrí primero el power net diagram
completo (es 1 sola página, se puede renderizar entera con `pdftoppm -png -r 150`), y
después saltá a la hoja DCDC correspondiente (69-83) en el esquemático completo para el
detalle de componentes.

## Manual de mantenimiento (THINKPAD-X30_-X31.pdf) — secciones clave

- Symptom-to-FRU index (poco después de "FRU tests")
- Removing and replacing a FRU — pág. 70
- Locations, vista frontal/trasera/inferior **para X31** (no la de X30) — pág. 141-143
- Parts list / X30-X31 model matrix — pág. 146
- LCD FRUs — pág. 157, Keyboard — pág. 159, Miscellaneous parts — pág. 164, Optional FRUs — pág. 166

## Cómo trabajar con estos PDFs desde la terminal

```bash
# Extraer texto de una hoja puntual (ej. hoja 74, DCDC:VCC3M/5M)
pdftotext -f 74 -l 74 -layout ibm_thinkpad_x31_tokyo-3_rev_2.00_sch.pdf -

# Buscar una red/señal en todo el esquemático (te da la hoja donde aparece)
pdftotext -layout ibm_thinkpad_x31_tokyo-3_rev_2.00_sch.pdf - | grep -n "VCC1R8M"

# Renderizar una hoja a imagen para inspección visual (mucho más legible que el texto)
pdftoppm -png -r 150 -f 74 -l 74 ibm_thinkpad_x31_tokyo-3_rev_2.00_sch.pdf /tmp/hoja74
# luego leer /tmp/hoja74-74.png con la herramienta de lectura de imágenes
```

## Reglas de consistencia (no negociables)

1. **Nunca mezclar valores** entre el esquemático vigente (rev 2.00 / TK2 w/TK3RC 5.01)
   y el archivado en `obsoleto/` sin decirlo explícitamente.
2. Si un dato del esquemático no coincide con lo que se ve en la placa real, **no asumir
   cuál tiene razón** — señalar la discrepancia y sugerir verificar con multímetro/EC
   number de la placa antes de dar un diagnóstico como definitivo.
3. Para ubicar un componente **físicamente en la placa** (lado top/bottom, footprint,
   coordenadas) no alcanza con el esquemático — usar la skill `x31-boardview`, que cruza
   cada referencia con su hoja de esquemático automáticamente.
4. Para reemplazos/compatibilidad de componentes (datasheet, precio, proveedor) usar la
   skill `x31-parts-research`.
