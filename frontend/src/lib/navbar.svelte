<!--
SPDX-FileCopyrightText: 2023 Marlon W (Mawoka)

SPDX-License-Identifier: MPL-2.0
-->

<script lang="ts">
	import Marque from '$lib/hestim/Marque.svelte';
	import { getLocalization } from '$lib/i18n';
	import { signedIn, pathname } from '$lib/stores';
	import { createTippy } from 'svelte-tippy';
	import { browser } from '$app/environment';
	import { beforeNavigate } from '$app/navigation';
	import { draw, slide } from 'svelte/transition';
	import { registration_disabled } from './config';

	const tippy = createTippy({
		arrow: true,
		animation: 'perspective-subtle',
		placement: 'bottom'
	});

	const { t } = getLocalization();

	let menuIsClosed = $state(true);
	const toggleMenu = () => {
		menuIsClosed = !menuIsClosed;
	};

	beforeNavigate(() => {
		menuIsClosed = true; // Closes menu to let the user see the page beneath
	});

	let darkMode = $state(false);
	if (browser) {
		darkMode =
			localStorage.theme === 'dark' ||
			(!('theme' in localStorage) &&
				window.matchMedia('(prefers-color-scheme: dark)').matches);
	}

	// HESTIM : retour à Planner en un clic. Adresse fixée à la construction (VITE_HESTIM_PLANNER_URL)
	// ou déduite du domaine (quiz.exemple.fr → planner.exemple.fr) ; /tableau mène au tableau du rôle.
	let plannerUrl: string | null = $state(import.meta.env.VITE_HESTIM_PLANNER_URL ?? null);
	if (browser && !plannerUrl && window.location.hostname.startsWith('quiz.')) {
		plannerUrl = `${window.location.protocol}//planner.${window.location.hostname.slice(5)}/tableau`;
	}

	const switchDarkMode = () => {
		!darkMode ? localStorage.setItem('theme', 'dark') : localStorage.setItem('theme', 'light');
		window.location.reload();
	};
</script>

<nav class="w-screen px-4 lg:px-10 py-2 fixed bg-[#001861] text-[#f2f1ec] shadow-md z-30 top-0">
	<!-- Desktop navbar -->
	<div class="hidden lg:flex lg:items-center lg:flex-row lg:justify-between">
		<div class="lg:flex lg:items-center lg:flex-row gap-1">
			<Marque />
			{#if plannerUrl}
				<a class="btn-nav" href={plannerUrl}>← Planner</a>
			{/if}
			<a class="btn-nav border-2 rounded-sm" href="/play">{$t('words.play')}</a>
			<a class="btn-nav" href="/explore">{$t('words.explore')}</a>
			<a class="btn-nav" href="/search">{$t('words.search')}</a>
			{#if $signedIn}
				<a class="btn-nav" href="/dashboard">{$t('words.dashboard')}</a>
			{:else}
			{/if}
		</div>
		<div class="lg:flex lg:items-center lg:flex-row gap-1">
			{#if $signedIn}
				<a class="btn-nav" href="/api/v1/users/logout">{$t('words.logout')}</a>
			{:else}
				{#if registration_disabled}
					<a class="btn-nav" href="/account/register">{$t('words.register')}</a>
				{/if}

				<a class="btn-nav" href="/account/login?returnTo={$pathname}">{$t('words.login')}</a
				>
			{/if}

			<div class="fit-content flex items-center justify-center gap-2">
				<div class="lg:flex items-center justify-center">
					{#if darkMode}
						<button
							onclick={() => {
								switchDarkMode();
							}}
							use:tippy={{ content: 'Switch light mode on' }}
							aria-label="Activate light mode"
						>
							<!-- Heroicons: sun -->
							<svg
								class="w-6 h-6"
								fill="none"
								aria-label="Sun-Icon"
								stroke="currentColor"
								viewBox="0 0 24 24"
								xmlns="http://www.w3.org/2000/svg"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									stroke="currentColor"
									d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"
								/>
							</svg>
						</button>
					{:else}
						<button
							onclick={() => {
								switchDarkMode();
							}}
							aria-label="Activate darkmode"
							use:tippy={{ content: 'Switch dark mode on' }}
						>
							<!-- Heroicons: moon -->
							<svg
								aria-label="Moon-Icon"
								class="w-6 h-6"
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
								xmlns="http://www.w3.org/2000/svg"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"
								/>
							</svg>
						</button>
					{/if}
				</div>
			</div>
		</div>
	</div>

	<!-- Mobile navbar -->
	<div class="lg:hidden">
		<!-- Navbar header -->
		<div class="flex items-center justify-between">
			<Marque />
			<a class="btn-nav flex" href="/play">{$t('words.play')}</a>

			<!-- Dark/Light mode toggle + Open/Close menu -->
			<div class="flex items-center">
				{#if darkMode}
					<!-- Sun icon -->
					<button
						class="px-3"
						onclick={() => {
							switchDarkMode();
						}}
						use:tippy={{ content: 'Switch light mode on' }}
						aria-label="Activate light mode"
					>
						<!-- Heroicons: sun -->
						<svg
							class="w-6 h-6"
							fill="none"
							aria-label="Sun-Icon"
							stroke="currentColor"
							viewBox="0 0 24 24"
							xmlns="http://www.w3.org/2000/svg"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								stroke="currentColor"
								d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"
							/>
						</svg>
					</button>
				{:else}
					<!-- Moon icon -->
					<button
						class="px-3"
						onclick={() => {
							switchDarkMode();
						}}
						aria-label="Activate darkmode"
						use:tippy={{ content: 'Switch dark mode on' }}
					>
						<!-- Heroicons: moon -->
						<svg
							aria-label="Moon-Icon"
							class="w-6 h-6"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
							xmlns="http://www.w3.org/2000/svg"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"
							/>
						</svg>
					</button>
				{/if}

				{#if menuIsClosed}
					<button
						class="px-3"
						id="open-menu"
						onclick={toggleMenu}
						aria-label="Open navbar"
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							width="24"
							height="24"
							viewBox="0 0 24 24"
							fill="none"
							stroke="#000000"
							stroke-width="2"
							stroke-linecap="round"
							stroke-linejoin="round"
						>
							<path d="M3 6h18M3 12h18M3 18h18" />
						</svg>
					</button>
				{:else}
					<button
						class="px-3"
						id="close-menu"
						onclick={toggleMenu}
						aria-label="Close navbar"
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							width="24"
							height="24"
							viewBox="0 0 24 24"
							fill="none"
							stroke="#000000"
							stroke-width="2"
							stroke-linecap="round"
							stroke-linejoin="round"
							><path in:draw|global={{ duration: 300 }} d="M18 6 6 18" /><path
								in:draw|global={{ duration: 300 }}
								d="m6 6 12 12"
							/></svg
						>
					</button>
				{/if}
			</div>
		</div>

		<!-- Navbar content -->
		{#if !menuIsClosed}
			<div class="flex flex-col" transition:slide|global={{ duration: 400 }}>
				{#if plannerUrl}
					<a class="btn-nav" href={plannerUrl}>← Planner</a>
				{/if}
				<a class="btn-nav" href="/explore">{$t('words.explore')}</a>
				<a class="btn-nav" href="/search">{$t('words.search')}</a>
				{#if $signedIn}
					<a class="btn-nav" href="/dashboard">{$t('words.dashboard')}</a>
				{:else}
				{/if}

				<hr class="my-1 border" />
				{#if $signedIn}
					<a class="btn-nav" href="/api/v1/users/logout">{$t('words.logout')}</a>
				{:else}
					{#if registration_disabled}
						<a class="btn-nav" href="/account/register">{$t('words.register')}</a>
					{/if}

					<a class="btn-nav" href="/account/login?returnTo={$pathname}"
						>{$t('words.login')}</a
					>
				{/if}

				<div class="fit-content flex items-center justify-center my-2">
				</div>
			</div>
		{/if}
	</div>
</nav>
