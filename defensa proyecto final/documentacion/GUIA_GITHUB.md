# Publicar Grace en GitHub sin alterar los ejercicios de clase

El repositorio de clases `pdiazu-create/Programacion_Estructurada_G6` fue consultado como referencia. **Esta entrega no realiza cambios en él.**

## Repositorio independiente para Grace

Grace se conserva en el repositorio privado `pdiazu-create/proyecto-final`, separado del repositorio académico. Para nuevas mejoras, clona ese repositorio y trabaja en una rama; abre un Pull Request hacia `main` para revisar los cambios antes de integrarlos.

No inicialices este proyecto dentro de `Programacion_Estructurada_G6`, no reemplaces archivos de ese repositorio y no uses `git push --force`.

Para clonar el proyecto:

```bash
git clone https://github.com/pdiazu-create/proyecto-final.git
cd proyecto-final
```

## Precauciones

- `data/estado.json` y `data/.grace_inicializada` están excluidos con `.gitignore`. Se generan al ejecutar el programa. No borres `estado.json` para reiniciar la demo; usa la interfaz.
- No subir cuentas, contraseñas, tokens, archivos académicos reales ni `Registro_confidencial_Grace_v1.1.docx`.
- El README público solo describe el MVP y no divulga detalles estratégicos confidenciales del concepto.
- Conservar el repositorio de ejercicios originales: es evidencia de aprendizaje.

## Probar antes de subir

```bash
python -m unittest discover -s tests -v
```

Para revisar cambios en VS Code usa el panel **Control de código fuente**. El proyecto incluye `.vscode/launch.json` y `.vscode/tasks.json` para ejecutarlo y probarlo cómodamente.

## GitHub Pages no ejecuta Python

El repositorio permite revisar el código, **no publicar automáticamente la aplicación funcional**. Grace v0.4 tiene servidor Python; no se puede ofrecer completa desde GitHub Pages. Para la exposición, usa `python app.py` localmente. No despliegues esta versión en un hosting público, pues no tiene autenticación real.
