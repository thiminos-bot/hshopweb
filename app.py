import os
from flask import Flask, jsonify, request
import database  # Fait le lien avec votre fichier database.py

app = Flask(__name__)

# 1. PAGE D'ACCUEIL (La racine qui affiche Bienvenue)
@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "status": "online",
        "message": "Bienvenue sur l'API HSHOP V1.0 PLATINIUM",
        "version": "1.0"
    })

# 2. LISTER LES PRODUITS (GET)
@app.route('/api/produits', methods=['GET'])
def obtenir_produits():
    liste_produits = database.lire_produits()
    if liste_produits is not None:
        return jsonify({"status": "success", "donnees": liste_produits}), 200
    return jsonify({"status": "error", "message": "Impossible de récupérer les produits"}), 500

# 3. AJOUTER UN PRODUIT (POST)
@app.route('/api/produits', methods=['POST'])
def creer_produit():
    data = request.get_json()
    champs_obligatoires = ['code', 'nom', 'prix_vente', 'stock']
    
    if not data or not all(k in data for k in champs_obligatoires):
        return jsonify({"status": "error", "message": "Données incomplètes (code, nom, prix_vente, stock requis)"}), 400
    
    categorie = data.get('categorie', 'GÉNÉRAL')
    seuil = data.get('seuil_alerte', 5)
    
    succes = database.ajouter_produit(
        data['code'], data['nom'], categorie, data['prix_vente'], data['stock'], seuil
    )
    
    if succes:
        return jsonify({"status": "success", "message": f"Produit '{data['nom']}' synchronisé !"}), 201
    return jsonify({"status": "error", "message": "Échec de l'insertion en base"}), 500

# 4. LISTER LES CATÉGORIES / RAYONS (GET)
@app.route('/api/categories', methods=['GET'])
def obtenir_categories():
    liste_cats = database.lire_categories()
    if liste_cats is not None:
        return jsonify({"status": "success", "donnees": liste_cats}), 200
    return jsonify({"status": "error", "message": "Impossible de récupérer les catégories"}), 500

# 5. AJOUTER UNE CATÉGORIE / RAYON (POST)
@app.route('/api/categories', methods=['POST'])
def creer_categorie():
    data = request.get_json()
    if not data or 'nom' not in data:
        return jsonify({"status": "error", "message": "Le champ 'nom' est obligatoire"}), 400
    
    succes = database.ajouter_categorie(data['nom'])
    if succes:
        return jsonify({"status": "success", "message": f"Rayon '{data['nom'].upper()}' ajouté !"}), 201
    return jsonify({"status": "error", "message": "Échec de l'ajout du rayon en base"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)