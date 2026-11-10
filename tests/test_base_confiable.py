"""Arranque verificable y distribución. Sin proveedor externo ni datos reales."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import gestor_grace as gestor
from version_grace import revision_codigo, servidor_actual


class BaseConfiable(unittest.TestCase):
    def test_huella_cambia_con_modulos_nuevos_y_ignora_datos(self):
        with tempfile.TemporaryDirectory() as carpeta:
            base = Path(carpeta)
            (base / 'web').mkdir()
            (base / 'grace').mkdir()
            archivo = base / 'web' / 'personalizacion.js'
            archivo.write_text('let tema = 1;\n', encoding='utf-8')
            primera = revision_codigo(base)
            archivo.write_bytes(b'let tema = 1;\r\n')
            self.assertEqual(revision_codigo(base), primera)
            (base / 'data').mkdir()
            (base / 'data' / 'estado.json').write_text('{}')
            (base / '.grace_proceso.json').write_text('{}')
            self.assertEqual(revision_codigo(base), primera)
            archivo.write_text('let tema = 2;\n')
            self.assertNotEqual(revision_codigo(base), primera)
            segunda = revision_codigo(base)
            (base / 'grace' / 'nuevo.py').write_text('VALOR = 1\n')
            self.assertNotEqual(revision_codigo(base), segunda)

    def test_servidor_antiguo_no_se_reutiliza_ni_inicia_otro(self):
        for estado in ({'estado': 'ok', 'publicacion_conjunta': True},
                       {'estado': 'ok', 'revision': 'antigua'}):
            with self.subTest(estado=estado):
                self.assertFalse(servidor_actual(estado))
                with patch.object(gestor, 'salud', return_value=estado), \
                        patch.object(gestor.subprocess, 'Popen') as crear:
                    with self.assertRaisesRegex(ValueError, 'reiniciarse'):
                        gestor.iniciar()
                    crear.assert_not_called()
        self.assertTrue(servidor_actual({'revision': revision_codigo()}))

    def test_inicio_reglas_no_hereda_clave(self):
        with tempfile.TemporaryDirectory() as carpeta, \
                patch.object(gestor, 'MARCADOR', Path(carpeta) / 'proceso.json'), \
                patch.dict(os.environ, {'GRACE_IA_KEY': 'SECRETO-FALSO'}), \
                patch.object(gestor.secrets, 'token_hex', return_value='instancia-prueba'), \
                patch.object(gestor, 'salud', side_effect=[None, {
                    'estado':'ok', 'instancia':'instancia-prueba', 'proceso':12345}]), \
                patch.object(gestor.subprocess, 'Popen') as crear:
            crear.return_value.pid = 12345
            crear.return_value.poll.return_value = None
            self.assertEqual(gestor.iniciar(modo='reglas'), 'iniciado')
            entorno = crear.call_args.kwargs['env']
            self.assertEqual(entorno['GRACE_IA'], 'reglas')
            self.assertNotIn('GRACE_IA_KEY', entorno)
            self.assertNotIn('SECRETO-FALSO', gestor.MARCADOR.read_text())

    def test_revision_de_salud_es_la_capturada_al_arrancar(self):
        import app
        inicio = app.REVISION_INICIO
        with patch('version_grace.revision_codigo', return_value='codigo-modificado'):
            self.assertEqual(app.REVISION_INICIO, inicio)
            self.assertFalse(servidor_actual({'revision': inicio}))
        self.assertEqual(len(inicio), 64)

    def test_lanzador_compara_huella_y_ofrece_reglas(self):
        base = Path(__file__).resolve().parents[1]
        lanzador = (base / 'Abrir_Grace.pyw').read_text(encoding='utf-8')
        self.assertIn('servidor_actual(servidor)', lanzador)
        self.assertNotIn("servidor.get('publicacion_conjunta')", lanzador)
        self.assertIn("abrir('reglas')", lanzador)


if __name__ == '__main__':
    unittest.main()
