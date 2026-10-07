<!--
SPDX-FileCopyrightText: 2023 Marlon W (Mawoka)
SPDX-FileCopyrightText: 2026 HESTIM

SPDX-License-Identifier: MPL-2.0
-->

<!--
	HESTIM : page d'erreur au style du panneau des départs (code en cases à volets, message,
	retour à l'accueil). Plus d'image chargée depuis un site externe (http.cat).
-->
<script lang="ts">
	import { navbarVisible } from '$lib/stores.svelte.ts';
	import { page } from '$app/state';
	import { getLocalization } from '$lib/i18n';

	navbarVisible.visible = true;
	let status = page.status;
	const { t } = getLocalization();
</script>

<svelte:head>
	<title>{$t('words.error')} - {status}</title>
</svelte:head>

<main class="flex min-h-[calc(100vh-4rem)] items-center justify-center px-4 py-12">
	<div class="w-full max-w-xl rounded-[6px] bg-[#001861] p-2 shadow-lg">
		<div class="rounded-[4px] bg-[#0b0b0d] px-6 py-10 text-center text-[#f2f1ec]">
			<div class="flex justify-center gap-2" aria-hidden="true">
				{#each String(status).split('') as chiffre}
					<span
						class="font-display flex h-24 w-16 items-center justify-center rounded-[4px] bg-[#212124] text-6xl font-bold shadow-[inset_0_-2px_0_#000]"
						>{chiffre}</span
					>
				{/each}
			</div>
			<h1 class="sr-only">{status}</h1>
			<p class="mt-6 text-lg text-[#a6a6ac]">
				{status === 404 ? $t('error_page.404_text') : $t('error_page.unknown_error_text')}
			</p>
			<a
				href="/"
				class="font-display mt-8 inline-block rounded-[4px] bg-[#f2f1ec] px-6 py-3 font-bold uppercase tracking-[0.1em] text-[#0b0b0d] hover:bg-white"
				>{$t('hestim.erreur.retour')}</a
			>
		</div>
	</div>
</main>
