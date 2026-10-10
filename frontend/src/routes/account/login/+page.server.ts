// SPDX-FileCopyrightText: 2023 Marlon W (Mawoka)
//
// SPDX-License-Identifier: MPL-2.0

import { redirect } from '@sveltejs/kit';

export async function load({ parent, url }) {
	const verified = url.searchParams.get('verified');
	const returnTo =
		url.searchParams.get('returnTo') !== null ? url.searchParams.get('returnTo') : '/dashboard';

	const { email } = await parent();
	if (email) {
		redirect(302, returnTo);
	}
	// HESTIM : l'enseignant qui arrive de Planner (?sso=1) y est déjà connecté ; il est envoyé
	// droit à la connexion par son compte HESTIM, sans passer par cette page.
	if (url.searchParams.get('sso') === '1') {
		redirect(302, '/api/v1/users/oauth/custom/login');
	}
	return {
		verified: verified !== null
	};
}
