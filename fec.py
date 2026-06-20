# =============================================================================
# fec.py — Module FEC (Facture Électronique Certifiée)
# HSHOP V2.0 PLATINIUM — BIOS CREATIONS
# Préparatoire : fonctionne sans API DGI (mode local signé)
# Compatible API DGI quand la documentation sera disponible
# =============================================================================

import hashlib
import hmac
import sqlite3
import datetime
import os
import io
import logging

logger = logging.getLogger("hshop")

# Clé secrète locale pour signature des factures (à garder confidentielle)
FEC_SECRET = b"HSHOP_FEC_BIOS_CREATIONS_2026_BF"

# Mode FEC : "local" (sans API DGI) ou "dgi" (avec API DGI quand dispo)
FEC_MODE = "local"

# URL API DGI — à renseigner quand la documentation sera disponible
DGI_API_URL = ""
DGI_API_KEY = ""


# =============================================================================
# 1. NUMÉROTATION SÉQUENTIELLE
# =============================================================================

def generer_numero_fec(conn: sqlite3.Connection, prefix: str = "FEC") -> str:
    """
    Génère un numéro de facture FEC séquentiel infalsifiable.
    Format : FEC-2026-000001
    Le compteur est stocké en base et ne peut que croître.
    """
    annee = datetime.datetime.now().year
    cursor = conn.cursor()

    # Créer la table de séquence si elle n'existe pas
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fec_sequences (
            annee     INTEGER PRIMARY KEY,
            compteur  INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.commit()

    # Incrémenter atomiquement
    cursor.execute("""
        INSERT INTO fec_sequences (annee, compteur) VALUES (?, 1)
        ON CONFLICT(annee) DO UPDATE SET compteur = compteur + 1
    """, (annee,))
    conn.commit()

    cursor.execute("SELECT compteur FROM fec_sequences WHERE annee = ?", (annee,))
    row = cursor.fetchone()
    compteur = row[0] if row else 1

    return f"{prefix}-{annee}-{compteur:06d}"


# =============================================================================
# 2. SIGNATURE HMAC (intégrité de la facture)
# =============================================================================

def signer_facture(numero: str, montant: float, ifu: str, date_heure: str) -> str:
    """
    Génère une signature HMAC-SHA256 pour garantir l'intégrité des données.
    Retourne les 16 premiers caractères en hexadécimal (compact, lisible).
    """
    payload = f"{numero}|{montant:.0f}|{ifu}|{date_heure}"
    signature = hmac.new(FEC_SECRET, payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return signature[:16].upper()


# =============================================================================
# 3. GÉNÉRATION DU QR CODE
# =============================================================================

def generer_qr_bytes(numero: str, montant: float, ifu: str,
                     date_heure: str, signature: str) -> bytes | None:
    """
    Génère un QR code contenant les données clés de la facture FEC.
    Retourne les bytes PNG du QR code, ou None si qrcode non installé.
    
    Contenu du QR : numéro|montant|IFU|date|signature
    """
    try:
        import qrcode
        from qrcode.image.pure import PyPNGImage

        data = f"{numero}|{montant:.0f}|{ifu}|{date_heure}|{signature}"

        qr = qrcode.QRCode(
            version=2,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=4,
            border=2,
        )
        qr.add_data(data)
        qr.make(fit=True)

        img = qr.make_image(image_factory=PyPNGImage)
        buffer = io.BytesIO()
        img.save(buffer)
        return buffer.getvalue()

    except ImportError:
        logger.warning("FEC: bibliothèque qrcode non installée — QR code ignoré")
        return None
    except Exception as e:
        logger.error(f"FEC: erreur génération QR code — {e}")
        return None


# =============================================================================
# 4. ENREGISTREMENT EN BASE
# =============================================================================

def init_table_fec(conn: sqlite3.Connection):
    """Crée la table fec_factures si elle n'existe pas."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fec_factures (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            numero       TEXT    NOT NULL UNIQUE,
            vente_id     INTEGER,
            montant      REAL    NOT NULL,
            ifu_vendeur  TEXT,
            date_heure   TEXT    NOT NULL,
            signature    TEXT    NOT NULL,
            qr_bytes     BLOB,
            mode         TEXT    DEFAULT 'local',
            statut       TEXT    DEFAULT 'emise',
            created_at   TEXT    DEFAULT (datetime('now','localtime'))
        )
    """)
    conn.commit()


def enregistrer_fec(conn: sqlite3.Connection, numero: str, vente_id: int,
                    montant: float, ifu: str, date_heure: str,
                    signature: str, qr_bytes: bytes | None) -> int:
    """
    Insère la facture FEC en base.
    Retourne l'ID de la ligne insérée.
    """
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO fec_factures
            (numero, vente_id, montant, ifu_vendeur, date_heure, signature, qr_bytes, mode)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (numero, vente_id, montant, ifu, date_heure, signature, qr_bytes, FEC_MODE))
    conn.commit()
    return cursor.lastrowid


# =============================================================================
# 5. FONCTION PRINCIPALE — à appeler lors de chaque vente
# =============================================================================

def emettre_facture_fec(conn: sqlite3.Connection, vente_id: int,
                        montant: float, ifu: str = "") -> dict:
    """
    Point d'entrée principal du module FEC.
    Appeler cette fonction juste après l'enregistrement d'une vente.

    Paramètres :
        conn      : connexion SQLite active
        vente_id  : ID de la vente dans la table `ventes`
        montant   : montant total TTC de la vente
        ifu       : IFU de la structure (récupéré depuis config)

    Retourne un dict avec toutes les données FEC :
        {
            "numero"     : "FEC-2026-000042",
            "date_heure" : "2026-06-14 10:35:22",
            "signature"  : "A3F1B2C4D5E6F708",
            "qr_bytes"   : b"...",   # bytes PNG ou None
            "fec_id"     : 42
        }
    """
    init_table_fec(conn)

    date_heure = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    numero = generer_numero_fec(conn)
    signature = signer_facture(numero, montant, ifu, date_heure)
    qr_bytes = generer_qr_bytes(numero, montant, ifu, date_heure, signature)
    fec_id = enregistrer_fec(conn, numero, vente_id, montant, ifu,
                             date_heure, signature, qr_bytes)

    logger.info(f"FEC émise : {numero} | vente_id={vente_id} | montant={montant:.0f} FCFA")

    # Si mode DGI activé, envoyer à l'API (placeholder)
    if FEC_MODE == "dgi" and DGI_API_URL:
        _envoyer_dgi(numero, montant, ifu, date_heure, signature)

    return {
        "numero"    : numero,
        "date_heure": date_heure,
        "signature" : signature,
        "qr_bytes"  : qr_bytes,
        "fec_id"    : fec_id,
    }


# =============================================================================
# 6. PLACEHOLDER API DGI (à compléter quand doc disponible)
# =============================================================================

def _envoyer_dgi(numero: str, montant: float, ifu: str,
                 date_heure: str, signature: str):
    """
    Envoi de la facture à l'API DGI Burkina Faso.
    À implémenter quand la documentation technique sera disponible.
    """
    try:
        import urllib.request
        import json

        payload = json.dumps({
            "numero"    : numero,
            "montant"   : montant,
            "ifu"       : ifu,
            "date_heure": date_heure,
            "signature" : signature,
        }).encode("utf-8")

        req = urllib.request.Request(
            DGI_API_URL,
            data=payload,
            headers={
                "Content-Type" : "application/json",
                "Authorization": f"Bearer {DGI_API_KEY}",
            }
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            logger.info(f"FEC DGI: réponse {resp.status} pour {numero}")

    except Exception as e:
        logger.error(f"FEC DGI: échec envoi {numero} — {e}")
        # On ne bloque pas la vente si l'API DGI est indisponible


# =============================================================================
# 7. UTILITAIRES
# =============================================================================

def get_fec_by_vente(conn: sqlite3.Connection, vente_id: int) -> dict | None:
    """Récupère les données FEC d'une vente par son ID."""
    cursor = conn.execute(
        "SELECT * FROM fec_factures WHERE vente_id = ?", (vente_id,)
    )
    row = cursor.fetchone()
    if not row:
        return None
    cols = [d[0] for d in cursor.description]
    return dict(zip(cols, row))


def get_fec_by_numero(conn: sqlite3.Connection, numero: str) -> dict | None:
    """Récupère une facture FEC par son numéro."""
    cursor = conn.execute(
        "SELECT * FROM fec_factures WHERE numero = ?", (numero,)
    )
    row = cursor.fetchone()
    if not row:
        return None
    cols = [d[0] for d in cursor.description]
    return dict(zip(cols, row))


def verifier_signature(fec: dict) -> bool:
    """
    Vérifie l'intégrité d'une facture FEC stockée en base.
    Retourne True si la signature est valide.
    """
    sig_calculee = signer_facture(
        fec["numero"], fec["montant"],
        fec["ifu_vendeur"] or "", fec["date_heure"]
    )
    return sig_calculee == fec["signature"]


def activer_mode_dgi(api_url: str, api_key: str):
    """Active le mode API DGI quand la documentation sera disponible."""
    global FEC_MODE, DGI_API_URL, DGI_API_KEY
    FEC_MODE = "dgi"
    DGI_API_URL = api_url
    DGI_API_KEY = api_key
    logger.info(f"FEC: mode DGI activé — {api_url}")
