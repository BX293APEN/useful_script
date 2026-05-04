#!/usr/bin/env bash
# =============================================================================
# kali-grub-install.sh
#   別のLinuxホスト（Ubuntu等）からKaliのGRUBを修復するスクリプト
#
# 使い方:
#   sudo bash kali-grub-install.sh
#
# 【重要な設計方針】
#   grub-install は chroot 内（Kali側）では実行しない。
#   Kali側のgrub-installが壊れているからこそ修復が必要なため、
#   ホスト（Ubuntu）側にインストール済みの grub-install を使って
#   直接USBディスクに書き込む。
#
#   grub.cfg の生成だけは chroot内でupdate-grubを試みるが、
#   失敗した場合はホスト側でフォールバックを生成する。
#
# 対応起動モード: UEFI (x86_64-efi) / BIOS/Legacy (i386-pc) ← 自動判定
# =============================================================================

set -euo pipefail

MNT="/mnt/kali-repair"
LOGFILE="/tmp/kali-grub-install.log"

# ─────────────────────────────────────────────
# 色付きログ
# ─────────────────────────────────────────────
log_info()  { echo -e "\e[32m[INFO]\e[0m  $*"; }
log_warn()  { echo -e "\e[33m[WARN]\e[0m  $*"; }
log_error() { echo -e "\e[31m[ERROR]\e[0m $*"; }
log_step()  { echo -e "\n\e[36m========== $* ==========\e[0m"; }

exec > >(tee -a "$LOGFILE") 2>&1
echo "============================================"
log_info "$(date '+%Y-%m-%d %H:%M:%S') kali-grub-install.sh 開始"
log_info "ログ: $LOGFILE"
echo "============================================"

# ─────────────────────────────────────────────
# 0. root確認 & コマンド確認
# ─────────────────────────────────────────────
log_step "事前確認"

if [[ "$EUID" -ne 0 ]]; then
    log_error "root権限が必要です: sudo bash kali-grub-install.sh"
    exit 1
fi

for cmd in mount umount blkid lsblk partprobe findmnt grub-install; do
    if ! command -v "$cmd" &>/dev/null; then
        log_error "コマンドが見つかりません: $cmd"
        if [[ "$cmd" == "grub-install" ]]; then
            log_error "  → sudo apt install grub-efi grub-pc でインストールしてください"
        fi
        exit 1
    fi
done

log_info "ホスト grub-install: $(command -v grub-install)"
log_info "ホスト grub バージョン: $(grub-install --version 2>&1 | head -1)"

# ─────────────────────────────────────────────
# 1. デバイス選択
# ─────────────────────────────────────────────
log_step "デバイス選択"

echo ""
echo "接続中のディスク一覧:"
echo "─────────────────────────────────────────────────────────"
# morning.sh 方式: ツリー表示で同容量USBが複数あっても判別しやすい
lsblk -po NAME,SIZE,LABEL,MOUNTPOINT | head -n1
lsblk -po NAME,SIZE,LABEL,MOUNTPOINT \
    | grep -E '^(/dev/sd|/dev/nvme|/dev/mmcblk)|^├─|^└─'
echo "─────────────────────────────────────────────────────────"
echo ""
log_warn "ホストPCのディスクを絶対に選ばないでください！"

# ホストのルートディスクを特定して警告に使う
HOST_ROOT_DISK=$(lsblk -no PKNAME "$(findmnt -no SOURCE /)" 2>/dev/null \
    | head -1 || true)
if [[ -n "$HOST_ROOT_DISK" ]]; then
    log_warn "ホストのルートディスクは /dev/${HOST_ROOT_DISK} です（選ばないこと）"
fi
echo ""

while true; do
    echo -n "KaliのUSBディスク (例: sdb または /dev/sdb): "
    read -r INPUT
    DISK="/dev/${INPUT#/dev/}"

    if [[ ! -b "$DISK" ]]; then
        log_error "${DISK} はブロックデバイスではありません。再入力してください。"
        continue
    fi

    # ホストのルートディスクは拒否
    if [[ -n "$HOST_ROOT_DISK" ]] && \
       [[ "$DISK" == "/dev/${HOST_ROOT_DISK}" || "$DISK" == "$HOST_ROOT_DISK" ]]; then
        log_error "それはホストPCのルートディスクです！絶対に選べません。"
        continue
    fi

    log_info "選択: $DISK"
    echo ""
    echo "選択したディスクのパーティション:"
    echo "─────────────────────────────────────────────────────────"
    lsblk -po NAME,SIZE,FSTYPE,LABEL,MOUNTPOINT "$DISK" || true
    echo "─────────────────────────────────────────────────────────"
    echo ""
    break
done

# ─────────────────────────────────────────────
# 2. パーティションの自動判定
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

    # EFI判定: vfat かつ EFI System パーティションタイプ
    if [[ "$FSTYPE" == "vfat" ]] && [[ "$PARTTYPE" == *"c12a7328"* ]]; then
        EFI_PART="$partdev"
        log_info "EFIパーティション検出: $EFI_PART (vfat, EFI System)"
        continue
    fi

    # rootパーティション判定: ext4 / xfs / btrfs のうち最大のもの
    if [[ "$FSTYPE" =~ ^(ext4|xfs|btrfs)$ ]]; then
        if (( SIZE_BYTES > ROOT_SIZE )); then
            ROOT_PART="$partdev"
            ROOT_SIZE="$SIZE_BYTES"
        fi
    fi
done < <(lsblk -lno NAME "$DISK" | tail -n +2 | sed "s|^|/dev/|")

if [[ -z "$ROOT_PART" ]]; then
    log_error "rootパーティション（ext4/xfs/btrfs）が見つかりませんでした。"
    log_error "lsblkで手動確認してください:"
    lsblk -po NAME,SIZE,FSTYPE,LABEL "$DISK"
    exit 1
fi

log_info "rootパーティション : $ROOT_PART"
if [[ -n "$EFI_PART" ]]; then
    log_info "EFIパーティション  : $EFI_PART"
else
    log_warn "EFIパーティションは見つかりませんでした → BIOSモードとして処理します"
fi

# ─────────────────────────────────────────────
# 3. UEFI/BIOSモード判定
# ─────────────────────────────────────────────
log_step "起動モード判定"

if [[ -n "$EFI_PART" ]] && [[ -d /sys/firmware/efi ]]; then
    BOOT_MODE="uefi"
    log_info "ホストがUEFIブート中 + EFIパーティション検出 → UEFIモードで修復"
elif [[ -n "$EFI_PART" ]]; then
    echo ""
    log_warn "EFIパーティションが検出されましたが、ホストはBIOSモードで起動しています。"
    echo "ターゲットPCはどちらのモードで起動しますか？"
    echo "  1) UEFI"
    echo "  2) BIOS/Legacy"
    read -rp "選択 (1 or 2): " MODE_SEL
    [[ "$MODE_SEL" == "1" ]] && BOOT_MODE="uefi" || BOOT_MODE="bios"
else
    BOOT_MODE="bios"
fi

log_info "起動モード: $BOOT_MODE"

# ─────────────────────────────────────────────
# UEFIモードのホスト grub-efi パッケージ確認
# ─────────────────────────────────────────────
if [[ "$BOOT_MODE" == "uefi" ]]; then
    # x86_64-efi モジュールが使えるか確認
    GRUB_LIB_EFI=""
    for d in /usr/lib/grub/x86_64-efi /usr/lib/grub-efi-amd64/x86_64-efi; do
        [[ -d "$d" ]] && { GRUB_LIB_EFI="$d"; break; }
    done
    if [[ -z "$GRUB_LIB_EFI" ]]; then
        log_error "ホストに grub-efi (x86_64-efi) モジュールがありません。"
        log_error "  → sudo apt install grub-efi-amd64 でインストールしてください"
        exit 1
    fi
    log_info "grub-efi モジュール: $GRUB_LIB_EFI"
fi

# ─────────────────────────────────────────────
# 最終確認
# ─────────────────────────────────────────────
echo ""
echo -e "\e[31m======================================================\e[0m"
echo -e "\e[31m  最終確認\e[0m"
echo -e "\e[31m  ディスク           : $DISK\e[0m"
echo -e "\e[31m  rootパーティション : $ROOT_PART\e[0m"
[[ -n "$EFI_PART" ]] && \
echo -e "\e[31m  EFIパーティション  : $EFI_PART\e[0m"
echo -e "\e[31m  起動モード         : $BOOT_MODE\e[0m"
echo -e "\e[31m  grub-install       : ホスト側を使用（chroot内は使わない）\e[0m"
echo -e "\e[31m======================================================\e[0m"
echo ""
read -rp "本当に続けますか？ (yes と入力して Enter): " CONFIRM
[[ "$CONFIRM" == "yes" ]] || { echo "中止しました。"; exit 0; }

# ─────────────────────────────────────────────
# cleanup トラップ
# ─────────────────────────────────────────────
cleanup() {
    log_info "クリーンアップ中..."
    umount -R "${MNT}/dev"               2>/dev/null || true
    umount -R "${MNT}/sys"               2>/dev/null || true
    umount    "${MNT}/proc"              2>/dev/null || true
    umount    "${MNT}/run"               2>/dev/null || true
    umount    "${MNT}/boot/efi"          2>/dev/null || true
    umount    "${MNT}"                   2>/dev/null || true
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

if mountpoint -q "$MNT" 2>/dev/null; then
    umount -R "$MNT" && log_info "残留マウント解除: $MNT"
fi

# ─────────────────────────────────────────────
# 5. マウント
# ─────────────────────────────────────────────
log_step "マウント"

mkdir -p "$MNT"
mount "$ROOT_PART" "$MNT"
log_info "マウント: $ROOT_PART → $MNT"

if [[ "$BOOT_MODE" == "uefi" ]]; then
    mkdir -p "${MNT}/boot/efi"
    mount "$EFI_PART" "${MNT}/boot/efi"
    log_info "マウント: $EFI_PART → ${MNT}/boot/efi"
fi

# ─────────────────────────────────────────────
# 6. bind マウント（chroot環境 ※grub.cfg生成用）
# ─────────────────────────────────────────────
log_step "bind マウント（chroot環境）"

mount --types proc /proc "${MNT}/proc"
mount --rbind      /sys  "${MNT}/sys"
mount --make-rslave      "${MNT}/sys"
mount --rbind      /dev  "${MNT}/dev"
mount --make-rslave      "${MNT}/dev"

# /run は存在する場合のみbind（なければ mkdir して bind）
mkdir -p "${MNT}/run"
mount --bind /run "${MNT}/run"

cp /etc/resolv.conf "${MNT}/etc/resolv.conf" 2>/dev/null || true

# ─────────────────────────────────────────────
# 7. grub-install をホスト側で実行
#    ※ chroot 内の Kali 側 grub-install は使わない
#    　 壊れているから修復が必要なのでchrootで実行しても意味がない
# ─────────────────────────────────────────────
log_step "GRUB インストール（ホスト側 grub-install を使用）"
log_info "重要: Kali側ではなくホスト（Ubuntu）のgrub-installで直接書き込みます"

if [[ "$BOOT_MODE" == "uefi" ]]; then
    log_info "UEFI用 grub-install 実行中..."
    grub-install \
        --target=x86_64-efi \
        --efi-directory="${MNT}/boot/efi" \
        --boot-directory="${MNT}/boot" \
        --bootloader-id=kali \
        --removable \
        --recheck \
        "$DISK"
    log_info "grub-install (UEFI) 完了"

    # EFIエントリ確認（ホスト側でも確認できる）
    if command -v efibootmgr &>/dev/null && [[ -d /sys/firmware/efi ]]; then
        log_info "EFIエントリ:"
        efibootmgr -v 2>/dev/null | grep -i "kali\|Boot" | head -10 || true
    fi

else
    log_info "BIOS用 grub-install 実行中..."
    grub-install \
        --target=i386-pc \
        --boot-directory="${MNT}/boot" \
        --recheck \
        "$DISK"
    log_info "grub-install (BIOS) 完了"
fi

# ─────────────────────────────────────────────
# 8. grub.cfg 生成
#    まず chroot内でupdate-grubを試み、
#    失敗または空の場合はホスト側でフォールバックを生成する
# ─────────────────────────────────────────────
log_step "grub.cfg 生成"

# Kali chrootでupdate-grubを試みる
log_info "chroot内でupdate-grubを試みます（失敗してもフォールバックあり）..."
CHROOT_OK=0

chroot "$MNT" /bin/bash << 'CHROOT_EOF' && CHROOT_OK=1 || true
# update-grub / grub-mkconfig で grub.cfg を生成する
# （grub-install はすでにホスト側で完了済み）
if command -v update-grub &>/dev/null; then
    update-grub
elif command -v grub-mkconfig &>/dev/null; then
    grub-mkconfig -o /boot/grub/grub.cfg
else
    echo "[CHROOT] update-grub も grub-mkconfig も見つかりません"
    exit 1
fi
CHROOT_EOF

GRUB_CFG="${MNT}/boot/grub/grub.cfg"

if [[ "$CHROOT_OK" -eq 1 ]] && \
   [[ -f "$GRUB_CFG" ]] && [[ -s "$GRUB_CFG" ]] && \
   grep -q "^menuentry" "$GRUB_CFG" 2>/dev/null; then
    log_info "grub.cfg が正常に生成されました"
    log_info "menuentry 数: $(grep -c '^menuentry' "$GRUB_CFG")"
    log_info "linux 行確認:"
    grep "linux " "$GRUB_CFG" | head -1
else
    # ─────────────────────────────────────────────
    # フォールバック: ホスト側で grub.cfg を直接生成
    # ─────────────────────────────────────────────
    log_warn "update-grub が失敗またはgrub.cfgが空 → ホスト側でフォールバック生成"

    KERNEL=$(ls "${MNT}/boot/vmlinuz-"* 2>/dev/null \
        | sort -V | tail -1 | xargs -r basename || true)
    if [[ -z "$KERNEL" ]]; then
        log_error "/boot/vmlinuz-* が見つかりません。grub.cfgを生成できません。"
        log_error "Kali側にカーネルがインストールされているか確認してください。"
        exit 1
    fi
    log_info "カーネル検出: $KERNEL"

    INITRD_FILE=$(ls "${MNT}/boot/initrd.img-"* "${MNT}/boot/initramfs-"* 2>/dev/null \
        | sort -V | tail -1 | xargs -r basename || true)
    if [[ -n "$INITRD_FILE" ]]; then
        INITRD_LINE="    initrd /boot/${INITRD_FILE}"
        log_info "initrd 検出: $INITRD_FILE"
    else
        INITRD_LINE=""
        log_warn "initrd が見つかりません"
    fi

    ROOT_UUID=$(blkid -s UUID -o value "$ROOT_PART")
    log_info "ROOT UUID: $ROOT_UUID"

    mkdir -p "${MNT}/boot/grub"

    cat > "$GRUB_CFG" << CFGEOF
# /boot/grub/grub.cfg - generated by kali-grub-install.sh (fallback)
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

menuentry "Kali Linux (recovery mode)" {
    set gfxpayload=text
    linux /boot/${KERNEL} root=UUID=${ROOT_UUID} ro single net.ifnames=0 biosdevname=0
${INITRD_LINE}
}
CFGEOF

    log_info "フォールバック grub.cfg 生成完了"
    log_info "linux 行確認:"
    grep "linux " "$GRUB_CFG" | head -1

    # UEFIの場合はEFIパーティションにもコピー
    if [[ "$BOOT_MODE" == "uefi" ]]; then
        mkdir -p "${MNT}/boot/efi/EFI/kali"
        cp "$GRUB_CFG" "${MNT}/boot/efi/EFI/kali/grub.cfg"
        mkdir -p "${MNT}/boot/efi/EFI/BOOT"
        cp "$GRUB_CFG" "${MNT}/boot/efi/EFI/BOOT/grub.cfg" 2>/dev/null || true
        log_info "grub.cfg → EFIパーティションにもコピーしました"
    fi
fi

# ─────────────────────────────────────────────
# 9. 明示的アンマウント
# ─────────────────────────────────────────────
trap - EXIT
log_step "アンマウント"

umount -R "${MNT}/dev"  || true
umount -R "${MNT}/sys"  || true
umount    "${MNT}/proc" || true
umount    "${MNT}/run"  || true
if [[ "$BOOT_MODE" == "uefi" ]]; then
    umount "${MNT}/boot/efi" || true
fi
umount "${MNT}"
sync

# ─────────────────────────────────────────────
# 完了
# ─────────────────────────────────────────────
echo ""
echo "============================================"
log_info "$(date '+%Y-%m-%d %H:%M:%S') 完了！"
echo ""
echo "  起動モード : $BOOT_MODE"
echo "  ROOT       : $ROOT_PART"
[[ "$BOOT_MODE" == "uefi" ]] && echo "  EFI        : $EFI_PART"
echo "  ディスク   : $DISK"
echo "  ログ       : $LOGFILE"
echo ""
echo "次のステップ:"
echo "  1. USBをUbuntuから抜いてターゲットPCに差す"
if [[ "$BOOT_MODE" == "bios" ]]; then
    echo "  2. BIOS設定でSecure Bootを無効化"
    echo "  3. Boot Orderで対象ディスクを最優先に設定"
elif [[ "$BOOT_MODE" == "uefi" ]]; then
    echo "  2. UEFI設定でSecure Bootを無効化"
    echo "  3. Boot Orderで 'kali' または 'BOOT' エントリを最優先に設定"
fi
echo "============================================"
