import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import * as L from 'leaflet';
import {
  TallerListItem,
  TalleresApiService,
} from '../../../core/services/talleres-api.service';

@Component({
  selector: 'app-talleres-page',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './talleres-page.component.html',
})
export class TalleresPageComponent implements OnInit {
  private readonly api = inject(TalleresApiService);
  private readonly fb = inject(FormBuilder);

  items: TallerListItem[] = [];
  total = 0;
  page = 1;
  pageSize = 10;
  loading = false;
  errorMessage = '';
  successMessage = '';
  createModalError = '';
  editModalError = '';

  readonly createOpen = signal(false);
  readonly editOpen = signal(false);

  createSubmitting = false;
  editSubmitting = false;
  estadoSubmittingId: number | null = null;
  geolocatingCreate = false;
  geolocatingEdit = false;

  private editId: number | null = null;
  private createMap: L.Map | null = null;
  private createMarker: L.Marker | null = null;
  private editMap: L.Map | null = null;
  private editMarker: L.Marker | null = null;
  private readonly markerIcon = L.divIcon({
    className: '',
    html: '<div style="width:16px;height:16px;border-radius:999px;background:#f97316;border:2px solid #fff;box-shadow:0 0 0 2px rgba(249,115,22,.3);"></div>',
    iconSize: [16, 16],
    iconAnchor: [8, 8],
  });

  filterForm = this.fb.nonNullable.group({
    q: [''],
    estado: ['todos' as 'todos' | 'activo' | 'inactivo'],
  });

  createForm = this.fb.nonNullable.group({
    nombre: ['', [Validators.required, Validators.maxLength(100)]],
    direccion: ['', [Validators.required, Validators.maxLength(255)]],
    latitud: ['', [Validators.required]],
    longitud: ['', [Validators.required]],
    telefono: ['', [Validators.maxLength(20)]],
    email: ['', [Validators.maxLength(150)]],
    capacidad_maxima: [10, [Validators.required, Validators.min(1), Validators.max(50000)]],
    horario_atencion: ['', [Validators.maxLength(120)]],
  });

  editForm = this.fb.nonNullable.group({
    nombre: ['', [Validators.required, Validators.maxLength(100)]],
    direccion: ['', [Validators.required, Validators.maxLength(255)]],
    latitud: ['', [Validators.required]],
    longitud: ['', [Validators.required]],
    telefono: ['', [Validators.maxLength(20)]],
    email: ['', [Validators.maxLength(150)]],
    capacidad_maxima: [10, [Validators.required, Validators.min(1), Validators.max(50000)]],
    horario_atencion: ['', [Validators.maxLength(120)]],
  });

  ngOnInit(): void {
    this.loadTalleres();
  }

  loadTalleres(): void {
    this.loading = true;
    this.errorMessage = '';
    const f = this.filterForm.getRawValue();
    let activo: boolean | null = null;
    if (f.estado === 'activo') {
      activo = true;
    } else if (f.estado === 'inactivo') {
      activo = false;
    }
    this.api
      .list({
        page: this.page,
        pageSize: this.pageSize,
        q: f.q || undefined,
        activo,
      })
      .subscribe({
        next: (r) => {
          this.items = r.items;
          this.total = r.total;
          this.loading = false;
        },
        error: (err: { error?: { detail?: unknown } }) => {
          this.loading = false;
          const d = err?.error?.detail;
          this.errorMessage = typeof d === 'string' ? d : 'No se pudieron cargar los talleres.';
        },
      });
  }

  applyFilters(): void {
    this.page = 1;
    this.loadTalleres();
  }

  prevPage(): void {
    if (this.page > 1) {
      this.page -= 1;
      this.loadTalleres();
    }
  }

  nextPage(): void {
    if (this.page * this.pageSize < this.total) {
      this.page += 1;
      this.loadTalleres();
    }
  }

  openCreateModal(): void {
    this.successMessage = '';
    this.createModalError = '';
    this.createForm.reset({
      nombre: '',
      direccion: '',
      latitud: '',
      longitud: '',
      telefono: '',
      email: '',
      capacidad_maxima: 10,
      horario_atencion: '',
    });
    this.createOpen.set(true);
    this.scheduleCreateMapInit();
  }

  closeCreateModal(): void {
    this.createModalError = '';
    this.destroyCreateMap();
    this.createOpen.set(false);
  }

  openEditModal(t: TallerListItem): void {
    this.successMessage = '';
    this.editModalError = '';
    this.editId = t.id;
    this.editForm.setValue({
      nombre: t.nombre,
      direccion: t.direccion,
      latitud: t.latitud != null ? String(t.latitud) : '',
      longitud: t.longitud != null ? String(t.longitud) : '',
      telefono: t.telefono ?? '',
      email: t.email ?? '',
      capacidad_maxima: t.capacidad_maxima,
      horario_atencion: t.horario_atencion ?? '',
    });
    this.editOpen.set(true);
    this.scheduleEditMapInit();
  }

  private scheduleCreateMapInit(): void {
    // El modal usa render condicional; esperamos a que el host tenga tamaño real.
    const run = () => {
      const host = document.getElementById('create-map');
      if (!host || host.clientWidth < 20 || host.clientHeight < 20) {
        window.setTimeout(run, 50);
        return;
      }
      this.initCreateMapFromForm();
      window.setTimeout(() => this.createMap?.invalidateSize(), 80);
    };
    window.setTimeout(run, 0);
  }

  private scheduleEditMapInit(): void {
    const run = () => {
      const host = document.getElementById('edit-map');
      if (!host || host.clientWidth < 20 || host.clientHeight < 20) {
        window.setTimeout(run, 50);
        return;
      }
      this.initEditMapFromForm();
      window.setTimeout(() => this.editMap?.invalidateSize(), 80);
    };
    window.setTimeout(run, 0);
  }

  closeEditModal(): void {
    this.editModalError = '';
    this.destroyEditMap();
    this.editOpen.set(false);
    this.editId = null;
  }

  private initCreateMapFromForm(): void {
    const host = document.getElementById('create-map');
    if (!host || this.createMap) {
      return;
    }
    const lat = Number(this.createForm.controls.latitud.value);
    const lon = Number(this.createForm.controls.longitud.value);
    const center: L.LatLngTuple =
      Number.isFinite(lat) && Number.isFinite(lon) ? [lat, lon] : [-17.7833, -63.1821];
    this.createMap = L.map(host, { center, zoom: 13, zoomControl: true });
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors',
    }).addTo(this.createMap);
    this.createMarker = L.marker(center, { draggable: true, icon: this.markerIcon }).addTo(this.createMap);
    this.createMarker.on('dragend', () => {
      const p = this.createMarker?.getLatLng();
      if (p) {
        this.patchCreateCoords(p.lat, p.lng);
      }
    });
    this.createMap.on('click', (ev: L.LeafletMouseEvent) => {
      this.createMarker?.setLatLng(ev.latlng);
      this.patchCreateCoords(ev.latlng.lat, ev.latlng.lng);
    });
    this.createMap.invalidateSize();
  }

  private initEditMapFromForm(): void {
    const host = document.getElementById('edit-map');
    if (!host || this.editMap) {
      return;
    }
    const lat = Number(this.editForm.controls.latitud.value);
    const lon = Number(this.editForm.controls.longitud.value);
    const center: L.LatLngTuple =
      Number.isFinite(lat) && Number.isFinite(lon) ? [lat, lon] : [-17.7833, -63.1821];
    this.editMap = L.map(host, { center, zoom: 13, zoomControl: true });
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors',
    }).addTo(this.editMap);
    this.editMarker = L.marker(center, { draggable: true, icon: this.markerIcon }).addTo(this.editMap);
    this.editMarker.on('dragend', () => {
      const p = this.editMarker?.getLatLng();
      if (p) {
        this.patchEditCoords(p.lat, p.lng);
      }
    });
    this.editMap.on('click', (ev: L.LeafletMouseEvent) => {
      this.editMarker?.setLatLng(ev.latlng);
      this.patchEditCoords(ev.latlng.lat, ev.latlng.lng);
    });
    this.editMap.invalidateSize();
  }

  private destroyCreateMap(): void {
    this.createMap?.remove();
    this.createMap = null;
    this.createMarker = null;
  }

  private destroyEditMap(): void {
    this.editMap?.remove();
    this.editMap = null;
    this.editMarker = null;
  }

  private patchCreateCoords(lat: number, lon: number): void {
    this.createForm.patchValue(
      { latitud: lat.toFixed(6), longitud: lon.toFixed(6) },
      { emitEvent: false },
    );
  }

  private patchEditCoords(lat: number, lon: number): void {
    this.editForm.patchValue(
      { latitud: lat.toFixed(6), longitud: lon.toFixed(6) },
      { emitEvent: false },
    );
  }

  useCurrentLocationCreate(): void {
    if (!navigator.geolocation || this.geolocatingCreate) {
      return;
    }
    this.geolocatingCreate = true;
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const { latitude, longitude } = pos.coords;
        this.patchCreateCoords(latitude, longitude);
        this.createMarker?.setLatLng([latitude, longitude]);
        this.createMap?.setView([latitude, longitude], 15);
        this.geolocatingCreate = false;
      },
      () => {
        this.createModalError = 'No se pudo obtener tu ubicación actual.';
        this.geolocatingCreate = false;
      },
      { enableHighAccuracy: true, timeout: 10000 },
    );
  }

  centerCreateMapOnCurrentLocation(): void {
    if (!navigator.geolocation || this.geolocatingCreate) {
      return;
    }
    this.geolocatingCreate = true;
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        this.createMap?.setView([pos.coords.latitude, pos.coords.longitude], 15);
        this.geolocatingCreate = false;
      },
      () => {
        this.createModalError = 'No se pudo centrar el mapa con tu ubicación.';
        this.geolocatingCreate = false;
      },
      { enableHighAccuracy: true, timeout: 10000 },
    );
  }

  useCurrentLocationEdit(): void {
    if (!navigator.geolocation || this.geolocatingEdit) {
      return;
    }
    this.geolocatingEdit = true;
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const { latitude, longitude } = pos.coords;
        this.patchEditCoords(latitude, longitude);
        this.editMarker?.setLatLng([latitude, longitude]);
        this.editMap?.setView([latitude, longitude], 15);
        this.geolocatingEdit = false;
      },
      () => {
        this.editModalError = 'No se pudo obtener tu ubicación actual.';
        this.geolocatingEdit = false;
      },
      { enableHighAccuracy: true, timeout: 10000 },
    );
  }

  centerEditMapOnCurrentLocation(): void {
    if (!navigator.geolocation || this.geolocatingEdit) {
      return;
    }
    this.geolocatingEdit = true;
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        this.editMap?.setView([pos.coords.latitude, pos.coords.longitude], 15);
        this.geolocatingEdit = false;
      },
      () => {
        this.editModalError = 'No se pudo centrar el mapa con tu ubicación.';
        this.geolocatingEdit = false;
      },
      { enableHighAccuracy: true, timeout: 10000 },
    );
  }

  hasCreateCoords(): boolean {
    const lat = Number(this.createForm.controls.latitud.value);
    const lon = Number(this.createForm.controls.longitud.value);
    return Number.isFinite(lat) && Number.isFinite(lon);
  }

  hasEditCoords(): boolean {
    const lat = Number(this.editForm.controls.latitud.value);
    const lon = Number(this.editForm.controls.longitud.value);
    return Number.isFinite(lat) && Number.isFinite(lon);
  }

  private buildCreateBody() {
    const v = this.createForm.getRawValue();
    const lat = Number(v.latitud);
    const lon = Number(v.longitud);
    if (Number.isNaN(lat) || Number.isNaN(lon)) {
      return null;
    }
    return {
      nombre: v.nombre.trim(),
      direccion: v.direccion.trim(),
      latitud: lat,
      longitud: lon,
      telefono: v.telefono?.trim() || null,
      email: v.email?.trim() || null,
      capacidad_maxima: v.capacidad_maxima,
      horario_atencion: v.horario_atencion?.trim() || null,
    };
  }

  saveCreate(): void {
    if (this.createForm.invalid) {
      this.createForm.markAllAsTouched();
      return;
    }
    const body = this.buildCreateBody();
    if (!body) {
      this.createModalError = 'Latitud y longitud deben ser números válidos.';
      return;
    }
    if (body.latitud < -90 || body.latitud > 90 || body.longitud < -180 || body.longitud > 180) {
      this.createModalError = 'Coordenadas fuera de rango (lat -90…90, lon -180…180).';
      return;
    }
    this.createSubmitting = true;
    this.createModalError = '';
    this.api.create(body).subscribe({
      next: () => {
        this.createSubmitting = false;
        this.closeCreateModal();
        this.successMessage = 'Taller registrado correctamente.';
        this.loadTalleres();
      },
      error: (err: { error?: { detail?: unknown } }) => {
        this.createSubmitting = false;
        const d = err?.error?.detail;
        this.createModalError = typeof d === 'string' ? d : 'No se pudo crear el taller.';
      },
    });
  }

  saveEdit(): void {
    if (this.editId == null || this.editForm.invalid) {
      this.editForm.markAllAsTouched();
      return;
    }
    const v = this.editForm.getRawValue();
    const lat = Number(v.latitud);
    const lon = Number(v.longitud);
    if (Number.isNaN(lat) || Number.isNaN(lon)) {
      this.editModalError = 'Latitud y longitud deben ser números válidos.';
      return;
    }
    if (lat < -90 || lat > 90 || lon < -180 || lon > 180) {
      this.editModalError = 'Coordenadas fuera de rango (lat -90…90, lon -180…180).';
      return;
    }
    this.editSubmitting = true;
    this.editModalError = '';
    this.api
      .update(this.editId, {
        nombre: v.nombre.trim(),
        direccion: v.direccion.trim(),
        latitud: lat,
        longitud: lon,
        telefono: v.telefono?.trim() || null,
        email: v.email?.trim() || null,
        capacidad_maxima: v.capacidad_maxima,
        horario_atencion: v.horario_atencion?.trim() || null,
      })
      .subscribe({
        next: () => {
          this.editSubmitting = false;
          this.closeEditModal();
          this.successMessage = 'Taller actualizado.';
          this.loadTalleres();
        },
        error: (err: { error?: { detail?: unknown } }) => {
          this.editSubmitting = false;
          const d = err?.error?.detail;
          this.editModalError = typeof d === 'string' ? d : 'No se pudo guardar.';
        },
      });
  }

  toggleDisponibilidad(t: TallerListItem): void {
    this.estadoSubmittingId = t.id;
    this.errorMessage = '';
    const req = t.disponibilidad ? this.api.desactivar(t.id) : this.api.reactivar(t.id);
    req.subscribe({
      next: () => {
        this.estadoSubmittingId = null;
        this.successMessage = t.disponibilidad ? 'Taller desactivado.' : 'Taller reactivado.';
        this.loadTalleres();
      },
      error: (err: { error?: { detail?: unknown } }) => {
        this.estadoSubmittingId = null;
        const d = err?.error?.detail;
        this.errorMessage = typeof d === 'string' ? d : 'No se pudo cambiar el estado.';
      },
    });
  }

  gpsResumen(t: TallerListItem): string {
    if (t.latitud == null || t.longitud == null) {
      return '—';
    }
    return `${Number(t.latitud).toFixed(5)}, ${Number(t.longitud).toFixed(5)}`;
  }
}
