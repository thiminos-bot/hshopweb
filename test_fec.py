# -*- coding: utf-8 -*-
"""
test_fec.py — Diagnostic isolé du module FEC
À lancer directement dans le dossier de l'appli web :

    python test_fec.py

Teste l'émission FEC sur la dernière vente enregistrée et affiche la
trace complète de l'erreur si ça plante — au lieu du message générique
caché dans hshop_v2.log.
"""
import traceback
import database
import config
import fec

print("=" * 60)
print("DIAGNOSTIC FEC")
print("=" * 60)

print(f"Module fec chargé depuis : {fec.__file__}")
print(f"FEC_MODE actuel          : {getattr(fec, 'FEC_MODE', 'introuvable')}")
print(f"Base de données utilisée : {database.get_db_path()}")
print("-" * 60)

conn = database.get_connection()
cur = conn.cursor()
cur.execute("SELECT id, total FROM ventes ORDER BY id DESC LIMIT 1")
row = cur.fetchone()

if not row:
    print("Aucune vente trouvée dans la base — impossible de tester.")
    conn.close()
else:
    vente_id, total = row["id"], row["total"]
    print(f"Test sur la dernière vente : id={vente_id}, total={total}")
    try:
        ifu, rccm = config.get_infos_fiscales()
        print(f"IFU récupéré (config.get_infos_fiscales) : '{ifu}'")
    except Exception:
        print("❌ ERREUR dès config.get_infos_fiscales() :")
        traceback.print_exc()
        ifu = ""

    try:
        result = fec.emettre_facture_fec(conn, vente_id, total, ifu)
        print("\n✅ FEC émise avec succès :")
        for k, v in result.items():
            if k == "qr_bytes" and v:
                print(f"   {k}: <{len(v)} octets PNG>")
            else:
                print(f"   {k}: {v}")
    except Exception:
        print("\n❌ ERREUR lors de fec.emettre_facture_fec() :")
        traceback.print_exc()
    finally:
        conn.close()

print("=" * 60)
