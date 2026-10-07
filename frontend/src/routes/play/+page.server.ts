// SPDX-FileCopyrightText: 2023 Marlon W (Mawoka)
//
// SPDX-License-Identifier: MPL-2.0

import { signedIn } from '$lib/stores';

export async function load({ url, parent }) {
	const { email } = await parent();
	if (email) {
		signedIn.set(true);
	}
	const token = url.searchParams.get('pin');
	// HESTIM : nom pré-rempli quand l'étudiant arrive depuis la plateforme (?name=), modifiable
	const name = (url.searchParams.get('name') ?? '').trim().slice(0, 40);
	// HESTIM : jeton signé par la plateforme (?hid=), renvoyé avec les scores pour les rattacher
	const hid = url.searchParams.get('hid') ?? '';
	return {
		game_pin: token === null ? '' : token,
		player_name: name,
		hestim: /^[A-Za-z0-9._-]{1,200}$/.test(hid) ? hid : ''
	};
}
