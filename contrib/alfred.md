# Start Master Server
```
alfred -i wlan0 -b none -m
# -b batmanif to be used on router
```

# Save Data
```
# Note that 0 - 63 are reserved (please send an e-mail to the
# authors if you want to register a datatype), and can not be used
# on the commandline. Information must be periodically written
# again to alfred, otherwise it will timeout and alfred will for-
# get about it (after 10 minutes).
cat r.xml | gzip | alfred -s 64
```

# Load Data
```
# 00:16:ea:c3:b8:26 is the mac of the sender
alfred-json -z -f string -r 64 | python -c 'import sys,json;print(json.load(sys.stdin)["00:16:ea:c3:b8:26"])'
```
