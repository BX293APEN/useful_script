RESET="\e[0m"

BOLD="\e[1m"          # 太字
DIM="\e[2m"           # 薄く
ITALIC="\e[3m"        # 斜体(非対応端末あり)
UNDER="\e[4m"         # 下線
BLINK="\e[5m"         # 点滅
REVERSE="\e[7m"       # 反転
HIDE="\e[8m"          # 非表示
STRIKE="\e[9m"        # 打ち消し線

FG_BLACK="\e[30m"
FG_RED="\e[31m"
FG_GREEN="\e[32m"
FG_YELLOW="\e[33m"
FG_BLUE="\e[34m"
FG_PURPLE="\e[35m"
FG_CYAN="\e[36m"
FG_WHITE="\e[37m"

FG_BRIGHT_BLACK="\e[90m"
FG_BRIGHT_RED="\e[91m"
FG_BRIGHT_GREEN="\e[92m"
FG_BRIGHT_YELLOW="\e[93m"
FG_BRIGHT_BLUE="\e[94m"
FG_BRIGHT_PURPLE="\e[95m"
FG_BRIGHT_CYAN="\e[96m"
FG_BRIGHT_WHITE="\e[97m"

BG_BLACK="\e[40m"
BG_RED="\e[41m"
BG_GREEN="\e[42m"
BG_YELLOW="\e[43m"
BG_BLUE="\e[44m"
BG_MAGENTA="\e[45m"
BG_CYAN="\e[46m"
BG_WHITE="\e[47m"

BG_BRIGHT_BLACK="\e[100m"
BG_BRIGHT_RED="\e[101m"
BG_BRIGHT_GREEN="\e[102m"
BG_BRIGHT_YELLOW="\e[103m"
BG_BRIGHT_BLUE="\e[104m"
BG_BRIGHT_PURPLE="\e[105m"
BG_BRIGHT_CYAN="\e[106m"
BG_BRIGHT_WHITE="\e[107m"

# ===== 256色 =====
FG_256() { printf "\e[38;5;%sm" "$1"; }
BG_256() { printf "\e[48;5;%sm" "$1"; }

# ===== TrueColor(24bitカラー) =====
FG_RGB() { printf "\e[38;2;%s;%s;%sm" "$1" "$2" "$3"; }
BG_RGB() { printf "\e[48;2;%s;%s;%sm" "$1" "$2" "$3"; }

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