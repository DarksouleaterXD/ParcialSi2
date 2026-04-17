import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { AuthService } from '../services/auth.service';
import { SHELL_NAV_MODULES, type ShellNavItem } from './nav-modules';

function initialPackageExpanded(): Record<string, boolean> {
  const r: Record<string, boolean> = {};
  for (const m of SHELL_NAV_MODULES) {
    r[m.packageId] = m.items.length > 0;
  }
  return r;
}

@Component({
  selector: 'app-main-shell',
  standalone: true,
  imports: [CommonModule, RouterOutlet, RouterLink, RouterLinkActive],
  host: {
    class: 'block min-h-screen',
  },
  templateUrl: './main-shell.component.html',
})
export class MainShellComponent implements OnInit {
  protected readonly nav = SHELL_NAV_MODULES;
  protected readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  readonly headerAvatarBroken = signal(false);
  /** Menú lateral estrecho (solo íconos). */
  readonly sidebarCollapsed = signal(false);
  /** Paquetes desplegados (acordeón); ignorado visualmente si el sidebar está colapsado. */
  readonly packageExpanded = signal<Record<string, boolean>>(initialPackageExpanded());

  ngOnInit(): void {
    this.auth.refreshProfile().subscribe({
      next: () => this.headerAvatarBroken.set(false),
      error: () => {},
    });
  }

  toggleSidebar(): void {
    this.sidebarCollapsed.update((c) => !c);
  }

  togglePackage(packageId: string): void {
    this.packageExpanded.update((s) => ({ ...s, [packageId]: !s[packageId] }));
  }

  isPackageExpanded(packageId: string): boolean {
    return this.packageExpanded()[packageId] === true;
  }

  navItemLabel(item: ShellNavItem): string {
    return this.isAdmin() && item.adminLabel ? item.adminLabel : item.label;
  }

  userInitials(): string {
    const p = this.auth.profile();
    if (!p) {
      return '?';
    }
    const a = (p.nombre?.trim()[0] ?? '').toUpperCase();
    const b = (p.apellido?.trim()[0] ?? '').toUpperCase();
    return (a + b || '?').slice(0, 2);
  }

  isAdmin(): boolean {
    return this.auth.isAdmin();
  }

  showItem(item: { adminOnly?: boolean }): boolean {
    if (item.adminOnly) {
      return this.isAdmin();
    }
    return true;
  }

  logout(): void {
    this.auth.logout().subscribe({
      error: () => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('roles');
        void this.router.navigateByUrl('/login');
      },
    });
  }
}
