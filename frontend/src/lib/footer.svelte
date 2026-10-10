<!--
SPDX-FileCopyrightText: 2023 Marlon W (Mawoka)
SPDX-FileCopyrightText: 2026 HESTIM

SPDX-License-Identifier: MPL-2.0
-->

<!--
	HESTIM : pied de page du panneau (noir mat, filet) ; le choix de la langue, et la mention de
	l'origine du logiciel avec le lien vers ses sources, comme l'exige la licence MPL-2.0.
-->
<script lang="ts">
	import LanguageToggle from './language-toggle.svelte';
	import { getLocalization } from '$lib/i18n';

	const { t } = getLocalization();
	const SOURCES = 'https://github.com/Claude20022002/ClassQuiz';
</script>

<footer class="w-screen bg-[#0b0b0d] text-[#a6a6ac] border-t border-[#2c2c30]">
	<div class="mx-auto flex max-w-6xl flex-col items-center gap-4 px-6 py-5 md:flex-row md:justify-between">
		<p class="text-sm text-center md:text-left">
			<span class="font-display font-bold uppercase tracking-[0.14em] text-[#f2f1ec]">PlannerQuiz</span>
			· {$t('hestim.footer.base')}
			<a href="https://github.com/mawoka-myblock/ClassQuiz" target="_blank" rel="noopener noreferrer" class="underline hover:text-[#f2f1ec]">ClassQuiz</a>
			(MPL-2.0) ·
			<a href={SOURCES} target="_blank" rel="noopener noreferrer" class="underline hover:text-[#f2f1ec]">{$t('hestim.footer.sources')}</a>
			·
			<a href="/docs/attribution" class="underline hover:text-[#f2f1ec]">{$t('hestim.footer.attributions')}</a>
		</p>
		<LanguageToggle />
	</div>
</footer>
