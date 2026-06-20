"""
config.py — HSHOP V2.0 PLATINIUM
Constantes globales, chemins, configuration application,
sauvegarde, horaires, sécurité (hash mdp).
"""
import os, sys, json, shutil, hashlib, logging
from datetime import datetime

try:
    import bcrypt as _bcrypt
    _BCRYPT_OK = True
except ImportError:
    _BCRYPT_OK = False

# ── Logger (partagé par tous les modules) ────────────────────
def setup_logger() -> logging.Logger:
    from logging.handlers import RotatingFileHandler
    _log_path = os.path.join(
        os.path.dirname(sys.executable) if getattr(sys, "frozen", False)
        else os.path.dirname(os.path.abspath(__file__)),
        "hshop_v2.log"
    )
    _fmt = logging.Formatter(
        "%(asctime)s [%(levelname)-8s] %(module)s.%(funcName)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    _lg = logging.getLogger("hshop")
    if _lg.handlers:          # éviter les doublons si importé plusieurs fois
        return _lg
    _lg.setLevel(logging.DEBUG)
    try:
        _fh = RotatingFileHandler(_log_path, maxBytes=1_000_000, backupCount=5, encoding="utf-8")
        _fh.setLevel(logging.INFO)
        _fh.setFormatter(_fmt)
        _lg.addHandler(_fh)
    except Exception:
        pass
    _ch = logging.StreamHandler()
    _ch.setLevel(logging.WARNING)
    _ch.setFormatter(_fmt)
    _lg.addHandler(_ch)
    return _lg

logger = setup_logger()

# ============================================================
# CONSTANTES PERSONNALISABLES PAR CLIENT
# ============================================================
NOM_STRUCTURE           = "SODIPAL SARL"
ADRESSE_STRUCTURE       = "Bobo-Dioulasso, Burkina Faso"
TEL_STRUCTURE           = "Tel :+22677290509 wtsp 57035304"
SALT                    = "HSHOP_SECURE_2026_V1"        # ← changer par client avant déploiement
SEUIL_STOCK_BAS_DEFAULT = 5
BACKUP_DEFAULT_DIR      = "sauvegardes"
LOGO_DISPLAY_SIZE       = (80, 80)

# Couleurs alerte stock (Treeview tags)
COLOR_STOCK_OK   = ""
COLOR_STOCK_BAS  = "#fff3cd"
COLOR_STOCK_VIDE = "#f8d7da"

# ============================================================
# CHEMINS
# ============================================================
def get_base_dir() -> str:
    """Dossier de base : dossier du .exe compilé ou du script .py."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

LOGO_PATH            = os.path.join(get_base_dir(), "logo.png")
BACKUP_CONFIG_FILE   = os.path.join(get_base_dir(), "backup_config.json")
APP_CONFIG_FILE      = os.path.join(get_base_dir(), "app_config.json")
PRINTER_CONFIG_FILE  = os.path.join(get_base_dir(), "printer_config.json")
LICENCE_FILE         = os.path.join(get_base_dir(), "licence.key")
HORAIRES_CONFIG_FILE = os.path.join(get_base_dir(), "horaires_caisse.json")

# ============================================================
# HELPERS GÉNÉRAUX
# ============================================================
def get_logo_path():
    """Cherche logo.png dans plusieurs emplacements possibles."""
    candidats = [
        LOGO_PATH,
        os.path.join(get_base_dir(), "logo.png"),
        os.path.join(os.path.dirname(sys.executable), "logo.png") if getattr(sys, "frozen", False) else None,
        os.path.join(os.getcwd(), "logo.png"),
    ]
    for p in candidats:
        if p and os.path.exists(p):
            return p
    return None

def ouvrir_fichier(chemin):
    import subprocess
    from tkinter import messagebox
    # Normaliser le chemin : évite WinError 2 causé par les slashes "/"
    chemin = os.path.normpath(chemin)
    try:
        if sys.platform == "win32":
            os.startfile(chemin)
        elif sys.platform == "darwin":
            subprocess.call(["open", chemin])
        else:
            subprocess.call(["xdg-open", chemin])
    except Exception as e:
        messagebox.showinfo("Fichier généré",
            f"✅ Fichier sauvegardé :\n{chemin}\n\n(Impossible d'ouvrir automatiquement : {e})\n\nOuvrez-le manuellement.")

def fmt_date(s) -> str:
    """Convertit une date SQLite (AAAA-MM-JJ…) en JJ/MM/AAAA [HH:MM]."""
    if not s: return ""
    s = str(s).strip()
    try:
        if len(s) >= 19:
            return datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
        elif len(s) >= 16:
            return datetime.strptime(s[:16], "%Y-%m-%d %H:%M").strftime("%d/%m/%Y %H:%M")
        elif len(s) >= 10:
            return datetime.strptime(s[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
    except Exception:
        pass
    return s

def parse_date_fr(s: str) -> str:
    """Convertit JJ/MM/AAAA → AAAA-MM-JJ. Lève ValueError si invalide."""
    s = s.strip()
    if not s: return ""
    if len(s) == 10 and s[4] == "-":
        datetime.strptime(s, "%Y-%m-%d")
        return s
    return datetime.strptime(s, "%d/%m/%Y").strftime("%Y-%m-%d")

# ============================================================
# SÉCURITÉ — MOT DE PASSE
# ============================================================
def hacher_mdp(mdp: str) -> str:
    """Hache avec bcrypt (rounds=12) ou SHA-256 en fallback."""
    if _BCRYPT_OK:
        return _bcrypt.hashpw(mdp.encode("utf-8"), _bcrypt.gensalt(rounds=12)).decode("utf-8")
    return hashlib.sha256((mdp + SALT).encode("utf-8")).hexdigest()

def verifier_mdp(mdp: str, hash_stocke: str) -> bool:
    """Vérifie un mdp. Supporte bcrypt ET l'ancien SHA-256 (migration transparente)."""
    if not hash_stocke:
        return False
    if hash_stocke.startswith("$2b$") or hash_stocke.startswith("$2a$"):
        if _BCRYPT_OK:
            try:
                return _bcrypt.checkpw(mdp.encode("utf-8"), hash_stocke.encode("utf-8"))
            except Exception:
                return False
        return False
    return hashlib.sha256((mdp + SALT).encode("utf-8")).hexdigest() == hash_stocke

# ============================================================
# CONFIG APPLICATION
# ============================================================
def charger_app_config() -> dict:
    defaut = {
        "db_path":           "hshop_v21.db",
        "seuil_stock_bas":   SEUIL_STOCK_BAS_DEFAULT,
        "nom_structure":     NOM_STRUCTURE,
        "adresse_structure": ADRESSE_STRUCTURE,
        "tel_structure":     TEL_STRUCTURE,
    }
    if os.path.exists(APP_CONFIG_FILE):
        try:
            with open(APP_CONFIG_FILE, "r", encoding="utf-8") as f:
                defaut.update(json.load(f))
        except Exception as e:
            logger.warning(f"charger_app_config — lecture échouée : {e}")
    return defaut

def sauvegarder_app_config(cfg: dict):
    with open(APP_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

def get_infos_structure() -> tuple:
    """Retourne (nom, adresse, tel) depuis la config."""
    cfg = charger_app_config()
    return (
        cfg.get("nom_structure",     NOM_STRUCTURE),
        cfg.get("adresse_structure", ADRESSE_STRUCTURE),
        cfg.get("tel_structure",     TEL_STRUCTURE),
    )

def get_infos_fiscales() -> tuple:
    """Retourne (ifu, rccm) depuis la config."""
    cfg = charger_app_config()
    return (
        cfg.get("ifu_structure",  ""),
        cfg.get("rccm_structure", ""),
    )

def get_db_path() -> str:
    """
    Détermine le chemin de la base de données.

    Toujours privilégier le fichier hshop_v21.db situé à côté de l'exécutable
    (get_base_dir()) : c'est l'emplacement attendu sur n'importe quel poste.

    Si app_config.json contient un chemin absolu (ex: copié depuis un autre
    poste), on ne lui fait confiance que s'il pointe vers un fichier qui
    existe réellement sur CETTE machine. Sinon on retombe sur le chemin local
    et on auto-corrige app_config.json pour éviter que le problème revienne.
    """
    cfg = charger_app_config()
    p = cfg.get("db_path", "hshop_v21.db")
    chemin_local = os.path.join(get_base_dir(), os.path.basename(p) if os.path.isabs(p) else p)

    if os.path.isabs(p):
        if os.path.exists(p):
            return p
        # Chemin absolu invalide sur cette machine → on bascule sur le fichier local
        logger.warning(
            f"get_db_path — chemin absolu introuvable sur ce poste ({p}), "
            f"bascule sur le fichier local : {chemin_local}"
        )
        if os.path.exists(chemin_local):
            try:
                cfg["db_path"] = os.path.basename(p)  # redevient relatif désormais
                sauvegarder_app_config(cfg)
                logger.info("get_db_path — app_config.json auto-corrigé en chemin relatif.")
            except Exception as e:
                logger.warning(f"get_db_path — auto-correction app_config.json échouée : {e}")
        return chemin_local

    return chemin_local

def get_seuil_stock() -> float:
    return float(charger_app_config().get("seuil_stock_bas", SEUIL_STOCK_BAS_DEFAULT))

# ============================================================
# SAUVEGARDE
# ============================================================
def charger_config_backup() -> dict:
    defaut = {"active": True, "dossier": BACKUP_DEFAULT_DIR, "garder_n": 30}
    if os.path.exists(BACKUP_CONFIG_FILE):
        try:
            with open(BACKUP_CONFIG_FILE, "r", encoding="utf-8") as f:
                defaut.update(json.load(f))
        except Exception as e:
            logger.warning(f"charger_config_backup — lecture échouée : {e}")
    return defaut

def sauvegarder_config_backup(cfg: dict):
    with open(BACKUP_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

def effectuer_sauvegarde() -> tuple:
    cfg = charger_config_backup()
    if not cfg.get("active", True):
        return True, "Sauvegarde désactivée."
    db = get_db_path()
    if not os.path.exists(db):
        return False, "Base de données introuvable."
    dossier_rel = cfg.get("dossier", BACKUP_DEFAULT_DIR)
    dossier = dossier_rel if os.path.isabs(dossier_rel) else os.path.join(get_base_dir(), dossier_rel)
    try:
        os.makedirs(dossier, exist_ok=True)
        horodatage = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = os.path.join(dossier, f"backup_{horodatage}.db")
        shutil.copy2(db, dest)
        garder = int(cfg.get("garder_n", 30))
        fichiers = sorted(f for f in os.listdir(dossier) if f.startswith("backup_") and f.endswith(".db"))
        while len(fichiers) > garder:
            os.remove(os.path.join(dossier, fichiers.pop(0)))
        logger.info(f"Sauvegarde réussie → {dest}")
        return True, os.path.abspath(dest)
    except Exception as e:
        logger.error(f"Sauvegarde échouée : {e}")
        return False, str(e)

# ============================================================
# HORAIRES CAISSE
# ============================================================
def charger_horaires_caisse() -> dict:
    defaut = {"actif": False, "heure_ouverture": "08:00", "heure_fermeture": "18:00"}
    if os.path.exists(HORAIRES_CONFIG_FILE):
        try:
            with open(HORAIRES_CONFIG_FILE, "r", encoding="utf-8") as f:
                defaut.update(json.load(f))
        except Exception as e:
            logger.warning(f"charger_horaires_caisse — lecture échouée : {e}")
    return defaut

def sauver_horaires_caisse(cfg: dict):
    with open(HORAIRES_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
