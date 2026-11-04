#!/usr/bin/env bash
# 批量抓取页面 DOM（绕过 JS 反爬）
# 用法: bash fetch_pages.sh <urls.txt> <outdir> [并发数]
set -u

URLS="${1:-urls.txt}"
OUT="${2:-html}"
JOBS="${3:-2}"
MIN_BYTES=20000          # 小于此值视为反爬占位页
BUDGET=20000             # virtual-time-budget ms
RETRY=2

mkdir -p "$OUT"

# ---- 定位 chromium ----
CHROME=""
for c in \
  "$HOME/AppData/Local/ms-playwright"/chromium-*/*/chrome.exe \
  "$HOME/AppData/Local/ms-playwright"/chromium-*/chrome-win*/chrome.exe \
  "/c/Program Files/Google/Chrome/Application/chrome.exe" \
  "/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" \
  "$(command -v chromium 2>/dev/null)" \
  "$(command -v google-chrome 2>/dev/null)"
do
  [ -f "$c" ] && CHROME="$c" && break
done
if [ -z "$CHROME" ]; then
  echo "ERROR: 未找到 Chromium。请先安装 Playwright 浏览器：" >&2
  echo "  npx playwright install chromium" >&2
  exit 1
fi
echo "chrome: $CHROME"

fname() {  # URL -> 安全文件名（必须与 extract.py 的 fname 完全一致）
  echo "$1" | sed -e 's#^https\?://##' -e 's#[/?=&#]#__#g' -e 's#___*#__#g' | sed 's#_*$##'
}

fetch_one() {
  local url="$1" out="$2" tmp="$2.tmp"
  local i=0 ok=0
  while [ $i -le $RETRY ]; do
    rm -f "$tmp"
    timeout 90 "$CHROME" \
      --headless --disable-gpu --no-sandbox --no-first-run \
      --disable-dev-shm-usage --disable-extensions --hide-scrollbars \
      --user-data-dir="/tmp/cr-$$-$RANDOM" \
      --virtual-time-budget=$BUDGET \
      --dump-dom "$url" > "$tmp" 2>/dev/null
    local sz=$(wc -c < "$tmp" 2>/dev/null || echo 0)
    if [ "$sz" -ge $MIN_BYTES ]; then
      mv "$tmp" "$out"; ok=1; break
    fi
    i=$((i+1)); sleep 2
  done
  if [ $ok -eq 1 ]; then
    echo "OK   $(wc -c < "$out") $url"
  else
    mv "$tmp" "$out" 2>/dev/null
    echo "BLOCKED $(wc -c < "$out" 2>/dev/null || echo 0) $url"
  fi
}
export -f fetch_one fname
export CHROME BUDGET MIN_BYTES RETRY

# 并发抓取
grep -v '^\s*$' "$URLS" | grep -v '^\s*#' | \
  xargs -I{} -P "$JOBS" bash -c '
    url="{}"
    name=$(fname "$url")
    fetch_one "$url" "'"$OUT"'/$name.html"
  '

echo "----"
total=$(grep -vc '^\s*$' "$URLS")
ok=$(grep -l . "$OUT"/*.html 2>/dev/null | wc -l)
blocked=$(find "$OUT" -name '*.html' -size -20k | wc -l)
echo "抓取完成: $ok/$total 个文件, 其中 $blocked 个疑似占位页"
if [ "$blocked" -gt 0 ]; then
  echo "提示: 占位页多为 JS 挑战。若占位页过半，检查站点是否要求特定 UA 或 Cookie，"
  echo "      可加 --user-agent 或改用 Playwright 脚本带 cookie 访问。"
fi
