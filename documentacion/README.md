# Documentación de Jaime

Sitio de documentación personal creado con Astro y Starlight. El proyecto está pensado para publicar notas, guías, referencias y proyectos relacionados con programación, aprendizaje e IoT.

## Tecnologías usadas

- **Astro**: framework principal del proyecto y sistema de build.
- **Starlight**: plantilla e integración de Astro para sitios de documentación.
- **MDX**: contenido enriquecido en `src/content/docs`, combinando Markdown con componentes Astro.
- **CSS nativo**: estilos del componente `AuthorCard` y animaciones globales sin framework adicional.
- **GitHub REST API**: el componente `AuthorCard.astro` consulta `https://api.github.com/users/{username}` para obtener avatar y cantidad de repositorios públicos.
- **View Transitions API**: usada para animar el cambio entre modo claro, oscuro y automático.

## Funcionalidades

- Sitio de documentación en español.
- Navegación lateral generada por Starlight.
- Búsqueda integrada en builds de producción.
- Soporte para modo claro, oscuro y automático.
- Transición circular al cambiar de tema, inspirada en `theme-toggle.rdsx.dev`.
- Tarjeta de autor dinámica con datos públicos de GitHub.

## Estructura principal

```text
.
|-- public/
|-- src/
|   |-- assets/
|   |-- components/
|   |   |-- AuthorCard.astro
|   |   `-- ThemeSelect.astro
|   |-- content/
|   |   `-- docs/
|   |       `-- index.mdx
|   |-- styles/
|   |   `-- theme-transition.css
|   `-- content.config.ts
|-- astro.config.mjs
|-- package.json
`-- tsconfig.json
```

## Componente de autor

El componente `src/components/AuthorCard.astro` acepta estas props:

- `username`: usuario de GitHub. Por defecto: `JaimeBerrios`.
- `role`: rol mostrado en la tarjeta.
- `bio`: descripción breve del autor.

Durante el render, el componente consulta la API pública de GitHub para mostrar la foto de perfil y la cantidad real de repositorios públicos.

## Transición de tema

El selector de tema de Starlight fue reemplazado por `src/components/ThemeSelect.astro`, manteniendo el comportamiento original, pero envolviendo el cambio de tema con `document.startViewTransition()`.

Los estilos de la animación viven en `src/styles/theme-transition.css`. Si el navegador no soporta View Transitions API, el cambio de tema funciona normalmente sin animación.

Referencia visual: https://theme-toggle.rdsx.dev/

## Comandos

Todos los comandos se ejecutan desde la raíz del proyecto:

| Comando | Acción |
| :-- | :-- |
| `npm install` | Instala dependencias |
| `npm run dev` | Levanta el servidor local en `localhost:4321` |
| `npm run build` | Genera el sitio de producción en `dist/` |
| `npm run preview` | Previsualiza el build localmente |

## Desarrollo local

```bash
npm run dev
```

Luego abre:

```text
http://localhost:4321
```
