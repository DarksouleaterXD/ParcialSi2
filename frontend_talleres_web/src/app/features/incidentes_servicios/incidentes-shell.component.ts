import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';

/** Contenedor mínimo para rutas hijas bajo `/incidentes/*`. */
@Component({
  selector: 'app-incidentes-shell',
  standalone: true,
  imports: [RouterOutlet],
  template: `<router-outlet />`,
})
export class IncidentesShellComponent {}
