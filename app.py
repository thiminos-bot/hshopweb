import os
from flask import Flask, jsonify, request
import database

app = Flask(__name__)

@app.route('/', methods=['GET'])
def home():
    return jsonify({"status": "online", "message": "Bienvenue sur l'API HSHOP V1.0 PLATINIUM"})

# 1. ROUTE POUR LIRE LES PRODUITS (GET)
@app.route('/api/produits', methods=['GET'])
def obtenir_produits():
    liste_produits = database.lire_produits()
    if liste_produits is not None:
        return jsonify({"status": "success", "donnees": liste_produits}), 200
    return jsonify({"status": "error", "message": "Impossible de récupérer les produits"}), 500

# 2. ROUTE POUR AJOUTER UN PRODUIT (POST)
@app.route('/api/produits', methods=['POST'])
def creer_produit():
    data = request.get_json()
    
    # Vérification des données reçues
    if not data or 'nom' not in data or 'prix' not in data or 'quantite' not in data:
        return jsonify({"status": "error", "message": "Données incomplètes"}), 400
    
    succes = database.ajouter_produit(data['nom'], data['prix'], data['quantite'])
    if succes:
        return jsonify({"status": "success", "message": "Produit ajouté avec succès !"}), 201
    return jsonify({"status": "error", "message": "Échec de l'ajout en base"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)