import os
from flask import Flask, jsonify, request
import database

app = Flask(__name__)

@app.route('/', methods=['GET'])
def home():
    return jsonify({"status": "online", "message": "Bienvenue sur l'API HSHOP V1.0 PLATINIUM"})

@app.route('/api/produits', methods=['GET'])
def obtenir_produits():
    liste_produits = database.lire_produits()
    if liste_produits is not None:
        return jsonify({"status": "success", "donnees": liste_produits}), 200
    return jsonify({"status": "error", "message": "Impossible de récupérer les produits depuis hshop_v21.db"}), 500

@app.route('/api/produits', methods=['POST'])
def creer_produit():
    data = request.get_json()
    
    # Validation selon vos champs réels
    champs_obligatoires = ['code', 'nom', 'prix_vente', 'stock']
    if not data or not all(k in data for k in champs_obligatoires):
        return jsonify({"status": "error", "message": "Données incomplètes (code, nom, prix_vente, stock requis)"}), 400
    
    # Extraction avec valeurs par défaut optionnelles
    categorie = data.get('categorie', 'GÉNÉRAL')
    seuil = data.get('seuil_alerte', 5)
    
    succes = database.ajouter_produit(
        data['code'], data['nom'], categorie, data['prix_vente'], data['stock'], seuil
    )
    
    if succes:
        return jsonify({"status": "success", "message": f"Produit '{data['nom']}' synchronisé !"}), 201
    return jsonify({"status": "error", "message": "Échec de l'insertion en base de données"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)