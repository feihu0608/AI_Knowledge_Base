#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
PROJECT=ai-knowledge-base
COMPOSE=(docker compose -p "$PROJECT")

case "${1:-help}" in
  init)
    test -f .env || { cp .env.example .env; chmod 600 .env; echo "已创建 .env，请先填写生产密码和密钥。"; exit 2; }
    "${COMPOSE[@]}" run --rm migrate
    ;;
  start) "${COMPOSE[@]}" up -d --build ;;
  stop) "${COMPOSE[@]}" down ;;
  restart) "${COMPOSE[@]}" up -d --build --remove-orphans ;;
  status) "${COMPOSE[@]}" ps ;;
  logs) "${COMPOSE[@]}" logs -f --tail=200 "${2:-api}" ;;
  migrate) "${COMPOSE[@]}" run --rm migrate ;;
  seed-demo) "${COMPOSE[@]}" run --rm api python scripts/seed_demo.py ;;
  config) "${COMPOSE[@]}" config --quiet && echo COMPOSE_CONFIG_PASS ;;
  *) echo "Usage: ./manage.sh {init|start|stop|restart|status|logs [service]|migrate|seed-demo|config}" ;;
esac
