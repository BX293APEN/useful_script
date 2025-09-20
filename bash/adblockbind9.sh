#!/usr/bin/env bash

set -e

d=$(date '+%Y%m')
now=$(date)

CONFIG_DIR="/home/pen/Documents/config"
DOMAIN_LIST="${CONFIG_DIR}/adblocklist.txt"
CONFIG_FILE="${CONFIG_DIR}/adnamed.conf.local"
ZONE_FILE="/etc/bind/adnamed.conf.local"

mkdir -p "${CONFIG_DIR}"

sleep 20 # 起動するまでスリープ

curl -o "${DOMAIN_LIST}" -L https://280blocker.net/files/280blocker_domain_${d}.txt
sed -i '1s/^\xEF\xBB\xBF//' "${DOMAIN_LIST}"
sed -i '1,/^[^#]/ { /^#/d }' "${DOMAIN_LIST}"
sed -i 's/^#//' "${DOMAIN_LIST}"

echo "// 広告ブロックリスト" > "$CONFIG_FILE"

while IFS= read -r domain; do
    if [[ -z "${domain}" ]];          then
        continue
    else                                    # 各ドメインに対してゾーン設定を追加
        tee -a "${CONFIG_FILE}" << EOF
zone "${domain}" {
    type master;
    file "empty.zone";
};

EOF

    fi
done < "${DOMAIN_LIST}"

echo "// Update : ${now}" >> "$CONFIG_FILE"

cp "${CONFIG_FILE}" "${ZONE_FILE}"

systemctl restart bind9
