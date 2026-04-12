import { Routes } from '@angular/router';

import { adminGuard } from './core/guards/admin.guard';
import { authGuard } from './core/guards/auth.guard';

export const routes: Routes = [
  { path: 'login', loadComponent: () => import('./features/usuario_autenticacion/login/login.component').then((m) => m.LoginComponent) },
  {
    path: 'register',
    loadComponent: () =>
      import('./features/usuario_autenticacion/register/register.component').then((m) => m.RegisterComponent),
  },
  {
    path: '',
    canActivate: [authGuard],
    loadComponent: () => import('./core/layout/main-shell.component').then((m) => m.MainShellComponent),
    children: [
      { path: '', pathMatch: 'full', redirectTo: 'dashboard' },
      {
        path: 'dashboard',
        loadComponent: () =>
          import('./features/usuario_autenticacion/dashboard/dashboard.component').then((m) => m.DashboardComponent),
      },
      {
        path: 'perfil',
        loadComponent: () =>
          import('./features/usuario_autenticacion/profile/profile-page.component').then((m) => m.ProfilePageComponent),
      },
      {
        path: 'vehiculos',
        loadComponent: () =>
          import('./features/usuario_autenticacion/vehiculos/vehiculos-page.component').then((m) => m.VehiculosPageComponent),
      },
      {
        path: 'users',
        canActivate: [adminGuard],
        loadComponent: () =>
          import('./features/usuario_autenticacion/users/users-page.component').then((m) => m.UsersPageComponent),
      },
      {
        path: 'roles',
        canActivate: [adminGuard],
        loadComponent: () =>
          import('./features/usuario_autenticacion/roles/roles-page.component').then((m) => m.RolesPageComponent),
      },
    ],
  },
  { path: '**', redirectTo: 'login' },
];
