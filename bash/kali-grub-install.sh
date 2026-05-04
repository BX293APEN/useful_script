#!/usr/bin/env bash
# =============================================================================
# kali-grub-install.sh
#   別のLinuxホスト（Ubuntu等）からKali Live USBのGRUBを修復するスクリプト
#
# 使い方:
#   sudo bash kali-grub-install.sh
#
# 【何度実行しても安全です】
#   このスクリプトはパーティション削除・フォーマット・rootfs展開を一切しません。
#   grub > で止まるUSBに対してそのまま実行してOKです。
#   やること: マウント → grub-install → grub.cfg生成 → アンマウント のみ。
#
# 【grub.cfg のroot指定方式】
#   initramfsあり（Kali等）→ UUID方式  root=UUID=xxxx  ← このスクリプト
#   initramfsなし（Yocto等）→ デバイス名固定  root=/dev/sda2
#   KaliはinitramfsがあるのでUUID方式を使います。
#   UUID方式ならターゲットPCでUSBが何番目のディスクになっても正しく起動します。
# =============================================================================

set -euo pipefail

MNT="/mnt/kali-repair"
LOGFILE="/tmp/kali-grub-install.log"

log_info()  { echo -e "\e[32m[INFO]\e[0m  $(date '+%H:%M:%S') $*"; }
log_warn()  { echo -e "\e[33m[WARN]\e[0m  $(date '+%H:%M:%S') $*"; }
log_error() { echo -e "\e[31m[ERROR]\e[0m $(date '+%H:%M:%S') $*"; exit 1; }
log_step()  { echo -e "\n\e[36m========== $* ==========\e[0m"; }

exec > >(tee -a "$LOGFILE") 2>&1
echo "============================================"
log_info "kali-grub-install.sh 開始  ログ: $LOGFILE"
echo "============================================"

# ─────────────────────────────────────────────
# 0. root確認 & コマンド確認
# ─────────────────────────────────────────────
log_step "事前確認"

[[ "$EUID" -eq 0 ]] || log_error "root権限が必要です: sudo bash kali-grub-install.sh"

for cmd in mount umount blkid lsblk findmnt; do
    command -v "$cmd" &>/dev/null || log_error "コマンドが見つかりません: $cmd"
done

# ─────────────────────────────────────────────
# 1. デバイス選択
# ─────────────────────────────────────────────
log_step "デバイス選択"

echo ""
echo "接続中のディスク一覧:"
echo "─────────────────────────────────────────────────────────"
lsblk -po NAME,SIZE,LABEL,MOUNTPOINT | head -n1
lsblk -po NAME,SIZE,LABEL,MOUNTPOINT \
    | grep -E '^(/dev/sd|/dev/nvme|/dev/mmcblk)|^[├└]─' \
    || lsblk -po NAME,SIZE,LABEL,MOUNTPOINT | grep -v "^NAME"
echo "─────────────────────────────────────────────────────────"

HOST_ROOT_DISK=$(findmnt -n -o SOURCE / \
    | sed 's/[0-9]*$//' | sed 's/p[0-9]*$//' || true)
echo ""
log_warn "ホストのルートディスクは ${HOST_ROOT_DISK} です（絶対に選ばないこと！）"
echo ""

while true; do
    echo -n "KaliのUSBディスク (例: sdb または /dev/sdb): "
    read -r INPUT
    DISK="/dev/${INPUT#/dev/}"

    if [[ ! -b "$DISK" ]]; then
        echo "[ERROR] ${DISK} はブロックデバイスではありません。再入力してください。"
        continue
    fi
    if [[ "$DISK" == "$HOST_ROOT_DISK" ]]; then
        echo "[ERROR] それはホストのルートディスクです！絶対に選べません。"
        continue
    fi

    echo ""
    echo "選択したディスクのパーティション:"
    echo "─────────────────────────────────────────────────────────"
    lsblk -po NAME,SIZE,FSTYPE,LABEL,MOUNTPOINT "$DISK" || true
    echo "─────────────────────────────────────────────────────────"
    echo ""
    break
done

# ─────────────────────────────────────────────
# 2. パーティション自動判定
# ─────────────────────────────────────────────
log_step "パーティション自動判定"

EFI_PART=""
ROOT_PART=""
ROOT_SIZE=0

while IFS= read -r partdev; do
    [[ -b "$partdev" ]] || continue
    FSTYPE=$(lsblk -no FSTYPE "$partdev" 2>/dev/null || true)
    PARTTYPE=$(lsblk -no PARTTYPE "$partdev" 2>/dev/null | tr '[:upper:]' '[:lower:]' || true)
    SIZE_BYTES=$(lsblk -bno SIZE "$partdev" 2>/dev/null || echo 0)

    if [[ "$FSTYPE" == "vfat" ]] && [[ "$PARTTYPE" == *"c12a7328"* ]]; then
        EFI_PART="$partdev"
        log_info "EFIパーティション検出: $EFI_PART"
        continue
    fi

    if [[ "$FSTYPE" =~ ^(ext4|xfs|btrfs)$ ]]; then
        if (( SIZE_BYTES > ROOT_SIZE )); then
            ROOT_PART="$partdev"
            ROOT_SIZE="$SIZE_BYTES"
        fi
    fi
done < <(lsblk -lno NAME "$DISK" | tail -n +2 | sed "s|^|/dev/|")

[[ -n "$ROOT_PART" ]] || log_error "rootパーティション（ext4/xfs/btrfs）が見つかりません"

log_info "rootパーティション : $ROOT_PART"
if [[ -n "$EFI_PART" ]]; then
    log_info "EFIパーティション  : $EFI_PART"
else
    log_warn "EFIパーティションが見つかりません → BIOSモードで処理します"
fi

# ─────────────────────────────────────────────
# 3. UEFI/BIOSモード判定
# ─────────────────────────────────────────────
log_step "起動モード判定"

if [[ -n "$EFI_PART" ]] && [[ -d /sys/firmware/efi ]]; then
    BOOT_MODE="uefi"
elif [[ -n "$EFI_PART" ]]; then
    echo "EFIパーティションが検出されましたがホストはBIOSモードです。"
    echo "ターゲットPCの起動モードを選んでください:"
    echo "  1) UEFI"
    echo "  2) BIOS/Legacy"
    read -rp "選択 (1 or 2): " MODE_SEL
    [[ "$MODE_SEL" == "1" ]] && BOOT_MODE="uefi" || BOOT_MODE="bios"
else
    BOOT_MODE="bios"
fi
log_info "起動モード: $BOOT_MODE"

# ─────────────────────────────────────────────
# 最終確認
# ─────────────────────────────────────────────
echo ""
echo -e "\e[31m======================================================\e[0m"
echo -e "\e[31m  ディスク           : $DISK\e[0m"
echo -e "\e[31m  rootパーティション : $ROOT_PART\e[0m"
[[ -n "$EFI_PART" ]] && echo -e "\e[31m  EFIパーティション  : $EFI_PART\e[0m"
echo -e "\e[31m  起動モード         : $BOOT_MODE\e[0m"
echo -e "\e[31m  ※ データは消去しません（grub修復のみ）\e[0m"
echo -e "\e[31m======================================================\e[0m"
read -rp "本当に続けますか？ (yes と入力して Enter): " CONFIRM
[[ "$CONFIRM" == "yes" ]] || { echo "中止しました。"; exit 0; }

# ─────────────────────────────────────────────
# cleanup トラップ
# ─────────────────────────────────────────────
cleanup() {
    log_info "クリーンアップ中..."
    umount -R "${MNT}/dev"      2>/dev/null || true
    umount -R "${MNT}/sys"      2>/dev/null || true
    umount    "${MNT}/proc"     2>/dev/null || true
    umount    "${MNT}/run"      2>/dev/null || true
    umount    "${MNT}/boot/efi" 2>/dev/null || true
    umount    "${MNT}"          2>/dev/null || true
}
trap cleanup EXIT

# ─────────────────────────────────────────────
# 4. 既存マウントの解除
# ─────────────────────────────────────────────
log_step "既存マウントの解除"

for part in "$ROOT_PART" ${EFI_PART:-}; do
    [[ -b "$part" ]] || continue
    while IFS= read -r mp; do
        [[ -n "$mp" ]] && umount "$mp" && log_info "アンマウント: $mp"
    done < <(lsblk -no MOUNTPOINT "$part" 2>/dev/null || true)
done
mountpoint -q "$MNT" 2>/dev/null && umount -R "$MNT" || true

# ─────────────────────────────────────────────
# 5. マウント
# ─────────────────────────────────────────────
log_step "マウント"

mkdir -p "$MNT"
mount "$ROOT_PART" "$MNT"
log_info "$ROOT_PART → $MNT"

if [[ "$BOOT_MODE" == "uefi" ]]; then
    mkdir -p "${MNT}/boot/efi"
    mount "$EFI_PART" "${MNT}/boot/efi"
    log_info "$EFI_PART → ${MNT}/boot/efi"
fi

# ─────────────────────────────────────────────
# 6. bind マウント
# ─────────────────────────────────────────────
log_step "bind マウント"

mount --types proc /proc "${MNT}/proc"
mount --rbind      /sys  "${MNT}/sys"
mount --make-rslave      "${MNT}/sys"
mount --rbind      /dev  "${MNT}/dev"
mount --make-rslave      "${MNT}/dev"
mkdir -p "${MNT}/run"
mount --bind /run        "${MNT}/run"

# systemd環境ではdangling symlinkになるためsymlinkを消してからコピー
rm -f "${MNT}/etc/resolv.conf"
cp /etc/resolv.conf "${MNT}/etc/resolv.conf" 2>/dev/null || true

# ─────────────────────────────────────────────
# 7. grub-install
#    優先: Kali側にあればchroot、なければホスト側
# ─────────────────────────────────────────────
log_step "grub-install"

KALI_GRUB_INSTALL=""
for _p in usr/bin/grub-install usr/sbin/grub-install; do
    [[ -f "${MNT}/${_p}" ]] && { KALI_GRUB_INSTALL="/${_p}"; break; }
done

if [[ -n "$KALI_GRUB_INSTALL" ]]; then
    log_info "Kali側のgrub-installをchrootで実行: $KALI_GRUB_INSTALL"

    if [[ "$BOOT_MODE" == "uefi" ]]; then
        chroot "$MNT" /usr/bin/env -i \
            HOME=/root PATH=/usr/bin:/usr/sbin:/bin:/sbin \
            /bin/bash -c "
set -e
${KALI_GRUB_INSTALL} \
    --target=x86_64-efi \
    --efi-directory=/boot/efi \
    --boot-directory=/boot \
    --bootloader-id=kali \
    --removable \
    --no-nvram \
    --recheck
echo '[CHROOT] grub-install (UEFI) 完了'
"
    else
        chroot "$MNT" /usr/bin/env -i \
            HOME=/root PATH=/usr/bin:/usr/sbin:/bin:/sbin \
            /bin/bash -c "
set -e
${KALI_GRUB_INSTALL} \
    --target=i386-pc \
    --boot-directory=/boot \
    --recheck \
    '${DISK}'
echo '[CHROOT] grub-install (BIOS) 完了'
"
    fi

else
    log_warn "Kali側にgrub-installなし → ホスト側で実行"

    if [[ "$BOOT_MODE" == "uefi" ]]; then
        [[ -d /usr/lib/grub/x86_64-efi ]] || \
            log_error "ホストにgrub-efiモジュールがありません: sudo apt install grub-efi-amd64-bin grub-common"
        grub-install \
            --target=x86_64-efi \
            --efi-directory="${MNT}/boot/efi" \
            --boot-directory="${MNT}/boot" \
            --bootloader-id=kali \
            --removable \
            --no-nvram \
            --recheck \
            "$DISK"
    else
        grub-install \
            --target=i386-pc \
            --boot-directory="${MNT}/boot" \
            --recheck \
            "$DISK"
    fi
fi

log_info "grub-install 完了"

# ─────────────────────────────────────────────
# 8. grub.cfg 生成
#    chrootでupdate-grubを試みる → 失敗したらフォールバック
#
#    【root指定方式の使い分け】
#    initramfsあり（Kali）→ UUID方式  root=UUID=xxxx  ← ここで使う方式
#    initramfsなし（Yocto等）→ デバイス名固定  root=/dev/sda2
#    KaliはinitramfsがあるのでUUID方式を使う。
#    UUID方式ならターゲットPCでUSBが何番目のディスクになっても正しく起動する。
# ─────────────────────────────────────────────
log_step "grub.cfg 生成"

log_info "chrootでupdate-grubを試みます..."
CHROOT_OK=0
chroot "$MNT" /usr/bin/env -i \
    HOME=/root PATH=/usr/bin:/usr/sbin:/bin:/sbin \
    /bin/bash -c '
if command -v update-grub &>/dev/null; then
    update-grub
elif command -v grub-mkconfig &>/dev/null; then
    grub-mkconfig -o /boot/grub/grub.cfg
else
    echo "[CHROOT] update-grub/grub-mkconfig が見つかりません"
    exit 1
fi
' && CHROOT_OK=1 || true

GRUB_CFG="${MNT}/boot/grub/grub.cfg"

if [[ "$CHROOT_OK" -eq 1 ]] && \
   [[ -f "$GRUB_CFG" ]] && [[ -s "$GRUB_CFG" ]] && \
   grep -q "^menuentry" "$GRUB_CFG" 2>/dev/null; then

    log_info "update-grub 成功"
    log_info "menuentry数: $(grep -c '^menuentry' "$GRUB_CFG")"
    log_info "linux行: $(grep 'linux ' "$GRUB_CFG" | head -1)"

else
    # ─────────────────────────────────────────────
    # フォールバック: UUID方式でgrub.cfgを直接生成
    # KaliはinitramfsありなのでUUID方式で問題なし
    # ─────────────────────────────────────────────
    log_warn "update-grub 失敗または grub.cfg が空 → フォールバック生成（UUID方式）"

    KERNEL=$(ls "${MNT}/boot/vmlinuz-"* 2>/dev/null | sort -V | tail -1 | xargs -r basename || true)
    [[ -n "$KERNEL" ]] || log_error "/boot/vmlinuz-* が見つかりません"
    log_info "カーネル: $KERNEL"

    INITRD_FILE=$(ls "${MNT}/boot/initrd.img-"* "${MNT}/boot/initramfs-"* 2>/dev/null \
        | sort -V | tail -1 | xargs -r basename || true)
    if [[ -n "$INITRD_FILE" ]]; then
        INITRD_LINE="    initrd /boot/${INITRD_FILE}"
        log_info "initrd: $INITRD_FILE"
    else
        # initrdなし = このスクリプトの想定外（Kaliには必ずあるはず）
        INITRD_LINE=""
        log_warn "initrdが見つかりません（Kaliには通常あるはずです）"
    fi

    ROOT_UUID=$(blkid -s UUID -o value "$ROOT_PART")
    log_info "ROOT UUID: $ROOT_UUID"

    mkdir -p "${MNT}/boot/grub"
    cat > "$GRUB_CFG" << CFGEOF
# /boot/grub/grub.cfg - generated by kali-grub-install.sh (fallback)
# root=UUID方式: initramfsがKernelを展開したあとUUIDでrootfsをマウントする
set default=0
set timeout=10

insmod part_gpt
insmod part_msdos
insmod ext2
insmod fat

menuentry "Kali Linux" {
    set gfxpayload=text
    linux /boot/${KERNEL} root=UUID=${ROOT_UUID} ro quiet splash net.ifnames=0 biosdevname=0
${INITRD_LINE}
}

menuentry "Kali Linux (verbose)" {
    set gfxpayload=text
    linux /boot/${KERNEL} root=UUID=${ROOT_UUID} ro loglevel=7 ignore_loglevel net.ifnames=0 biosdevname=0
${INITRD_LINE}
}

menuentry "Kali Linux (recovery)" {
    set gfxpayload=text
    linux /boot/${KERNEL} root=UUID=${ROOT_UUID} ro single net.ifnames=0 biosdevname=0
${INITRD_LINE}
}
CFGEOF

    log_info "フォールバック grub.cfg 生成完了"
    log_info "linux行: $(grep 'linux /boot' "$GRUB_CFG" | head -1)"
fi

# ─────────────────────────────────────────────
# grub.cfg を EFIパーティションの全箇所にコピー（3箇所）
# GRUBがどのパスを参照しても確実に読み込めるようにする
# ─────────────────────────────────────────────
if [[ "$BOOT_MODE" == "uefi" ]]; then
    log_info "grub.cfg を EFIパーティションにもコピー（3箇所）..."

    # rootfs側 /boot/EFI/BOOT/（GRUBが最初に探すパス）
    mkdir -p "${MNT}/boot/EFI/BOOT"
    cp "$GRUB_CFG" "${MNT}/boot/EFI/BOOT/grub.cfg"

    # EFIパーティション /EFI/kali/（--bootloader-id=kali の場所）
    mkdir -p "${MNT}/boot/efi/EFI/kali"
    cp "$GRUB_CFG" "${MNT}/boot/efi/EFI/kali/grub.cfg"

    # EFIパーティション /EFI/BOOT/（--removable のfallback path）
    mkdir -p "${MNT}/boot/efi/EFI/BOOT"
    cp "$GRUB_CFG" "${MNT}/boot/efi/EFI/BOOT/grub.cfg"

    log_info "grub.cfg コピー完了 (3箇所)"
fi

# ─────────────────────────────────────────────
# 9. 明示的アンマウント
# ─────────────────────────────────────────────
trap - EXIT
log_step "アンマウント"

sync
umount -R "${MNT}/dev"  || true
umount -R "${MNT}/sys"  || true
umount    "${MNT}/proc" || true
umount    "${MNT}/run"  || true
[[ "$BOOT_MODE" == "uefi" ]] && umount "${MNT}/boot/efi" || true
umount "${MNT}"
sync

echo ""
echo "============================================"
log_info "完了！"
echo ""
echo "  起動モード : $BOOT_MODE"
echo "  ROOT       : $ROOT_PART"
[[ "$BOOT_MODE" == "uefi" ]] && echo "  EFI        : $EFI_PART"
echo "  ディスク   : $DISK"
echo "  ログ       : $LOGFILE"
echo ""
echo "次のステップ:"
echo "  1. USBを抜いてターゲットPCに差す"
echo "  2. UEFI設定で Secure Boot を無効化"
echo "  3. Boot Order で 'kali' または 'BOOT' を最優先に"
echo "============================================"
