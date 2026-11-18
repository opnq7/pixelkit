#!/bin/bash
cd /home/claude/aoye
while pgrep -f "s6_end/scene.py:make" >/dev/null; do sleep 5; done
R(){ # name dur
 PYTHONPATH=/home/claude/pixelkit:/home/claude/aoye:/home/claude/aoye/$1 python3 -m pixelkit.render $1/scene.py:make --dur $2 --audio out/$3_audio.wav --out out/$1_v3.mp4 --workers 2 --crf 18 --preset medium > out/$1_render.log 2>&1
}
R s1_cave 55.2 s1
R s2_rem 58.8 s2
R s3_awake 46.4 s3
echo done > out/run_all.done
