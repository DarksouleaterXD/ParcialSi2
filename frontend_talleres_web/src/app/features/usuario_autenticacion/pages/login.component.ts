import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { Router } from '@angular/router';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  template: `
    <div class="min-h-screen bg-slate-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div class="sm:mx-auto sm:w-full sm:max-w-md">
        <h2 class="mt-6 text-center text-3xl font-extrabold text-slate-900">
          Iniciar Sesión
        </h2>
        <p class="mt-2 text-center text-sm text-slate-600">
          O
          <a href="/registro" class="font-medium text-amber-600 hover:text-amber-500 transition-colors">
            crear una cuenta nueva
          </a>
        </p>
      </div>

      <div class="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div class="bg-white py-8 px-4 shadow-md sm:rounded-xl sm:px-10 border border-slate-100">
          <form [formGroup]="loginForm" (ngSubmit)="onSubmit()" class="space-y-6">
            
            <!-- Email -->
            <div>
              <label for="email" class="block text-sm font-medium text-slate-700">
                Correo Electrónico
              </label>
              <div class="mt-1">
                <input
                  id="email"
                  type="email"
                  formControlName="email"
                  autocomplete="email"
                  class="appearance-none block w-full px-3 py-2 border border-slate-300 rounded-md shadow-sm placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-amber-500 sm:text-sm transition-all duration-200"
                  [ngClass]="{'border-red-300 focus:ring-red-500 focus:border-red-500': submitted && f['email'].errors}"
                  placeholder="ejemplo@correo.com"
                />
              </div>
              @if (submitted && f['email'].errors) {
                <div class="mt-1 text-sm text-red-600">
                  @if (f['email'].errors['required']) { <span>El correo es requerido.</span> }
                  @if (f['email'].errors['email']) { <span>El formato de correo es inválido.</span> }
                </div>
              }
            </div>

            <!-- Password -->
            <div>
              <label for="password" class="block text-sm font-medium text-slate-700">
                Contraseña
              </label>
              <div class="mt-1">
                <input
                  id="password"
                  type="password"
                  formControlName="password"
                  autocomplete="current-password"
                  class="appearance-none block w-full px-3 py-2 border border-slate-300 rounded-md shadow-sm placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-amber-500 sm:text-sm transition-all duration-200"
                  [ngClass]="{'border-red-300 focus:ring-red-500 focus:border-red-500': submitted && f['password'].errors}"
                  placeholder="••••••••"
                />
              </div>
              @if (submitted && f['password'].errors) {
                <div class="mt-1 text-sm text-red-600">
                  @if (f['password'].errors['required']) { <span>La contraseña es requerida.</span> }
                  @if (f['password'].errors['minlength']) { <span>La contraseña debe tener al menos 6 caracteres.</span> }
                </div>
              }
            </div>

            <!-- Remember me & Forgot password -->
            <div class="flex items-center justify-between">
              <div class="flex items-center">
                <input
                  id="remember-me"
                  type="checkbox"
                  class="h-4 w-4 text-amber-600 focus:ring-amber-500 border-slate-300 rounded transition-colors"
                />
                <label for="remember-me" class="ml-2 block text-sm text-slate-900">
                  Recordarme
                </label>
              </div>

              <div class="text-sm">
                <a href="#" class="font-medium text-amber-600 hover:text-amber-500 transition-colors">
                  ¿Olvidaste tu contraseña?
                </a>
              </div>
            </div>

            <!-- Submit Button -->
            <div>
              <button
                type="submit"
                [disabled]="isLoading()"
                class="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-amber-600 hover:bg-amber-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-amber-500 transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed items-center"
              >
                @if (isLoading()) {
                  <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Procesando...
                } @else {
                  Ingresar
                }
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  `
})
export class LoginComponent {
  loginForm: FormGroup;
  submitted = false;
  isLoading = signal(false);

  constructor(
    private formBuilder: FormBuilder,
    private router: Router
  ) {
    this.loginForm = this.formBuilder.group({
      email: ['', [Validators.required, Validators.email]],
      password: ['', [Validators.required, Validators.minLength(6)]]
    });
  }

  get f() { return this.loginForm.controls; }

  onSubmit(): void {
    this.submitted = true;

    if (this.loginForm.invalid) {
      return;
    }

    this.isLoading.set(true);

    // TODO: Connect to backend auth service
    setTimeout(() => {
      console.log('Login success:', this.loginForm.value);
      this.isLoading.set(false);
    }, 1500);
  }
}