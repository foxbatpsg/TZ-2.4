#!/usr/bin/env bash
# push.sh — push с самовосстановлением сломанного ref-namespace.
#
# Проблема проекта: в .git/refs/ есть посторонний namespace refs/cline/...
# Из-за него git после push/fetch НЕ записывает refs/remotes/origin/master,
# и `git status` врёт: "Your branch is based on 'origin/master', but the
# upstream is gone".
#
# Сам push при этом проходит успешно — страдает только локальный ref.
# Этот скрипт делает push и затем чинит ref вручную.
#
# Использование:
#   ./push.sh                    # push текущей ветки
#   ./push.sh -m "сообщение"     # закоммитить всё и запушить

set -u

# --- защита от запуска через WSL-bash ---
# В Windows есть три bash.exe; WSL-версия не видит git/awk и падает с 127.
case "$(uname -s 2>/dev/null || echo unknown)" in
  MINGW*|MSYS*|CYGWIN*) : ;;   # Git Bash — то, что нужно
  Linux)
    if [ -n "${WSL_DISTRO_NAME:-}" ] || grep -qi microsoft /proc/version 2>/dev/null; then
      echo "ОШИБКА: скрипт запущен через WSL-bash, а нужен Git Bash." >&2
      echo "WSL не видит Windows-пути и git этого репозитория." >&2
      echo "Запускайте через push.bat либо: \"C:\\Program Files\\Git\\bin\\bash.exe\" push.sh" >&2
      exit 127
    fi
    ;;
esac

# --- проверка, что git вообще доступен (иначе 127 будет невнятным) ---
if ! command -v git >/dev/null 2>&1; then
  echo "ОШИБКА: git не найден в PATH. Возможно, выбран не тот bash." >&2
  exit 127
fi

BRANCH="$(git rev-parse --abbrev-ref HEAD)"
REMOTE="origin"

if [ -z "$BRANCH" ] || [ "$BRANCH" = "HEAD" ]; then
  echo "ОШИБКА: не удалось определить текущую ветку (detached HEAD?)." >&2
  exit 1
fi

# --- шаг 1: опциональный коммит ---
if [ "${1:-}" = "-m" ]; then
  MSG="${2:-}"
  if [ -z "$MSG" ]; then
    echo "Ошибка: -m требует сообщение коммита." >&2
    exit 1
  fi
  echo "==> git add -A"
  git add -A
  echo "==> git commit -m \"$MSG\""
  git commit -m "$MSG" || echo "    (нечего коммитить — продолжаем)"
fi

# --- шаг 2: push ---
echo "==> git push $REMOTE $BRANCH"
if ! git push "$REMOTE" "$BRANCH"; then
  echo "ОШИБКА: push не удался. Разберитесь с причиной перед повтором." >&2
  exit 1
fi

# --- шаг 3: самовосстановление ref ---
# Без awk: `git ls-remote` возвращает "<sha>\t<ref>", берём первое поле
# через параметрное развёртывание — работает в любом sh/bash.
REMOTE_LINE="$(git ls-remote "$REMOTE" "refs/heads/$BRANCH" 2>/dev/null | head -n 1)"
REMOTE_SHA="${REMOTE_LINE%%[[:space:]]*}"
LOCAL_SHA="$(git rev-parse HEAD)"

if [ -z "$REMOTE_SHA" ]; then
  echo "ПРЕДУПРЕЖДЕНИЕ: не удалось получить SHA с remote." >&2
  exit 1
fi

if [ "$REMOTE_SHA" != "$LOCAL_SHA" ]; then
  echo "ВНИМАНИЕ: SHA не совпадают! remote=$REMOTE_SHA local=$LOCAL_SHA" >&2
  exit 1
fi

REF_FILE=".git/refs/remotes/$REMOTE/$BRANCH"
mkdir -p "$(dirname "$REF_FILE")"
printf '%s\n' "$REMOTE_SHA" > "$REF_FILE"
echo "==> ref починен: $REF_FILE -> $REMOTE_SHA"

# --- шаг 4: проверка ---
echo ""
echo "=== ИТОГ ==="
git status -sb | head -1
git branch -vv | head -1

if git status -sb | head -1 | grep -q 'gone'; then
  echo ""
  echo "ПРЕДУПРЕЖДЕНИЕ: ref всё ещё помечен 'gone'." >&2
  exit 1
fi

echo ""
echo "Готово. Локально и на remote: $REMOTE_SHA"
