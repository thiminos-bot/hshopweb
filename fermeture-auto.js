// fermeture-auto.js
// Fermeture automatique des comptes CAISSIER/VENDEUR (et magasinier) à une
// heure définie par l'admin dans Paramètres > Horaires de caisse.
// Les comptes admin ne sont JAMAIS déconnectés automatiquement.
// Avertissement non bloquant 30 minutes avant la fermeture.
// À l'heure dite : clôture personnelle automatique (comme un clic sur
// "Clôturer" dans cloture-caisse.html) + téléchargement du PDF, PUIS déconnexion.

(function () {
    const AVERTISSEMENT_MINUTES_AVANT = 30;
    const INTERVALLE_VERIF_MS = 20000; // vérifie toutes les 20 secondes

    let avertissementDejaAffiche = false;
    let fermetureEnCours = false; // évite un double déclenchement pendant la clôture asynchrone
    let heureFermetureMinutes = null; // minutes depuis minuit, ou null si inactif

    function minutesDepuisMinuit(date) {
        return date.getHours() * 60 + date.getMinutes();
    }

    function parserHeure(hhmm) {
        const [h, m] = (hhmm || "18:00").split(":").map(Number);
        return (h || 0) * 60 + (m || 0);
    }

    function creerBandeauAvertissement(minutesRestantes) {
        if (document.getElementById("bandeau-fermeture-auto")) return;
        const bandeau = document.createElement("div");
        bandeau.id = "bandeau-fermeture-auto";
        bandeau.style.cssText = "position:fixed;top:0;left:0;right:0;z-index:9999;background:#F59E0B;color:#fff;" +
            "text-align:center;padding:10px 16px;font-weight:bold;font-size:14px;font-family:sans-serif;" +
            "box-shadow:0 2px 6px rgba(0,0,0,0.15);";
        bandeau.innerText = `⚠️ La caisse va se fermer automatiquement dans ${minutesRestantes} minute(s) — ta caisse sera clôturée et un rapport PDF généré. Pense à finaliser tes opérations en cours.`;
        document.body.prepend(bandeau);
        // Pousse le contenu vers le bas pour ne rien cacher
        document.body.style.paddingTop = (document.body.style.paddingTop ? parseInt(document.body.style.paddingTop) : 0) + 44 + "px";
    }

    function telechargerBlob(blob, nomFichier) {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url; a.download = nomFichier;
        document.body.appendChild(a); a.click(); a.remove();
        window.URL.revokeObjectURL(url);
    }

    function attendre(ms) { return new Promise(resolve => setTimeout(resolve, ms)); }

    async function clotureAutomatiqueEtTelechargement(token) {
        try {
            const reponseCloture = await fetch("/cloture-caisse", {
                method: "POST",
                headers: { "Authorization": `Bearer ${token}`, "Content-Type": "application/json" },
                body: JSON.stringify({ notes: "Clôture automatique — heure de fermeture atteinte", perimetre: "perso" })
            });
            // 400 "rien à clôturer" est normal si le caissier n'a rien vendu/dépensé
            // depuis la dernière clôture — on ignore silencieusement dans ce cas.
            if (!reponseCloture.ok) return;

            const data = await reponseCloture.json();
            const reponsePdf = await fetch(`/cloture-caisse/${data.id}/pdf`, { headers: { "Authorization": `Bearer ${token}` } });
            if (reponsePdf.ok) {
                const blob = await reponsePdf.blob();
                telechargerBlob(blob, `cloture_auto_${data.id}.pdf`);
                await attendre(1500); // laisse le temps au téléchargement de démarrer avant de quitter la page
            }
        } catch (e) { /* la clôture/le PDF ne doivent jamais empêcher la déconnexion */ }
    }

    async function deconnecterAutomatiquement() {
        if (fermetureEnCours) return;
        fermetureEnCours = true;

        const token = localStorage.getItem("hshop_token");
        if (token) await clotureAutomatiqueEtTelechargement(token);

        try { localStorage.clear(); } catch (e) {}
        window.location.href = "login.html?fermeture=auto";
    }

    async function chargerHorairesEtDemarrer() {
        const token = localStorage.getItem("hshop_token");
        const role = localStorage.getItem("hshop_role");
        if (!token) return; // pas connecté, rien à faire ici

        // Jamais de fermeture automatique pour un compte admin.
        if (role === "admin") return;

        try {
            const response = await fetch("/horaires-caisse", { headers: { "Authorization": `Bearer ${token}` } });
            if (!response.ok) return;
            const h = await response.json();
            if (!h.actif) return;

            heureFermetureMinutes = parserHeure(h.heure_fermeture);
            verifierEtAgir(); // vérif immédiate au chargement
            setInterval(verifierEtAgir, INTERVALLE_VERIF_MS);
        } catch (e) { /* pas bloquant : pas de fermeture auto si la config est inaccessible */ }
    }

    function verifierEtAgir() {
        if (heureFermetureMinutes === null || fermetureEnCours) return;
        const maintenant = minutesDepuisMinuit(new Date());
        const minutesAvantFermeture = heureFermetureMinutes - maintenant;

        if (minutesAvantFermeture <= 0) {
            deconnecterAutomatiquement();
            return;
        }
        if (minutesAvantFermeture <= AVERTISSEMENT_MINUTES_AVANT && !avertissementDejaAffiche) {
            avertissementDejaAffiche = true;
            creerBandeauAvertissement(minutesAvantFermeture);
        }
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", chargerHorairesEtDemarrer);
    } else {
        chargerHorairesEtDemarrer();
    }
})();
