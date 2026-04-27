/**
 * Build de producción (Vercel, `ng build`): si definís `NG_API_BASE_URL` en el proyecto
 * Vercel, `scripts/vercel-env.cjs` reescribe este archivo al buildear (HTTPS del backend en Render).
 * Sin esa variable, editá `apiUrl` a tu API pública y dejá `authMock: false` para usar FastAPI.
 */
export const environment = {
  production: true,
  apiUrl: 'https://parcialsi2.onrender.com/api',
  authMock: false,
};
