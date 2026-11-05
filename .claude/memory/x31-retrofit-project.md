---
name: x31-retrofit-project
description: "Proyecto en curso del usuario — retrofit del IBM ThinkPad X31 reemplazando el planar por una placa moderna, conservando teclado/batería/carcasa originales"
metadata: 
  node_type: memory
  type: project
  originSessionId: 4d8c83da-2e0d-4e2c-8845-7edaa1a8b933
  modified: 2026-09-02T20:43:25.821Z
---

El usuario está evaluando reemplazar el planar (mainboard) del IBM ThinkPad X31 por una
placa moderna, conservando la carcasa. Prioridades explícitas del usuario (2026-09-02):
pantalla y batería son flexibles (acepta DIY/reemplazo), pero el **teclado debe ser
exactamente el original** por autenticidad, con dos restricciones duras: no modificar el
conector del teclado de forma irreversible, y resolver el mapeo de teclas. La batería
también se busca mantener "lo más auténtica posible" aunque acepta re-celdar.

Investigación completa (esquemático + boardview + research externo) volcada en
`/home/dante/Desktop/dante/x31/retrofit_investigacion.md`. Hallazgos clave:
- Teclado: conector J1 = JAE KX14 series (board-to-board, 40 pos, 0.8mm pitch, no ZIF) →
  se puede adaptar sin tocar el original con la contraparte macho/hembra de la familia
  KX14. Matriz 16×8 (DRV/SENSE) escaneada directo por el EC — no hay protocolo serie en
  el teclado, cualquier MCU puede escanearla. El mapeo tecla física↔matriz NO existe en
  ninguna documentación pública, hay que reconstruirlo a mano con multímetro (método
  estándar en la comunidad deskthority/thinkpads forum).
- TrackPoint: habla PS/2 (clock+data) directo al EC, sin chip conversor propio — hay
  precedentes documentados (proyecto ThinkPad 380ED en Hackaday.io) de emularlo con un
  microcontrolador.
- Batería: pack SBS/SMBus real (6 celdas Li-Ion, 10.8V, 4.4Ah, 3S2P), la "inteligencia"
  vive en el pack, no en el planar — reconstruible re-celdando manteniendo la placa
  interna con alimentación de respaldo durante el cambio (método estándar de rebuild).
  Pero para que siga funcionando como "smart battery" real, la placa de reemplazo
  necesita un cargador que hable SBS/SMBus (cualquier laptop x86 real lo tiene; un SBC
  genérico sin gestión de batería no).
- Pantalla: panel 12.1" XGA CCFL (no LED) — sí existen placas driver LVDS→VGA/HDMI en
  AliExpress/eBay para XGA 12.1" con CCFL, pero son más raras que las variantes LED-only,
  hay que buscar explícitamente "con inversor CCFL incluido".
- No existe ningún donor board moderno (tipo FrankenPad/51nb) compatible mecánicamente
  con el chasis X31 — es una generación anterior a la que cubre esa comunidad (T60/X60 en
  adelante). El camino es un SBC genérico + adaptadores a medida, no un trasplante de
  placa de otro ThinkPad.

Ver también [[x31-boardview]] si se crea, o las skills del proyecto (x31-schematics,
x31-boardview, x31-parts-research) para seguir profundizando cada punto.
