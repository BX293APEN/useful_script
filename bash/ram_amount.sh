#!/usr/bin/env bash

get_pid() {
    local program_name="$1"
    local pid
    pid=$(pgrep -x "$program_name" | head -1)

    if [[ -z "$pid" ]]; then
        echo "Error: '$program_name' が見つかりません" >&2
        return 1
    fi

    echo "$program_name $pid"
}

ram_amount() {
    local program_name="$1"
    local info pid name

    info=$(get_pid "$program_name") || return 1
    name=$(echo "$info" | awk '{print $1}')
    pid=$(echo "$info" | awk '{print $2}')

    local rss vm_peak
    rss=$(grep VmRSS /proc/"$pid"/status 2>/dev/null | awk '{print $2}')
    vm_peak=$(grep VmPeak /proc/"$pid"/status 2>/dev/null | awk '{print $2}')

    if [[ -z "$rss" ]]; then
        echo "Error: PID $pid の情報を取得できません" >&2
        return 1
    fi

    local nameSize=10
    local pidSize=7
    local columnSize=15

    printf "%-${nameSize}s %-${pidSize}s %-${columnSize}s %-${columnSize}s\n" "プログラム名" "PID" "現在のRAM" "最大RAM"
    printf "%-${nameSize}s %-${pidSize}s %-${columnSize}s %-${columnSize}s\n" "${name}" "${pid}" "${rss}" "${vm_peak}"
}