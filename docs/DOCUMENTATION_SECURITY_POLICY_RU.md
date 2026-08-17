# Политика безопасности документации NOESIS

Документация является частью attack surface: пользователь может скопировать команду или пример без дополнительной проверки. Поэтому каждый Markdown code fence должен быть безопасным по умолчанию, воспроизводимым и явно маркировать, является ли действие read-only, simulation или real side effect.

Запрещены реальные или похожие на реальные credentials, `curl | sh`, неограниченный `sudo`, `rm -rf` по системным или домашним путям, inline `eval`/`exec`, shell interpolation пользовательского ввода и примеры с включённым `shell=True`. Для process execution нужно показывать argv-массив, workspace containment, timeout и явный Gatekeeper approval.

Каждый пример, способный менять файлы, сеть, процессы, аккаунты, платежи или публикации, должен иметь отдельный раздел с target, side effect, required capability, approval state, rollback path и expected audit event. В документации нельзя называть simulated platform tests native verification или local contract tests world-ranking benchmark.

`scripts/docs_security_audit.py` проверяет fenced code blocks в Markdown и должен входить в release audit. Если пример намеренно описывает опасный pattern как запрещённый, он должен быть вынесен из executable code fence в обычную prose или в специально тестируемый security holdout, чтобы copy-paste surface оставался безопасным.
