#!/usr/bin/env bash
set -Eeuo pipefail
(( EUID == 0 )) || {
  printf 'Su sekilde calistir: sudo %s\n' "$0" >&2
  exit 1
}
/usr/local/sbin/cachy-freeze publish
printf '%s\n' "Yeni Golden yayinlandi. Hazir oldugunuzda uygulamadan FROZEN moda gecin."
