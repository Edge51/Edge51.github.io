---
layout: post
title:  "Name of post"
date:   2022-05-26 11:53:54 +0800
categories: jekyll update
---


# Process


![process layout](/resources/pic/Layout%20of%20a%20process%20in%20memory.png)

# git set up proxy and unset

git config --global https.proxy 'socks5://127.0.0.1:1080'
git config --global http.proxy 'socks5://127.0.0.1:1080'

git config --global --unset http.proxy
git config --global --unset https.proxy
