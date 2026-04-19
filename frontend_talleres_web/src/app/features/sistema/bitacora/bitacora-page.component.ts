import { CommonModule, DatePipe } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import {
  BitacoraApiService,
  BitacoraDetailResponse,
  BitacoraItem,
} from '../../../core/services/bitacora-api.service';

@Component({
  selector: 'app-bitacora-page',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, DatePipe],
  templateUrl: './bitacora-page.component.html',
})
export class BitacoraPageComponent implements OnInit {
  private readonly api = inject(BitacoraApiService);
  private readonly fb = inject(FormBuilder);

  readonly items = signal<BitacoraItem[]>([]);
  readonly total = signal(0);
  readonly page = signal(1);
  readonly pageSize = signal(10);
  readonly loading = signal(false);
  readonly errorMessage = signal('');

  readonly detailOpen = signal(false);
  readonly detailLoading = signal(false);
  readonly detailError = signal('');
  readonly detail = signal<BitacoraDetailResponse | null>(null);

  readonly hasPrevPage = computed(() => this.page() > 1);
  readonly hasNextPage = computed(() => this.page() * this.pageSize() < this.total());

  readonly filterForm = this.fb.nonNullable.group({
    fecha: [''],
    modulo: [''],
    usuario: [''],
    accion: [''],
  });

  ngOnInit(): void {
    this.loadBitacora();
  }

  loadBitacora(): void {
    const f = this.filterForm.getRawValue();
    this.loading.set(true);
    this.errorMessage.set('');
    this.api
      .listBitacora({
        page: this.page(),
        pageSize: this.pageSize(),
        fecha: f.fecha || undefined,
        modulo: f.modulo || undefined,
        usuario: f.usuario || undefined,
        accion: f.accion || undefined,
      })
      .subscribe({
        next: (res) => {
          this.items.set(res.items);
          this.total.set(res.total);
          this.loading.set(false);
        },
        error: (err: { error?: { detail?: string } }) => {
          this.loading.set(false);
          this.errorMessage.set(err?.error?.detail ?? 'No se pudo cargar la bitácora.');
        },
      });
  }

  applyFilters(): void {
    this.page.set(1);
    this.loadBitacora();
  }

  clearFilters(): void {
    this.filterForm.reset({
      fecha: '',
      modulo: '',
      usuario: '',
      accion: '',
    });
    this.page.set(1);
    this.loadBitacora();
  }

  prevPage(): void {
    if (this.page() > 1) {
      this.page.update((p) => p - 1);
      this.loadBitacora();
    }
  }

  nextPage(): void {
    if (this.page() * this.pageSize() < this.total()) {
      this.page.update((p) => p + 1);
      this.loadBitacora();
    }
  }

  openDetail(row: BitacoraItem): void {
    this.detailOpen.set(true);
    this.detailLoading.set(true);
    this.detailError.set('');
    this.detail.set(null);
    this.api.getDetail(row.id).subscribe({
      next: (res) => {
        this.detail.set(res);
        this.detailLoading.set(false);
      },
      error: (err: { error?: { detail?: string } }) => {
        this.detailLoading.set(false);
        this.detailError.set(err?.error?.detail ?? 'No se pudo cargar el detalle.');
      },
    });
  }

  closeDetail(): void {
    this.detailOpen.set(false);
    this.detailLoading.set(false);
    this.detailError.set('');
    this.detail.set(null);
  }
}
