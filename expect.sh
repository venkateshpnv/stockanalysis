#!/usr/bin/expect -f

set timeout -1

spawn hotspotshield account signin

expect "Username: "

sleep 1
send -- "petlanvenkatesh@gmail.com\r"
sleep 1
expect "Password: "
sleep 1
send -- "Hotspot3#Pnv\r"
interact
