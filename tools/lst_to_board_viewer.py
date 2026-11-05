#!/usr/bin/env python3
"""
Convierte "IBM X31 Boardview/Tokyo2 Dv.LST" (BOM + placement en texto plano,
ancho fijo) a un visor HTML autocontenido con pan/zoom y resaltado de
componentes por referencia (CODE), 100% local (sin publicar nada afuera).

Uso:
    python3 tools/lst_to_board_viewer.py

Genera: "IBM X31 Boardview/board_viewer.html"

No requiere librerías externas de Python. La única dependencia en el HTML
generado es la librería JS "svg-pan-zoom" cargada por CDN (cdnjs) para el
pan/zoom del SVG — si se abre sin internet, el visor igual muestra la placa,
sólo se pierde el pan/zoom con mouse (se puede agregar --offline-panzoom
más adelante si hace falta 100% sin red).
"""
import json
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LST_PATH = ROOT / "IBM X31 Boardview" / "Tokyo2 Dv.LST"
CST_PATH = ROOT / "IBM X31 Boardview" / "Tokyo2 Dv.CST"
OUT_PATH = ROOT / "IBM X31 Boardview" / "board_viewer.html"

SEPARATOR_PREFIX = "$====="

# --- Estructura del .CST, tabla de componentes (bytes 12..~37785) ---
# Reverseada y validada por regresión contra el .LST (ver investigación):
# cada registro = [1 byte largo][nombre ASCII][2 bytes X LE][2 bytes Y LE]
# [1 byte plane][2 bytes sin identificar][2 bytes reservados][2 bytes 0x0180]
CST_TABLE_START = 12
CST_TRAIL_LEN = 11

# --- Tags de sección de 4 letras encontrados en el .CST (confirmados contra
# los strings del propio CORDOBA-CASTW.EXE: "reading DEVICE/VIA/PAD/LINE/
# SHAPE data"). Cada tag marca el inicio de su sección; el fin de una sección
# es el inicio del siguiente tag (por offset), o el fin del archivo para la
# última.
SECTION_TAGS = (b"CDev", b"CVia", b"CPad", b"CLin", b"CSha")

# --- CLin: registro de 14 bytes por segmento de pista, reverseado y
# validado igual que CPad (mediana ~31 mils contra los pines reales de
# CPad, con extremos que encadenan exacto entre segmentos consecutivos de
# una misma pista). OJO: los datos de la sección empiezan con 1 byte
# huérfano (mismo patrón que el diccionario de redes) — hay que saltarlo.
#   offset 0-1  : probable índice de red (rango calza con el diccionario)
#   offset 2-3  : sin identificar (¿capa/ancho?)
#   offset 4-5  : X1 crudo (misma calibración que CDev/CPad)
#   offset 6-7  : Y1 crudo
#   offset 8-9  : X2 crudo
#   offset 10-11: Y2 crudo
#   offset 12-13: sin identificar (cierre/estado, casi constante)
CLIN_RECORD_LEN = 14
CLIN_ORPHAN_SKIP = 1

# --- CPad: registro de 16 bytes por pin, reverseado y validado por
# regresión de vecino-más-cercano contra las coordenadas de pin reales del
# .LST (mediana ~0.3 mils en componentes de 2 terminales) y por sentido
# eléctrico de las redes resueltas (ver investigación):
#   offset 0-1  : sin identificar (varía en todo el rango uint16)
#   offset 2-3  : sin identificar, acotado (¿índice de forma de pad?)
#   offset 4-5  : índice de red (SIGNAL) en el diccionario de nombres
#   offset 6-7  : X crudo (misma calibración lineal que la tabla CDev)
#   offset 8-9  : Y crudo (ídem)
#   offset 10-15: sin identificar (flags/estado, no se usan acá)
CPAD_RECORD_LEN = 16


def find_columns(lst_lines):
    """Usa la línea de '====' del propio archivo para derivar los offsets
    de cada columna (formato de ancho fijo)."""
    sep_line = next(l for l in lst_lines if l.startswith(SEPARATOR_PREFIX))
    cols = []
    i = 0
    n = len(sep_line)
    while i < n:
        if sep_line[i] == "=":
            start = i
            while i < n and sep_line[i] == "=":
                i += 1
            cols.append((start, i))
        else:
            i += 1
    return cols


FIELD_NAMES = [
    "code", "pn", "description", "plane",
    "l1x", "l1y", "l2x", "l2y", "space",
    "cx", "cy", "ori", "comment", "cdbname", "page",
]


def parse_number(s):
    s = s.strip()
    if not s or set(s) <= {"?"}:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def slice_field(line, col, pad=0):
    start, end = col
    start = max(0, start - pad)
    end = min(len(line), end + pad)
    return line[start:end].strip()


def parse_lst(path):
    raw = path.read_text(encoding="latin-1").splitlines()
    cols = find_columns(raw)
    # cols orden esperado: CODE,P/N,DESCRIPTION,NBR,LEAD-L1(x,y como 1 bloque
    # con guion pero en la práctica trae 2 numeros separados por espacio,
    # ver abajo), LEAD-L2, SPACE, CENTER POS, ORI, COMMENT, CDB NAME, PAGE
    # LEAD-L1/L2/CENTER POS en realidad ocupan 2 sub-columnas numéricas
    # (x e y) dentro del ancho declarado -> las separamos por regex numérico
    # en vez de por sub-offset, es más robusto.
    parts = []
    for line in raw:
        if not line.strip():
            continue
        if line[0] != " ":
            continue  # header/comentarios/continuaciones empiezan con $,%,*,-
        code_col, pn_col, desc_col, plane_col = cols[0], cols[1], cols[2], cols[3]
        l1_col, l2_col, space_col, center_col, ori_col = cols[4], cols[5], cols[6], cols[7], cols[8]
        comment_col, cdb_col, page_col = cols[9], cols[10], cols[11]

        code = slice_field(line, code_col)
        if not code:
            continue
        pn = slice_field(line, pn_col)
        desc = slice_field(line, desc_col)
        plane = slice_field(line, plane_col)

        def two_nums(col):
            chunk = slice_field(line, col, pad=0)
            nums = re.findall(r"-?\d+", chunk)
            if len(nums) >= 2:
                return float(nums[0]), float(nums[1])
            return None, None

        l1x, l1y = two_nums(l1_col)
        l2x, l2y = two_nums(l2_col)
        space_raw = slice_field(line, space_col, pad=0)
        space = parse_number(space_raw)
        cx, cy = two_nums(center_col)
        ori = slice_field(line, ori_col, pad=0)
        comment = slice_field(line, comment_col, pad=0)
        page_raw = slice_field(line, page_col, pad=0)
        page_nums = re.findall(r"\d+", page_raw)
        page = int(page_nums[-1]) if page_nums else None

        if cx is None and l1x is not None:
            cx = l1x
        if cy is None and l1y is not None:
            cy = l1y
        if cx is None:
            continue  # sin ninguna coordenada usable, no se puede ubicar

        parts.append({
            "code": code,
            "pn": pn,
            "desc": desc,
            "plane": plane,
            "l1": [l1x, l1y] if l1x is not None else None,
            "l2": [l2x, l2y] if l2x is not None else None,
            "space": space,
            "cx": cx,
            "cy": cy,
            "ori": ori,
            "footprint": comment,
            "page": page,
        })
    return parts


def parse_cst_table(path):
    """Parsea la tabla de componentes del .CST (formato binario reverseado y
    validado por regresión contra el .LST, ver notas de investigación arriba).
    Devuelve {code: {"x": raw_x, "y": raw_y, "plane": int}}. Si el archivo no
    existe o la estructura no calza (ej. una versión de .CST distinta), no
    revienta: devuelve {} y el resto del pipeline sigue sin cruce (LST solo)."""
    if not path.exists():
        return {}
    try:
        data = path.read_bytes()
    except OSError:
        return {}
    n = len(data)
    records = {}
    pos = CST_TABLE_START
    import struct
    while pos < n - (1 + CST_TRAIL_LEN):
        L = data[pos]
        if not (1 <= L <= 12):
            break
        name_bytes = data[pos + 1:pos + 1 + L]
        if not all(32 <= b < 127 for b in name_bytes):
            break
        trail = data[pos + 1 + L:pos + 1 + L + CST_TRAIL_LEN]
        if len(trail) < CST_TRAIL_LEN:
            break
        if trail[9:11] != b"\x01\x80":
            # el marcador constante no calza: dejamos de confiar en el resto
            # de la tabla acá en vez de seguir leyendo basura.
            break
        code = name_bytes.decode("ascii").strip()
        raw_x = struct.unpack_from("<h", trail, 0)[0]
        raw_y = struct.unpack_from("<h", trail, 2)[0]
        plane = trail[4]
        if code and code not in records:
            records[code] = {"x": raw_x, "y": raw_y, "plane": plane}
        pos += 1 + L + CST_TRAIL_LEN
    return records


def find_cdev_table_end(data):
    """Repite el mismo recorrido de parse_cst_table sólo para saber dónde
    termina la tabla de componentes — ahí empieza el diccionario de nombres
    de red que usa la sección CPad."""
    n = len(data)
    pos = CST_TABLE_START
    while pos < n - (1 + CST_TRAIL_LEN):
        L = data[pos]
        if not (1 <= L <= 12):
            break
        name_bytes = data[pos + 1:pos + 1 + L]
        if not all(32 <= b < 127 for b in name_bytes):
            break
        trail = data[pos + 1 + L:pos + 1 + L + CST_TRAIL_LEN]
        if len(trail) < CST_TRAIL_LEN or trail[9:11] != b"\x01\x80":
            break
        pos += 1 + L + CST_TRAIL_LEN
    return pos


def calibrate_cst(lst_parts, cst_records):
    """Ajusta por mínimos cuadrados raw_x->cx y raw_y->cy usando los
    componentes presentes en ambos archivos. Devuelve (ax,bx,ay,by,resid_x,resid_y)
    o None si no hay suficientes muestras en común para calibrar con confianza."""
    xs, ys_cx, ys_cy = [], [], []
    for code, rec in cst_records.items():
        p = lst_parts.get(code)
        if p is None:
            continue
        xs.append(rec["x"])
        ys_cx.append(p["cx"])
        ys_cy.append(rec["y"])
    # nombres reutilizados: armamos dos regresiones independientes
    def linfit(raw, real):
        n = len(raw)
        if n < 30:
            return None
        mr = sum(raw) / n
        mv = sum(real) / n
        srr = sum((r - mr) ** 2 for r in raw)
        if srr == 0:
            return None
        srv = sum((r - mr) * (v - mv) for r, v in zip(raw, real))
        b = srv / srr
        a = mv - b * mr
        resid = [v - (a + b * r) for r, v in zip(raw, real)]
        return a, b, resid

    raw_x = [cst_records[c]["x"] for c in cst_records if c in lst_parts]
    raw_y = [cst_records[c]["y"] for c in cst_records if c in lst_parts]
    real_cx = [lst_parts[c]["cx"] for c in cst_records if c in lst_parts]
    real_cy = [lst_parts[c]["cy"] for c in cst_records if c in lst_parts]

    fit_x = linfit(raw_x, real_cx)
    fit_y = linfit(raw_y, real_cy)
    if fit_x is None or fit_y is None:
        return None
    ax, bx, resid_x = fit_x
    ay, by, resid_y = fit_y
    return {"ax": ax, "bx": bx, "ay": ay, "by": by, "resid_x": resid_x, "resid_y": resid_y}


def cross_validate(parts, cst_records, calib):
    """Anota cada componente con el resultado de cruzarlo contra el .CST:
    - 'missing': no está en la tabla del .CST (sin verificación cruzada)
    - 'match': posición y cara coinciden dentro de tolerancia
    - 'mismatch': está en ambos archivos pero los datos no coinciden
      (se muestra igual, nunca se oculta una discrepancia)."""
    if calib is None:
        for p in parts:
            p["verify"] = {"status": "unavailable"}
        return {"verified": 0, "mismatch": 0, "missing": len(parts), "tolerance": None}

    # tolerancia: 6 desvíos estándar del residuo de calibración, con piso de
    # 15 mils (cuantización de enteros) — generoso a propósito para no marcar
    # "mismatch" por ruido de redondeo, sólo por discrepancias reales.
    import statistics
    all_resid = calib["resid_x"] + calib["resid_y"]
    std = statistics.pstdev(all_resid) if len(all_resid) > 1 else 0
    tolerance = max(15.0, 6 * std)

    counts = {"verified": 0, "mismatch": 0, "missing": 0}
    for p in parts:
        rec = cst_records.get(p["code"])
        if rec is None:
            p["verify"] = {"status": "missing"}
            counts["missing"] += 1
            continue
        cst_cx = calib["ax"] + calib["bx"] * rec["x"]
        cst_cy = calib["ay"] + calib["by"] * rec["y"]
        dx = cst_cx - p["cx"]
        dy = cst_cy - p["cy"]
        dist = (dx ** 2 + dy ** 2) ** 0.5
        plane_ok = str(rec["plane"]) == str(p["plane"]).strip()
        if dist <= tolerance and plane_ok:
            p["verify"] = {"status": "match", "delta": round(dist, 1)}
            counts["verified"] += 1
        else:
            p["verify"] = {
                "status": "mismatch",
                "delta": round(dist, 1),
                "cst_xy": [round(cst_cx, 1), round(cst_cy, 1)],
                "cst_plane": rec["plane"],
                "plane_ok": plane_ok,
            }
            counts["mismatch"] += 1
    counts["tolerance"] = round(tolerance, 1)
    return counts


def estimate_box(p):
    """Estimación de tamaño/orientación del rectángulo del componente.
    No es geometría exacta de footprint (no tenemos esa librería) — es una
    aproximación visual: exacta cuando hay 2 leads reales (pasivos, la
    mayoría), heurística por cantidad de pines para BGA/QFP grandes sin
    coordenadas de lead. (Se refina después con datos reales de CPad si
    están disponibles — ver refine_box_from_pins.)"""
    if p["l1"] and p["l2"] and None not in p["l1"] and None not in p["l2"]:
        (x1, y1), (x2, y2) = p["l1"], p["l2"]
        dx, dy = x2 - x1, y2 - y1
        length = max((dx**2 + dy**2) ** 0.5, 20)
        width = p["space"] if p["space"] and p["space"] > 0 else max(length * 0.5, 20)
        angle = 0.0
        import math
        angle = math.degrees(math.atan2(dy, dx))
        return {"w": length, "h": width, "angle": angle, "exact": True}
    # heurística por pin count (extraído del footprint, ej QFP100_..., PBGA593_...)
    m = re.search(r"(\d{2,4})", p["footprint"] or "")
    pins = int(m.group(1)) if m else 4
    side = max(52 * (pins ** 0.5), 40)
    return {"w": side, "h": side, "angle": 0.0, "exact": False, "pin_count": pins if m else None}


def refine_box_from_pins(p):
    """Si el componente tiene 3+ pines reales asignados (de CPad), reemplaza
    la caja heurística por una calculada de la nube de pines real — deja de
    ser una aproximación por cantidad de pines y pasa a ser geometría real
    (con un margen fijo hacia el borde del cuerpo, que sí seguimos sin
    conocer con exactitud)."""
    pins = p.get("pins")
    if not pins or len(pins) < 3 or p["box"]["exact"] is True:
        return
    xs = [pt["x"] for pt in pins]
    ys = [pt["y"] for pt in pins]
    span_x = max(xs) - min(xs)
    span_y = max(ys) - min(ys)
    margin = max(span_x, span_y) * 0.14 + 25
    w = max(span_x + margin * 2, 30)
    h = max(span_y + margin * 2, 30)
    p["box"] = {"w": w, "h": h, "angle": 0.0, "exact": "pins", "pin_count": p["box"].get("pin_count")}


def parse_section_tags(data):
    """Ubica los 5 tags de sección de 4 letras del .CST. Devuelve
    {tag: offset_del_tag}. Faltan tags -> {} para esa clave (el resto del
    pipeline sigue funcionando sin esa sección)."""
    tags = {}
    for tag in SECTION_TAGS:
        idx = data.find(tag)
        if idx != -1:
            tags[tag.decode()] = idx
    return tags


def section_data_range(tags, name, file_len):
    """(inicio, fin) de los datos de una sección — justo después de su tag
    y hasta el próximo tag por offset (o fin de archivo)."""
    if name not in tags:
        return None
    start = tags[name] + 4
    later = sorted(pos for pos in tags.values() if pos > tags[name])
    end = later[0] if later else file_len
    return start, end


def parse_pascal_strings(data, start, end=None, min_len=1, max_len=40):
    """Lee strings estilo Pascal (1 byte largo + ascii) consecutivos a
    partir de `start`, parando en el primer byte que no calce (fin de la
    tabla). Usado tanto para la tabla de componentes como para el
    diccionario de nombres de red."""
    n = len(data) if end is None else min(end, len(data))
    pos = start
    out = []
    while pos < n - 1:
        L = data[pos]
        if not (min_len <= L <= max_len):
            break
        chunk = data[pos + 1:pos + 1 + L]
        if len(chunk) < L or not all(9 <= b < 127 for b in chunk):
            break
        out.append(chunk.decode("ascii").strip())
        pos += 1 + L
    return out, pos


def parse_net_dictionary(data, cdev_end):
    """El diccionario de nombres de red (usado por índice desde CPad) vive
    justo después de la tabla de componentes, precedido por 1 byte marcador
    que no forma parte de ningún string (se detecta solo probando desde
    cdev_end y cdev_end+1)."""
    for offset in (0, 1, 2):
        names, end = parse_pascal_strings(data, cdev_end + offset)
        if len(names) > 100:  # una tabla real, no ruido
            return names
    return []


def parse_cpad_section(data, cpad_range, net_names, calib):
    """Decodifica la sección CPad: posición real de cada pin + su red.
    Devuelve una lista de {"x","y","net"} en coordenadas reales (mils, ya
    calibradas con la misma transformación que la tabla de componentes)."""
    if cpad_range is None or calib is None:
        return []
    start, end = cpad_range
    ax, bx, ay, by = calib["ax"], calib["bx"], calib["ay"], calib["by"]
    pins = []
    n_records = (end - start) // CPAD_RECORD_LEN
    for i in range(n_records):
        off = start + i * CPAD_RECORD_LEN
        rec = data[off:off + CPAD_RECORD_LEN]
        if len(rec) < CPAD_RECORD_LEN:
            break
        rx = struct.unpack_from("<h", rec, 6)[0]
        ry = struct.unpack_from("<h", rec, 8)[0]
        sig_idx = struct.unpack_from("<H", rec, 4)[0]
        net = net_names[sig_idx] if 0 <= sig_idx < len(net_names) else None
        pins.append({"x": ax + bx * rx, "y": ay + by * ry, "net": net})
    return pins


def parse_clin_section(data, clin_range, calib):
    """Decodifica la sección CLin: segmentos de pista de cobre reales
    (X1,Y1)-(X2,Y2), ya calibrados a mils reales. No distinguimos capa
    (top/bottom copper) — ese campo no está confirmado — así que todas las
    pistas se dibujan igual, sea cual sea la capa física real."""
    if clin_range is None or calib is None:
        return []
    start, end = clin_range
    start += CLIN_ORPHAN_SKIP
    ax, bx, ay, by = calib["ax"], calib["bx"], calib["ay"], calib["by"]
    segments = []
    n_records = (end - start) // CLIN_RECORD_LEN
    for i in range(n_records):
        off = start + i * CLIN_RECORD_LEN
        rec = data[off:off + CLIN_RECORD_LEN]
        if len(rec) < CLIN_RECORD_LEN:
            break
        x1 = struct.unpack_from("<h", rec, 4)[0]
        y1 = struct.unpack_from("<h", rec, 6)[0]
        x2 = struct.unpack_from("<h", rec, 8)[0]
        y2 = struct.unpack_from("<h", rec, 10)[0]
        segments.append((ax + bx * x1, ay + by * y1, ax + bx * x2, ay + by * y2))
    return segments


def clin_path_d(segments):
    """Arma un único atributo 'd' de <path> con todos los segmentos, en vez
    de miles de elementos SVG sueltos — con ~85k segmentos, un solo <path>
    es lo único que mantiene el pan/zoom fluido."""
    parts_d = []
    for x1, y1, x2, y2 in segments:
        parts_d.append(f"M{x1:.0f},{y1:.0f} L{x2:.0f},{y2:.0f}")
    return " ".join(parts_d)


def assign_pins_to_parts(pins, parts, cell=400, max_dist=1400):
    """Asigna cada pin decodificado de CPad a un componente. Requiere que
    cada part ya tenga su "box" calculada (estimate_box), porque para
    componentes grandes (BGA/QFP) un pin del borde suele quedar más cerca
    del *centro* de un pasivo vecino que del centro del propio chip — así
    que primero probamos contención dentro de la caja heurística de cada
    candidato (con margen), y sólo si ninguna contiene el pin caemos a
    vecino-más-cercano por centro (grid espacial simple, no fuerza bruta)."""
    grid = {}
    for p in parts:
        key = (int(p["cx"] // cell), int(p["cy"] // cell))
        grid.setdefault(key, []).append(p)
    max_dist2 = max_dist * max_dist
    for pin in pins:
        kx, ky = int(pin["x"] // cell), int(pin["y"] // cell)
        containing = []
        nearest, nearest_d2 = None, max_dist2
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for cand in grid.get((kx + dx, ky + dy), []):
                    dx_ = pin["x"] - cand["cx"]
                    dy_ = pin["y"] - cand["cy"]
                    d2 = dx_ * dx_ + dy_ * dy_
                    if d2 < nearest_d2:
                        nearest_d2, nearest = d2, cand
                    box = cand["box"]
                    hw = box["w"] / 2 * 1.25 + 15  # margen: el footprint real
                    hh = box["h"] / 2 * 1.25 + 15  # suele exceder un poco el pin extremo
                    if abs(dx_) <= hw and abs(dy_) <= hh:
                        containing.append((d2, cand))
        if containing:
            containing.sort(key=lambda t: t[0])
            containing[0][1].setdefault("pins", []).append(pin)
        elif nearest is not None:
            nearest.setdefault("pins", []).append(pin)


# --- Categoría visual por prefijo de referencia (dato que ya tenemos, no
# requiere geometría nueva) — sirve para colorear/dibujar cada componente de
# forma más parecida a su tipo real en vez de un rectángulo genérico.
CATEGORY_RULES = [
    (re.compile(r"^VR\d"), "ic"),
    (re.compile(r"^R\d"), "resistor"),
    (re.compile(r"^C\d"), "capacitor"),
    (re.compile(r"^CN\d"), "connector"),
    (re.compile(r"^L\d"), "inductor"),
    (re.compile(r"^Y\d"), "crystal"),
    (re.compile(r"^D\d"), "diode"),
    (re.compile(r"^Q\d"), "transistor"),
    (re.compile(r"^U\d"), "ic"),
    (re.compile(r"^J\d"), "connector"),
    (re.compile(r"^T\d"), "inductor"),
    (re.compile(r"^F\d"), "fuse"),
    (re.compile(r"^FB\d"), "inductor"),
    (re.compile(r"^SW\d"), "switch"),
    (re.compile(r"^K\d"), "connector"),
    (re.compile(r"^M\d"), "mic"),
    (re.compile(r"^SP\d"), "speaker"),
]


def get_category(code):
    for pat, cat in CATEGORY_RULES:
        if pat.match(code):
            return cat
    return "other"


# --- Puertos externos reales identificados leyendo el refdes directo de la
# hoja de esquemático correspondiente (no por posición/heurística — cada uno
# se confirmó viendo el símbolo con su J-number en la hoja indicada). Fuente
# de cada uno, para poder volver a verificar:
#   J3  hoja 61 (PARALLEL CONNECTOR)
#   J6  hoja 57 (USB CONNECTOR, señales USBP2±)
#   J8  hoja 25 (GFX:EXT CRT CONNECTOR)
#   J10 hoja 44 (DOCKING CONNECTOR)
#   J11 hoja 39 ("PIN 1-8 RJ45 PINS / PIN 9-10 RJ11 PINS" — combo Ethernet+módem)
#   J13 hoja 69 (DCDC:DC-IN AND CHARGER, señal -EXTPWR)
#   J17 hoja 57 (USB CONNECTOR, señales USBP3±)
#   J18 hoja 71 (DCDC:BATTERY INPUT)
#   J19 hoja 47, literal "LINE IN" en el símbolo
#   J20 hoja 47, literal "HEADPHONE" en el símbolo
#   J21 hoja 48, literal "EXT MIC" en el símbolo
PORT_LABELS = {
    "J3": "Paralelo (DB25)",
    "J6": "USB",
    "J8": "VGA / monitor ext.",
    "J10": "Docking",
    "J11": "Ethernet (RJ45) + módem (RJ11)",
    "J13": "DC-IN (AC)",
    "J17": "USB",
    "J18": "Batería",
    "J19": "Line-in",
    "J20": "Headphone",
    "J21": "Mic externo",
}

# Margen extra de "cuerpo de conector" para los puertos de arriba: son
# ESTIMACIONES estándar de cuánto sobresale la carcasa real del conector más
# allá de sus pines (no está medido en ningún archivo — el .LST sólo tiene
# la huella de los pines). Se documenta así de explícito en la UI. Valores
# en mils, aproximados por tipo de conector.
PORT_SHELL_MARGIN = {
    "J3": 350,   # DB25, carcasa grande
    "J8": 250,   # DB15 (VGA)
    "J11": 200,  # RJ45/RJ11 combo
    "J13": 150,  # barril DC
    "J6": 120, "J17": 120,  # USB-A
    "J19": 90, "J20": 90, "J21": 90,  # jacks 3.5mm
    "J10": 150,  # docking
    "J18": 100,  # batería
}


def convex_hull(points):
    """Envolvente convexa (monotone chain, sin dependencias). points: lista
    de (x,y). Se usa para aproximar el contorno de la placa — es una
    aproximación real (no la silueta exacta, que no tenemos): un contorno
    convexo no puede representar entrantes como el hueco de la batería o la
    bisagra, así que va a "cortar en línea recta" esas zonas."""
    pts = sorted(set(points))
    if len(pts) <= 2:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def dilate_cells(occ, radius=1, eight=True):
    """Dilata (morfológicamente) un set de celdas ocupadas — se usa para
    darle un margen parejo al contorno final sin perder los entrantes
    reales (a diferencia de empujar cada vértice desde el centroide, que
    distorsiona justo las zonas cóncavas que queremos conservar)."""
    neigh = [(dx, dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if (dx, dy) != (0, 0)]
    if not eight:
        neigh = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    out = set(occ)
    frontier = set(occ)
    for _ in range(radius):
        new = set()
        for (cx, cy) in frontier:
            for dx, dy in neigh:
                new.add((cx + dx, cy + dy))
        out |= new
        frontier = new
    return out


def largest_connected_component(occ):
    """Componente conexa más grande (4-vecinos) de un set de celdas — así
    se descarta ruido aislado (algún punto suelto lejos del resto)."""
    if not occ:
        return set()
    visited = set()
    best = []
    for start in occ:
        if start in visited:
            continue
        comp = []
        stack = [start]
        visited.add(start)
        while stack:
            c = stack.pop()
            comp.append(c)
            cx, cy = c
            for n in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                if n in occ and n not in visited:
                    visited.add(n)
                    stack.append(n)
        if len(comp) > len(best):
            best = comp
    return set(best)


def grid_boundary_polygon(occ, cell):
    """Traza el borde exterior de un set de celdas ocupadas (marching
    squares por aristas: cada lado de celda que no linda con otra celda
    ocupada es un segmento de borde; se hilvanan por vértice compartido en
    loops cerrados, y se devuelve el de mayor área = contorno exterior)."""
    adj = {}

    def add_edge(p1, p2):
        adj.setdefault(p1, []).append(p2)
        adj.setdefault(p2, []).append(p1)

    for (cx, cy) in occ:
        x0, y0 = cx * cell, cy * cell
        x1, y1 = x0 + cell, y0 + cell
        if (cx - 1, cy) not in occ:
            add_edge((x0, y0), (x0, y1))
        if (cx + 1, cy) not in occ:
            add_edge((x1, y0), (x1, y1))
        if (cx, cy - 1) not in occ:
            add_edge((x0, y0), (x1, y0))
        if (cx, cy + 1) not in occ:
            add_edge((x0, y1), (x1, y1))

    def edge_key(a, b):
        return (a, b) if a <= b else (b, a)

    used = set()
    loops = []
    for v0 in list(adj.keys()):
        for v1 in adj[v0]:
            if edge_key(v0, v1) in used:
                continue
            loop = [v0]
            used.add(edge_key(v0, v1))
            cur = v1
            loop.append(cur)
            while cur != v0:
                candidates = [n for n in adj.get(cur, []) if edge_key(cur, n) not in used]
                if not candidates:
                    break
                nxt = candidates[0]
                used.add(edge_key(cur, nxt))
                loop.append(nxt)
                cur = nxt
            if len(loop) > 3 and loop[0] == loop[-1]:
                loops.append(loop[:-1])
    if not loops:
        return []

    def area(loop):
        s = 0.0
        for i in range(len(loop)):
            x1, y1 = loop[i]
            x2, y2 = loop[(i + 1) % len(loop)]
            s += x1 * y2 - x2 * y1
        return abs(s) / 2

    return max(loops, key=area)


def board_outline(parts, extra_points=None, cell=190, margin_mils=170):
    """Contorno de la placa: envolvente CÓNCAVA (grilla de ocupación +
    trazado de borde) sobre la nube de puntos real — pines de CPad,
    extremos de pista de CLin, y esquinas de componentes como respaldo
    donde no hay pines/pistas asignados. A diferencia de una envolvente
    convexa, esto sí puede mostrar entrantes reales (ej. el recorte de la
    jaula de PC Card que confirma el manual de mantenimiento) porque se
    basa en dónde hay geometría real, no en una forma que sólo puede
    "abombarse hacia afuera". Sigue siendo una aproximación (depende de la
    densidad de puntos disponible, no es la silueta recortada exacta), pero
    ya no inventa nada que no esté respaldado por datos reales."""
    points = []
    for p in parts:
        w, h = p["box"]["w"], p["box"]["h"]
        cx, cy = p["cx"], p["cy"]
        shell = PORT_SHELL_MARGIN.get(p["code"], 0)
        w, h = w + 2 * shell, h + 2 * shell
        points.extend([
            (cx - w / 2, cy - h / 2), (cx + w / 2, cy - h / 2),
            (cx - w / 2, cy + h / 2), (cx + w / 2, cy + h / 2),
        ])
    if extra_points:
        points.extend(extra_points)
    if not points:
        return ""

    occ = {(int(x // cell), int(y // cell)) for x, y in points}
    occ = largest_connected_component(occ)
    if not occ:
        return ""
    dilate_radius = max(1, round(margin_mils / cell))
    occ = dilate_cells(occ, radius=dilate_radius, eight=True)

    loop = grid_boundary_polygon(occ, cell)
    if not loop:
        return ""
    return " ".join(f"{x:.0f},{y:.0f}" for x, y in loop)


def build_html(parts, verify_summary, pin_summary, clin_segments):
    # Las boxes/categorías ya se calcularon en main() (antes de asignar
    # pines, porque assign_pins_to_parts necesita la box heurística para la
    # prueba de contención). Acá sólo refinamos con los pines reales, si
    # los hay.
    for p in parts:
        refine_box_from_pins(p)
    pin_summary["refined"] = sum(1 for p in parts if p["box"]["exact"] == "pins")

    xs = [p["cx"] for p in parts]
    ys = [p["cy"] for p in parts]
    minx, maxx = min(xs), max(xs)
    miny, maxy = min(ys), max(ys)
    pad = 300
    view = (minx - pad, miny - pad, (maxx - minx) + 2 * pad, (maxy - miny) + 2 * pad)

    trace_points = []
    for x1, y1, x2, y2 in clin_segments:
        trace_points.append((x1, y1))
        trace_points.append((x2, y2))
    hull_points = board_outline(parts, extra_points=trace_points)
    traces_d = clin_path_d(clin_segments)

    data_json = json.dumps(parts, ensure_ascii=False)

    if verify_summary.get("tolerance") is None:
        verify_line = "No se pudo cruzar contra Tokyo2 Dv.CST (archivo ausente o formato inesperado) — sólo datos del .LST, sin verificación cruzada."
    else:
        verify_line = (
            f"Verificado cruzando contra Tokyo2 Dv.CST: "
            f"<b>{verify_summary['verified']}</b> coinciden, "
            f"<b>{verify_summary['mismatch']}</b> discrepancias, "
            f"<b>{verify_summary['missing']}</b> sin registro en el .CST "
            f"(tolerancia &plusmn;{verify_summary['tolerance']} mils)."
        )

    if pin_summary.get("total_pins"):
        pin_line = (
            f"Pines reales decodificados de CPad: <b>{pin_summary['total_pins']}</b> "
            f"asignados a <b>{pin_summary['parts_with_pins']}</b> componentes "
            f"(<b>{pin_summary['refined']}</b> con caja recalculada por geometría real)."
        )
    else:
        pin_line = "Sin datos de pines de CPad (sección ausente o no decodificable) — cajas por heurística/lead solamente."

    html = HTML_TEMPLATE.replace("__DATA_JSON__", data_json)
    html = html.replace("__VIEWBOX__", f"{view[0]} {view[1]} {view[2]} {view[3]}")
    html = html.replace("__NPARTS__", str(len(parts)))
    html = html.replace("__VERIFY_LINE__", verify_line)
    html = html.replace("__BOARD_HULL__", hull_points)
    html = html.replace("__PIN_LINE__", pin_line)
    html = html.replace("__TRACES_D__", traces_d)
    html = html.replace("__NTRACES__", str(len(clin_segments)))
    return html


HTML_TEMPLATE = r"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>IBM X31 - Boardview (Tokyo2, local)</title>
<style>
  :root{
    --bg:#0b1220; --panel:#121b2e; --ink:#e7edf7; --muted:#93a3bd;
    --accent:#3ba7ff; --hi:#ffcc33;
    --desk:#050a12;           /* fuera de la placa (escritorio) */
    --soldermask:#0d4023;     /* verde solder-mask */
    --soldermask-2:#0a3319;   /* variante más oscura, para el degradé */
    --silk:#e8e2c9;           /* blanco/crema serigrafía */
    --copper-pad:#c9a24a;     /* dorado, pads/leads */
  }
  html,body{margin:0;height:100%;background:var(--bg);color:var(--ink);
    font:14px/1.4 -apple-system,Segoe UI,Roboto,sans-serif;}
  #app{display:flex;height:100%;}
  #board-wrap{flex:1;position:relative;overflow:hidden;}
  #board-svg{width:100%;height:100%;background:var(--desk);}
  #board-outline{fill:url(#soldermask-grad);stroke:var(--silk);stroke-width:10;
    stroke-opacity:.55;stroke-linejoin:round;}
  #trace-layer{fill:none;stroke:var(--copper-pad);stroke-width:9;stroke-opacity:.5;stroke-linecap:round;}
  #trace-layer.hidden{display:none;}
  #sidebar{width:340px;background:var(--panel);border-left:1px solid #223047;
    padding:14px;box-sizing:border-box;overflow-y:auto;}
  h1{font-size:15px;margin:0 0 4px;}
  .sub{color:var(--muted);font-size:12px;margin-bottom:14px;}
  input[type=text]{width:100%;box-sizing:border-box;padding:8px 10px;
    border-radius:8px;border:1px solid #2a3a56;background:#0d1626;color:var(--ink);
    font-size:14px;}
  .row{display:flex;gap:8px;margin-bottom:10px;}
  select,button{padding:8px 10px;border-radius:8px;border:1px solid #2a3a56;
    background:#0d1626;color:var(--ink);font-size:13px;}
  button{cursor:pointer;}
  button.primary{background:var(--accent);border-color:var(--accent);color:#04182c;font-weight:600;}
  #results{margin-top:10px;display:flex;flex-direction:column;gap:6px;max-height:220px;overflow-y:auto;}
  .res-item{padding:6px 8px;border-radius:6px;background:#0d1626;cursor:pointer;font-size:13px;}
  .res-item:hover{background:#17233a;}
  .res-item b{color:var(--accent);}
  #detail{margin-top:16px;padding:12px;border-radius:8px;background:#0d1626;
    border:1px solid #223047;font-size:13px;display:none;}
  #detail div{margin-bottom:4px;}
  #detail .k{color:var(--muted);display:inline-block;width:88px;}
  .legend{margin-top:16px;font-size:12px;color:var(--muted);}
  .legend div{margin-bottom:3px;}
  .swatch{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:6px;vertical-align:middle;}
  a.hint{color:var(--accent);text-decoration:none;}
  #count{font-size:12px;color:var(--muted);margin-top:2px;}
  .comp-rect{stroke-width:2.5;cursor:pointer;}
  .comp-rect.bottom{opacity:.55;}
  .comp-rect.approx{stroke-dasharray:5 4;}
  .comp-rect:hover{filter:brightness(1.35);}
  .comp-rect.mismatch{stroke:#ff3b3b !important;stroke-width:7;stroke-dasharray:none;}
  .verify-ok{color:#4ade80;}
  .verify-bad{color:#ff6b6b;}
  .verify-na{color:var(--muted);}
  .hi-rect{fill:none;stroke:var(--hi);stroke-width:14;filter:drop-shadow(0 0 6px var(--hi));}
  .hi-arrow{fill:var(--hi);}
  .comp-label{fill:var(--silk);font-family:"Courier New",monospace;pointer-events:none;
    paint-order:stroke; stroke:#000; stroke-width:6px; stroke-opacity:.55;}
  .comp-label.bottom{opacity:.55;}
  .port-tag-bg{fill:#0d2a4a;stroke:#5fc3ff;stroke-width:4;fill-opacity:.92;}
  .port-tag{fill:#8fe0ff;font-family:"Courier New",monospace;font-weight:bold;
    text-anchor:middle;pointer-events:none;}
  .pin-tick{stroke:var(--copper-pad);stroke-width:8;}
  .pin-pad{fill:var(--copper-pad);stroke:#00000055;stroke-width:1;}
  .cat-swatch{display:inline-block;width:14px;height:10px;border-radius:2px;
    margin-right:6px;vertical-align:middle;border-width:2px;border-style:solid;}
</style>
</head>
<body>
<div id="app">
  <div id="board-wrap">
    <svg id="board-svg" viewBox="__VIEWBOX__" preserveAspectRatio="xMidYMid meet">
      <defs>
        <radialGradient id="soldermask-grad" cx="35%" cy="30%" r="80%">
          <stop offset="0%" stop-color="var(--soldermask)"/>
          <stop offset="100%" stop-color="var(--soldermask-2)"/>
        </radialGradient>
      </defs>
      <polygon id="board-outline" points="__BOARD_HULL__"></polygon>
      <path id="trace-layer" d="__TRACES_D__"></path>
      <g id="board-layer"></g>
      <g id="label-layer"></g>
      <g id="highlight-layer"></g>
    </svg>
  </div>
  <div id="sidebar">
    <h1>IBM ThinkPad X31 &mdash; Boardview (Tokyo2, local)</h1>
    <div class="sub">Generado localmente desde Tokyo2 Dv.LST &middot; __NPARTS__ componentes &middot; IBM CONFIDENTIAL (no publicar)</div>
    <div class="sub" id="verify-summary">__VERIFY_LINE__</div>
    <div class="sub" id="pin-summary">__PIN_LINE__</div>
    <div class="sub" id="trace-summary">Pistas de cobre reales decodificadas de CLin: <b>__NTRACES__</b> segmentos (sin distinguir capa top/bottom — se dibujan todas juntas).</div>

    <div class="row">
      <input id="q" type="text" placeholder="Referencia (ej. U4, C233, R950)"
        onkeydown="if(event.key==='Enter') doSearch()">
      <button class="primary" onclick="doSearch()">Buscar</button>
    </div>
    <div class="row">
      <select id="sideFilter" onchange="applySideFilter()">
        <option value="all">Ambas caras</option>
        <option value="top">Sólo TOP (componentes)</option>
        <option value="bottom">Sólo BOTTOM (soldadura)</option>
      </select>
      <button onclick="resetView()">Reset vista</button>
    </div>
    <div class="row">
      <button id="tracesBtn" onclick="toggleTraces()">Mostrar pistas de cobre</button>
    </div>
    <div id="results"></div>
    <div id="detail"></div>

    <div class="legend" id="legend"></div>
  </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/svg-pan-zoom@3.6.2/dist/svg-pan-zoom.min.js"></script>
<script>
const DATA = __DATA_JSON__;
const byCode = {};
DATA.forEach(p => { byCode[p.code.toUpperCase()] = p; });

const svgNS = "http://www.w3.org/2000/svg";
const boardLayer = document.getElementById("board-layer");
const labelLayer = document.getElementById("label-layer");
const hiLayer = document.getElementById("highlight-layer");

// Estilo por categoría (inferida del prefijo de referencia, ej. R->resistor,
// C->capacitor, U->IC, J->conector...). Es una convención visual tipo PCB,
// no geometría real de footprint — pero lee mucho más parecido a la placa
// real que un rectángulo genérico de un solo color.
const CATEGORY_STYLE = {
  resistor:   {fill:"#c9a66b", stroke:"#7a5c33", label:"Resistor"},
  capacitor:  {fill:"#9aa3b5", stroke:"#565d6b", label:"Capacitor"},
  inductor:   {fill:"#c97a3d", stroke:"#7a4a22", label:"Inductor / choke / transformador"},
  crystal:    {fill:"#cfd8e3", stroke:"#7c8a9c", label:"Cristal / oscilador"},
  diode:      {fill:"#3a3f47", stroke:"#000000", label:"Diodo"},
  transistor: {fill:"#3a3f47", stroke:"#000000", label:"Transistor / MOSFET"},
  ic:         {fill:"#23282f", stroke:"#000000", label:"Circuito integrado"},
  connector:  {fill:"#b7bdc7", stroke:"#5b6472", label:"Conector"},
  fuse:       {fill:"#e2c14d", stroke:"#8a6d1f", label:"Fusible"},
  switch:     {fill:"#7c8a9c", stroke:"#4b5563", label:"Switch"},
  mic:        {fill:"#7c8a9c", stroke:"#4b5563", label:"Micrófono"},
  speaker:    {fill:"#7c8a9c", stroke:"#4b5563", label:"Parlante"},
  other:      {fill:"#6b7280", stroke:"#3f454f", label:"Otro / mecánico"},
};

function styleFor(p){ return CATEGORY_STYLE[p.category] || CATEGORY_STYLE.other; }

function drawBoard(filter){
  boardLayer.innerHTML = "";
  labelLayer.innerHTML = "";
  DATA.forEach(p => {
    const isTop = p.plane === "1";
    if (filter === "top" && !isTop) return;
    if (filter === "bottom" && isTop) return;
    const st = styleFor(p);
    const g = document.createElementNS(svgNS, "g");
    g.setAttribute("transform", `translate(${p.cx},${p.cy}) rotate(${p.box.angle||0})`);
    const rect = document.createElementNS(svgNS, "rect");
    rect.setAttribute("x", -p.box.w/2);
    rect.setAttribute("y", -p.box.h/2);
    rect.setAttribute("width", p.box.w);
    rect.setAttribute("height", p.box.h);
    rect.setAttribute("rx", Math.min(p.box.w, p.box.h) * 0.08);
    rect.setAttribute("fill", st.fill);
    rect.setAttribute("stroke", st.stroke);
    const isMismatch = p.verify && p.verify.status === "mismatch";
    rect.setAttribute("class", "comp-rect" + (isTop?"":" bottom") + (p.box.exact?"":" approx") + (isMismatch?" mismatch":""));
    rect.dataset.code = p.code;
    rect.addEventListener("click", () => showDetail(p, true));
    g.appendChild(rect);

    // Pines reales (decodificados de la sección CPad del .CST) — se dibujan
    // como pads chicos en su posición exacta. Esto es geometría real, no
    // decorativa: si existe, se usa en vez de los ticks sintéticos de abajo.
    if (p.pins && p.pins.length){
      p.pins.forEach(pt => {
        const pad = document.createElementNS(svgNS, "rect");
        const s = Math.max(Math.min(p.box.w, p.box.h) * 0.09, 10);
        pad.setAttribute("x", pt.x - p.cx - s/2);
        pad.setAttribute("y", pt.y - p.cy - s/2);
        pad.setAttribute("width", s);
        pad.setAttribute("height", s);
        pad.setAttribute("class", "pin-pad");
        if (pt.net){
          const title = document.createElementNS(svgNS, "title");
          title.textContent = pt.net;
          pad.appendChild(title);
        }
        g.appendChild(pad);
      });
    }

    // Ticks sintéticos de pines: sólo como respaldo cuando NO hay pines
    // reales (CPad) para este componente — puramente decorativo/orientativo
    // (cantidad aproximada por footprint), da lectura de "chip" en vez de
    // bloque liso.
    if (p.category === "ic" && p.box.exact === false && (!p.pins || !p.pins.length) && p.box.pin_count){
      const n = Math.max(4, Math.min(64, Math.round(p.box.pin_count / 4) * 4));
      const perSide = Math.round(n / 4);
      const w = p.box.w, h = p.box.h;
      for (let side = 0; side < 4; side++){
        for (let i = 0; i < perSide; i++){
          const t = (i + 0.5) / perSide;
          const tick = document.createElementNS(svgNS, "line");
          let x1,y1,x2,y2;
          if (side === 0){ x1 = -w/2 + t*w; y1 = -h/2; x2 = x1; y2 = -h/2 - h*0.045; }
          else if (side === 1){ x1 = w/2; y1 = -h/2 + t*h; x2 = w/2 + w*0.045; y2 = y1; }
          else if (side === 2){ x1 = w/2 - t*w; y1 = h/2; x2 = x1; y2 = h/2 + h*0.045; }
          else { x1 = -w/2; y1 = h/2 - t*h; x2 = -w/2 - w*0.045; y2 = y1; }
          tick.setAttribute("x1", x1); tick.setAttribute("y1", y1);
          tick.setAttribute("x2", x2); tick.setAttribute("y2", y2);
          tick.setAttribute("class", "pin-tick");
          g.appendChild(tick);
        }
      }
    }
    boardLayer.appendChild(g);

    // Etiqueta silkscreen (referencia) — tamaño proporcional al componente,
    // legible al hacer zoom, como la serigrafía real de una placa.
    const label = document.createElementNS(svgNS, "text");
    const fontSize = Math.max(Math.min(Math.min(p.box.w, p.box.h) * 0.42, 260), 22);
    label.setAttribute("x", p.cx);
    label.setAttribute("y", p.cy + fontSize * 0.34);
    label.setAttribute("text-anchor", "middle");
    label.setAttribute("font-size", fontSize);
    label.setAttribute("class", "comp-label" + (isTop ? "" : " bottom"));
    label.textContent = p.code;
    labelLayer.appendChild(label);

    // Puerto externo real identificado (leyendo el refdes directo del
    // esquemático, ver PORT_LABELS en el generador) — etiqueta destacada,
    // siempre legible, aparte del refdes normal.
    if (p.port){
      const tagSize = 130;
      const text = `${p.code} · ${p.port}`;
      const approxW = text.length * tagSize * 0.56;
      const tagY = p.cy - Math.max(p.box.h, p.box.w) / 2 - tagSize * 0.9;
      const bg = document.createElementNS(svgNS, "rect");
      bg.setAttribute("x", p.cx - approxW / 2 - 20);
      bg.setAttribute("y", tagY - tagSize * 0.8);
      bg.setAttribute("width", approxW + 40);
      bg.setAttribute("height", tagSize * 1.15);
      bg.setAttribute("rx", tagSize * 0.2);
      bg.setAttribute("class", "port-tag-bg");
      labelLayer.appendChild(bg);
      const tag = document.createElementNS(svgNS, "text");
      tag.setAttribute("x", p.cx);
      tag.setAttribute("y", tagY);
      tag.setAttribute("text-anchor", "middle");
      tag.setAttribute("font-size", tagSize);
      tag.setAttribute("class", "port-tag");
      tag.textContent = text;
      labelLayer.appendChild(tag);
    }
  });
}

function clearHighlight(){ hiLayer.innerHTML = ""; }

function highlight(codes){
  clearHighlight();
  let found = [];
  codes.forEach(c => {
    const p = byCode[c.toUpperCase()];
    if (!p) return;
    found.push(p);
    const w = p.box.w + 260, h = p.box.h + 260;
    const rect = document.createElementNS(svgNS, "rect");
    rect.setAttribute("x", p.cx - w/2);
    rect.setAttribute("y", p.cy - h/2);
    rect.setAttribute("width", w);
    rect.setAttribute("height", h);
    rect.setAttribute("rx", 40);
    rect.setAttribute("class", "hi-rect");
    hiLayer.appendChild(rect);

    // flecha apuntando desde arriba-izquierda hacia la caja
    const ax = p.cx - w/2 - 500, ay = p.cy - h/2 - 500;
    const tx = p.cx - w/2 - 20, ty = p.cy - h/2 - 20;
    const arrow = document.createElementNS(svgNS, "path");
    const angle = Math.atan2(ty-ay, tx-ax);
    const ah = 140;
    const lx = tx - ah*Math.cos(angle - 0.4), ly = ty - ah*Math.sin(angle - 0.4);
    const rx = tx - ah*Math.cos(angle + 0.4), ry = ty - ah*Math.sin(angle + 0.4);
    arrow.setAttribute("d", `M${ax},${ay} L${tx},${ty} M${tx},${ty} L${lx},${ly} M${tx},${ty} L${rx},${ry}`);
    arrow.setAttribute("stroke", "var(--hi)");
    arrow.setAttribute("stroke-width", "26");
    arrow.setAttribute("fill", "none");
    arrow.setAttribute("stroke-linecap", "round");
    hiLayer.appendChild(arrow);
  });
  return found;
}

function verifyLine(p){
  const v = p.verify || {status: "unavailable"};
  if (v.status === "match"){
    return `<div><span class="k">Verificación</span><span class="verify-ok">&#10003; coincide con .CST (&Delta;${v.delta} mils)</span></div>`;
  }
  if (v.status === "mismatch"){
    return `<div><span class="k">Verificación</span><span class="verify-bad">&#9888; discrepancia con .CST (&Delta;${v.delta} mils${v.plane_ok ? "" : ", cara distinta"})</span></div>
            <div><span class="k"></span><span class="verify-bad" style="font-size:12px">.CST dice: ${v.cst_xy[0]}, ${v.cst_xy[1]} &middot; plane=${v.cst_plane}</span></div>`;
  }
  if (v.status === "missing"){
    return `<div><span class="k">Verificación</span><span class="verify-na">sin registro en .CST (sólo .LST)</span></div>`;
  }
  return `<div><span class="k">Verificación</span><span class="verify-na">.CST no disponible al generar</span></div>`;
}

function pinsLine(p){
  if (!p.pins || !p.pins.length){
    return `<div><span class="k">Pines (CPad)</span><span class="verify-na">sin datos reales — caja ${p.box.exact===true?"exacta por lead":"heurística"}</span></div>`;
  }
  const nets = [...new Set(p.pins.map(pt => pt.net).filter(Boolean))];
  const netSample = nets.slice(0, 6).join(", ") + (nets.length > 6 ? `, +${nets.length-6} más` : "");
  return `<div><span class="k">Pines (CPad)</span><span class="verify-ok">${p.pins.length} reales — caja recalculada</span></div>
          <div><span class="k">Redes</span><span style="font-size:12px">${netSample || "-"}</span></div>`;
}

function showDetail(p, zoom){
  const el = document.getElementById("detail");
  el.style.display = "block";
  el.innerHTML = `
    <div><span class="k">Referencia</span><b>${p.code}</b></div>
    ${p.port ? `<div><span class="k">Puerto</span><span class="port-tag" style="font-size:14px">${p.port}</span></div>` : ""}
    <div><span class="k">Descripción</span>${p.desc || "-"}</div>
    <div><span class="k">P/N</span>${p.pn || "-"}</div>
    <div><span class="k">Footprint</span>${p.footprint || "-"}</div>
    <div><span class="k">Cara</span>${p.plane === "1" ? "TOP (componente)" : p.plane === "10" ? "BOTTOM (soldadura)" : (p.plane||"-")}</div>
    <div><span class="k">Coord. (mils)</span>${Math.round(p.cx)}, ${Math.round(p.cy)}</div>
    <div><span class="k">Hoja esquem.</span>${p.page ? ("#" + p.page) : "-"}</div>
    ${verifyLine(p)}
    ${pinsLine(p)}
  `;
  if (zoom) focusOn(p);
}

let panZoomInst = null;
// Centra y hace zoom sobre un punto (cx,cy) en coordenadas del viewBox
// original, de forma que un recuadro de w x h (en esas mismas unidades,
// más margen) entre completo en pantalla. Usa la fórmula estándar de
// svg-pan-zoom: screen = (svgUnit - viewBox.origin) * realZoom * zoom + pan
function focusOn(p){
  if (!panZoomInst) return;
  const margin = 1.6; // deja aire alrededor del componente
  const w = p.box.w * margin + 800, h = p.box.h * margin + 800;
  const sizes = panZoomInst.getSizes();
  const zoomX = sizes.width / (w * sizes.realZoom);
  const zoomY = sizes.height / (h * sizes.realZoom);
  const targetZoom = Math.min(Math.min(zoomX, zoomY), MAX_ZOOM);
  panZoomInst.zoom(targetZoom);
  const vb = sizes.viewBox;
  const panX = sizes.width / 2 - (p.cx - vb.x) * sizes.realZoom * targetZoom;
  const panY = sizes.height / 2 - (p.cy - vb.y) * sizes.realZoom * targetZoom;
  panZoomInst.pan({x: panX, y: panY});
}

function doSearch(){
  const q = document.getElementById("q").value.trim();
  if (!q) return;
  const codes = q.split(",").map(s => s.trim()).filter(Boolean);
  const found = highlight(codes);
  const resDiv = document.getElementById("results");
  resDiv.innerHTML = "";
  if (found.length === 0){
    resDiv.innerHTML = `<div class="res-item">Sin coincidencia exacta. Escribí la referencia tal como figura en el esquemático (ej. "U4").</div>`;
    return;
  }
  found.forEach(p => {
    const d = document.createElement("div");
    d.className = "res-item";
    d.innerHTML = `<b>${p.code}</b> — ${p.desc || p.footprint} (hoja #${p.page || "?"})`;
    d.onclick = () => showDetail(p, true);
    resDiv.appendChild(d);
  });
  showDetail(found[0], true);
}

function applySideFilter(){
  drawBoard(document.getElementById("sideFilter").value);
}

function buildLegend(){
  const el = document.getElementById("legend");
  const rows = Object.entries(CATEGORY_STYLE).map(([key, st]) => {
    const count = DATA.filter(p => p.category === key).length;
    if (count === 0) return "";
    return `<div><span class="cat-swatch" style="background:${st.fill};border-color:${st.stroke}"></span>${st.label} (${count})</div>`;
  }).join("");
  el.innerHTML = `
    ${rows}
    <div style="margin-top:8px">Cara BOTTOM (soldadura) se dibuja más tenue (opacidad reducida) que TOP.</div>
    <div><span class="swatch" style="background:var(--copper-pad);border-radius:0"></span> Pin real (posición y red decodificadas de la sección CPad del .CST) &mdash; pasá el mouse para ver la red</div>
    <div><span class="swatch" style="background:none;border-top:2px solid var(--copper-pad)"></span> Pista de cobre real (sección CLin) &mdash; todas las capas superpuestas, sin distinguir top/bottom</div>
    <div><span class="swatch" style="background:none;border:2px dashed var(--muted)"></span> Caja heurística (sin pines reales ni coords de lead — sólo estimación por cantidad de pines)</div>
    <div><span class="swatch" style="background:none;border:2px solid #ff3b3b"></span> Discrepancia .LST vs .CST (ver detalle antes de confiar en la posición)</div>
    <div style="margin-top:8px">El <b>contorno de placa es una envolvente cóncava</b> calculada sobre la densidad real de pines (CPad) y pistas (CLin) — sigue los entrantes reales donde no hay datos (confirmado contra el diagrama explosionado del Hardware Maintenance Manual, pág. 148, y contra fotos reales del planar FRU 93P3656), pero no es la silueta recortada exacta: depende de la densidad de puntos disponible, así que puede no calzar al mil en zonas con poca población de componentes.</div>
    <div style="margin-top:8px"><span class="port-tag" style="font-size:12px">J3 · Puerto</span> = <b>puerto externo real</b>, identificado leyendo el refdes directo de la hoja de esquemático correspondiente (no por posición). El contorno se extiende un margen extra en estos puntos para representar la carcasa del conector — ese margen es una <b>estimación estándar por tipo de conector (DB25/VGA/USB/RJ45/jack), no una medición</b> (el .LST sólo trae la huella de los pines, no el cuerpo del conector).</div>
    <div style="margin-top:8px">Tip: el número de <b>hoja de esquemático</b> de cada componente sale en el panel de detalle al buscarlo &mdash; abrilo con la skill <code>x31-schematics</code>.</div>
    <div style="margin-top:8px">Tip: podés abrir este archivo con <code>?find=U4</code> o <code>?find=U4,C233</code> en la URL para que resalte directo al cargar.</div>
  `;
}

function resetView(){
  if (panZoomInst){ panZoomInst.resetZoom(); panZoomInst.resetPan(); }
  clearHighlight();
  document.getElementById("detail").style.display = "none";
  document.getElementById("results").innerHTML = "";
}

function toggleTraces(){
  const layer = document.getElementById("trace-layer");
  const btn = document.getElementById("tracesBtn");
  const hidden = layer.classList.toggle("hidden");
  btn.textContent = hidden ? "Mostrar pistas de cobre" : "Ocultar pistas de cobre";
}

// Las ~84.600 pistas de cobre (un solo <path>, pero con mucha geometría)
// son lo más pesado de renderizar/repintar en cada pan-zoom — arrancan
// ocultas por defecto y se pueden prender con el botón de arriba.
document.getElementById("trace-layer").classList.add("hidden");

drawBoard("all");
buildLegend();

const MAX_ZOOM = 40;
window.addEventListener("load", () => {
  try {
    panZoomInst = svgPanZoom('#board-svg', {
      zoomEnabled: true, panEnabled: true, controlIconsEnabled: true,
      fit: true, center: true, minZoom: 0.3, maxZoom: MAX_ZOOM,
    });
  } catch (e) {
    // Si la librería de pan/zoom no cargó (ej. sin internet), el visor
    // sigue funcionando: el resaltado y la búsqueda no dependen de ella,
    // sólo se pierde el auto-zoom/pan suave.
    console.warn("svg-pan-zoom no disponible, siguiendo sin pan/zoom:", e);
  }
  const params = new URLSearchParams(window.location.search);
  const find = params.get("find");
  if (find){
    document.getElementById("q").value = find;
    doSearch();
  }
});
</script>
</body>
</html>
"""


def main():
    if not LST_PATH.exists():
        print(f"No encuentro {LST_PATH}", file=sys.stderr)
        sys.exit(1)
    parts = parse_lst(LST_PATH)
    if not parts:
        print("No se parseó ningún componente — revisar formato del LST.", file=sys.stderr)
        sys.exit(1)
    lst_by_code = {p["code"]: p for p in parts}

    # boxes/categoría primero: assign_pins_to_parts (más abajo) necesita la
    # box heurística para la prueba de contención de pines.
    for p in parts:
        p["box"] = estimate_box(p)
        p["category"] = get_category(p["code"])
        p["port"] = PORT_LABELS.get(p["code"])

    cst_records = parse_cst_table(CST_PATH)
    calib = calibrate_cst(lst_by_code, cst_records) if cst_records else None
    verify_summary = cross_validate(parts, cst_records, calib)

    # --- CPad: pines reales por componente (posición + red), decodificados
    # y validados por regresión contra el .LST (ver notas arriba). Opcional:
    # si el .CST no está o algo no calza, seguimos sólo con .LST/CDev.
    pin_summary = {"total_pins": 0, "parts_with_pins": 0, "refined": 0}
    clin_segments = []
    if CST_PATH.exists() and calib is not None:
        raw = CST_PATH.read_bytes()
        tags = parse_section_tags(raw)

        try:
            cdev_end = find_cdev_table_end(raw)
            net_names = parse_net_dictionary(raw, cdev_end)
            cpad_range = section_data_range(tags, "CPad", len(raw))
            pins = parse_cpad_section(raw, cpad_range, net_names, calib)
            assign_pins_to_parts(pins, parts)
            pin_summary["total_pins"] = len(pins)
            pin_summary["parts_with_pins"] = sum(1 for p in parts if p.get("pins"))
        except Exception as e:  # no dejamos que un fallo acá tumbe todo el resto
            print(f"  (aviso: no se pudo decodificar CPad: {e})", file=sys.stderr)

        try:
            clin_range = section_data_range(tags, "CLin", len(raw))
            clin_segments = parse_clin_section(raw, clin_range, calib)
        except Exception as e:
            print(f"  (aviso: no se pudo decodificar CLin: {e})", file=sys.stderr)

    html = build_html(parts, verify_summary, pin_summary, clin_segments)
    OUT_PATH.write_text(html, encoding="utf-8")

    print(f"OK: {len(parts)} componentes -> {OUT_PATH}")
    if calib is None:
        print("  (sin cruce contra .CST: archivo ausente, vacío o formato inesperado)")
    else:
        print(
            f"  cruce contra .CST: {verify_summary['verified']} verificados, "
            f"{verify_summary['mismatch']} discrepancias, "
            f"{verify_summary['missing']} sin registro en .CST "
            f"(tolerancia ±{verify_summary['tolerance']} mils)"
        )
        if verify_summary["mismatch"] > 0:
            print("  ATENCIÓN: hay discrepancias reales entre .LST y .CST — revisar en el visor antes de confiar ciegamente en esas posiciones.")
        print(
            f"  CPad: {pin_summary['total_pins']} pines decodificados, "
            f"{pin_summary['parts_with_pins']} componentes con pines reales, "
            f"{pin_summary['refined']} cajas recalculadas por geometría real."
        )
        print(f"  CLin: {len(clin_segments)} segmentos de pista de cobre decodificados.")


if __name__ == "__main__":
    main()
