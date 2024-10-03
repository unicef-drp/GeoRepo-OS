FROM python:3.10.4-buster AS prod

# Enable postgresql-client-14
RUN echo "deb http://apt.postgresql.org/pub/repos/apt/ bookworm-pgdg main" | tee /etc/apt/sources.list.d/pgdg.list
RUN echo "deb http://deb.debian.org/debian/ stable main contrib non-free" | tee /etc/apt/sources.list.d/debian.list
RUN wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add -

RUN apt-get update -y && apt-get upgrade -y

# WORKAROUND fix for missing libcrypt.so.1
# https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=993755#27
RUN apt-get install -y --no-install-recommends libcrypt1; exit 0

RUN mkdir /home/tmp_workaround
WORKDIR /home/tmp_workaround
RUN apt -y download libcrypt1
RUN dpkg-deb -x libcrypt1_*.deb .
RUN cp -av lib/x86_64-linux-gnu/* /lib/x86_64-linux-gnu/
RUN apt -y --fix-broken install
RUN apt-get update -y --allow-releaseinfo-change --fix-missing

WORKDIR /home/web/

RUN apt-get install -y --no-install-recommends \
    gcc gettext geoip-bin cron \
    postgresql-client-14 \
    spatialite-bin libsqlite3-mod-spatialite \
    python3-dev python3-gdal python3-psycopg2 python3-ldap \
    python3-pip python3-pil python3-lxml python3-pylibmc \
    uwsgi uwsgi-plugin-python3 libz-dev libjpeg-dev libfreetype6-dev python-dev \
    libssl-dev libffi-dev

# Install pip packages
ADD deployment/docker/requirements.txt /requirements.txt
RUN pip3 install --upgrade pip && pip install --upgrade pip
# Fix uwsgi build failure missing cc1
ARG CPUCOUNT=1
RUN pip3 install -r /requirements.txt

# Install nodejs and npm using nvm
RUN mkdir /usr/local/nvm
ENV NVM_DIR /usr/local/nvm
ENV NODE_VERSION 16.20.2

RUN curl https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash \
    && . $NVM_DIR/nvm.sh \
    && nvm install $NODE_VERSION \
    && nvm alias default $NODE_VERSION \
    && nvm use default

ENV NODE_PATH $NVM_DIR/v$NODE_VERSION/lib/node_modules
ENV PATH $NVM_DIR/versions/node/v$NODE_VERSION/bin:$PATH

# Tegola
RUN wget https://github.com/go-spatial/tegola/releases/download/v0.15.2/tegola_linux_amd64.zip -P /home/web/
RUN unzip /home/web/tegola_linux_amd64.zip -d /opt/

# GDAL
RUN apt-get install -y --no-install-recommends gdal-bin

# topojson-server
RUN npm install -g topojson-server

# mapshaper
RUN npm install -g mapshaper

ADD django_project /home/web/django_project

EXPOSE 8080

ADD deployment/docker/uwsgi.conf /uwsgi.conf
ADD deployment/docker/uwsgi_auth.conf /uwsgi_auth.conf

# Build front end
WORKDIR /home/web/django_project/dashboard
RUN npm install --legacy-peer-deps && npm run build-react
RUN rm -rf /home/web/django_project/dashboard/node_modules

WORKDIR /home/web/django_project
ENTRYPOINT ["sh", "/home/web/django_project/entrypoint.sh"]
CMD ["uwsgi", "--ini", "/uwsgi.conf"]

FROM prod as dev

# This section taken on 2 July 2015 from
# https://docs.docker.com/examples/running_ssh_service/
# Sudo is needed by pycharm when it tries to pip install packages
RUN apt-get update && apt-get install -y openssh-server sudo
RUN mkdir /var/run/sshd
RUN echo 'root:docker' | chpasswd
RUN sed -i 's/^PermitRootLogin */#PermitRootLogin /' /etc/ssh/sshd_config
RUN echo "PermitRootLogin yes" >> /etc/ssh/sshd_config

# SSH login fix. Otherwise user is kicked off after login
RUN sed 's@session\s*required\s*pam_loginuid.so@session optional pam_loginuid.so@g' -i /etc/pam.d/sshd

ENV NOTVISIBLE "in users profile"
RUN echo "export VISIBLE=now" >> /etc/profile

# End of cut & paste section
ADD deployment/docker/requirements-dev.txt /requirements-dev.txt
RUN pip install -r /requirements-dev.txt

# --------------------------------------------------------
# Open ports as needed
# --------------------------------------------------------

# Open port 8080 as we will be running our django dev server on
EXPOSE 8080
# Open port 22 as we will be using a remote interpreter from pycharm
EXPOSE 22

CMD ["/usr/sbin/sshd", "-D"]
