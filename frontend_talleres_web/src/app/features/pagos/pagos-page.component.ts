import { CommonModule, CurrencyPipe, DatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { PagosApiService } from '../../core/services/pagos-api.service';
import type { PagoDto } from '../../core/models/pagos.dto';

@Component({
  selector: 'app-pagos-page',
  standalone: true,
  imports: [CommonModule, CurrencyPipe, DatePipe],
  templateUrl: './pagos-page.component.html',
})
export class PagosPageComponent implements OnInit {
  private readonly api = inject(PagosApiService);

  readonly items = signal<PagoDto[]>([]);
  readonly total = signal(0);
  readonly page = signal(1);
  readonly pageSize = signal(10);
  readonly loading = signal(false);
  readonly errorMessage = signal('');

  readonly isEmpty = computed(() => !this.loading() && !this.errorMessage() && this.items().length === 0);
  readonly hasPrevPage = computed(() => this.page() > 1);
  readonly hasNextPage = computed(() => this.page() * this.pageSize() < this.total());

  ngOnInit(): void {
    this.loadPagos();
  }

  loadPagos(): void {
    this.loading.set(true);
    this.errorMessage.set('');
    this.api.getPagos(this.page(), this.pageSize()).subscribe({
      next: (res) => {
        this.items.set(res.items ?? []);
        this.total.set(res.total ?? 0);
        this.loading.set(false);
      },
      error: (err: unknown) => {
        this.loading.set(false);
        this.errorMessage.set(this.errorFrom(err));
      },
    });
  }

  prevPage(): void {
    if (!this.hasPrevPage()) {
      return;
    }
    this.page.update((p) => p - 1);
    this.loadPagos();
  }

  nextPage(): void {
    if (!this.hasNextPage()) {
      return;
    }
    this.page.update((p) => p + 1);
    this.loadPagos();
  }

  estadoBadgeClass(estado: string | null | undefined): string {
    const e = (estado ?? '').trim().toUpperCase();
    if (e === 'COMPLETADO' || e === 'PAGADO') {
      return 'border-emerald-200 bg-emerald-50 text-emerald-700';
    }
    return 'border-slate-200 bg-slate-100 text-slate-700';
  }

  private errorFrom(err: unknown): string {
    const e = err as HttpErrorResponse;
    const detail = e?.error?.detail;
    if (typeof detail === 'string' && detail.trim()) {
      return detail;
    }
    if (e.status === 401) {
      return 'La sesión expiró. Volvé a iniciar sesión.';
    }
    if (e.status === 403) {
      return 'No tenés permisos para ver pagos.';
    }
    if (e.status === 0) {
      return 'No se pudo conectar con el servidor.';
    }
    return 'No se pudo cargar el listado de pagos.';
  }
}

