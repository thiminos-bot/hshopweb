# -*- coding: utf-8 -*-
"""
reconcilier_stock.py — à lancer UNE SEULE FOIS dans C:\\HSHOP_API
(après avoir remplacé database.py par la version corrigée)

Aligne la colonne "stock" sur "stock_actuel" partout où elles divergent.
stock_actuel est la valeur de référence : c'est elle que la caisse, le
dashboard et tous les rapports utilisent.
"""
import database

conn = database.get_connection()
cur = conn.cursor()

cur.execute("SELECT id, nom, stock, stock_actuel FROM produits WHERE stock != stock_actuel")
diffs = cur.fetchall()

if not diffs:
    print("✅ Rien à réconcilier — stock et stock_actuel sont déjà identiques partout.")
else:
    print(f"{len(diffs)} produit(s) à réconcilier :")
    for d in diffs:
        print(f"  - {d['nom']} (id={d['id']}) : stock={d['stock']} → stock_actuel={d['stock_actuel']}")

    cur.execute("UPDATE produits SET stock = stock_actuel WHERE stock != stock_actuel")
    conn.commit()
    print(f"\n✅ {len(diffs)} produit(s) réconcilié(s).")

conn.close()
