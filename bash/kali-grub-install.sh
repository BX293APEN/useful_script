#!/usr/bin/env bash
# =============================================================================
# kali-grub-install.sh
#   別のLinuxホストからchroot経由でKaliのGRUBを修復するスクリプト
#
# 使い方:
#   sudo bash kali-grub-install.sh
#
# 聞かれるのはデバイス名のみ（例: sdb）
#   → パーティション番号は自動判定します
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
echo "============================================"

# ─────────────────────────────────────────────
# 0. root確認 & コマンド確認
# ─────────────────────────────────────────────
log_step "事前確認"

if [[ "$EUID" -ne 0 ]]; then
    log_error "root権限が必要です: sudo bash kali-grub-install.sh"
    exit 1
fi

for cmd in mount umount chroot blkid lsblk partprobe findmnt; do
    command -v "$cmd" &>/dev/null || { log_error "コマンドが見つかりません: $cmd"; exit 1; }
done

# ─────────────────────────────────────────────
# 1. デバイス選択（ディスク名のみ聞く）
# ─────────────────────────────────────────────
log_step "デバイス選択"

echo ""
echo "接続中のディスク一覧:"
echo "─────────────────────────────────────────────────────────"
lsblk -po NAME,SIZE,TYPE,FSTYPE,LABEL,MOUNTPOINT \
    | grep -E "^NAME|^/dev/sd|^/dev/nvme|^/dev/mmcblk"
echo "─────────────────────────────────────────────────────────"
echo ""
log_warn "ホストPCのディスクを絶対に選ばないでください！"
echo ""

HOST_ROOT_DISK=$(lsblk -no PKNAME "$(findmnt -no SOURCE /)" 2>/dev/null || true)

while true; do
    echo -n "Kaliが入っているディスク (例: sdb または /dev/sdb): "
    read -r INPUT
    DISK="/dev/${INPUT#/dev/}"

    if [[ ! -b "$DISK" ]]; then
        log_error "${DISK} はブロックデバイスではありません。再入力してください。"
        continue
    fi

    # ホストのルートディスクは拒否
    if [[ "/dev/${HOST_ROOT_DISK}" == "$DISK" ]] || [[ "$HOST_ROOT_DISK" == "$DISK" ]]; then
        log_error "それはホストPCのルートディスクです！絶対に選べません。"
        continue
    fi

    log_info "選択: $DISK"
    echo ""
    echo "選択したディスクのパーティション:"
    lsblk -po NAME,SIZE,TYPE,FSTYPE,LABEL,MOUNTPOINT "$DISK" || true
    echo ""
    break
done

# ─────────────────────────────────────────────
# 2. パーティションの自動判定
# ─────────────────────────────────────────────
log_step "パーティション自動判定"

# パーティション名のプレフィックス（nvme0n1 → nvme0n1p1、sdb → sdb1）
if [[ "$DISK" =~ [0-9]$ ]]; then
    PART_PREFIX="${DISK}p"
else
    PART_PREFIX="${DISK}"
fi

# EFIパーティション: vfatかつESP (partition type EF00) を探す
EFI_PART=""
ROOT_PART=""

# lsblkでパーティション一覧を取得して自動判定
while IFS= read -r partdev; do
    [[ -b "$partdev" ]] || continue
    FSTYPE=$(lsblk -no FSTYPE "$partdev" 2>/dev/null || true)
    PARTTYPE=$(lsblk -no PARTTYPE "$partdev" 2>/dev/null | tr '[:upper:]' '[:lower:]' || true)
    SIZE_BYTES=$(lsblk -bno SIZE "$partdev" 2>/dev/null || echo 0)

    # EFI判定: vfat かつ パーティションタイプがEFI System (c12a7328-...)
    if [[ "$FSTYPE" == "vfat" ]] && [[ "$PARTTYPE" == *"c12a7328"* ]]; then
        EFI_PART="$partdev"
        log_info "EFIパーティション検出: $EFI_PART (vfat, EFI System)"
        continue
    fi

    # rootパーティション判定: ext4 / xfs / btrfs のうち最大のもの
    if [[ "$FSTYPE" =~ ^(ext4|xfs|btrfs)$ ]]; then
        if [[ -z "$ROOT_PART" ]]; then
            ROOT_PART="$partdev"
            ROOT_SIZE="$SIZE_BYTES"
        else
            # より大きなパーティションをrootとみなす
            PREV_SIZE=$(lsblk -bno SIZE "$ROOT_PART" 2>/dev/null || echo 0)
            if (( SIZE_BYTES > PREV_SIZE )); then
                ROOT_PART="$partdev"
            fi
        fi
    fi
done < <(lsblk -lno NAME "$DISK" | tail -n +2 | sed "s|^|/dev/|")

# ─────────────────────────────────────────────
# 2-A. 判定結果の確認・補完
# ─────────────────────────────────────────────
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

# EFIパーティションが見つかっている かつ ホストがUEFIで起動している場合はUEFI
if [[ -n "$EFI_PART" ]] && [[ -d /sys/firmware/efi ]]; then
    BOOT_MODE="uefi"
elif [[ -n "$EFI_PART" ]]; then
    # EFIパーティションはあるがホストがBIOSブート → ユーザーに確認
    echo ""
    echo "EFIパーティションが検出されましたが、ホストはBIOSモードで起動しています。"
    echo "ターゲットPCはどちらのモードで使いますか？"
    echo "  1) UEFI"
    echo "  2) BIOS/Legacy"
    read -rp "選択 (1 or 2): " MODE_SEL
    if [[ "$MODE_SEL" == "1" ]]; then
        BOOT_MODE="uefi"
    else
        BOOT_MODE="bios"
    fi
else
    BOOT_MODE="bios"
fi

log_info "起動モード: $BOOT_MODE"

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
echo -e "\e[31m  MBR/EFIに書き込むディスク: $DISK\e[0m"
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

for part in "$ROOT_PART" "$EFI_PART"; do
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
# 6. bind マウント（chroot環境）
# ─────────────────────────────────────────────
log_step "bind マウント（chroot環境）"

mount --types proc /proc    "${MNT}/proc"
mount --rbind      /sys     "${MNT}/sys"
mount --make-rslave         "${MNT}/sys"
mount --rbind      /dev     "${MNT}/dev"
mount --make-rslave         "${MNT}/dev"
mount --bind       /run     "${MNT}/run"

# UEFI時: efivarsもbindマウント（grub-installが書き込みに使う）
if [[ "$BOOT_MODE" == "uefi" ]] && [[ -d /sys/firmware/efi/efivars ]]; then
    mount --bind /sys/firmware/efi/efivars "${MNT}/sys/firmware/efi/efivars"
    log_info "efivars をbindマウントしました"
fi

cp /etc/resolv.conf "${MNT}/etc/resolv.conf" 2>/dev/null || true

# ─────────────────────────────────────────────
# 7. chroot内でGRUBインストール＋grub.cfg生成
# ─────────────────────────────────────────────
log_step "GRUB インストール (chroot)"
log_info "モード: $BOOT_MODE | ディスク: $DISK"

# update-grub 後に grub.cfg が生成されているか確認する関数
# 失敗・空・存在しない場合はホスト側でフォールバックを生成する
generate_fallback_grub_cfg() {
    log_warn "update-grub が grub.cfg を生成できなかったためフォールバックを生成します"

    # ホスト側からカーネル・initrd を取得
    KERNEL=$(ls "${MNT}/boot/vmlinuz-"* 2>/dev/null \
        | sort -V | tail -1 | xargs basename 2>/dev/null || true)
    if [[ -z "$KERNEL" ]]; then
        log_error "/boot/vmlinuz-* が見つかりません。grub.cfg を生成できません。"
        return 1
    fi
    log_info "カーネル検出: $KERNEL"

    INITRD_LINE=""
    INITRD_FILE=$(ls "${MNT}/boot/initrd.img-"* "${MNT}/boot/initramfs-"* 2>/dev/null \
        | sort -V | tail -1 | xargs basename 2>/dev/null || true)
    if [[ -n "$INITRD_FILE" ]]; then
        INITRD_LINE="    initrd /boot/${INITRD_FILE}"
        log_info "initrd 検出: $INITRD_FILE"
    fi

    ROOT_UUID=$(blkid -s UUID -o value "$ROOT_PART")
    log_info "ROOT UUID: $ROOT_UUID"

    mkdir -p "${MNT}/boot/grub"

    # プレースホルダで書いてから sed で置換（morning.sh と同じ方式）
    cat > "${MNT}/boot/grub/grub.cfg" << 'CFGEOF'
# /boot/grub/grub.cfg - generated by kali-grub-install.sh (fallback)
set default=0
set timeout=10

insmod part_gpt
insmod part_msdos
insmod ext2
insmod fat

menuentry "Kali Linux" {
    set gfxpayload=text
    linux /boot/__KERNEL__ root=UUID=__ROOT_UUID__ ro quiet splash net.ifnames=0 biosdevname=0
__INITRD_LINE__
}

menuentry "Kali Linux (verbose)" {
    set gfxpayload=text
    linux /boot/__KERNEL__ root=UUID=__ROOT_UUID__ ro loglevel=7 ignore_loglevel net.ifnames=0 biosdevname=0
__INITRD_LINE__
}

menuentry "Kali Linux (recovery mode)" {
    set gfxpayload=text
    linux /boot/__KERNEL__ root=UUID=__ROOT_UUID__ ro single net.ifnames=0 biosdevname=0
__INITRD_LINE__
}
CFGEOF

    sed -i \
        -e "s|__KERNEL__|${KERNEL}|g" \
        -e "s|__ROOT_UUID__|${ROOT_UUID}|g" \
        -e "s|__INITRD_LINE__|${INITRD_LINE}|g" \
        "${MNT}/boot/grub/grub.cfg"

    log_info "フォールバック grub.cfg 生成完了"
    log_info "linux 行確認:"
    grep "linux " "${MNT}/boot/grub/grub.cfg" | head -1

    # UEFIの場合はEFIパーティションにもコピー
    if [[ "$BOOT_MODE" == "uefi" ]]; then
        mkdir -p "${MNT}/boot/efi/EFI/kali"
        cp "${MNT}/boot/grub/grub.cfg" "${MNT}/boot/efi/EFI/kali/grub.cfg"
        cp "${MNT}/boot/grub/grub.cfg" "${MNT}/boot/efi/EFI/BOOT/grub.cfg" 2>/dev/null || true
        log_info "grub.cfg → EFIパーティションにもコピーしました"
    fi
}

if [[ "$BOOT_MODE" == "uefi" ]]; then
    chroot "$MNT" /bin/bash << 'CHROOT_EOF'
set -e

echo "[CHROOT] UEFI用 grub-install 実行中..."
grub-install \
    --target=x86_64-efi \
    --efi-directory=/boot/efi \
    --bootloader-id=kali \
    --removable \
    --recheck

echo "[CHROOT] grub.cfg 生成中 (update-grub)..."
update-grub || true   # 失敗してもここでは止めない（ホスト側でフォールバック）

echo "[CHROOT] EFIエントリ確認:"
efibootmgr -v 2>/dev/null || echo "  (efibootmgr 利用不可)"

echo "[CHROOT] 完了"
CHROOT_EOF

else
    chroot "$MNT" /bin/bash -c "
set -e
echo '[CHROOT] BIOS用 grub-install 実行中...'
grub-install \
    --target=i386-pc \
    --recheck \
    '$DISK'

echo '[CHROOT] grub.cfg 生成中 (update-grub)...'
update-grub || true   # 失敗してもここでは止めない（ホスト側でフォールバック）

echo '[CHROOT] 完了'
"
fi

# ─────────────────────────────────────────────
# 7-A. grub.cfg 確認 → 空・なしならフォールバック生成
# ─────────────────────────────────────────────
GRUB_CFG="${MNT}/boot/grub/grub.cfg"
if [[ ! -f "$GRUB_CFG" ]] || [[ ! -s "$GRUB_CFG" ]] || \
   ! grep -q "^menuentry" "$GRUB_CFG" 2>/dev/null; then
    generate_fallback_grub_cfg
else
    log_info "grub.cfg が正常に生成されています"
    log_info "menuentry 数: $(grep -c '^menuentry' "$GRUB_CFG")"
    log_info "linux 行確認:"
    grep "linux " "$GRUB_CFG" | head -1
fi

# ─────────────────────────────────────────────
# 8. 明示的アンマウント
# ─────────────────────────────────────────────
trap - EXIT
log_step "アンマウント"

umount -R "${MNT}/dev"  || true
umount -R "${MNT}/sys"  || true
umount    "${MNT}/proc" || true
umount    "${MNT}/run"  || true
[[ "$BOOT_MODE" == "uefi" ]] && umount "${MNT}/boot/efi" || true
umount    "${MNT}"
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
echo "  1. PCを再起動する"
if [[ "$BOOT_MODE" == "bios" ]]; then
    echo "  2. BIOS設定でSecure Bootを無効化"
    echo "  3. Boot Orderで対象ディスクを最優先に設定"
elif [[ "$BOOT_MODE" == "uefi" ]]; then
    echo "  2. UEFI設定でSecure Bootを無効化"
    echo "  3. Boot Orderで 'kali' を最優先に設定"
fi
echo "============================================"
