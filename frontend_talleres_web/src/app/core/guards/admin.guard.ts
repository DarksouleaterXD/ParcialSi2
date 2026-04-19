import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

export const adminGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  if (!auth.isLoggedIn()) {
    return router.createUrlTree(['/login']);
  }
  const admin =
    auth.isAdmin() || (auth.profile()?.roles?.includes('Administrador') ?? false);
  if (admin) {
    return true;
  }
  return router.createUrlTree(['/dashboard']);
};
