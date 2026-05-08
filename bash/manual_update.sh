manual_update(){
    local package="$1"
    local url="$2"
    wget -O "/tmp/${package}-installer.deb" "${url}"
    sudo apt install "/tmp/${package}-installer.deb"
}

discord_update() {
    manual_update discord "https://discord.com/api/download/stable?platform=linux&format=deb"
}

# .bashrc に source [path]/manual_update.sh として読み込ませること