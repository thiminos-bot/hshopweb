# database.py — HSHOP V1.0 PLATINIUM
# BIOS Creations — 2026

import sqlite3
import os
import logging

log = logging.getLogger("hshop")
DB_NAME = "hshop_v21.db"

def get_db_path() -> str:
    """Retourne le chemin de la base de données."""
    return os.path.abspath(DB_NAME)

def lire_produits():
    """Récupère tous les produits actifs de la base HSHOP PLATINIUM."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT COALESCE(code_barre, code, '') AS code,
                   nom,
                   categorie,
                   prix_vente,
                   COALESCE(stock, stock_actuel, 0) AS stock_reel,
                   COALESCE(seuil_alerte, stock_min, 0) AS seuil
            FROM produits
            WHERE actif = 1
            ORDER BY nom
        """)
        lignes = cursor.fetchall()
        return [dict(ligne) for ligne in lignes]
    except sqlite3.Error as e:
        log.error(f"Erreur SQL HSHOP Produits : {e}")
        return []  # Retourne une liste vide au lieu de faire crasher le serveur
    finally:
        conn.close()

def ajouter_produit(code, nom, categorie, prix_vente, stock, seuil):
    """Insère un produit selon le schéma officiel HSHOP."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO produits 
            (code_barre, code, nom, categorie, prix_vente, stock, stock_actuel, seuil_alerte, stock_min, actif)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, (code, code, nom, categorie, float(prix_vente), float(stock), float(stock), float(seuil), float(seuil)))
        conn.commit()
        return True
    except sqlite3.Error as e:
        log.error(f"Erreur d'insertion HSHOP : {e}")
        return False
    finally:
        conn.close()

def lire_categories():
    """Récupère toutes les catégories de la base HSHOP."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, nom FROM categories ORDER BY nom")
        lignes = cursor.fetchall()
        return [dict(ligne) for ligne in lignes]
    except sqlite3.Error as e:
        log.error(f"Erreur SQL Catégories : {e}")
        return []  # Retourne une liste vide en cas de problème
    finally:
        conn.close()

def ajouter_categorie(nom):
    """Insère un nouveau rayon en majuscules."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO categories (nom) VALUES (?)", (nom.upper(),))
        conn.commit()
        return True
    except sqlite3.Error as e:
        log.error(f"Erreur insertion Catégorie : {e}")
        return False
    finally:
        conn.close()