import { CommonModule, DatePipe } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
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

  items: BitacoraItem[] = [];
  total = 0;
  page = 1;
  pageSize = 10;
  loading = false;
  errorMessage = '';

  readonly detailOpen = signal(false);
  detailLoading = false;
  detailError = '';
  detail: BitacoraDetailResponse | null = null;

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
    this.loading = true;
    this.errorMessage = '';
    this.api
      .listBitacora({
        page: this.page,
        pageSize: this.pageSize,
        fecha: f.fecha || undefined,
        modulo: f.modulo || undefined,
        usuario: f.usuario || undefined,
        accion: f.accion || undefined,
      })
      .subscribe({
        next: (res) => {
          this.items = res.items;
          this.total = res.total;
          this.loading = false;
        },
        error: (err) => {
          this.loading = false;
          this.errorMessage = err?.error?.detail ?? 'No se pudo cargar la bitácora.';
        },
      });
  }

  applyFilters(): void {
    this.page = 1;
    this.loadBitacora();
  }

  clearFilters(): void {
    this.filterForm.reset({
      fecha: '',
      modulo: '',
      usuario: '',
      accion: '',
    });
    this.page = 1;
    this.loadBitacora();
  }

  prevPage(): void {
    if (this.page > 1) {
      this.page -= 1;
      this.loadBitacora();
    }
  }

  nextPage(): void {
    if (this.page * this.pageSize < this.total) {
      this.page += 1;
      this.loadBitacora();
    }
  }

  openDetail(row: BitacoraItem): void {
    this.detailOpen.set(true);
    this.detailLoading = true;
    this.detailError = '';
    this.detail = null;
    this.api.getDetail(row.id).subscribe({
      next: (res) => {
        this.detail = res;
        this.detailLoading = false;
      },
      error: (err) => {
        this.detailLoading = false;
        this.detailError = err?.error?.detail ?? 'No se pudo cargar el detalle.';
      },
    });
  }

  closeDetail(): void {
    this.detailOpen.set(false);
    this.detailLoading = false;
    this.detailError = '';
    this.detail = null;
  }
}
