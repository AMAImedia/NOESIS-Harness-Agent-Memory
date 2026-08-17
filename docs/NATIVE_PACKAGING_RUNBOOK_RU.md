# Native packaging runbook для NOESIS

## Обязательная модель сборки

PyInstaller и Briefcase должны запускаться на самой target OS с Python 3.14 и соответствующей архитектурой. Linux-сборка не является доказательством Windows `.exe` или macOS `.app`. Для macOS arm64 и x86_64 нужны отдельные native jobs либо подтверждённый universal2 build.

Сначала используется PyInstaller `onedir`: он проще для диагностики missing imports и позволяет проверить состав артефакта. `onefile` не является default, потому что распаковывается во временную директорию и требует отдельного cleanup/crash review. На Windows нельзя добавлять UAC elevation как способ обхода ограничений.

Briefcase является альтернативным native app/installer backend. Для macOS production distribution нужны code signing и notarization; identity и entitlements должны быть явными, минимальными и проверенными. Unsigned/ad-hoc artifacts разрешены только для локальной development verification.

## Команды

На Windows Python 3.14 запускается:

```text
python scripts/build_native.py --backend pyinstaller --target windows --run
python scripts/build_native.py --backend briefcase --target windows --run
```

На macOS Python 3.14 запускается:

```text
python3 scripts/build_native.py --backend pyinstaller --target macos --run
python3 scripts/build_native.py --backend briefcase --target macos --run
```

Без `--run` команда выполняет только fail-closed target check и печатает план; это безопасный режим для CI discovery. Нативная сборка не должна скачивать модели, credentials или произвольные dependencies во время packaging job.

## Release gates

Перед публикацией нужно проверить install/uninstall в чистой системе, loopback binding, data-root separation, session persistence, child timeout/recovery, no-network mode, UI CSP, redacted logs, license/provenance artifacts, SHA-256 manifest и SBOM. На macOS дополнительно проверяются signing, notarization, entitlements и quarantine behavior. На Windows проверяются Authenticode signing, SmartScreen metadata, отсутствие неожиданного UAC и clean user data path.

Текущая sandbox-среда — Linux/CPython 3.12.3, поэтому native commands здесь намеренно завершаются fail-closed и не являются native evidence.


## Реализованный checksum/SBOM gate

`python3 scripts/build_portable_artifact.py --root . --output dist/noesis-portable.zip` создаёт `PORTABLE_MANIFEST.json` с Python 3.14-only runtime policy, размером и SHA-256 каждого включённого файла, а также `PORTABLE_SBOM.spdx.json` в формате SPDX 2.3. SBOM содержит только фактически упакованные файлы и повторяет их SHA-256; `.env`, credential-like key files, model weights и virtual environments исключаются builder policy. Этот source-portable artifact gate не заменяет native Windows/macOS build evidence.

Focused verification: `tests.test_packaging_artifact`; полный suite должен пройти без `ResourceWarning`. Target-host `.exe`/`.app` evidence по-прежнему требует запуска `scripts/build_native.py` на соответствующей Windows/macOS машине с Python 3.14.


## Target-host evidence verifier

После target-host сборки запускается `scripts/verify_native_artifact.py`. Для Windows он проверяет Python 3.14, Windows host, `.exe` shape, SHA-256 и Authenticode через `signtool`; для macOS — Python 3.14, macOS host, `.app` bundle, SHA-256, `codesign --verify --deep --strict` и `spctl` assessment. Скрипт не запускает приложение и не подменяет native build.

Статусы имеют строгое значение: `verified` означает выполненные release signing gates; `development_unsigned` разрешён только для локальной разработки с явным флагом; `not_run` означает отсутствие target host, инструмента подписи или runner evidence. Linux execution с `--target windows` или `--target macos` обязан завершаться `target_host_or_python_mismatch`.


## CI packaging-contract smoke

CI job `packaging-contract` выполняется на Python 3.14 и проверяет оба static native manifest, строит source-portable ZIP с SHA-256/SBOM, затем намеренно запускает Windows native verifier на Linux и требует `exit 2` с причиной `target_host_or_python_mismatch`. Это проверяет honesty boundary и artifact evidence schema, но не является Windows/macOS native build evidence.
