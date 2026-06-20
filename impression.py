"""
impression.py — HSHOP V1.0 PLATINIUM
Constantes ESC/POS, construction ticket thermique,
impression (win32print / LPT / série), diagnostic.
"""
import os, sys, logging
from datetime import datetime
from config import (get_logo_path, get_infos_structure, PRINTER_CONFIG_FILE, logger)

# ============================================================
# CONFIG IMPRIMANTE
# ============================================================
def charger_config_imprimante() -> dict:
    import json
    try:
        if os.path.exists(PRINTER_CONFIG_FILE):
            with open(PRINTER_CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception: pass
    return {"active": False, "methode": "win", "nom_imprimante": "",
            "port_serie": "COM1", "baudrate": 9600, "largeur": 32}

def sauver_config_imprimante(cfg: dict):
    import json
    with open(PRINTER_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

# ============================================================
# CONSTANTES ESC/POS
# ============================================================
ESC = b'\x1b'; GS = b'\x1d'
ESC_INIT      = ESC + b'@'
ESC_ALIGN_L   = ESC + b'a\x00'
ESC_ALIGN_C   = ESC + b'a\x01'
ESC_ALIGN_R   = ESC + b'a\x02'
ESC_BOLD_ON   = ESC + b'E\x01'
ESC_BOLD_OFF  = ESC + b'E\x00'
ESC_DOUBLE_ON = GS  + b'!\x11'
ESC_DOUBLE_OFF= GS  + b'!\x00'
ESC_UNDER_ON  = ESC + b'-\x01'
ESC_UNDER_OFF = ESC + b'-\x00'
ESC_CUT       = GS  + b'V\x42\x00'
ESC_FEED      = b'\n'

def _ligne(texte: str, largeur: int = 32) -> bytes:
    return texte.encode("cp437", errors="replace")[:largeur] + b'\n'

def _separateur(largeur: int = 32, char: str = "-") -> bytes:
    return (char * largeur).encode("cp437") + b'\n'

def _ligne_2col(gauche: str, droite: str, largeur: int = 32) -> bytes:
    espace = max(1, largeur - len(gauche) - len(droite))
    return _ligne(gauche + " " * espace + droite, largeur)

def logo_vers_escpos(logo_path: str, largeur_px: int = 256) -> bytes:
    try:
        from PIL import Image as PILImage
        img = PILImage.open(logo_path).convert("L")
        ratio = largeur_px / img.width
        img = img.resize((largeur_px, max(1, int(img.height * ratio))), PILImage.LANCZOS)
        img = img.point(lambda p: 0 if p < 128 else 255, '1')
        w, h = img.size; w_bytes = (w + 7) // 8
        pixels = img.load(); bitmap = bytearray()
        for y in range(h):
            for bx in range(w_bytes):
                byte = 0
                for bit in range(8):
                    x = bx * 8 + bit
                    val = (0 if pixels[x, y] == 0 else 1) if x < w else 1
                    byte |= (val << (7 - bit))
                bitmap.append(byte)
        xL = w_bytes & 0xFF; xH = (w_bytes >> 8) & 0xFF
        yL = h & 0xFF; yH = (h >> 8) & 0xFF
        return b'\x1d\x76\x30\x00' + bytes([xL, xH, yL, yH]) + bytes(bitmap)
    except Exception as e:
        logger.warning(f"[Logo ESC/POS] {e}"); return b''

def construire_ticket_escpos(vendeur, panier, total, recu, monnaie,
                              id_vente, mode, client_nom=None, largeur=32,
                              remise_globale=0.0) -> bytes:
    buf = bytearray()
    buf += ESC_INIT
    logo = get_logo_path()
    if logo:
        ld = logo_vers_escpos(logo, largeur_px=200)
        if ld: buf += ESC_ALIGN_C + ld + ESC_FEED
    buf += ESC_ALIGN_C + ESC_DOUBLE_ON + ESC_BOLD_ON
    nom, adr, tel = get_infos_structure()
    buf += nom[:largeur].center(largeur // 2).encode("cp437", errors="replace") + b'\n'
    buf += ESC_DOUBLE_OFF + ESC_BOLD_OFF + ESC_ALIGN_C
    buf += _ligne(tel[:largeur].center(largeur), largeur)
    buf += _separateur(largeur, "=")
    buf += ESC_ALIGN_C + ESC_BOLD_ON
    buf += _ligne("Bon de commande".center(largeur), largeur)
    buf += ESC_BOLD_OFF + _separateur(largeur, "-") + ESC_ALIGN_L
    buf += _ligne(f"Rfc N. {id_vente:08d}-{id_vente % 1000:03d}", largeur)
    buf += _ligne(f"Rmc N  {id_vente:06d}", largeur)
    now = datetime.now()
    buf += ESC_ALIGN_C + _ligne("Date de saisie".center(largeur), largeur)
    buf += ESC_BOLD_ON + _ligne(now.strftime("%d/%m/%Y").center(largeur), largeur) + ESC_BOLD_OFF
    buf += _ligne(now.strftime("%H:%M:%S").center(largeur), largeur) + ESC_ALIGN_L
    if client_nom: buf += _ligne(f"Client : {client_nom}"[:largeur], largeur)
    buf += _ligne(f"Vendeur: {vendeur}"[:largeur], largeur)
    buf += _ligne(f"Imprime {now.strftime('%d/%m/%Y %H:%M')}"[:largeur], largeur)
    buf += _separateur(largeur, "-")
    col_des = largeur - 18
    buf += ESC_BOLD_ON
    buf += _ligne(("Designation".ljust(col_des) + "Qte".center(8) + "P.Unit".rjust(8))[:largeur], largeur)
    buf += ESC_BOLD_OFF + _separateur(largeur, "-")
    sous_total_brut = 0.0
    remise_articles_total = 0.0
    for it in panier:
        nd = it['nom'][:col_des].ljust(col_des)
        q  = (f"{it['qty']:.3f}".rstrip('0').rstrip('.') if it['qty'] != int(it['qty']) else f"{int(it['qty'])}").center(8)
        pu = f"{it['prix']:,.0f}".rjust(8)
        buf += _ligne(nd + q + pu, largeur)
        ligne_brute = it['prix'] * it['qty']
        remise_art_pct = it.get('remise', 0.0) or 0.0
        sous_total_brut += ligne_brute
        if remise_art_pct > 0:
            ligne_nette = ligne_brute * (1 - remise_art_pct / 100.0)
            remise_articles_total += (ligne_brute - ligne_nette)
            buf += _ligne(f"  remise {remise_art_pct:.0f}%"[:largeur], largeur)
            buf += _ligne(f"  => {ligne_nette:,.0f} FCFA"[:largeur], largeur)
        else:
            buf += _ligne(f"  => {ligne_brute:,.0f} FCFA"[:largeur], largeur)
    buf += _separateur(largeur, "=") + ESC_ALIGN_L
    remise_g = max(0.0, remise_globale or 0.0)
    if remise_articles_total > 0 or remise_g > 0:
        buf += _ligne_2col("Sous-total", f"{sous_total_brut:,.0f}", largeur)
        if remise_articles_total > 0:
            buf += _ligne_2col("Remise articles", f"-{remise_articles_total:,.0f}", largeur)
        if remise_g > 0:
            buf += _ligne_2col("Remise globale", f"-{remise_g:,.0f}", largeur)
        buf += _separateur(largeur, "-")
    buf += _ligne(f"Paye : {mode}"[:largeur], largeur) + _separateur(largeur, "-")
    buf += ESC_ALIGN_L + ESC_BOLD_ON + ESC_DOUBLE_ON
    buf += f"Mnt=".encode("cp437") + f"{total:,.0f} FCFA".encode("cp437", errors="replace") + b'\n'
    buf += ESC_DOUBLE_OFF + ESC_BOLD_OFF
    if monnaie > 0:
        buf += _ligne(f"Recu  : {recu:,.0f} FCFA"[:largeur], largeur)
        buf += _ligne(f"Rendu : {monnaie:,.0f} FCFA"[:largeur], largeur)
    buf += ESC_FEED + ESC_ALIGN_C
    barval = f"{id_vente:06d}".encode("ascii")
    buf += GS + b'h\x50' + GS + b'w\x02' + GS + b'H\x02' + GS + b'f\x00'
    buf += GS + b'k\x49' + bytes([len(barval)]) + barval
    buf += b'\n' + ESC_ALIGN_C
    buf += _ligne("Merci de votre fidelite !".center(largeur), largeur)
    buf += _ligne("Marchandises non reprises".center(largeur), largeur)
    buf += b'\n\n\n' + ESC_CUT
    return bytes(buf)

def imprimer_ticket_thermique(vendeur, panier, total, recu, monnaie,
                               id_vente, mode, client_nom=None, callback_erreur=None,
                               remise_globale=0.0):
    cfg = charger_config_imprimante()
    if not cfg.get("active", False): return
    largeur = int(cfg.get("largeur", 32))
    methode = cfg.get("methode", "win")

    def _notifier(msg):
        if callback_erreur:
            try: callback_erreur(msg)
            except Exception: pass
        logger.warning(f"[Imprimante] {msg}")

    try:
        data = construire_ticket_escpos(vendeur, panier, total, recu, monnaie,
                                        id_vente, mode, client_nom, largeur,
                                        remise_globale=remise_globale)
        if methode == "win":
            import win32print
            nom = cfg.get("nom_imprimante", "").strip() or win32print.GetDefaultPrinter()
            h = win32print.OpenPrinter(nom)
            try:
                win32print.StartDocPrinter(h, 1, ("Ticket", None, "RAW"))
                win32print.StartPagePrinter(h)
                win32print.WritePrinter(h, data)
                win32print.EndPagePrinter(h)
                win32print.EndDocPrinter(h)
            finally:
                win32print.ClosePrinter(h)
        elif methode == "lpt":
            with open(cfg.get("port_serie", "LPT1"), "wb") as f: f.write(data)
        elif methode == "usb_serie":
            import serial
            with serial.Serial(cfg.get("port_serie", "COM1"),
                               baudrate=int(cfg.get("baudrate", 9600)), timeout=5) as s:
                s.write(data)
    except ImportError as e:
        _notifier(f"Module manquant : {e} → pip install pywin32")
    except Exception as e:
        _notifier(f"Erreur impression ({methode}) : {e}")

def diagnostiquer_impression() -> str:
    lignes = []
    cfg = charger_config_imprimante()
    lignes += [
        f"📄 Fichier config : {PRINTER_CONFIG_FILE}",
        f"   Existe         : {'Oui' if os.path.exists(PRINTER_CONFIG_FILE) else '❌ Non'}",
        f"   Impression      : {'✅ ACTIVÉE' if cfg.get('active') else '❌ DÉSACTIVÉE'}",
        f"   Méthode         : {cfg.get('methode','win')}",
        f"   Imprimante      : {cfg.get('nom_imprimante','(défaut)')}",
        f"   Port série/LPT  : {cfg.get('port_serie','—')}",
        f"   Largeur ticket  : {cfg.get('largeur',32)} caractères", "",
    ]
    try:
        import win32print
        default = win32print.GetDefaultPrinter()
        printers = [p[2] for p in win32print.EnumPrinters(
            win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)]
        lignes += [f"✅ win32print disponible",
                   f"   Imprimante défaut : {default}",
                   f"   Imprimantes dispo : {len(printers)}"]
        for p in printers[:5]: lignes.append(f"     • {p}")
        if len(printers) > 5: lignes.append(f"     … et {len(printers)-5} autre(s)")
    except ImportError:
        lignes.append("❌ win32print NON installé → pip install pywin32")
    except Exception as e:
        lignes.append(f"⚠️  win32print erreur : {e}")
    lignes.append("")
    try:
        import serial; lignes.append("✅ pyserial disponible")
    except ImportError:
        lignes.append("ℹ️  pyserial non installé (nécessaire pour port série/USB)")
    return "\n".join(lignes)
