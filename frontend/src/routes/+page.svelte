<!--
SPDX-FileCopyrightText: 2023 Marlon W (Mawoka)
SPDX-FileCopyrightText: 2026 HESTIM

SPDX-License-Identifier: MPL-2.0
-->

<!--
	HESTIM : accueil de l'espace Quiz pour un visiteur non connecté (un compte connecté va
	directement à son tableau de bord, voir +page.server.ts). Remplace la vitrine du logiciel
	libre ClassQuiz : rejoindre une partie, se connecter avec son compte HESTIM, et les trois
	façons de jouer. Panneau des départs : cadre bleu marine, cases noir mat, capitales.
-->
<script lang="ts">
	import { navbarVisible } from '$lib/stores.svelte.ts';
	import { getLocalization } from '$lib/i18n';
	import Footer from '$lib/footer.svelte';

	const { t } = getLocalization();
	navbarVisible.visible = true;

	const jeux = [
		{ titre: 'hestim.accueil.direct', texte: 'hestim.accueil.direct_texte' },
		{ titre: 'hestim.accueil.equipes', texte: 'hestim.accueil.equipes_texte' },
		{ titre: 'hestim.accueil.nuage', texte: 'hestim.accueil.nuage_texte' }
	];
</script>

<svelte:head>
	<title>HESTIM Quiz</title>
	<meta name="description" content={$t('hestim.accueil.description')} />
</svelte:head>

<main class="min-h-[calc(100vh-4rem)] px-4 py-12 lg:py-20">
	<section class="mx-auto max-w-5xl">
		<div class="rounded-[6px] bg-[#001861] p-2 shadow-lg">
			<div class="rounded-[4px] bg-[#0b0b0d] px-6 py-12 text-center text-[#f2f1ec] lg:px-16 lg:py-16">
				<img src="/hestim-embleme.png" alt="" width="88" height="88" class="mx-auto rounded-[10px] bg-white p-2" />
				<h1 class="mt-8 text-5xl lg:text-7xl">HESTIM Quiz</h1>
				<p class="mx-auto mt-4 max-w-2xl text-lg lg:text-xl text-[#a6a6ac]">{$t('hestim.accueil.phrase')}</p>
				<div class="mt-10 flex flex-col items-center justify-center gap-3 sm:flex-row">
					<a
						href="/play"
						class="font-display w-full rounded-[4px] bg-[#f2f1ec] px-8 py-3 text-lg font-bold uppercase tracking-[0.1em] text-[#0b0b0d] transition hover:bg-white sm:w-auto"
						>{$t('hestim.accueil.rejoindre')}</a
					>
					<a
						href="/account/login"
						class="font-display w-full rounded-[4px] border border-[#2c2c30] px-8 py-3 text-lg font-bold uppercase tracking-[0.1em] text-[#f2f1ec] transition hover:border-[#a6a6ac] sm:w-auto"
						>{$t('hestim.accueil.connexion')}</a
					>
				</div>
			</div>
		</div>

		<ul class="mt-8 grid gap-4 md:grid-cols-3">
			{#each jeux as jeu}
				<li class="rounded-[6px] border border-gray-200 bg-white p-6 dark:border-[#2c2c30] dark:bg-[#212124]">
					<h2 class="text-xl text-[#001861] dark:text-[#f2f1ec]">{$t(jeu.titre)}</h2>
					<p class="mt-2 text-gray-600 dark:text-[#a6a6ac]">{$t(jeu.texte)}</p>
				</li>
			{/each}
		</ul>
	</section>
</main>

<Footer />
