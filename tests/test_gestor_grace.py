import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import gestor_grace as gestor
from version_grace import revision_codigo


class PruebasGestorGrace(unittest.TestCase):
    def test_inicio_secreto_solo_en_entorno_y_marcador_sin_clave(self):
        with tempfile.TemporaryDirectory() as carpeta:
            with patch.object(gestor, 'MARCADOR', Path(carpeta)/'proceso.json') as marcador:
                with patch.object(gestor.secrets, 'token_hex', return_value='instancia-prueba'):
                    with patch.object(gestor, 'salud', side_effect=[
                            None, {'estado':'ok','instancia':'instancia-prueba','proceso':12345}]):
                        with patch.object(gestor.subprocess, 'Popen') as crear:
                            crear.return_value.pid = 12345
                            crear.return_value.poll.return_value = None
                            self.assertEqual(gestor.iniciar('CLAVE-FALSA'), 'iniciado')
                            args, kwargs = crear.call_args
                            self.assertNotIn('CLAVE-FALSA', str(args))
                            self.assertEqual(kwargs['env']['GRACE_IA_KEY'], 'CLAVE-FALSA')
                            self.assertNotIn('CLAVE-FALSA', marcador.read_text())

    def test_existente_no_inicia_otro_servidor(self):
        with patch.object(gestor, 'salud', return_value={
                'estado':'ok', 'revision':revision_codigo()}):
            with patch.object(gestor.subprocess, 'Popen') as crear:
                self.assertEqual(gestor.iniciar(''), 'existente')
                crear.assert_not_called()

    def test_detener_no_termina_proceso_ajeno(self):
        with tempfile.TemporaryDirectory() as carpeta:
            marcador = Path(carpeta)/'proceso.json'
            marcador.write_text(json.dumps({'proceso':123, 'instancia':'otra'}))
            with patch.object(gestor, 'MARCADOR', marcador):
                with patch.object(gestor, 'salud', return_value={'proceso':123,'instancia':'actual'}):
                    with patch.object(gestor.os, 'kill') as terminar:
                        with self.assertRaises(ValueError):
                            gestor.detener()
                        terminar.assert_not_called()


if __name__ == '__main__':
    unittest.main()
