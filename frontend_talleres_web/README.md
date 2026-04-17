# FrontendTalleresWeb

This project was generated using [Angular CLI](https://github.com/angular/angular-cli) version 19.2.24.

## Development server

To start a local development server, run:

```bash
ng serve
```

Once the server is running, open your browser and navigate to `http://localhost:4200/`. The application will automatically reload whenever you modify any of the source files.

## Code scaffolding

Angular CLI includes powerful code scaffolding tools. To generate a new component, run:

```bash
ng generate component component-name
```

For a complete list of available schematics (such as `components`, `directives`, or `pipes`), run:

```bash
ng generate --help
```

## Tailwind-only style convention

This frontend is Tailwind-only for component styling.

- New components are generated without `.scss` files by default (`@schematics/angular:component.style = none`).
- Keep styling in templates with Tailwind utility classes.
- If a component needs dynamic visual states, prefer `ngClass`/`[class.*]` with Tailwind classes.
- Do not introduce component-level `scss`, `css`, `sass`, or `less` files unless explicitly approved.

### PR checklist (styles)

- [ ] No new `.scss`/`.sass`/`.less` files were added in `src/app`.
- [ ] Styling changes use Tailwind utility classes in templates.
- [ ] Form/input states use utility classes consistently (`focus`, `disabled`, `error`).
- [ ] No Bootstrap or custom global CSS was introduced for feature-level styling.

### Automated guardrail (no `.scss` in `src/app`)

Run this local check before committing:

```bash
npm run check:tailwind-only
```

Behavior:

- Fails with exit code `1` if any `*.scss` file exists under `src/app`.
- Prints the detected file paths so you can remove them.
- Passes with exit code `0` when no `.scss` files are found.

If it fails:

1. Remove the reported `.scss` file(s) from `src/app`.
2. Move styling to Tailwind utility classes in component templates.
3. Re-run `npm run check:tailwind-only` until it passes.

## Building

To build the project run:

```bash
ng build
```

This will compile your project and store the build artifacts in the `dist/` directory. By default, the production build optimizes your application for performance and speed.

## Running unit tests

To execute unit tests with the [Karma](https://karma-runner.github.io) test runner, use the following command:

```bash
ng test
```

## Running end-to-end tests

For end-to-end (e2e) testing, run:

```bash
ng e2e
```

Angular CLI does not come with an end-to-end testing framework by default. You can choose one that suits your needs.

## Additional Resources

For more information on using the Angular CLI, including detailed command references, visit the [Angular CLI Overview and Command Reference](https://angular.dev/tools/cli) page.
