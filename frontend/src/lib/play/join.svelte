<!--
SPDX-FileCopyrightText: 2023 Marlon W (Mawoka)

SPDX-License-Identifier: MPL-2.0
-->

<script lang="ts">
	import { socket } from '$lib/socket';
	import { onDestroy, onMount } from 'svelte';
	import { browser } from '$app/environment';
	import * as Sentry from '@sentry/browser';
	import { getLocalization } from '$lib/i18n';
	import Cookies from 'js-cookie';
	import { hcaptcha_site_key, recaptcha_key, sentry_dsn } from '$lib/config';

	const { t } = getLocalization();

	interface Props {
		game_pin: string;
		game_mode: any;
		username: any;
		hestim?: string;
	}

	let {
		game_pin = $bindable(),
		game_mode = $bindable(),
		username = $bindable(),
		hestim = ''
	}: Props = $props();
	let custom_field = $state();
	let custom_field_value = $state();
	let captcha_enabled = $state();

	let hcaptchaSitekey = hcaptcha_site_key;

	let hcaptcha = {
		execute: async (_a, _b) => ({ response: '' }), // eslint-disable-line @typescript-eslint/no-unused-vars
		// eslint-disable-next-line @typescript-eslint/no-empty-function
		render: (_a, _b) => {} // eslint-disable-line @typescript-eslint/no-unused-vars
	};
	let hcaptchaWidgetID;

	onMount(() => {
		if (browser) {
			// HESTIM : un nom déjà fourni par la plateforme (?name=) n'est pas remplacé
			if (!username) prefetch_username();
			hcaptcha = window.hcaptcha;
			if (hcaptcha.render) {
				hcaptchaWidgetID = hcaptcha.render('hcaptcha', {
					sitekey: hcaptchaSitekey,
					size: 'invisible',
					theme: 'dark'
				});
			}
		}
	});

	onDestroy(() => {
		if (browser) {
			hcaptcha = {
				execute: async () => ({ response: '' }),
				// eslint-disable-next-line @typescript-eslint/no-empty-function
				render: () => {}
			};
		}
	});

	const prefetch_username = async () => {
		const res = await fetch('/api/v1/users/me');
		if (res.status !== 200) {
			return;
		}
		const json = await res.json();
		username = json.username;
	};

	const set_game_pin = async () => {
		let process_var;
		try {
			process_var = process;
		} catch {
			process_var = { env: { API_URL: undefined } };
		}

		const res = await fetch(
			`${process_var.env.API_URL ?? ''}/api/v1/quiz/play/check_captcha/${game_pin}`
		);
		const json = await res.json();
		game_mode = json.game_mode;
		if (res.status === 200) {
			captcha_enabled = json.enabled;
			custom_field = json.custom_field;
		}
		if (res.status === 404) {
			/*			alertModal.set({
                open: true,
                title: 'Game not found',
                body: 'The game pin you entered seems invalid.'
            });*/
			if (browser) {
				alert('Game not found');
			}
			game_pin = '';
			return;
		}
		if (res.status !== 200) {
			/*			alertModal.set({
                open: true,
                body: `Unknown error with response-code ${res.status}`,
                title: 'Unknown Error'
            });*/
			alert('Unknown error');
			return;
		}
	};

	$effect(() => {
		if (game_pin.length > 5) {
			set_game_pin();
		}
	});

	const setUsername = async (e: Event) => {
		e.preventDefault();
		if (username.length <= 3) {
			return;
		}
		let captcha_resp: string;
		if (Cookies.get('kicked')) {
			console.log("%cYou're Banned!", 'font-size:6rem');
			return;
		}

		if (captcha_enabled) {
			if (hcaptchaSitekey) {
				try {
					const { response } = await hcaptcha.execute(hcaptchaWidgetID, {
						async: true
					});
					captcha_resp = response;
					socket.emit('join_game', {
						username: username,
						game_pin: game_pin,
						captcha: captcha_resp,
						custom_field: custom_field ? custom_field_value : undefined,
						hestim: hestim || undefined
					});
				} catch (e) {
					if (sentry_dsn !== null) {
						Sentry.captureException(e);
					}
					/*					alertModal.set({
                        open: true,
                        body: "The captcha failed, which is normal, but most of the time it's fixed by reloading!",
                        title: 'Captcha failed'
                    });*/
					alert('Captcha failed!');
					window.location.reload();
				}
			} else if (recaptcha_key) {
				// eslint-disable-next-line no-undef
				grecaptcha.ready(() => {
					// eslint-disable-next-line no-undef
					grecaptcha.execute(recaptcha_key, { action: 'submit' }).then(function (token) {
						socket.emit('join_game', {
							username: username,
							game_pin: game_pin,
							captcha: token,
							custom_field: custom_field ? custom_field_value : undefined,
							hestim: hestim || undefined
						});
					});
				});
			}
		} else {
			socket.emit('join_game', {
				username: username,
				game_pin: game_pin,
				captcha: undefined,
				custom_field: custom_field ? custom_field_value : undefined,
				hestim: hestim || undefined
			});
		}
	};
	socket.on('game_not_found', () => {
		game_pin = '';
		if (browser) {
			alert('Game not found');
		}
	});
	$effect(() => {
		const cleaned = game_pin.replace(/\D/g, '');
		if (game_pin.replace(/\D/g, '') === game_pin) {
			return;
		}
		game_pin = cleaned;
	});
</script>

<svelte:head>
	{#if captcha_enabled && hcaptchaSitekey}
		<script src="https://js.hcaptcha.com/1/api.js" async defer></script>
	{/if}
	{#if recaptcha_key && captcha_enabled}
		<script src="https://www.google.com/recaptcha/api.js?render={recaptcha_key}"></script>
	{/if}
</svelte:head>

<!-- HESTIM : écran de connexion à la partie au style du panneau des départs de la plateforme -->
<div class="hestim-ecran">
	{#if game_pin === '' || game_pin.length < 6}
		<form class="hestim-panneau" onsubmit={(e) => e.preventDefault()}>
			<div class="hestim-barre"><span>HESTIM</span><span>Quiz en direct</span></div>
			<div class="hestim-corps">
				<label class="hestim-libelle" for="hestim-pin">{$t('words.game_pin')}</label>
				<input
					id="hestim-pin"
					class="hestim-champ hestim-pin"
					bind:value={game_pin}
					maxlength="6"
					inputmode="numeric"
					autocomplete="off"
					placeholder="000000"
				/>
				<button type="submit" class="hestim-bouton" disabled={game_pin.length < 6}>{$t('words.submit')}</button>
			</div>
		</form>
	{:else}
		<form onsubmit={setUsername} class="hestim-panneau">
			<div class="hestim-barre"><span>HESTIM</span><span>{$t('words.game_pin')} {game_pin}</span></div>
			<div class="hestim-corps">
				<label class="hestim-libelle" for="hestim-nom">{$t('words.username')}</label>
				<input id="hestim-nom" class="hestim-champ" bind:value={username} maxlength="17" autocomplete="off" />
				{#if custom_field}
					<label class="hestim-libelle" for="hestim-champ-libre">{custom_field}</label>
					<input id="hestim-champ-libre" class="hestim-champ" bind:value={custom_field_value} />
				{/if}
				<button type="submit" class="hestim-bouton" disabled={username.length <= 3}>{$t('words.submit')}</button>
			</div>
		</form>
	{/if}
</div>
<div
	id="hcaptcha"
	class="h-captcha"
	data-sitekey={hcaptchaSitekey}
	data-size="invisible"
	data-theme="dark"
></div>

<style>
	/* HESTIM : couleurs et polices de la plateforme (shared/design-tokens.json) */
	.hestim-ecran {
		position: fixed;
		inset: 0;
		z-index: 20;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 16px;
		background: #0b0b0d;
		font-family: 'Barlow', 'Segoe UI', system-ui, sans-serif;
	}
	.hestim-panneau {
		width: 100%;
		max-width: 420px;
		padding: 8px;
		border-radius: 6px;
		background: #001861;
	}
	.hestim-barre {
		display: flex;
		justify-content: space-between;
		padding: 4px 8px 10px;
		color: #ffffff;
		font-family: 'Barlow Condensed', 'Arial Narrow', sans-serif;
		font-weight: 700;
		font-size: 1.05rem;
		letter-spacing: 0.12em;
		text-transform: uppercase;
	}
	.hestim-corps {
		display: flex;
		flex-direction: column;
		gap: 12px;
		padding: 20px 16px;
		border-radius: 4px;
		background: #0b0b0d;
	}
	.hestim-libelle {
		color: #a6a6ac;
		font-family: 'Barlow Condensed', 'Arial Narrow', sans-serif;
		font-weight: 600;
		font-size: 0.95rem;
		letter-spacing: 0.14em;
		text-transform: uppercase;
	}
	.hestim-champ {
		width: 100%;
		min-height: 52px;
		padding: 8px 14px;
		border: 1px solid #2c2c30;
		border-radius: 4px;
		background: #212124;
		color: #f2f1ec;
		font-size: 1.25rem;
		text-align: center;
		outline: none;
	}
	.hestim-champ:focus {
		border-color: #f2f1ec;
	}
	.hestim-pin {
		font-family: 'Barlow Condensed', 'Arial Narrow', sans-serif;
		font-weight: 700;
		font-size: 2.5rem;
		letter-spacing: 0.35em;
		font-variant-numeric: tabular-nums;
	}
	.hestim-champ::placeholder {
		color: #4a4a50;
	}
	.hestim-bouton {
		min-height: 52px;
		margin-top: 4px;
		border-radius: 4px;
		background: #f2f1ec;
		color: #0b0b0d;
		font-family: 'Barlow Condensed', 'Arial Narrow', sans-serif;
		font-weight: 700;
		font-size: 1.15rem;
		letter-spacing: 0.12em;
		text-transform: uppercase;
		cursor: pointer;
	}
	.hestim-bouton:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}
	.hestim-bouton:focus-visible,
	.hestim-champ:focus-visible {
		outline: 2px solid #f26322;
		outline-offset: 2px;
	}
</style>
