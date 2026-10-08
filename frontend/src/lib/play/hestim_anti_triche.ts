// SPDX-FileCopyrightText: 2026 HESTIM
//
// SPDX-License-Identifier: MPL-2.0

/**
 * HESTIM, anti-triche pendant une partie (lot 3).
 *
 * - Ordre des réponses mélangé sur chaque téléphone : deux voisins ne voient pas la bonne réponse
 *   au même endroit. Seulement en mode « normal » (le texte des réponses est sur le téléphone) ;
 *   en mode « kahoot », le téléphone n'affiche que des formes qui doivent correspondre au
 *   projecteur. La réponse est envoyée par son texte (ou par sa position d'origine pour les cases
 *   à cocher) : la correction ne change pas.
 * - Journal des sorties : chaque sortie de l'onglet ou de l'application pendant une question
 *   (plus d'une seconde) est signalée au serveur, qui la compte pour l'enseignant.
 */

/** Positions d'origine des réponses, dans l'ordre où les afficher. */
export const ordreAffichage = (nombre: number, game_mode: string): number[] => {
	const ordre = Array.from({ length: nombre }, (_, i) => i);
	if (game_mode !== 'normal') return ordre;
	// Mélange de Fisher-Yates, hasard non prévisible
	const hasard = new Uint32Array(Math.max(nombre, 1));
	crypto.getRandomValues(hasard);
	for (let i = nombre - 1; i > 0; i--) {
		const j = hasard[i] % (i + 1);
		[ordre[i], ordre[j]] = [ordre[j], ordre[i]];
	}
	return ordre;
};

const SORTIE_MIN_MS = 1000;

/**
 * Surveille les sorties pendant une question : `active()` dit si la question attend encore une
 * réponse ; `signaler(duree_ms)` envoie la sortie. Renvoie la fonction d'arrêt (qui signale une
 * sortie encore en cours, par exemple si la question se termine pendant l'absence).
 */
export const suivreSorties = (
	active: () => boolean,
	signaler: (duree_ms: number) => void
): (() => void) => {
	let depuis: number | null = null;
	const partir = () => {
		if (depuis === null && active()) depuis = Date.now();
	};
	const revenir = () => {
		if (depuis === null) return;
		const duree = Date.now() - depuis;
		depuis = null;
		if (duree >= SORTIE_MIN_MS) signaler(duree);
	};
	// Onglet ou application en arrière-plan (téléphone), autre fenêtre au premier plan (ordinateur)
	const visibilite = () => (document.hidden ? partir() : revenir());
	const retour = () => {
		if (!document.hidden) revenir();
	};
	document.addEventListener('visibilitychange', visibilite);
	window.addEventListener('blur', partir);
	window.addEventListener('focus', retour);
	return () => {
		document.removeEventListener('visibilitychange', visibilite);
		window.removeEventListener('blur', partir);
		window.removeEventListener('focus', retour);
		revenir();
	};
};
