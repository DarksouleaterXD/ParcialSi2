import { AbstractControl, ValidationErrors, ValidatorFn } from '@angular/forms';

export const passwordMatchValidator: ValidatorFn = (group: AbstractControl): ValidationErrors | null => {
  const password = group.get('password')?.value;
  const confirm = group.get('confirmPassword')?.value;
  if (password == null || confirm == null || confirm === '') {
    return null;
  }
  return password === confirm ? null : { passwordMismatch: true };
};
