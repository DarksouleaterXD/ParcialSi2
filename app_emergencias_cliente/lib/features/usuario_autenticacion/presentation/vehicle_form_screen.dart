import 'package:flutter/material.dart';

import '../../../core/authorized_client.dart' show ApiClientException, SessionExpiredException;
import '../../../core/theme/app_spacing.dart';
import '../../../core/widgets/app_section_header.dart';
import '../../../core/widgets/app_snackbar.dart';
import '../../../core/widgets/app_text_field.dart';
import '../../../core/widgets/primary_button.dart';
import '../data/vehicles_api.dart';
import '../domain/vehicle.dart';

/// Create (`POST /vehiculos`) or edit (`PATCH /vehiculos/{id}`).
class VehicleFormScreen extends StatefulWidget {
  const VehicleFormScreen({super.key, required this.api, this.vehicle, this.onSessionExpired});

  final VehiclesApi api;
  final Vehicle? vehicle;
  final VoidCallback? onSessionExpired;

  @override
  State<VehicleFormScreen> createState() => _VehicleFormScreenState();
}

class _VehicleFormScreenState extends State<VehicleFormScreen> {
  final _formKey = GlobalKey<FormState>();
  final _placa = TextEditingController();
  final _marca = TextEditingController();
  final _modelo = TextEditingController();
  final _anio = TextEditingController();
  final _color = TextEditingController();
  var _saving = false;
  String? _error;

  /// Baseline for PATCH diffs (updated from [GET /vehiculos/{id}] when editing).
  Vehicle? _baseline;
  var _loadingRemote = false;

  bool get _edit => widget.vehicle != null;

  @override
  void initState() {
    super.initState();
    final v = widget.vehicle;
    if (v != null) {
      _baseline = v;
      _applyVehicle(v);
      _loadingRemote = true;
      WidgetsBinding.instance.addPostFrameCallback((_) => _refreshVehicleFromServer());
    }
  }

  void _applyVehicle(Vehicle v) {
    _placa.text = v.placa;
    _marca.text = v.marca;
    _modelo.text = v.modelo;
    _anio.text = v.anio.toString();
    _color.text = v.color ?? '';
  }

  Future<void> _refreshVehicleFromServer() async {
    final id = _baseline?.id;
    if (id == null) {
      return;
    }
    try {
      final v = await widget.api.getById(id);
      if (!mounted) {
        return;
      }
      setState(() {
        _baseline = v;
        _applyVehicle(v);
        _loadingRemote = false;
      });
    } on SessionExpiredException {
      widget.onSessionExpired?.call();
      if (mounted) {
        Navigator.of(context).pop(false);
      }
    } catch (_) {
      if (mounted) {
        setState(() => _loadingRemote = false);
      }
    }
  }

  @override
  void dispose() {
    _placa.dispose();
    _marca.dispose();
    _modelo.dispose();
    _anio.dispose();
    _color.dispose();
    super.dispose();
  }

  String? _required(String? v, String label) {
    if (v == null || v.trim().isEmpty) {
      return 'Completá $label.';
    }
    return null;
  }

  String? _anioValidator(String? v) {
    final req = _required(v, 'el año');
    if (req != null) {
      return req;
    }
    final n = int.tryParse(v!.trim());
    if (n == null) {
      return 'Año inválido.';
    }
    if (n < 1980 || n > 2035) {
      return 'Entre 1980 y 2035.';
    }
    return null;
  }

  Future<void> _save() async {
    setState(() => _error = null);
    if (!(_formKey.currentState?.validate() ?? false)) {
      return;
    }
    setState(() => _saving = true);
    try {
      if (_edit) {
        final base = _baseline ?? widget.vehicle!;
        final id = base.id;
        final patch = <String, dynamic>{};
        final placa = _placa.text.trim().toUpperCase();
        if (placa != base.placa) {
          patch['placa'] = placa;
        }
        final marca = _marca.text.trim();
        if (marca != base.marca) {
          patch['marca'] = marca;
        }
        final modelo = _modelo.text.trim();
        if (modelo != base.modelo) {
          patch['modelo'] = modelo;
        }
        final anio = int.parse(_anio.text.trim());
        if (anio != base.anio) {
          patch['anio'] = anio;
        }
        final color = _color.text.trim();
        final prevC = base.color ?? '';
        if (color != prevC) {
          patch['color'] = color.isEmpty ? null : color;
        }
        if (patch.isEmpty) {
          if (mounted) {
            AppSnackBar.info(context, 'No hay cambios para guardar.');
          }
          setState(() => _saving = false);
          return;
        }
        await widget.api.update(id, patch);
      } else {
        await widget.api.create({
          'placa': _placa.text.trim().toUpperCase(),
          'marca': _marca.text.trim(),
          'modelo': _modelo.text.trim(),
          'anio': int.parse(_anio.text.trim()),
          'color': _color.text.trim().isEmpty ? null : _color.text.trim(),
        });
      }
      if (mounted) {
        AppSnackBar.success(
          context,
          _edit ? 'Vehículo actualizado.' : 'Vehículo registrado.',
        );
        Navigator.of(context).pop(true);
      }
    } on SessionExpiredException {
      widget.onSessionExpired?.call();
      if (mounted) {
        Navigator.of(context).pop(false);
      }
    } on ApiClientException catch (e) {
      setState(() => _error = e.message);
    } catch (e) {
      setState(() => _error = 'Error inesperado: $e');
    } finally {
      if (mounted) {
        setState(() => _saving = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(
        title: Text(_edit ? 'Editar vehículo' : 'Agregar vehículo'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          tooltip: 'Volver',
          onPressed: () => Navigator.of(context).pop(false),
        ),
      ),
      body: SafeArea(
        child: Column(
          children: [
            if (_loadingRemote) const LinearProgressIndicator(minHeight: 2),
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.fromLTRB(AppSpacing.lg, AppSpacing.md, AppSpacing.lg, AppSpacing.xl),
                child: Form(
                  key: _formKey,
                  autovalidateMode: AutovalidateMode.onUserInteraction,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Card(
                        child: Padding(
                          padding: const EdgeInsets.all(AppSpacing.lg),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: [
                              const AppSectionHeader(
                                title: 'Datos del vehículo',
                                subtitle: 'Placa, marca, modelo, año y color. Los marcados * son obligatorios.',
                              ),
                              const SizedBox(height: AppSpacing.md),
                              AppTextField(
                                controller: _placa,
                                label: 'Placa',
                                helperText: 'Se guardará en mayúsculas.',
                                prefixIcon: Icons.pin_outlined,
                                textCapitalization: TextCapitalization.characters,
                                validator: (v) => _required(v, 'la placa'),
                              ),
                              const SizedBox(height: AppSpacing.sm),
                              AppTextField(
                                controller: _marca,
                                label: 'Marca',
                                prefixIcon: Icons.directions_car_outlined,
                                validator: (v) => _required(v, 'la marca'),
                              ),
                              const SizedBox(height: AppSpacing.sm),
                              AppTextField(
                                controller: _modelo,
                                label: 'Modelo',
                                prefixIcon: Icons.label_outline_rounded,
                                validator: (v) => _required(v, 'el modelo'),
                              ),
                              const SizedBox(height: AppSpacing.sm),
                              AppTextField(
                                controller: _anio,
                                label: 'Año',
                                prefixIcon: Icons.calendar_today_outlined,
                                keyboardType: TextInputType.number,
                                validator: _anioValidator,
                              ),
                              const SizedBox(height: AppSpacing.sm),
                              AppTextField(
                                controller: _color,
                                label: 'Color (opcional)',
                                prefixIcon: Icons.palette_outlined,
                              ),
                            ],
                          ),
                        ),
                      ),
                      if (_error != null) ...[
                        const SizedBox(height: AppSpacing.sm),
                        DecoratedBox(
                          decoration: BoxDecoration(
                            color: scheme.errorContainer.withValues(alpha: 0.45),
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(color: scheme.error.withValues(alpha: 0.25)),
                          ),
                          child: Padding(
                            padding: const EdgeInsets.all(AppSpacing.md),
                            child: Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Icon(Icons.error_outline_rounded, color: scheme.error),
                                const SizedBox(width: AppSpacing.sm),
                                Expanded(
                                  child: Text(
                                    _error!,
                                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                                          color: scheme.onErrorContainer,
                                          fontWeight: FontWeight.w600,
                                        ),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ],
                      const SizedBox(height: AppSpacing.lg),
                      Row(
                        children: [
                          Expanded(
                            child: SecondaryButton(
                              label: 'Cancelar',
                              onPressed: _saving ? null : () => Navigator.of(context).pop(false),
                            ),
                          ),
                          const SizedBox(width: AppSpacing.sm),
                          Expanded(
                            child: PrimaryButton(
                              label: _edit ? 'Guardar cambios' : 'Guardar vehículo',
                              loadingLabel: 'Guardando…',
                              isLoading: _saving,
                              onPressed: _saving ? null : _save,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
