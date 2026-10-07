<!--
SPDX-FileCopyrightText: 2026 HESTIM

SPDX-License-Identifier: MPL-2.0
-->

<!--
	HESTIM : nuage de mots des réponses libres (question TEXT), affiché à l'animateur après la
	question. Les réponses identiques (casse, accents et espaces ignorés) sont regroupées ; la
	taille suit le nombre de réponses. Les bonnes réponses attendues sont soulignées.
-->
<script lang="ts">
	import type { Question } from '$lib/quiz_types';

	interface Props {
		data: Array<{ username: string; answer: string; right: boolean }>;
		question: Question;
	}

	let { data, question }: Props = $props();

	const COULEURS = ['#001861', '#137D3F', '#B4410C', '#3B63E0', '#7048C9', '#0F8A7E'];
	const cle = (texte: string) =>
		String(texte ?? '')
			.replace(/<[^>]*>/g, '')
			.normalize('NFD')
			.replace(/[̀-ͯ]/g, '')
			.toLowerCase()
			.replace(/\s+/g, ' ')
			.trim();

	let attendues = $derived(
		new Set((Array.isArray(question.answers) ? question.answers : []).map((a) => cle(a?.answer)))
	);

	let mots = $derived.by(() => {
		const groupes = new Map<string, { texte: string; nombre: number }>();
		for (const r of data ?? []) {
			const k = cle(r.answer);
			if (!k) continue;
			const g = groupes.get(k) ?? { texte: String(r.answer).replace(/<[^>]*>/g, '').trim(), nombre: 0 };
			g.nombre += 1;
			groupes.set(k, g);
		}
		const liste = [...groupes.entries()].map(([k, g]) => ({ ...g, cle: k }));
		const max = Math.max(1, ...liste.map((m) => m.nombre));
		// Les plus fréquents au centre : on alterne gauche et droite autour du premier
		const tries = liste.sort((a, b) => b.nombre - a.nombre || a.texte.localeCompare(b.texte));
		const centre: typeof tries = [];
		tries.forEach((m, i) => (i % 2 ? centre.push(m) : centre.unshift(m)));
		return centre.map((m, i) => ({
			...m,
			taille: 1 + 3 * Math.sqrt(m.nombre / max),
			couleur: COULEURS[i % COULEURS.length]
		}));
	});
</script>

<figure class="flex flex-col items-center gap-3 w-full">
	<div
		class="flex flex-wrap justify-center items-center gap-x-6 gap-y-2 max-w-4xl px-4"
		role="list"
		aria-label="Nuage de mots"
	>
		{#each mots as mot (mot.cle)}
			<span
				role="listitem"
				class="font-bold leading-tight"
				class:underline={attendues.has(mot.cle)}
				style="font-size: {mot.taille}rem; color: {mot.couleur};"
				title="{mot.nombre} réponse(s)"
				aria-label="{mot.texte} : {mot.nombre} réponse(s)">{mot.texte}</span
			>
		{/each}
	</div>
	<figcaption class="text-sm opacity-70">
		{(data ?? []).length} réponse(s) · {mots.length} différente(s)
	</figcaption>
</figure>
