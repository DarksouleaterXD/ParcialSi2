import { AbstractControl, ValidationErrors, ValidatorFn } from '@angular/forms';

/** Acepta dominios .local (EmailStr de backend / entornos internos). */
export const emailFlexibleValidator: ValidatorFn = (control: AbstractControl): ValidationErrors | null => {
  const raw = control.value;
  if (raw == null || String(raw).trim() === '') {
    return null;
  }
  const v = String(raw).trim().toLowerCase();
  if (!v.includes('@')) {
    return { emailInvalid: true };
  }
  const parts = v.split('@');
  if (parts.length !== 2 || !parts[0] || !parts[1]) {
    return { emailInvalid: true };
  }
  return null;
};
