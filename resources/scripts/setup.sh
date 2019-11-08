sudo yum -y update

# INSTALL GIT
sudo yum install -y git-core

# INSTALL PYTHON 3
sudo yum install -y python37

sudo yum install -y python3-devel
echo 'alias python=python3' >> ~/.bashrc
source ~/.bashrc

# INSTALL SUPERVISOR
sudo yum install -y libffi-devel
sudo yum install -y openssl-devel
sudo yum groupinstall -y "Development tools"
sudo /usr/bin/python3 -m pip install supervisor

# CLONE ANNOTATION
cd ~
git clone https://github.com/klahnakoski/annotations.git
cd ~/annotations
git checkout dev
sudo /usr/bin/python3 -m pip install -r requirements.txt

mkdir ~/logs

# SUPERVISOR CONFIG
sudo cp ~/TUID/resources/config/supervisord.conf /etc/supervisord.conf

# START DAEMON (OR THROW ERROR IF RUNNING ALREADY)
sudo /usr/bin/supervisord -c /etc/supervisord.conf

# READ CONFIG
sudo /usr/bin/supervisorctl reread
sudo /usr/bin/supervisorctl update

# INSTALL GUNICORN


