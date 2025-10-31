#!/usr/bin/env bash

# /etc/dnsmasq.conf に追記
# conf-dir=/etc/dnsmasq.d/,*.conf


set -e

d=$(date '+%Y%m')
now=$(date)

CONFIG_DIR="/home/pen/Documents/config"
DOMAIN_LIST="${CONFIG_DIR}/adblocklist.txt"
DNSMASQ_CONF="${CONFIG_DIR}/adblock.conf"
TARGET_CONF="/etc/dnsmasq.d/adblock.conf"

mkdir -p "${CONFIG_DIR}"

sleep 20 # 起動するまでスリープ

# ドメインリスト取得と整形
curl -o "${DOMAIN_LIST}" -L "https://280blocker.net/files/280blocker_domain_${d}.txt"

# BOM削除
sed -i '1s/^\xEF\xBB\xBF//' "${DOMAIN_LIST}"

# コメント削除
sed -i '1,/^[^#]/ { /^#/d }' "${DOMAIN_LIST}"

# 無効にされているドメインも有効化
sed -i 's/^# //' "${DOMAIN_LIST}"

# dnsmasq 用設定ファイル生成
echo "# 広告ブロックリスト" > "${DNSMASQ_CONF}"

while IFS= read -r domain; do
    if [[ -n "${domain}" ]]; then
        echo "address=/${domain}/0.0.0.0" >> "${DNSMASQ_CONF}"
        echo "address=/${domain}/::" >> "${DNSMASQ_CONF}"
    fi
done < "${DOMAIN_LIST}"

echo "# Updated: ${now}" >> "${DNSMASQ_CONF}"

# 設定ファイルを配置
sudo cp "${DNSMASQ_CONF}" "${TARGET_CONF}"

# dnsmasq を再起動
sudo systemctl restart dnsmasq
