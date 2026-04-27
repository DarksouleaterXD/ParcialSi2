import 'dart:async';
import 'dart:io';
import 'dart:typed_data';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:geolocator/geolocator.dart';
import 'package:image_picker/image_picker.dart';
import 'package:latlong2/latlong.dart';
import 'package:path_provider/path_provider.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:record/record.dart';

import '../../../core/auth_api.dart';
import '../../../core/auth_storage.dart';
import '../../../core/authorized_client.dart' show ApiClientException, AuthorizedClient, SessionExpiredException;
import '../../../core/theme/app_spacing.dart';
import '../../../core/widgets/primary_button.dart';
import '../../usuario_autenticacion/data/vehicles_api.dart';
import '../../usuario_autenticacion/domain/vehicle.dart';
import '../../usuario_autenticacion/presentation/session_navigation.dart';
import '../data/incidents_api.dart';
import '../data/incidents_repository.dart';
import '../offline/idempotency_key_util.dart';
import '../offline/pending_incidents_store.dart';
import '../offline/pending_report_enqueue.dart';
import 'incident_confirmation_screen.dart';
import 'pending_outbox_screen.dart';
import 'widgets/evidence_attach_panel.dart';
import 'widgets/location_summary_tile.dart';
import 'widgets/report_step_indicator.dart';

/// Wizard CU-09: vehículo → ubicación → evidencias → confirmar y enviar.
class ReportIncidentScreen extends StatefulWidget {
  const ReportIncidentScreen({
    super.key,
    required this.storage,
    required this.authApi,
    required this.vehiclesApi,
  });

  final AuthStorage storage;
  final AuthApi authApi;
  final VehiclesApi vehiclesApi;

  @override
  State<ReportIncidentScreen> createState() => _ReportIncidentScreenState();
}

class _ReportIncidentScreenState extends State<ReportIncidentScreen> {
  late final IncidentsRepository _repo = IncidentsRepository(
    IncidentsApi(AuthorizedClient(storage: widget.storage)),
  );

  final _desc = TextEditingController();
  final _extraText = TextEditingController();
  final _audioRecorder = AudioRecorder();

  var _step = 0;
  var _vehiclesLoading = true;
  String? _vehiclesError;
  List<Vehicle> _vehicles = [];
  int? _selectedVehicleId;

  var _locLoading = false;
  String? _locError;
  double? _lat;
  double? _lng;
  double? _accuracy;
  final MapController _mapController = MapController();
  static const LatLng _fallbackCenter = LatLng(-17.7833, -63.1821);

  final List<PhotoItem> _photoItems = [];

  List<int>? _audioBytes;
  String? _audioMime;
  String? _audioName;

  var _isRecording = false;
  var _isRecordStarting = false;
  var _recordSeconds = 0;
  Timer? _recordTimer;

  var _submitting = false;
  String? _submitError;

  @override
  void initState() {
    super.initState();
    _loadVehicles();
  }

  @override
  void dispose() {
    _recordTimer?.cancel();
    if (_isRecording) {
      unawaited(_audioRecorder.stop());
    }
    unawaited(_audioRecorder.dispose());
    _desc.dispose();
    _extraText.dispose();
    super.dispose();
  }

  Future<void> _loadVehicles() async {
    setState(() {
      _vehiclesLoading = true;
      _vehiclesError = null;
    });
    try {
      final page = await widget.vehiclesApi.list(pageSize: 100);
      if (!mounted) {
        return;
      }
      setState(() {
        _vehicles = page.items;
        _vehiclesLoading = false;
      });
    } on SessionExpiredException {
      if (mounted) {
        navigateToLoginReplacingStack(context: context, storage: widget.storage, authApi: widget.authApi);
      }
    } on ApiClientException catch (e) {
      if (mounted) {
        setState(() {
          _vehiclesLoading = false;
          _vehiclesError = e.message;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() {
          _vehiclesLoading = false;
          _vehiclesError = 'No se pudo conectar con el servidor';
        });
      }
    }
  }

  Future<void> _captureLocation() async {
    setState(() {
      _locLoading = true;
      _locError = null;
    });
    try {
      final enabled = await Geolocator.isLocationServiceEnabled();
      if (!enabled) {
        setState(() {
          _locLoading = false;
          _locError = 'Activá el servicio de ubicación del dispositivo.';
        });
        return;
      }
      var perm = await Geolocator.checkPermission();
      if (perm == LocationPermission.denied) {
        perm = await Geolocator.requestPermission();
      }
      if (perm == LocationPermission.deniedForever) {
        setState(() {
          _locLoading = false;
          _locError = 'Ubicación bloqueada. Habilitala en los ajustes del sistema.';
        });
        return;
      }
      if (perm == LocationPermission.denied) {
        setState(() {
          _locLoading = false;
          _locError = 'Se necesita permiso de ubicación para reportar.';
        });
        return;
      }
      final pos = await Geolocator.getCurrentPosition();
      if (!mounted) {
        return;
      }
      setState(() {
        _lat = pos.latitude;
        _lng = pos.longitude;
        _accuracy = pos.accuracy;
        _locLoading = false;
      });
      _mapController.move(LatLng(pos.latitude, pos.longitude), 16);
    } catch (_) {
      if (mounted) {
        setState(() {
          _locLoading = false;
          _locError = 'No se pudo obtener la ubicación. Reintentá.';
        });
      }
    }
  }

  Future<void> _pickPhoto() async {
    if (_photoItems.length >= ReportSubmitPayload.maxPhotosPerReport) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text(
              'Llegaste al máximo de fotos por reporte. Quitá una con la X en el chip para agregar otra.',
            ),
          ),
        );
      }
      return;
    }
    final source = await showModalBottomSheet<ImageSource>(
      context: context,
      builder: (ctx) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: const Icon(Icons.photo_camera_outlined),
              title: const Text('Cámara'),
              onTap: () => Navigator.pop(ctx, ImageSource.camera),
            ),
            ListTile(
              leading: const Icon(Icons.photo_library_outlined),
              title: const Text('Galería'),
              onTap: () => Navigator.pop(ctx, ImageSource.gallery),
            ),
          ],
        ),
      ),
    );
    if (source == null || !mounted) {
      return;
    }
    final picker = ImagePicker();
    final file = await picker.pickImage(source: source, maxWidth: 2048, imageQuality: 85);
    if (file == null || !mounted) {
      return;
    }
    final bytes = await file.readAsBytes();
    final mime = _detectImageMime(bytes);
    if (mime == null) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Formato de imagen no compatible. Usá JPG, PNG o WEBP.'),
          ),
        );
      }
      return;
    }
    setState(() {
      _photoItems.add(
        PhotoItem(
          bytes: bytes,
          mimeType: mime,
          filename: _safeFileName(file.path, mime),
        ),
      );
    });
  }

  String? _detectImageMime(Uint8List bytes) {
    if (bytes.length >= 3 &&
        bytes[0] == 0xFF &&
        bytes[1] == 0xD8 &&
        bytes[2] == 0xFF) {
      return 'image/jpeg';
    }
    if (bytes.length >= 8 &&
        bytes[0] == 0x89 &&
        bytes[1] == 0x50 &&
        bytes[2] == 0x4E &&
        bytes[3] == 0x47 &&
        bytes[4] == 0x0D &&
        bytes[5] == 0x0A &&
        bytes[6] == 0x1A &&
        bytes[7] == 0x0A) {
      return 'image/png';
    }
    if (bytes.length >= 12 &&
        bytes[0] == 0x52 &&
        bytes[1] == 0x49 &&
        bytes[2] == 0x46 &&
        bytes[3] == 0x46 &&
        bytes[8] == 0x57 &&
        bytes[9] == 0x45 &&
        bytes[10] == 0x42 &&
        bytes[11] == 0x50) {
      return 'image/webp';
    }
    return null;
  }

  String _safeFileName(String path, String mime) {
    final seg = path.split(RegExp(r'[/\\]')).lastWhere((s) => s.isNotEmpty, orElse: () => 'foto.jpg');
    if (seg.contains('.')) {
      return seg;
    }
    if (mime == 'image/png') {
      return 'foto.png';
    }
    if (mime == 'image/webp') {
      return 'foto.webp';
    }
    return 'foto.jpg';
  }

  Future<void> _toggleRecording() async {
    if (_isRecording) {
      _recordTimer?.cancel();
      _recordTimer = null;
      final path = await _audioRecorder.stop();
      if (!mounted) {
        return;
      }
      setState(() => _isRecording = false);
      if (path != null && path.isNotEmpty) {
        final file = File(path);
        Uint8List? bytes;
        for (var attempt = 0; attempt < 8; attempt++) {
          if (await file.exists()) {
            final b = await file.readAsBytes();
            if (b.isNotEmpty) {
              bytes = b;
              break;
            }
          }
          await Future<void>.delayed(const Duration(milliseconds: 100));
        }
        if (bytes == null || bytes.isEmpty) {
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(
                content: Text(
                  'No se pudo leer la grabación (archivo vacío o aún en uso). Volvé a grabar 2–3 segundos o más y detené con el botón rojo.',
                ),
              ),
            );
          }
          return;
        }
        final detectedAudioMime = _detectAudioMime(bytes) ?? 'audio/mp4';
        if (!mounted) {
          return;
        }
        setState(() {
          _audioBytes = List<int>.from(bytes!);
          _audioMime = detectedAudioMime;
          _audioName = _audioFileNameForMime(detectedAudioMime);
        });
      } else {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('No se generó ruta de audio. Revisá el permiso de micrófono o probá otra vez.'),
            ),
          );
        }
      }
      return;
    }

    if (kIsWeb) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text(
              'La grabación de audio no está disponible en el navegador. Usá la app en Android o iOS.',
            ),
          ),
        );
      }
      return;
    }

    setState(() => _isRecordStarting = true);
    try {
      final mic = await Permission.microphone.request();
      if (!mic.isGranted) {
        if (mounted) {
          setState(() => _isRecordStarting = false);
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Se necesita permiso de micrófono para grabar.')),
          );
        }
        return;
      }
      if (!await _audioRecorder.hasPermission()) {
        if (mounted) {
          setState(() => _isRecordStarting = false);
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('No se pudo acceder al micrófono.')),
          );
        }
        return;
      }
      final dir = await getTemporaryDirectory();
      final path = '${dir.path}/cu09_${DateTime.now().millisecondsSinceEpoch}.m4a';
      await _audioRecorder.start(
        const RecordConfig(encoder: AudioEncoder.aacLc),
        path: path,
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _isRecordStarting = false;
        _isRecording = true;
        _recordSeconds = 0;
      });
      _recordTimer = Timer.periodic(const Duration(seconds: 1), (_) {
        if (mounted) {
          setState(() => _recordSeconds++);
        }
      });
    } on Object catch (e, st) {
      if (mounted) {
        setState(() => _isRecordStarting = false);
        debugPrint('record start failed: $e\n$st');
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('No se pudo iniciar la grabación: $e'),
          ),
        );
      }
    }
  }

  String? _detectAudioMime(Uint8List bytes) {
    if (bytes.length >= 12 &&
        bytes[0] == 0x52 &&
        bytes[1] == 0x49 &&
        bytes[2] == 0x46 &&
        bytes[3] == 0x46 &&
        bytes[8] == 0x57 &&
        bytes[9] == 0x41 &&
        bytes[10] == 0x56 &&
        bytes[11] == 0x45) {
      return 'audio/wav';
    }
    if (bytes.length >= 3 &&
        bytes[0] == 0x49 &&
        bytes[1] == 0x44 &&
        bytes[2] == 0x33) {
      return 'audio/mpeg';
    }
    if (bytes.length >= 2 && bytes[0] == 0xFF && (bytes[1] & 0xE0) == 0xE0) {
      return 'audio/mpeg';
    }
    if (bytes.length >= 12 &&
        bytes[0] == 0x1A &&
        bytes[1] == 0x45 &&
        bytes[2] == 0xDF &&
        bytes[3] == 0xA3) {
      return 'audio/webm';
    }
    if (bytes.length >= 8 &&
        bytes[4] == 0x66 &&
        bytes[5] == 0x74 &&
        bytes[6] == 0x79 &&
        bytes[7] == 0x70) {
      return 'audio/mp4';
    }
    for (var i = 0; i <= 76 && i + 4 < bytes.length; i++) {
      if (bytes[i] == 0x66 && bytes[i + 1] == 0x74 && bytes[i + 2] == 0x79 && bytes[i + 3] == 0x70) {
        return 'audio/mp4';
      }
    }
    return null;
  }

  String _audioFileNameForMime(String mime) {
    if (mime == 'audio/wav') {
      return 'evidencia.wav';
    }
    if (mime == 'audio/webm') {
      return 'evidencia.webm';
    }
    if (mime == 'audio/mpeg') {
      return 'evidencia.mp3';
    }
    return 'evidencia.m4a';
  }

  bool _canGoNext() {
    switch (_step) {
      case 0:
        return _selectedVehicleId != null;
      case 1:
        return _lat != null && _lng != null;
      case 2:
        return true;
      default:
        return true;
    }
  }

  void _next() {
    if (!_canGoNext()) {
      return;
    }
    setState(() {
      _step = (_step + 1).clamp(0, 3);
      _submitError = null;
    });
  }

  void _back() {
    if (_step > 0) {
      setState(() {
        _step--;
        _submitError = null;
      });
    } else {
      Navigator.of(context).pop();
    }
  }

  String _messageForApi(ApiClientException e) {
    switch (e.statusCode) {
      case 403:
        return e.message.isNotEmpty ? e.message : 'No tenés permiso para esta acción.';
      case 404:
        return e.message.isNotEmpty ? e.message : 'Recurso no encontrado.';
      case 422:
        return e.message.isNotEmpty ? e.message : 'Revisá los datos ingresados.';
      case 409:
        return e.message;
      case 413:
        return e.message.isNotEmpty ? e.message : 'El archivo es demasiado grande.';
      case 0:
      default:
        if (e.statusCode >= 500) {
          return 'Error del servidor. Reintentá más tarde.';
        }
        if (e.statusCode == 0) {
          return 'No se pudo conectar con el servidor.';
        }
        return e.message;
    }
  }

  Vehicle? _vehicleById(int id) {
    for (final v in _vehicles) {
      if (v.id == id) {
        return v;
      }
    }
    return null;
  }

  Future<void> _showOfflineQueuedDialog() async {
    if (!mounted) {
      return;
    }
    await showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Guardado en el dispositivo'),
        content: const Text(
          'El reporte quedó en cola como «Pendiente de envío». '
          'Cuando vuelva el internet se puede enviar automáticamente o tocá «Reintentar ahora» en Pendientes.',
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Seguir acá')),
          FilledButton(
            onPressed: () {
              Navigator.pop(ctx);
              Navigator.of(context).push<void>(
                MaterialPageRoute<void>(
                  builder: (_) => PendingOutboxScreen(storage: widget.storage),
                ),
              );
            },
            child: const Text('Ver pendientes'),
          ),
        ],
      ),
    );
  }

  Future<void> _submit() async {
    final vid = _selectedVehicleId;
    final lat = _lat;
    final lng = _lng;
    final v = vid == null ? null : _vehicleById(vid);
    if (v == null || lat == null || lng == null) {
      return;
    }
    final idemKey = generateIncidentIdempotencyKey();
    final vehicleLabel = '${v.placa} · ${v.marca} ${v.modelo}';
    final payload = ReportSubmitPayload(
      vehiculoId: v.id,
      latitud: lat,
      longitud: lng,
      descripcionTexto: _desc.text.trim().isEmpty ? null : _desc.text.trim(),
      photos: List<PhotoItem>.from(_photoItems),
      audioBytes: _audioBytes,
      audioMimeType: _audioMime,
      audioFilename: _audioName,
      extraTextEvidence: _extraText.text.trim().isEmpty ? null : _extraText.text.trim(),
    );

    final conn = await Connectivity().checkConnectivity();
    final onlyOffline = conn.length == 1 && conn.first == ConnectivityResult.none;
    if (onlyOffline) {
      final clientErr = payload.validateClientSide();
      if (clientErr != null) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(clientErr)));
        }
        return;
      }
      setState(() {
        _submitting = true;
        _submitError = null;
      });
      try {
        await enqueuePendingReport(
          store: pendingIncidentsGlobal,
          payload: payload,
          incidentIdempotencyKey: idemKey,
          vehiculoLabel: vehicleLabel,
        );
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('No se pudo guardar: $e')));
        }
        if (mounted) {
          setState(() => _submitting = false);
        }
        return;
      }
      if (!mounted) {
        return;
      }
      setState(() => _submitting = false);
      await _showOfflineQueuedDialog();
      return;
    }

    setState(() {
      _submitting = true;
      _submitError = null;
    });
    try {
      final outcome = await _repo.submitReport(
        payload,
        incidentIdempotencyKey: idemKey,
      );
      if (!mounted) {
        return;
      }
      await Navigator.of(context).pushReplacement(
        MaterialPageRoute<void>(
          builder: (_) => IncidentConfirmationScreen(
            storage: widget.storage,
            authApi: widget.authApi,
            incidenteId: outcome.detail.id,
            initialWarnings: outcome.warnings,
          ),
        ),
      );
    } on SessionExpiredException {
      if (mounted) {
        navigateToLoginReplacingStack(context: context, storage: widget.storage, authApi: widget.authApi);
      }
    } on ApiClientException catch (e) {
      if (e.statusCode == 0) {
        final clientErr = payload.validateClientSide();
        if (clientErr != null) {
          if (mounted) {
            setState(() {
              _submitting = false;
              _submitError = clientErr;
            });
          }
          return;
        }
        try {
          await enqueuePendingReport(
            store: pendingIncidentsGlobal,
            payload: payload,
            incidentIdempotencyKey: idemKey,
            vehiculoLabel: vehicleLabel,
          );
        } catch (ex) {
          if (mounted) {
            setState(() {
              _submitting = false;
              _submitError = 'No se pudo guardar localmente: $ex';
            });
          }
          return;
        }
        if (!mounted) {
          return;
        }
        setState(() => _submitting = false);
        await _showOfflineQueuedDialog();
        return;
      }
      if (mounted) {
        setState(() {
          _submitting = false;
          _submitError = _messageForApi(e);
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() {
          _submitting = false;
          _submitError = 'No se pudo conectar con el servidor';
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(
        title: const Text('Reportar emergencia'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_rounded),
          onPressed: _back,
        ),
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(AppSpacing.lg, AppSpacing.sm, AppSpacing.lg, 0),
            child: ReportStepIndicator(currentStep: _step),
          ),
          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(AppSpacing.lg),
              child: _buildStepBody(context, scheme),
            ),
          ),
          Padding(
            padding: EdgeInsets.fromLTRB(
              AppSpacing.lg,
              AppSpacing.sm,
              AppSpacing.lg,
              AppSpacing.lg + MediaQuery.paddingOf(context).bottom,
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                if (_step < 3)
                  PrimaryButton(
                    label: 'Continuar',
                    icon: Icons.arrow_forward_rounded,
                    onPressed: _canGoNext() ? _next : null,
                  )
                else ...[
                  if (_submitError != null) ...[
                    Text(
                      _submitError!,
                      style: TextStyle(color: scheme.error, fontWeight: FontWeight.w600),
                    ),
                    const SizedBox(height: AppSpacing.sm),
                  ],
                  PrimaryButton(
                    label: 'Enviar reporte',
                    icon: Icons.send_rounded,
                    isLoading: _submitting,
                    loadingLabel: 'Enviando…',
                    onPressed: _submitting ? null : _submit,
                  ),
                  const SizedBox(height: AppSpacing.sm),
                  SecondaryButton(
                    label: 'Atrás',
                    icon: Icons.arrow_back_rounded,
                    onPressed: _submitting ? null : _back,
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStepBody(BuildContext context, ColorScheme scheme) {
    if (_step == 0) {
      return _stepVehicle(context, scheme);
    }
    if (_step == 1) {
      return _stepLocation(context, scheme);
    }
    if (_step == 2) {
      return EvidenceAttachPanel(
        descriptionController: _desc,
        extraTextController: _extraText,
        photoCount: _photoItems.length,
        maxPhotos: ReportSubmitPayload.maxPhotosPerReport,
        hasAudio: _audioBytes != null && _audioBytes!.isNotEmpty,
        isRecordStarting: _isRecordStarting,
        isRecording: _isRecording,
        recordingSeconds: _recordSeconds,
        onPickPhoto: _pickPhoto,
        onRemovePhoto: (index) {
          if (index < 0 || index >= _photoItems.length) {
            return;
          }
          setState(() => _photoItems.removeAt(index));
        },
        onToggleRecord: _toggleRecording,
        onClearAudio: () => setState(() {
          _audioBytes = null;
          _audioMime = null;
          _audioName = null;
        }),
      );
    }
    return _stepReview(context, scheme);
  }

  Widget _stepVehicle(BuildContext context, ColorScheme scheme) {
    if (_vehiclesLoading) {
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: 48),
        child: Center(child: CircularProgressIndicator()),
      );
    }
    if (_vehiclesError != null) {
      return Column(
        children: [
          Icon(Icons.cloud_off_outlined, size: 48, color: scheme.onSurfaceVariant),
          const SizedBox(height: AppSpacing.md),
          Text(_vehiclesError!, textAlign: TextAlign.center),
          const SizedBox(height: AppSpacing.lg),
          SecondaryButton(
            label: 'Reintentar',
            icon: Icons.refresh_rounded,
            onPressed: _loadVehicles,
          ),
        ],
      );
    }
    if (_vehicles.isEmpty) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Icon(Icons.directions_car_outlined, size: 48, color: scheme.onSurfaceVariant),
          const SizedBox(height: AppSpacing.md),
          Text(
            'Necesitás al menos un vehículo registrado para reportar una emergencia.',
            style: Theme.of(context).textTheme.bodyLarge,
            textAlign: TextAlign.center,
          ),
        ],
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          'Seleccioná el vehículo involucrado',
          style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700),
        ),
        const SizedBox(height: AppSpacing.md),
        Text('Vehículo', style: Theme.of(context).textTheme.labelLarge),
        const SizedBox(height: AppSpacing.xs),
        ..._vehicles.map((v) {
          final selected = _selectedVehicleId == v.id;
          return Padding(
            padding: const EdgeInsets.only(bottom: AppSpacing.xs),
            child: Card(
              color: selected ? scheme.primaryContainer.withValues(alpha: 0.55) : null,
              child: InkWell(
                borderRadius: BorderRadius.circular(12),
                onTap: () => setState(() => _selectedVehicleId = v.id),
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md, vertical: AppSpacing.sm),
                  child: Row(
                    children: [
                      Expanded(
                        child: Text(
                          '${v.placa} · ${v.marca} ${v.modelo}',
                          style: Theme.of(context).textTheme.bodyLarge?.copyWith(fontWeight: FontWeight.w600),
                        ),
                      ),
                      Icon(
                        selected ? Icons.check_circle_rounded : Icons.circle_outlined,
                        color: selected ? scheme.primary : scheme.outline,
                      ),
                    ],
                  ),
                ),
              ),
            ),
          );
        }),
      ],
    );
  }

  Widget _stepLocation(BuildContext context, ColorScheme scheme) {
    final selected = (_lat != null && _lng != null) ? LatLng(_lat!, _lng!) : _fallbackCenter;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          'Ubicación del incidente',
          style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700),
        ),
        const SizedBox(height: AppSpacing.sm),
        Text(
          'Usamos tu posición actual para que los auxilios te encuentren.',
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: scheme.onSurfaceVariant),
        ),
        const SizedBox(height: AppSpacing.lg),
        ClipRRect(
          borderRadius: BorderRadius.circular(14),
          child: SizedBox(
            height: 260,
            child: FlutterMap(
              mapController: _mapController,
              options: MapOptions(
                initialCenter: selected,
                initialZoom: _lat != null ? 16 : 13,
                onTap: (_, point) {
                  setState(() {
                    _lat = point.latitude;
                    _lng = point.longitude;
                    _accuracy = null;
                    _locError = null;
                  });
                },
              ),
              children: [
                TileLayer(
                  urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                  userAgentPackageName: 'com.example.app_emergencias_cliente',
                ),
                if (_lat != null && _lng != null)
                  MarkerLayer(
                    markers: [
                      Marker(
                        point: LatLng(_lat!, _lng!),
                        width: 42,
                        height: 42,
                        child: const Icon(Icons.location_on_rounded, size: 42, color: Color(0xFFF97316)),
                      ),
                    ],
                  ),
              ],
            ),
          ),
        ),
        const SizedBox(height: AppSpacing.sm),
        Text(
          'Tocá el mapa para ajustar manualmente la ubicación.',
          style: Theme.of(context).textTheme.bodySmall?.copyWith(color: scheme.onSurfaceVariant),
        ),
        const SizedBox(height: AppSpacing.md),
        if (_locLoading)
          const Center(child: Padding(padding: EdgeInsets.all(24), child: CircularProgressIndicator()))
        else if (_lat != null && _lng != null)
          LocationSummaryTile(latitud: _lat!, longitud: _lng!, accuracyMeters: _accuracy)
        else if (_locError != null) ...[
          Text(_locError!, style: TextStyle(color: scheme.error)),
          const SizedBox(height: AppSpacing.md),
        ],
        const SizedBox(height: AppSpacing.md),
        OutlinedButton.icon(
          onPressed: _locLoading ? null : _captureLocation,
          icon: const Icon(Icons.my_location_rounded),
          label: Text(_lat == null ? 'Obtener ubicación actual' : 'Actualizar ubicación'),
        ),
      ],
    );
  }

  Widget _stepReview(BuildContext context, ColorScheme scheme) {
    final v = _vehicleById(_selectedVehicleId!)!;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          'Confirmá y enviá',
          style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700),
        ),
        const SizedBox(height: AppSpacing.md),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(AppSpacing.md),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _reviewRow('Vehículo', '${v.placa} (${v.marca} ${v.modelo})'),
                _reviewRow('Ubicación', '${_lat!.toStringAsFixed(5)}, ${_lng!.toStringAsFixed(5)}'),
                _reviewRow(
                  'Descripción',
                  _desc.text.trim().isEmpty ? '—' : _desc.text.trim(),
                ),
                if (_extraText.text.trim().isNotEmpty)
                  _reviewRow('Nota adicional', _extraText.text.trim()),
                _reviewRow('Evidencias', _evidenceReviewSummary()),
              ],
            ),
          ),
        ),
      ],
    );
  }

  /// Resumen del paso final: siempre muestra `Fotos (N)` y audio si aplica.
  String _evidenceReviewSummary() {
    final n = _photoItems.length;
    final hasAudio = _audioBytes != null && _audioBytes!.isNotEmpty;
    if (n == 0 && !hasAudio) {
      return 'Ninguna';
    }
    final parts = <String>['Fotos ($n)'];
    if (hasAudio) {
      parts.add('Audio');
    }
    return parts.join(' · ');
  }

  Widget _reviewRow(String k, String v) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.sm),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 100,
            child: Text(
              k,
              style: Theme.of(context).textTheme.labelLarge?.copyWith(
                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
            ),
          ),
          Expanded(child: Text(v, style: Theme.of(context).textTheme.bodyMedium)),
        ],
      ),
    );
  }
}
