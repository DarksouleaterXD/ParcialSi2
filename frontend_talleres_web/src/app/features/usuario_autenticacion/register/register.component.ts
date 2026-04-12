import { CommonModule } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';
import { emailFlexibleValidator } from '../validators/login.validators';
import { passwordMatchValidator } from '../validators/register.validators';

@Component({
  selector: 'app-register',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterLink],
  templateUrl: './register.component.html',
})
export class RegisterComponent {
  private readonly fb = inject(FormBuilder);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  readonly showPassword = signal(false);
  readonly showConfirmPassword = signal(false);

  readonly form = this.fb.nonNullable.group(
    {
      nombre: ['', [Validators.required, Validators.maxLength(100)]],
      apellido: ['', [Validators.required, Validators.maxLength(100)]],
      email: ['', [Validators.required, emailFlexibleValidator]],
      telefono: ['', [Validators.maxLength(20)]],
      password: ['', [Validators.required, Validators.minLength(8)]],
      confirmPassword: ['', [Validators.required]],
    },
    { validators: passwordMatchValidator },
  );

  serverError = '';
  loading = false;

  private controlInvalid(name: string): boolean {
    const c = this.form.get(name);
    return !!c && (c.touched || c.dirty) && c.invalid;
  }

  nombreErrorVisible(): boolean {
    return this.controlInvalid('nombre');
  }

  apellidoErrorVisible(): boolean {
    return this.controlInvalid('apellido');
  }

  emailErrorVisible(): boolean {
    return this.controlInvalid('email');
  }

  telefonoErrorVisible(): boolean {
    return this.controlInvalid('telefono');
  }

  passwordErrorVisible(): boolean {
    return this.controlInvalid('password');
  }

  confirmPasswordErrorVisible(): boolean {
    const c = this.form.get('confirmPassword');
    const touched = !!c && (c.touched || c.dirty);
    if (!touched) return false;
    if (c.invalid && c.errors?.['required']) return true;
    return touched && !!this.form.errors?.['passwordMismatch'];
  }

  togglePassword(): void {
    this.showPassword.update((v) => !v);
  }

  toggleConfirmPassword(): void {
    this.showConfirmPassword.update((v) => !v);
  }

  submit(): void {
    this.serverError = '';
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const raw = this.form.getRawValue();
    this.loading = true;
    this.auth
      .register({
        nombre: raw.nombre,
        apellido: raw.apellido,
        email: raw.email,
        password: raw.password,
        telefono: raw.telefono?.trim() ? raw.telefono.trim() : null,
      })
      .subscribe({
        next: () => {
          this.loading = false;
          void this.router.navigate(['/login'], {
            queryParams: { registered: '1' },
          });
        },
        error: () => {
          this.loading = false;
          this.serverError = 'No se pudo completar el registro. Intentá de nuevo.';
        },
      });
  }
}
