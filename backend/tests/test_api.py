"""Run with: python -m unittest discover -s tests -v (from backend)."""
import asyncio
import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from app.main import app
from app.db import database
from app.services.serial_service import SerialMonitor


async def asgi_request(method, path, payload=None, token=None):
    """Exercise the real ASGI router without optional HTTP client dependencies."""
    body = json.dumps(payload).encode() if payload is not None else b''
    headers = [(b'content-type', b'application/json')]
    if token:
        headers.append((b'authorization', f'Bearer {token}'.encode()))
    messages = []
    received = False

    async def receive():
        nonlocal received
        if not received:
            received = True
            return {'type': 'http.request', 'body': body, 'more_body': False}
        await asyncio.Event().wait()

    async def send(message):
        messages.append(message)

    scope = {'type': 'http', 'asgi': {'version': '3.0'}, 'http_version': '1.1',
             'method': method, 'scheme': 'http', 'path': path, 'raw_path': path.encode(),
             'query_string': b'', 'root_path': '', 'headers': headers,
             'client': ('127.0.0.1', 1234), 'server': ('test', 80)}
    await app(scope, receive, send)
    status = next(m['status'] for m in messages if m['type'] == 'http.response.start')
    result = b''.join(m.get('body', b'') for m in messages if m['type'] == 'http.response.body')
    return status, json.loads(result) if result else None


class APITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='centinela-test-')
        self.addCleanup(self.temp.cleanup)
        self.db_patch = patch.object(database, 'DB_PATH', self.temp.name + '/test.db')
        self.db_patch.start()
        self.addCleanup(self.db_patch.stop)
        database.init_db()
        self.token = None
        status, data = self.request('POST', '/auth/setup', {
            'username': 'administrator', 'full_name': 'Test Administrator',
            'password': 'Test-password-123'})
        self.assertEqual(status, 201, data)
        self.token = data['access_token']

    def request(self, method, path, payload=None):
        return asyncio.run(asgi_request(method, path, payload, self.token))

    def incident(self):
        status, data = self.request('POST', '/sensors/', {
            'incident_text': 'Persona herida junto al nodo 2',
            'latitude': 13.48, 'longitude': -88.18})
        self.assertEqual(status, 201, data)
        return data['id']

    def assignment(self):
        incident = self.incident()
        status, data = self.request('PATCH', f'/incidents/{incident}', {'priority': 'Alta', 'triage_state': 'Validada'})
        self.assertEqual(status, 200, data)
        status, brigade = self.request('POST', '/brigades/', {'name': 'Brigada A'})
        self.assertEqual(status, 201, brigade)
        status, assignment = self.request('POST', '/assignments', {'incident_id': incident, 'brigade_id': brigade['id']})
        self.assertEqual(status, 201, assignment)
        return incident, brigade['id'], assignment['id']

    def test_health_and_authentication(self):
        self.token = None
        status, data = self.request('GET', '/health/')
        self.assertEqual((status, data['database']), (200, 'connected'))
        for method, path in [('GET', '/incidents'), ('POST', '/sensors/clear-hardware')]:
            self.assertEqual(self.request(method, path)[0], 401)

    def test_clear_hardware_connected_and_disconnected(self):
        for connected, expected in [(False, 503), (True, 200)]:
            with patch('app.api.routes.sensors.serial_monitor.send_command', return_value=connected) as send:
                self.assertEqual(self.request('POST', '/sensors/clear-hardware')[0], expected)
                send.assert_called_once_with('CLEAR_ALERT')

    def test_validation_requires_priority(self):
        incident = self.incident()
        self.assertEqual(self.request('PATCH', f'/incidents/{incident}', {'triage_state': 'Validada'})[0], 409)
        self.assertEqual(database.get_incident(incident)['triage_state'], 'Pendiente de validación')
        self.assertEqual(self.request('PATCH', f'/incidents/{incident}', {'priority': 'Media', 'triage_state': 'Validada'})[0], 200)
        self.assertEqual(self.request('PATCH', f'/incidents/{incident}', {'priority': 'Pendiente'})[0], 409)

    def test_legacy_validated_pending_cannot_dispatch(self):
        incident = self.incident()
        with database.connection() as conn:
            conn.execute("UPDATE sensors_data SET triage_state='Validada' WHERE id=?", (incident,))
        brigade = database.create_brigade('Brigada', '', [])
        self.assertEqual(self.request('POST', '/assignments', {'incident_id': incident, 'brigade_id': brigade['id']})[0], 409)

    def test_direct_closure_completes_assignment_and_releases_brigade(self):
        incident, brigade, assignment = self.assignment()
        self.assertEqual(self.request('PATCH', f'/incidents/{incident}', {'resolution_status': 'Resuelta'})[0], 200)
        self.assertEqual(database.get_assignment(assignment)['status'], 'Completada')
        self.assertIsNotNone(database.get_assignment(assignment)['completed_at'])
        self.assertEqual(database.get_brigade(brigade)['status'], 'Disponible')
        self.assertEqual(self.request('PATCH', f'/assignments/{assignment}', {'status': 'En camino'})[0], 409)

    def test_direct_cancellation(self):
        incident, brigade, assignment = self.assignment()
        self.assertEqual(self.request('PATCH', f'/incidents/{incident}', {'resolution_status': 'Cancelada'})[0], 200)
        self.assertEqual(database.get_assignment(assignment)['status'], 'Cancelada')
        self.assertEqual(database.get_brigade(brigade)['status'], 'Disponible')

    def test_normal_dispatch_lifecycle(self):
        incident, brigade, assignment = self.assignment()
        for state in ['En camino', 'Atendiendo', 'Completada']:
            self.assertEqual(self.request('PATCH', f'/assignments/{assignment}', {'status': state})[0], 200)
        self.assertEqual(database.get_incident(incident)['resolution_status'], 'Resuelta')
        self.assertEqual(database.get_brigade(brigade)['status'], 'Disponible')

    def test_no_duplicate_dispatch_or_inconsistent_state(self):
        incident, brigade, assignment = self.assignment()
        self.assertEqual(self.request('POST', '/assignments', {'incident_id': incident, 'brigade_id': brigade})[0], 409)
        self.assertEqual(self.request('PATCH', f'/incidents/{incident}', {'resolution_status': 'Abierta'})[0], 409)

    def test_concurrent_dispatch_keeps_one_assignment(self):
        incident = self.incident()
        database.update_incident(incident, {'priority': 'Alta', 'triage_state': 'Validada'})
        brigades = [database.create_brigade(name, '', [])['id'] for name in ['Equipo A', 'Equipo B']]
        user_id = database.get_user_by_username('administrator')['id']

        def dispatch(brigade):
            try:
                database.create_assignment(incident, brigade, user_id, '')
                return True
            except ValueError:
                return False

        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(executor.map(dispatch, brigades))
        self.assertEqual(sorted(outcomes), [False, True])
        self.assertEqual(len(database.list_assignments()), 1)

    def test_application_lifespan(self):
        async def run():
            async with app.router.lifespan_context(app):
                status, data = await asgi_request('GET', '/health/')
                self.assertEqual(status, 200)
                self.assertEqual(data['database'], 'connected')
        with patch('app.main.serial_monitor.start') as start, patch('app.main.serial_monitor.stop') as stop:
            asyncio.run(run())
            start.assert_called_once()
            stop.assert_called_once()


class SerialTests(unittest.TestCase):
    def setUp(self):
        self.monitor = SerialMonitor()
        self.patcher = patch('app.services.serial_service.insert_sensor_data', return_value=1)
        self.insert = self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def test_emergency_words_are_preserved(self):
        for text in ['Persona inconsciente junto al nodo 2', 'Paciente conectado a oxígeno', 'Error en suministro eléctrico']:
            for encoded in [text, json.dumps({'incident_text': text, 'node_id': 2})]:
                self.monitor._process_data(encoded)
        self.assertEqual(self.insert.call_count, 6)

    def test_protocol_messages_are_ignored(self):
        for text in ['OK', 'CLEAR_ALERT', 'Alerta limpiada', 'Nodo receptor conectado', 'Buzzer apagado']:
            self.monitor._process_data(text)
        self.insert.assert_not_called()

    def test_non_object_json_does_not_interrupt_reception(self):
        for text in ['[]', 'null', '42', 'true', '"text"']:
            self.monitor._process_data(text)
        self.insert.assert_not_called()
        self.monitor._process_data('Persona herida')
        self.insert.assert_called_once()

    def test_failed_storage_can_be_retried(self):
        self.insert.side_effect = [RuntimeError('database is locked'), 2]
        self.monitor._process_data('Persona herida')
        self.monitor._process_data('Persona herida')
        self.monitor._process_data('Persona herida')
        self.assertEqual(self.insert.call_count, 2)

    def test_duplicates_expire(self):
        with patch('app.services.serial_service.time.monotonic', return_value=100):
            self.monitor._process_data('Persona herida')
            self.monitor._process_data('Persona herida')
        with patch('app.services.serial_service.time.monotonic', return_value=116):
            self.monitor._process_data('Persona herida')
        self.assertEqual(self.insert.call_count, 2)

    def test_corrupted_json_recovery(self):
        self.monitor._process_data('{"node_id":2,"incident_text":"Persona herida","latitude":13.4,"longitude":-88.1,}')
        self.assertEqual(self.insert.call_args.args[:6], (2, 'Emergencia', 'Pendiente', 13.4, -88.1, 'Persona herida'))

    def test_invalid_coordinates_ignored(self):
        for lat in [999, float('nan'), float('inf')]:
            self.monitor._process_data(json.dumps({'incident_text': 'Persona herida', 'latitude': lat}))
        self.insert.assert_not_called()


if __name__ == '__main__':
    unittest.main()
