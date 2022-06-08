---
layout: post
title:  "Setting up a Single Node Hadoop Cluster in Docker"
date:   2022-05-25 20:38:54 +0800
categories: jekyll update
---

code DockerFile

```
FROM centos:7

LABEL 	name="centos-for-hadoop" \
		maintainer="Edge51" \
		email="liuyuanyuanedge@163.com"

# 安装相关工具
RUN yum install -y openssh-server sudo openssh-clients vim net-tools curl wget initscripts

# 生成主机密钥文件
RUN ssh-keygen -t rsa -P '' -f ~/.ssh/id_rsa
RUN cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys

RUN ssh-keygen -t rsa -f /etc/ssh/ssh_host_rsa_key
RUN ssh-keygen -t ecdsa -f /etc/ssh/ssh_host_ecdsa_key
RUN ssh-keygen -t ed25519 -f /etc/ssh/ssh_host_ed25519_key

# 创建自定义组和用户、设置密码并授予root权限
# RUN groupadd -g 1124 bigdata && useradd -m -u 1124 -g bigdata hdpuser
# RUN echo "hdpuser:hdpuser" | chpasswd
# RUN echo "hdpuser ALL=(ALL)	NOPASSWD:ALL" >> /etc/sudoers
RUN echo "root:hadoop" | chpasswd

# 创建模块和软件目录并修改权限
RUN mkdir /opt/software && mkdir /opt/module
# RUN chown -R hdpuser:bigdata /opt/module && chown -R hdpuser:bigdata /opt/software

# 将本地的文件复制到镜像中
ADD $PWD/../hadoop-3.3.3.tar.gz /opt/software
ADD $PWD/../jdk-8u331-linux-x64.tar.gz /opt/module
COPY $PWD/sshd_config /etc/ssh/
COPY $PWD/hadoop-env.sh /opt/software/hadoop-3.3.3/etc/hadoop/
COPY $PWD/core-site.xml /opt/software/hadoop-3.3.3/etc/hadoop/
COPY $PWD/hdfs-site.xml /opt/software/hadoop-3.3.3/etc/hadoop/
COPY $PWD/yarn-site.xml /opt/software/hadoop-3.3.3/etc/hadoop/
COPY $PWD/mapred-site.xml /opt/software/hadoop-3.3.3/etc/hadoop/

# TODO
# 下面的几个文件中只是添加了开头几行的环境变量，貌似应该在hadoop-env中定义
# 暂时还没有测试
COPY $PWD/start-dfs.sh /opt/software/hadoop-3.3.3/sbin/
COPY $PWD/stop-dfs.sh /opt/software/hadoop-3.3.3/sbin/
COPY $PWD/start-yarn.sh /opt/software/hadoop-3.3.3/sbin/
COPY $PWD/stop-yarn.sh /opt/software/hadoop-3.3.3/sbin/


# 设置环境变量
ENV CENTOS_DEFAULT_HOME /root
ENV JAVA_HOME /opt/module/jdk1.8.0_331
ENV HADOOP_HOME /opt/software/hadoop-3.3.3
ENV JRE_HOME ${JAVA_HOME}/jre
ENV CLASSPATH ${JAVA_HOME}/lib:${JRE_HOME}/lib
ENV PATH ${JAVA_HOME}/bin:${HADOOP_HOME}/bin:${HADOOP_HOME}/sbin:$PATH

# 默认工作目录
WORKDIR $CENTOS_DEFAULT_HOME

EXPOSE 22

CMD ["/bin/bash"]
```


Build Image from DockerFile

```
sudo docker build -t edge51/hadoop-single:1.0 .
```
Run container

```
docker network create --subnet=172.24.0.0/24
docker run -itd --privileged --name hadoop-single1 --hostname hadoop-single -P -p 9000:9000 -p 9870:9870 -p 50070:50070 -p 8088:8088 -p 19888:19888 -p 9864:9864 --net hadoop-single --ip 172.24.0.3 edge51/hadoop-single:1.0
```

Get into the container
```
docker exec -it hadoop-single1 /bin/bash
```

Start sshd service
```
/sbin/sshd -f /etc/ssh/sshd_config
```

Format and start
```
hdfs namenode -format
start-dfs.sh
start-yarn.sh
```

Visit the website for namenode, hostname:9870 and hostname:8088.
