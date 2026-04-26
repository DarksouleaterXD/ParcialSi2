import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { environment } from '../../../environments/environment';
import type { PagoListResponseDto } from '../models/pagos.dto';

@Injectable({ providedIn: 'root' })
export class PagosApiService {
  private readonly http = inject(HttpClient);
  private readonly base = environment.apiUrl;
  private readonly prefix = `${this.base}/pagos`;

  getPagos(page = 1, pageSize = 10): Observable<PagoListResponseDto> {
    const params = new HttpParams().set('page', String(page)).set('page_size', String(pageSize));
    return this.http.get<PagoListResponseDto>(this.prefix, { params }).pipe(
      catchError((err: HttpErrorResponse) => throwError(() => err)),
    );
  }
}

