# Заметки об источниках внешней атрибуции

Эти источники проверены по README/provenance-формулировкам и являются только references, а не доказательством скопированного кода или endorsement.

| Проект | Официальный источник | Подтверждённая роль в формулировках |
|---|---|---|
| Cloudflare OS | https://github.com/cloudflare/cloudflare-os | Ссылка на архитектуру capability/security |
| Project Think | https://blog.cloudflare.com/project-think/ | Ссылка на durable execution, fibers, sessions и agent runtime |
| DeepSeek Harness | https://github.com/deepseek-ai/deepseek-harness | Ссылка на plugin-oriented model/tool/skill/session/sandbox harness |
| OpenClaw | https://github.com/openclaw/openclaw | Ссылка на personal-agent gateway, channels, skills/plugins и cross-platform surface |
| Hermes Agent | https://github.com/NousResearch/hermes-agent | Ссылка на memory, skills, gateway и delegate |

Формулировка из официального README OpenClaw получена с GitHub: это персональный AI-ассистент, работающий на устройствах, соединяющий модели, инструменты, каналы сообщений и опциональные companion-приложения через один Gateway. Официальный поисковый результат DeepSeek на GitHub идентифицирует DeepSeek Harness как open-source agent harness. Официальный исходный код Hermes использован как upstream repository reference.

Политика атрибуции: NOESIS в данный момент не вендорит ни один из этих upstream-источников. Любое будущее повторное использование кода требует точной ревизии, license/NOTICE ревью, маркировки изменений, dependency audit и security review.
