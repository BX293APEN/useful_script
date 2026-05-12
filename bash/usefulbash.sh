RESET=$'\033[0m'

BOLD=$'\033[1m'          # 太字
DIM=$'\033[2m'           # 薄く
ITALIC=$'\033[3m'        # 斜体(非対応端末あり)
UNDER=$'\033[4m'         # 下線
BLINK=$'\033[5m'         # 点滅
REVERSE=$'\033[7m'       # 反転
HIDE=$'\033[8m'          # 非表示
STRIKE=$'\033[9m'        # 打ち消し線

FG_BLACK=$'\033[30m'
FG_RED=$'\033[31m'
FG_GREEN=$'\033[32m'
FG_YELLOW=$'\033[33m'
FG_BLUE=$'\033[34m'
FG_PURPLE=$'\033[35m'
FG_CYAN=$'\033[36m'
FG_WHITE=$'\033[37m'

FG_BRIGHT_BLACK=$'\033[90m'
FG_BRIGHT_RED=$'\033[91m'
FG_BRIGHT_GREEN=$'\033[92m'
FG_BRIGHT_YELLOW=$'\033[93m'
FG_BRIGHT_BLUE=$'\033[94m'
FG_BRIGHT_PURPLE=$'\033[95m'
FG_BRIGHT_CYAN=$'\033[96m'
FG_BRIGHT_WHITE=$'\033[97m'

BG_BLACK=$'\033[40m'
BG_RED=$'\033[41m'
BG_GREEN=$'\033[42m'
BG_YELLOW=$'\033[43m'
BG_BLUE=$'\033[44m'
BG_MAGENTA=$'\033[45m'
BG_CYAN=$'\033[46m'
BG_WHITE=$'\033[47m'

BG_BRIGHT_BLACK=$'\033[100m'
BG_BRIGHT_RED=$'\033[101m'
BG_BRIGHT_GREEN=$'\033[102m'
BG_BRIGHT_YELLOW=$'\033[103m'
BG_BRIGHT_BLUE=$'\033[104m'
BG_BRIGHT_PURPLE=$'\033[105m'
BG_BRIGHT_CYAN=$'\033[106m'
BG_BRIGHT_WHITE=$'\033[107m'

# ===== 256色 =====
FG_256() { printf "\033[38;5;%sm" "$1"; }
BG_256() { printf "\033[48;5;%sm" "$1"; }

# ===== TrueColor(24bitカラー) =====
FG_RGB() { printf "\033[38;2;%s;%s;%sm" "$1" "$2" "$3"; }
BG_RGB() { printf "\033[48;2;%s;%s;%sm" "$1" "$2" "$3"; }

DISP_STR(){
    for arg in "$@"; do
        printf "%s" "${arg}"
    done
}

trim() {
    local var="$1"
    var="${var#"${var%%[![:space:]]*}"}"   # 前
    var="${var%"${var##*[![:space:]]}"}"   # 後
    echo "$var"
}

# ===== ログ出力用 =====
LOG(){
    local name=$(trim "${1:-USERAPP}")
    local state=$(trim "${2:-LOG}")
    local action=$(trim "${3:-ACTION}")
    local nowtime="$(date '+%Y/%m/%d %H:%M:%S')"
    local detail=$(trim "${4:-log detail}")
    
    echo -e "[${name}][${state}][${action}] ${nowtime} ${detail}"  # -eでエスケープシーケンス有効化
}

LOG_INFO(){
    local name="${1:-USERAPP}"
    local state="INFO"
    local action="${2:-ACTION}"
    local detail="${3:-detail}"

    DISP_STR "${FG_BRIGHT_CYAN}" "${BG_BLACK}"
    LOG "${name}" "${state}" "${action}" "${detail}"
    DISP_STR "${RESET}"
}

LOG_WARN(){
    local name="${1:-USERAPP}"
    local state="WARN"
    local action="${2:-ACTION}"
    local detail="${3:-detail}"

    DISP_STR "${FG_YELLOW}" "${BG_BLACK}"
    LOG "${name}" "${state}" "${action}" "${detail}"
    DISP_STR "${RESET}"
}

LOG_OK(){
    local name="${1:-USERAPP}"
    local state="OK"
    local action="${2:-ACTION}"
    local detail="${3:-detail}"

    DISP_STR "${FG_GREEN}" "${BG_BLACK}"
    LOG "${name}" "${state}" "${action}" "${detail}"
    DISP_STR "${RESET}"
}

LOG_ERROR(){
    local name="${1:-USERAPP}"
    local state="ERROR"
    local action="${2:-ACTION}"
    local detail="${3:-detail}"

    DISP_STR "${FG_RED}" "${BG_BLACK}"
    LOG "${name}" "${state}" "${action}" "${detail}"
    DISP_STR "${RESET}"
}

LOG_FAIL(){
    local name="${1:-USERAPP}"
    local state="FAIL"
    local action="${2:-ACTION}"
    local detail="${3:-detail}"

    DISP_STR "$(FG_RGB 204 51 0)" "${BG_BLACK}"
    LOG "${name}" "${state}" "${action}" "${detail}"
    DISP_STR "${RESET}"
}