/** Módulos de dominio — definición de la navegación lateral. */
export type ShellNavIcon = 'home' | 'users' | 'roles' | 'car' | 'wrench' | 'alert' | 'card' | 'cpu' | 'list';

export interface ShellNavItem {
  /** Comandos absolutos para `RouterLink` (evita ambigüedad con rutas hijas). */
  routerLink: (string | number)[];
  label: string;
  /** Texto alternativo en el menú cuando el usuario es administrador */
  adminLabel?: string;
  adminOnly?: boolean;
  icon: ShellNavIcon;
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
    items: [],
    comingSoon: true,
    soonIcon: 'alert',
  },
  {
    packageId: 'pagos',
    title: 'Pagos',
    packageIcon: 'card',
    items: [],
    comingSoon: true,
    soonIcon: 'card',
  },
  {
    packageId: 'sistema',
    title: 'Sistema',
    packageIcon: 'cpu',
    items: [{ routerLink: ['/', 'bitacora'], label: 'Bitácora', adminOnly: true, icon: 'list' }],
  },
];
