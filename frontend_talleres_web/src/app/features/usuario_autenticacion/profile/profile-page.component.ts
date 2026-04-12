import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import {
  AbstractControl,
  FormBuilder,
  ReactiveFormsModule,
  ValidationErrors,
  ValidatorFn,
  Validators,
} from '@angular/forms';
import { RouterLink } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-profile-page',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterLink],
  templateUrl: './profile-page.component.html',
})
export class ProfilePageComponent implements OnInit {
  protected readonly auth = inject(AuthService);
  private readonly fb = inject(FormBuilder);

  readonly avatarBroken = signal(false);
  profileError = '';
  profileSuccess = '';
  profileSubmitting = false;

  passwordError = '';
  passwordSuccess = '';
  passwordSubmitting = false;
  readonly showPwd = signal({ actual: false, n1: false, n2: false });

  profileForm = this.fb.nonNullable.group({
    nombre: ['', [Validators.required, Validators.maxLength(100)]],
    apellido: ['', [Validators.required, Validators.maxLength(100)]],
    telefono: ['', [Validators.maxLength(20)]],
    foto_perfil: ['', [Validators.maxLength(255)]],
  });

  private static readonly passwordsMatchValidator: ValidatorFn = (g: AbstractControl): ValidationErrors | null => {
    const n = g.get('password_nueva')?.value as string | undefined;
    const c = g.get('password_confirmacion')?.value as string | undefined;
    if (!n?.length || !c?.length) {
      return null;
    }
    return n === c ? null : { mismatch: true };
  };

  pwdForm = this.fb.nonNullable.group(
    {
      password_actual: ['', [Validators.required]],
      password_nueva: [
        '',
        [Validators.required, Validators.minLength(8), Validators.pattern(/^(?=.*[A-Za-z])(?=.*\d).+/)],
      ],
      password_confirmacion: ['', [Validators.required]],
    },
    { validators: ProfilePageComponent.passwordsMatchValidator },
  );

  ngOnInit(): void {
    this.auth.refreshProfile().subscribe({
      next: (p) => {
        this.profileForm.patchValue({
          nombre: p.nombre,
          apellido: p.apellido,
          telefono: p.telefono ?? '',
          foto_perfil: p.foto_perfil ?? '',
        });
        this.avatarBroken.set(false);
      },
      error: () => {
        this.profileError = 'No se pudo cargar el perfil.';
      },
    });
  }

  initials(): string {
    const p = this.auth.profile();
    if (!p) {
      return '?';
    }
    const a = (p.nombre?.trim()[0] ?? '').toUpperCase();
    const b = (p.apellido?.trim()[0] ?? '').toUpperCase();
    return (a + b || '?').slice(0, 2);
  }

  fechaRegistroFmt(): string {
    const raw = this.auth.profile()?.fecha_registro;
    if (!raw) {
      return '—';
    }
    try {
      return new Intl.DateTimeFormat('es', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(raw));
    } catch {
      return raw;
    }
  }

  saveProfile(): void {
    this.profileError = '';
    this.profileSuccess = '';
    if (this.profileForm.invalid) {
      this.profileForm.markAllAsTouched();
      return;
    }
    const v = this.profileForm.getRawValue();
    this.profileSubmitting = true;
    this.auth
      .updateMyProfile({
        nombre: v.nombre.trim(),
        apellido: v.apellido.trim(),
        telefono: v.telefono.trim() || null,
        foto_perfil: v.foto_perfil.trim() || null,
      })
      .subscribe({
        next: () => {
          this.profileSubmitting = false;
          this.profileSuccess = 'Perfil actualizado correctamente.';
          this.avatarBroken.set(false);
        },
        error: (err: { error?: { detail?: unknown } }) => {
          this.profileSubmitting = false;
          const d = err?.error?.detail;
          this.profileError = typeof d === 'string' ? d : 'No se pudo guardar.';
        },
      });
  }

  savePassword(): void {
    this.passwordError = '';
    this.passwordSuccess = '';
    if (this.pwdForm.invalid) {
      this.pwdForm.markAllAsTouched();
      return;
    }
    const v = this.pwdForm.getRawValue();
    this.passwordSubmitting = true;
    this.auth
      .changePassword({
        password_actual: v.password_actual,
        password_nueva: v.password_nueva,
        password_confirmacion: v.password_confirmacion,
      })
      .subscribe({
        next: () => {
          this.passwordSubmitting = false;
          this.passwordSuccess = 'Contraseña actualizada.';
          this.pwdForm.reset();
        },
        error: (err: { error?: { detail?: unknown } }) => {
          this.passwordSubmitting = false;
          const d = err?.error?.detail;
          this.passwordError = typeof d === 'string' ? d : 'No se pudo cambiar la contraseña.';
        },
      });
  }

  togglePwd(field: 'actual' | 'n1' | 'n2'): void {
    this.showPwd.update((s) => ({ ...s, [field]: !s[field] }));
  }
}
