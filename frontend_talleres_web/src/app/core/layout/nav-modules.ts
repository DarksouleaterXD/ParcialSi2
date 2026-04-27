/** Módulos de dominio — definición de la navegación lateral. */
export type ShellNavIcon =
  | 'home'
  | 'users'
  | 'roles'
  | 'car'
  | 'wrench'
  | 'alert'
  | 'card'
  | 'banknotes'
  | 'cpu'
  | 'list'
  /** Triángulo de alerta (genérico). */
  | 'triangleAlert'
  /** Rayo — cola de solicitudes / incidentes (no Bitácora). */
  | 'bolt';

export interface ShellNavItem {
  /** Comandos absolutos para `RouterLink` (evita ambigüedad con rutas hijas). */
  routerLink: (string | number)[];
  label: string;
  /** Texto alternativo en el menú cuando el usuario es administrador */
  adminLabel?: string;
  adminOnly?: boolean;
  icon: ShellNavIcon;
  /** Por defecto `exact: true`; usar `false` si el ítem debe activarse con rutas hijas (ej. detalle). */
  routerLinkActiveOptions?: { exact: boolean };
}

export interface ShellNavModule {
  packageId: string;
  /** Texto visible del acordeón del paquete */
  title: string;
  /** Ícono del encabezado desplegable del paquete */
  packageIcon: ShellNavIcon;
  items: ShellNavItem[];
  comingSoon?: boolean;
  soonIcon?: ShellNavIcon;
}

export const SHELL_NAV_MODULES: ShellNavModule[] = [
  {
    packageId: 'usuario_autenticacion',
    title: 'Usuario y autenticación',
    packageIcon: 'users',
    items: [
      { routerLink: ['/', 'dashboard'], label: 'Inicio', icon: 'home' },
      { routerLink: ['/', 'vehiculos'], label: 'Mis vehículos', adminLabel: 'Vehículos registrados', icon: 'car' },
      { routerLink: ['/', 'users'], label: 'Usuarios', adminOnly: true, icon: 'users' },
      { routerLink: ['/', 'roles'], label: 'Roles', adminOnly: true, icon: 'roles' },
    ],
  },
  {
    packageId: 'taller_tecnico',
    title: 'Taller técnico',
    packageIcon: 'wrench',
    items: [
      { routerLink: ['/', 'talleres'], label: 'Gestionar talleres', adminOnly: true, icon: 'wrench' },
      { routerLink: ['/', 'tecnicos'], label: 'Gestionar técnicos', adminOnly: true, icon: 'users' },
    ],
  },
  {
    packageId: 'incidentes_servicios',
    title: 'Incidentes y servicios',
    packageIcon: 'alert',
    items: [
      {
        routerLink: ['/', 'incidentes', 'solicitudes'],
        label: 'Solicitudes',
        icon: 'bolt',
        routerLinkActiveOptions: { exact: false },
      },
      {
        routerLink: ['/', 'incidentes', 'calificaciones'],
        label: 'Calificaciones',
        icon: 'list',
        adminOnly: true,
        routerLinkActiveOptions: { exact: true },
      },
    ],
  },
  {
    packageId: 'pagos',
    title: 'Pagos',
    packageIcon: 'banknotes',
    items: [{ routerLink: ['/', 'pagos'], label: 'Pagos y comisiones', icon: 'banknotes' }],
  },
  {
    packageId: 'sistema',
    title: 'Sistema',
    packageIcon: 'cpu',
    items: [{ routerLink: ['/', 'bitacora'], label: 'Bitácora', adminOnly: true, icon: 'list' }],
  },
];
