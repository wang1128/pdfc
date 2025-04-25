#!/bin/bash

# 第一步：执行mp4转wav
/Users/penghao/GitHub/pdfc/venv/bin/python /Users/penghao/GitHub/pdfc/mp4_2_wav.py

# 等待30分钟（1800秒）
sleep 800

# 第二步：执行ASR测试
/Users/penghao/GitHub/pdfc/venv/bin/python /Users/penghao/GitHub/pdfc/fun_asr/fun_asr_wav_2_txt.py



