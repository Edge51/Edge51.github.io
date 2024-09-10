---
title: "后端本地开发环境搭建"
collection: BackEnd
type: "Environment Installation"
permalink: /teaching/2014-spring-teaching-1
date: 2024-09-02
---

Golang Installation
======

MySQL
======
安装mysql之后，默认没有账号，需要通过root权限进入，并创建用户并授权
```mysql
CREATE USER 'sammy' IDENTIFIED WITH mysql_native_password BY 'password';
bind-ip
```
[参考博客](https://www.digitalocean.com/community/tutorials/how-to-install-mysql-on-ubuntu-20-04#step-3-%E2%80%94-creating-a-dedicated-mysql-user-and-granting-privileges)


Redis
======

Kafka
======

RabbitMQ
======

kubernetes
======

JetBrains Installations
======

### install.sh

``` mermaid

```

Firefox Settings
======

### hide top tab bar
about:config
toolkit.legacyUserProfileCustomizations.stylesheets true

about:support
under the Application Basics section, there will be a section called Profile Folder with a button to Open Directory.

In the Profile Directory create a new folder called chrome. In the chrome folder create or edit the file userChrome.css if it already exists.

```css
/* hides the title bar */
#titlebar {
  visibility: collapse;
}

/* hides the sidebar */
#sidebar-header {
  visibility: collapse !important;
} 

/* leaves space for the window buttons */
#nav-bar {
    margin-top: -8px;
    margin-right: 74px;
    margin-bottom: -4px;
}

```