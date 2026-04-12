import { CommonModule } from '@angular/common';
import { Component, inject, OnInit, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';
import { emailFlexibleValidator } from '../validators/login.validators';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterLink],
  templateUrl: './login.component.html',
})
export class LoginComponent implements OnInit {
  private readonly fb = inject(FormBuilder);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);

  readonly showPassword = signal(false);
  readonly registeredHint = signal(false);

  readonly form = this.fb.nonNullable.group({
    email: ['', [Validators.required, emailFlexibleValidator]],
    password: ['', [Validators.required, Validators.minLength(4)]],
  });

  serverError = '';
  loading = false;

  ngOnInit(): void {
    const q = this.route.snapshot.queryParamMap.get('registered');
    this.registeredHint.set(q === '1');
  }

  private fieldInvalid(name: 'email' | 'password'): boolean {
    const c = this.form.get(name);
    return !!c && (c.touched || c.dirty) && c.invalid;
  }

  emailErrorVisible(): boolean {
    return this.fieldInvalid('email');
  }

  passwordErrorVisible(): boolean {
    return this.fieldInvalid('password');
  }

  togglePassword(): void {
    this.showPassword.update((v) => !v);
  }

  submit(): void {
    this.serverError = '';
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const { email, password } = this.form.getRawValue();
    this.loading = true;
    this.auth.login({ email, password }).subscribe({
      next: (res) => {
        this.loading = false;
        if (res.roles.includes('Administrador')) {
          void this.router.navigateByUrl('/dashboard');
          return;
        }
        void this.router.navigateByUrl('/vehiculos');
      },
      error: (err: { error?: { detail?: unknown } }) => {
        this.loading = false;
        const detail = err?.error?.detail;
        this.serverError = typeof detail === 'string' ? detail : 'Credenciales inválidas o error de red.';
      },
    });
  }
}
