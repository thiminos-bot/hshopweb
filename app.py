import os
from flask import Flask, jsonify
import database  # Ceci importe votre fichier database.py

app = Flask(__name__)

@app.route('/', methods=['GET'])
def home():
    """Point d'entrée pour vérifier que l'API est en ligne."""
    return jsonify({
        "status": "online",
        "message": "Bienvenue sur l'API HSHOP V1.0 PLATINIUM",
        "version": "1.0"
    })

@app.route('/api/status', methods=['GET'])
def db_status():
    """Endpoint de test pour vérifier la connexion à la base de données."""
    try:
        path = database.get_db_path()
        return jsonify({
            "status": "success",
            "database_path": path,
            "message": "Connexion à la base SQLite opérationnelle."
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Erreur lors de l'accès à la base : {str(e)}"
        })

if __name__ == '__main__':
    # Configuration pour le développement local
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)