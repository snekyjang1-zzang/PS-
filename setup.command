#!/bin/bash
cd "$(dirname "$0")"
if command -v python3 >/dev/null 2>&1; then python3 mgp.py setup; else echo "Python 3 이 없습니다. https://www.python.org/downloads/ 에서 설치한 뒤 다시 실행하세요."; fi
echo
read -n 1 -s -r -p "아무 키나 누르면 닫힙니다."
