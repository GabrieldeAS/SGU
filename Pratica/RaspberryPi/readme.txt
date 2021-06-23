Foi utilizado um Raspberry Pi 4, com kernel armv7l
# Libere a camera
Preferences -> Raspberry Pi Configuration -> Interfaces -> Camera Enabled e I2C Enabled

# Dê permissão ao arquivo install.sh
chmod +777 install.sh

# Execute o arquivo para instalar as dependências
sh install.sh

# Rode o código 
python3 raspberryCameraAndMxl.py
