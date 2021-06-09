sudo apt update
sudo apt install python3-pip -y

sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt install -y python3.9
sudo apt install -y python3.9-dev libpq-dev python3.9-venv

platform=`dpkg --print-architecture`
if [ "$platform" == 'arm64' ]; then
    sudo apt install -y gcc-arm-linux-gnueabihf
fi

# Docker
sudo apt-get install -y curl apt-transport-https ca-certificates software-properties-common

curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

if [ "$platform" == 'arm64' ]; then
    echo "deb [arch=arm64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
elif [ "$platform" == 'amd64' ] || [ "$platform" == 'x86_64' ]; then
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
fi

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose
