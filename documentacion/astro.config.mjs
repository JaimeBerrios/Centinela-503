// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

export default defineConfig({
	base: '/documentacion',
	integrations: [
		starlight({
			title: 'Centinela 503',
			logo: {
				src: './src/assets/isotipo.svg',
				replacesTitle: false,
			},
			defaultLocale: 'root',
			locales: {
				root: { label: 'Español', lang: 'es' },
			},
			customCss: ['./src/styles/theme-transition.css'],
			components: {
				ThemeSelect: './src/components/ThemeSelect.astro',
			},
			social: [{ icon: 'github', label: 'GitHub', href: 'https://github.com/JaimeBerrios' }],
			sidebar: [
				{
					label: 'Plataforma',
					items: [
						{ label: 'Arquitectura del Sistema', slug: 'guides/arquitectura' },
						{ label: 'Backend (FastAPI)', slug: 'guides/backend' },
						{ label: 'Frontend (Vanilla JS)', slug: 'guides/frontend' },
						{ label: 'Simulador de Alertas', slug: 'guides/simulador' },
					],
				},
				{
					label: 'Nosotros',
					items: [
						{ label: 'Equipo de Desarrollo', slug: 'team' },
					],
				},
			],
		}),
	],
});
