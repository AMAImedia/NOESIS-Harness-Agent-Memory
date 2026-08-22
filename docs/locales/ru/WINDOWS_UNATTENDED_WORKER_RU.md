# Автономный NOESIS worker на Windows

В ветке deployment находится stdlib-only worker для непрерывной локальной работы NOESIS Harness. Он запускается задачей Windows Task Scheduler `NOESIS-Harness-AutoLoop` от имени системной учётной записи `SYSTEM` с максимальным доступным уровнем прав.

## Контракт работы

Worker выполняет один ограниченный validation cycle, атомарно сохраняет JSON state в `.noesis_autoloop/state.json`, пишет журнал в `.noesis_autoloop/worker.log` и затем ждёт следующий cycle. Файловый lock запрещает параллельные процессы. Если процесс-владелец lock исчез, stale lock удаляется при следующем запуске. Windows profile по умолчанию запускает проверенный platform-neutral smoke suite на Python 3.11; Linux profile сохраняет полный discovery suite.

Задача имеет AtStartup trigger и recovery trigger каждые 15 минут, не запускает второй экземпляр одновременно и имеет bounded restart policy: 10 попыток с интервалом 2 минуты. Старые задачи `NOESIS_TrainWatchdog` и `NOESIS-YT-*` не изменяются.

## Граница безопасности

Worker проверяет и фиксирует локальное состояние проекта. Он не создаёт молчащий код, не вызывает модель, не публикует release и не заявляет внешний benchmark. Настоящая автономная разработка требует явно настроенной локальной model command или одобренной API-backed command через `NOESIS_AUTOLOOP_COMMAND`; произвольные команды по умолчанию запрещены. Native Windows packaging, macOS и external A/B остаются отдельными evidence lanes.

## Проверка запуска

На подключённом Windows host подтверждены `RunLevel=Highest`, `User=SYSTEM`, успешный smoke cycle `73` тестов, обновляющийся heartbeat и активный lock во время работы long-lived worker. Deployment branch — `windows-autoloop`; worker и installer синхронизированы с GitHub.
