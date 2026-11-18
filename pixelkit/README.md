# pixelkit · HD-2D 像素故事视频工具包

用 numpy + OpenCV + ffmpeg 做「HD-2D 像素风」故事短片的引擎（画面、角色、UI、物理、音乐、音效、母带、渲染）。
**画面与声音的标准 = 参考片《Claude Dreaming》**（参考帧在 `assets/ref/`，量化指标见 `docs/STYLE_GUIDE.md`）。

> **v0.14 起在 Windows 本机运行**（原来在 Linux 沙盒 `/data/pixelkit`）。文中旧的 `/data/...`、`python3`、`PYTHONPATH=...` 写法
> 对应到本机：`import pixelkit` 已经全局可用（`pixelkit.pth`），命令用 `python`，工程放 `D:\像素风2d知识\作品\`。
> 知识口播视频的标准和流程在 `D:\像素风2d知识\标准与方法\`。

```
工具包/pixelkit/
  pixelkit/            引擎（import pixelkit）
    core palette persp materials light camera post particles anim ui blocks scene qa render titles edit shots perform credits
    characters/claude.py      Claude 像素角色（表情 / 动作 / 状态灯 / CRT 关机）
    characters/human.py       Q 版人类角色生成器（发型 / 眼镜 / 胡茬 / 服装 → 表情 + 手臂动作）
    sets/office.py props.py dressing.py   可复用场景（办公室）、30+ 道具、生活感布景
    sets/inserts.py           特写插入镜头（ClockInsert 挂钟）
    audio/synth music cues master   合成器 / 配乐 / 音效库 / 母带
  assets/fonts  assets/ref        像素字体（zh12 / zh10 / zh8 / silk / p2p）与参考帧
  docs/STYLE_GUIDE.md             画面 / 镜头 / 节奏 / 声音的标准与验收范围
  docs/HANDOFF.md                 项目交接（进度、剧情、分镜、恢复步骤）
```

## 一个镜头 / 一幕 = 三个文件（模板在 `templates/`：`opening/` 单镜头，`act1/` 多镜头剪辑，`act2/` 表单 + 双人交叉剪辑，`act3/` 外景多场景 + 地图 / 航拍 + 定格 + 脸屏转场 + 回忆气泡，`act4/` 对白正反打 + 表演层 + 侧面双人 + 拼接油画段，`act5/` 匹配溶解 + 微距拉远 + 文档窗口流式生成 + 黑场 / 片名 / 追光舞台片尾「Claude 制作」，`egg/` 夜间办公室近景 + 相框特写 + 走进照片，`bridge23/` 黑场 HUD 时间跳过，`bridge34/` 复用上一幕布景的延时走路过场，`full/` 全片 EDL）

| 文件 | 职责 | 规则 |
|---|---|---|
| `timeline.py` | **唯一的时间真相源**：节拍网格、事件时间、镜头轨道、角色状态、物理模拟 | 画面和声音都只从这里取时间 |
| `scene.py` | `make(**kw)` → 对象，`frame(t)` 返回 1080p 浮点 RGB | 必须对 t **无状态**（多进程乱序渲染） |
| `audio.py` | 从 timeline 排布音乐 + 音效 → `out/*.wav`（−16.5 LUFS） | 世界时间事件用 `TL.real()` 换算成真实时间 |

新片子：复制模板目录 → 改 `timeline.py` 的事件表 → 在 `scene.py` 里换布景 / 角色状态 → `audio.py` 跟着时间表自动对齐。

## 常用命令

```bash
# 1) 静帧抽查（任意时间点，乱序）→ 3 列拼图 + 每帧原图（本机单进程 ≈3.5 秒/帧）
python -m pixelkit.stills scene.py 0.8,3.05,8.95 [--only F,W] --out _work/x/sheet.png

# 2) 画面验收：与参考片的量化指标比较（饱和度 / 明暗分布 / 暖高光 / 紫阴影 / 质感 …）
python -c "from pixelkit import qa; qa.report(r'_work/x/f_06.75.png')"

# 3) 声音（≈2 秒）
cd 作品/<期>/<段> && python audio.py

# 4) 渲染 + 混流（本机 16 核：--workers 12 左右；每个 worker ≈1.4 GB 内存）
python -m pixelkit.render 作品/<期>/<段>/scene.py:make --dur 10.5 --audio out/xxx_audio.wav --out out/xxx.mp4 --workers 12
#   预览：--frames 90:150（只渲一段） / --kw "{\"OW\":960,\"OH\":540}" --crf 20（半分辨率）
```

模板 `templates/*` 里的路径已改成相对文件位置（`_KIT` / `_PROJ` / `_WORK`），复制到 `作品/` 下改 `_PROJ` 即可。
`templates/aoye/` 依赖的 GPT 背景板（`assets/plates/*.png`）和配音 wav 没有随包带过来，只能当代码参考；其余模板可直接出静帧。

## 模块速查

- **scene** `World.render(cam, st, mid, fg, glow_out, ui, frame)`：背景（含自发光）→ 中景精灵 → 光照 → 前景虚化 → 尘埃辉光 → 调色 → UI（480×270 网格，自动 ×4）。
- **light** `TOD` 预设 `golden / late / sunset / dusk / night`，`LightRig.point()` 点光（显示器青光、LED 绿光），`god_rays`。
- **post** `GRADES['golden_hd2d' | 'night_hd2d' | 'neutral']`：tonemap、分离色调、bloom + halation、暗角、颗粒。
- **camera** `Cam(zoom, cx, cy, sx, sy)`：任意缩放下像素保持锐利；`w2ui()` 世界坐标 → UI 坐标。
- **anim** `Track(keys, log=True)`（镜头缩放用对数插值）、`ramp / smoothstep / hop / squash_curve / shake / back_out`。
- **blocks** 掉落文字砖块：`brick(['周报'], col, tail=False)`、`Sim.add_landing(t_land, …)` 按「落地时刻」反推生成时刻，支持砸头弹开（bonk），`sim.events` 驱动音效与表情。
- **ui** 聊天气泡、「好的！」对话泡（带金币）、飞金币、HUD（时间 / 计数器）、JRPG 对话框、Win95 窗口、眩晕星星、冲击线。
- **characters.claude** 表情 `normal blink closed half wide happy focus dizzy q sad off`，手臂 `rest type up`，状态灯呼吸 `led_k`。
- **audio.music** `Grid(bpm, t0)` 让 beat 0 对齐关键事件；Theme A（C–Am–F–G）的 lead / harmony / bass / arp / drums / roll / stab，全部支持 `t_min / t_max` 硬切。
- **audio.cues** `room_tone clock_ticks snore breath_hum pad_swell ding chat_in pop ui_slide crt_wake voice_line ok coin sparkle jump fall thud clack bonk dizzy typing whoosh riser crash impact scratch`。
- **audio.master** `wet`（卷积混响发送）、`cut`（冻结硬切）、`fade`、`finalize(mix, −16.5)`（高通 → 胶水压缩 → 响度归一 → 软削波）、`report`。
- **shots** `OfficeShot`：办公室镜头基类（布景 + 光照 + god rays + 夹紧相机 `mk_cam` + 显示器点光 + `desk_and_claude` 绘制顺序 椅子→身体→桌子→桌上物→爪子），传入 `tl=timeline` 即可复用。
- **edit** `Edit().add(name, t0, frame_fn, 'cut'|'zoomcut'|'dissolve'|'fade'|…, d)`：多镜头共用一条全局时间线的剪辑表，`shot_at(t)` 供调试 / 音频路由（见 `act1/scene.py: Act1`）；`make(only=[...])` 只渲指定镜头做测试。
- **titles** `TitleCard(主标题, 英文, 小字)`：参考片风格标题卡（暗色笔刷条 + 金色衬线字擦入 + 闪光扫过 + 末尾金尘消散），`frame(t, dur)`。
- **sets.inserts** `ClockInsert(tod, wall, brand)`：挂钟特写（ALWAYS / ON 品牌字、石膏墙斑驳），配 `cues.tock / hour_chime`。
- **ui 扩展**：表情 `EYES sad/tired/up`、`MOUTHS frown/wavy`；Win95 系列 `w95_window / w95_panel / w95_field / w95_open_fx / cursor / highlight`（查词典、弹窗）；日历 `month_info / cal_cells / cal_grid / WEEK_ZH`；印章 `stamp_sprite / rubber_stamp(bold=True 像素加粗)`；`hud_popup`（大数字弹出）、`blit_scaled`；**`chat_feed`**（多组聊天流，按组上推）、**`ff_badge`**（▶▶ x180 快进角标）、**`narration(cv, t, boxes)`**（JRPG 旁白框）。
- **anim 扩展** `type_times / typed_n / type_end`（逐字打字时间）、**`boxes_prep / box_at`**（旁白框时序：开合、逐字、英文同步）。
- **blocks 扩展** `GOLD_HI`、`brick(hi=…, body_E=…)` 高亮 / 自发光砖、`Body(gk, vmax, sway, tag)` 可配重力与摇摆（叠塔摇晃）、`put_bodies(flash_fn, hide_fn)`、`Poof` 消散烟。
- **audio.music 扩展** Theme B（`CH_B / MEL_B / theme_b`，慵懒周末感）、`keys_comp / soft_bass / lazy_drums`、`INSTR`、`phrase / piano_phrase`（任意旋律短句）。
- **audio.cues 扩展** `tock hour_chime ticker stamp paper_flip window_open window_close mouse_click key result_ding box_open question line_clear soft_land tension_pad night_bed title_sting`；`voice_line(times=ln['times'])` 与旁白逐字同步。
- **audio.master** `finalize` 带真峰保护（自动降软削波阈值直到 ≤ −1 dBTP）。
- **render** 多进程按序喂给单个 libx264 编码器（无分段接缝），再混入 AAC。

### v0.17 新增（001《深度工作》正片沉淀）
- **新模块 `hudx`（微光 HUD 扩展件，和 `hud` 同一套黑金辉光外观，全部 480×270 UI 画布 + 辉光层 gv）**：
  `chapter_card`（全片读条放大落到画面中央 → 当前段充能点亮 + 章名砸下 → 缩回顶部；返回背景压暗量）、
  `skill_hotbar`（三格技能栏：锁抖 → 锁碎 + 光环 → 图标回弹 → 呼吸辉光）、`choice_panel`（选择题：逐行滑入 / 光标跳动 / 划线打叉 / 选中金光）、
  `item_card`（灰卡 = 普攻、金卡 = 大招，可盖章）、`hp_tag`（头顶小标签，可划掉）、`error_bar`（红黑警示条）、`status_flip`（状态牌翻牌）、
  `book_says`（「书里说」角标：作者头像插槽 + 引号）、`input_card`（评论区输入框）、`boss_bar`、`time_axis / time_block`（一天的时间轴 + 金块 / 灰块）、
  `clock_ring`（24 段圆环被一口口啃掉，带牙印）、`clock_face`（钟面 + 扇区）、`density_meter`（信息密度竖表）、`quest_list`（任务卡 + 勾选动画）、
  `calendar`（月历 + 马克笔金叉 + 每格小读条）、`icon(name)`（msg meet form note doc book puzzle star portal split drop bag cert people lock key gift coin hourglass）、
  `check_mark / cross_mark / stroke_x`（笔画动画）。测试接触表：`作品/001_深度工作/_work/test_hudx.py`。
- **`tools/import_pose.py`**：GPT 角色姿势 → 真像素精灵。按**两眼间距**对齐尺度（小橘眼距 ≈ 21.4–21.9 px），复用已有 `palette.npy`，补描边。
- **`tools/look_report.py`**：质感体检。成片和参考片用同一把尺子量：剪辑节奏、画面事件密度、超 3 秒的无事件段、饱和度、主色集中度、暗部占比、像素颗粒、场景重复。达标线和用法见 `标准与方法/质感差距分析.md`。
  眼睛检测失败时（耳机、帽子上的星星会干扰）用 `--scale` 直接给比例（法师类 0.072）。
- **`characters.juzi` 新姿势**：`cup`（双爪捧着，光核由代码加）`reach / hold`（伸爪够手机 / 收回握拳）`scratch`（挠头）`peek`（从左边探头）`busy`（忙乱打字的打工人，无耳机）。
- **pfx 并行烘焙不再撞车**：每个进程用自己的临时目录，烘焙完先检查别人是否已写好。多进程渲染第一次用新特效不会再 `bake failed`。
- **做法沉淀（001 正片）**：
  - 一期正片 = 若干 `Segment`（全局时间轴上的一段：镜头表 `[(T_from, shot_fn)]` + 章节卡 + 全片读条 + 「书里说」角标 + 字幕），
    每个 shot_fn 返回 `(img, cv, gv, opts)`；段落边界吸附到 30 fps 帧格，分段渲染后直接首尾相接不漂移（见 001 `ep.Segment`）。
  - 配音分段生成后用 `voice_post_body.py` **只加不减**地补静音：章节卡前 ≥ 2 s、金句后 ≥ 1 s、命名仪式的名词后 0.55 s（`WORD_GAPS`）。
  - 角色和道具一有接触就用 GPT 整图（捧东西、伸手、挠头）；代码只做表情、呼吸、眼神、光。

### v0.16 新增（001《深度工作》：高质感 HUD + 主角小橘 + 书本出场）
- **hud.py「微光 HUD」**：所有组件同时画「UI 画布 cv」和「辉光画布 gv」，`hud.compose(img, cv, gv)` 把 gv 两层模糊后加到画面上——UI 有真光晕（旧 UI 发平的主因）。
  `cast_bar_pro`（技能插槽 + 双线金框 + 玻璃槽 + 流动能量（Bayer 抖动亮波）+ 前沿辉光 + 汇聚光点 + 剩余时间）、`cast_shatter_pro`（裂纹 → 碎块飞散 + 红闪 + 框体抖）、
  `dmg_number`（逐位砸下 + 渐变 + 描边投影 + 星芒）、`big_text`（渐变像素大字）、`roll_number`（老虎机滚动数字）、`speed_lines`（冲击速度线）、`slam_stamp`（盖章猛砸 + 冲击环）、
  `panel`（黑金面板：双线金边、角菱形、斜向扫光）、`name_tag`（引线名牌）。
- **bookreveal.py**：书本出场（每期换封面复用）：压暗 → 光柱落下 → 书在光里翻转 1.5 圈下落（背面自动生成：深蓝 + 金框 + 徽记；侧面画书脊）→ 落定冲击环 + 碎光 + 暖色光爆 → 背后光芒慢转 + 推镜 → 封面扫光 → TitleCard 金色衬线标题在右侧揭晓 → `t_out` 后书缩小飞到左上角停靠（`dock()` 之后每帧画「本期书目」）。`title_at` 可对齐到配音念书名的那一刻；`sfx(bus, t0)` 配套音效。
- **castbar.py**：读条基础版（`cast_bar / cast_shatter / mp_bar / film_rail` 顶部全片读条 / `orb_sprite` 注意力光核）；颜色语义 BLUE 专注 / RED 打断 / GOLD 价值 / GREY 普攻。
- **characters.juzi「小橘」**（频道主角，奶油橘白小猫）：GPT 按设定图出姿势 → 统一头宽 48、同一 56 色调色板量化（素材在 `工具包/素材库/角色/小橘/`）→ 代码表演层：
  眼睛 normal / blink / closed / happy / half / focus / dilated（瞳孔放大）/ shock / sad / blank + look 平移、口鼻统一重画（w / o / smile / flat / frown）、尾巴摆、1 px 呼吸、自动眨眼。
  姿势：stand / desk / phone / mage / back / student / office / back_stand / pocket（加新姿势：素材库放 png + POSES 加一行）。
  **流程定论（用户 2026-11-09）**：纯代码画的主角两版都被评「丑」；角色设计交给 GPT（出 2–3 个方向让用户挑），代码只管演。
- **characters.reddot**：红点怪（未读红点变的小怪，脸中间是通知数字）：face idle / grin / cute / oops / shock / sleep，arms rest / poke / up / hold / wave / push。
- characters.kitty：代码画的猫（被否的第一版，留作参考，不要用）。
- **v0.16b（开场 v3 反馈）**：`characters.reddot.sprite(pose)` 红点怪 v2（GPT 设计稿，grin / poke / jump / peek，素材库/角色/红点怪）；`bookreveal` v2 = 真 3D 透视书（贴图四边形 + warpPerspective 最近邻：
  斜着转正降落、封面绕书脊打开、翻页、书页暖光、光粒上升、合上、停靠；配 pixelfx holy/holy-pillar），v1 留在 bookreveal_v1.py。
  **pixelfx 用法定论**：先 `node tools/list.mjs` 搜、渲 contact 挑、换调色板（PAL_BLUE / PAL_GOLD），再用 `fx_on_stage`（001 ep.py：真 alpha 合成到 320 舞台 + 亮像素自发光）放进世界层；
  **bookreveal v4（当前版，用户认可方向）**：v1 流程（光柱 → 1.25 圈 3D 旋转降落带残影 → 落地冲击环 + 光爆 + 碎光 → 光芒 + 光晕 + 环绕星芒 → 扫光）+ 精装书（`hardcover()`：布面板、金色双线压纹框、四角包金、书脊金带、书页厚度）→ `t_out` 时从上到下化成金色光粒消散。节奏（用户 2026-11-09）：**先暗再慢慢变亮**——先压到近黑停半拍，书以剪影降下、边落边被照亮，落地是柔和光晕（不硬闪）；封面要是画面里最亮的东西（提亮 1.1 + 饱和 1.18、正面不吃暗面、外圈轮廓光）。不翻页、不停靠（用户：翻页奇怪、角落 UI 没必要）。v1/v2 留档。
  **角色和道具不要拼贴**：小橘爪子 + 笔记本分开合成会穿模（用户：「手和书穿模，太怪」）→ 让 GPT 把「角色 + 手里/桌上的东西」画成一张整图（juzi `desk_nb` / `chin_nb`）。
  已验证好用：arcane/arcane-orb（光核）、arcane/arcane-beam（大招光束）、arcane/spell-charge（聚能）、holy/holy-pillar（天降光柱）、impacts/crit-hit。
- 剪辑语法（参考片「一只索尔」拆出来的，用在 001 开场 v2）：每句换镜头、景别大跳（大特写 ↔ 全景）、重读词 `punch()` 冲击推进 + 速度线、硬切为主 + 甩镜 / 闪白转场、手持微漂 `drift()`。

### v0.15 新增（GPT 拆件 → 像素木偶）
> 结论（用户 2026-11-08）：**人物不用这套，继续用代码画的角色**；puppet 留作备用（会动的道具等）。
- **puppet.py**：GPT 画「长什么样」，代码管「怎么动」。`key_out`（抠纯品红底）→ `split_parts`（连通域分件）→ `pixelize_all`
  （同一缩放、同一调色板、统一 1px 描边）→ `Puppet({name: Part(rgba, pivot, parent, joint, z)})` → `render(angles, offsets)`。
  旋转默认 EPX（实测：CRT 头这种大块刚体用剪切法会被拉碎，EPX 转 4–8° 仍干净）。
- GPT 拆件的**相对大小不可靠**（手、天线、腿常常画大），以全身图比例为准逐件微调缩放（模板里的 `FUDGE`）。
- 表情不让 GPT 画：头部屏幕留空，代码按 `claude.EYES` 画眼睛（眨眼中间帧、看向、开心、瞪大都现成）。
- 举手不要超过约 135°，否则短手臂会整个藏到大头后面。
- 素材：`工具包/素材库/角色/claude_gpt拆件/`（全身图、拆件图、方正躯干 torso.png、提示词、两版测试片）；模板：`templates/puppet_test/`。
- **v1 → v2 用户反馈「像在拼贴、下半身怪」**，原因和改法（`rig_v2.py` = 推荐写法「混合绑骨」）：
  1. 每个部件各自一圈描边 → 关节处全是线。改：GPT 部件不补描边，整体只描**一圈外轮廓**；画在身体前面的手臂自带描边，但关节 4–5 px 内不描。
  2. 整根 GPT 手臂旋转 → 画好的明暗跟着转，光向乱。改：**会弯会动的部分（手臂、腿）用代码画**（`limb()`：折线 + 按左上光实时算亮边 / 暗边，颜色从 GPT 躯干取 4 档），肩 → 肘 → 腕两段，前臂 `spring_follow` 跟随上臂（拖拽 + 过冲，限幅 ±35°）。
  3. GPT 躯干是布袋形 → 腿像从袋底戳出来。改：单独重画躯干（方正卫衣、平下摆），腿从下摆里伸出、画在躯干后面。
  4. 举手过 70° 时手臂改画到头前面，否则会藏到大头后面。
  → 原则：**GPT 画刚性、有细节、决定长相的部件（头、躯干、手、道具），代码画连接和变形的部分（四肢）**。

### v0.14 新增（迁到 Windows + 知识口播工具链）
- **Windows 可用**：`pixelkit/__init__` 把 `cv2.imread / imwrite` 换成中文路径安全版（原版在中文路径下**静默失败**、不报错不出图）；
  新模块 **`fonts.py`**：标题卡 / 片尾的平滑字体按角色查找（`serifb serif it itb sans sansl`），顺序 = `assets/fonts/smooth/` → Linux 路径 → Windows 字体，
  旧的 `(path, index)` 写法照常可用；`render.stills` / `stills` 默认输出到当前目录 `_work/`；63 个模板文件的 `/data/...`、`/home/claude/...` 改成相对路径；
  `render` / `render.patch` 在 Windows 上用 spawn 起进程（Linux 仍是 fork）。实测本机 8 进程 ≈0.4 秒/帧（1080p，act1）。
- **新模块 `pfx.py`**：直接用 `工具包/vendor/pixelfx` 的 244 个像素特效。`pfx.FX(id, opts, palette, seed)` 第一次用时调 Node 烘焙成精灵表并缓存到
  `assets/fx_cache/`，之后 `fx.draw(canvas, t_local, x, y, scale, flip, alpha)` 是纯 t 函数（多进程渲染安全）；`fx.duration / fps / loop / pivot`；
  `pfx.find('coin')` 搜目录。目标可以是 `core.Canvas`、RGBA 数组或 RGB 浮点图。pixelfx 的字体只有英文数字，中文一律用 pixelkit 字体叠。
- 配套（不在本包内）：`配音相关/导演配音/导演配音.py` 逐句导演配音 → `manifest.json`（每句 / 每字时间、重读词时刻），作为每期 `timeline.py` 的时间源；
  `标准与方法/` 下的交付标准、参考片拆解、制作流程、信息呈现手法库（手法 ↔ 组件对照）、配音导演规范。

### v0.3 新增（第二幕《请假单》沉淀）
- **characters.human** Q 版人类：`Look(hair messy/short/side/long/bun/bald, hair_col, skin, glasses None/square/round, stubble, bags, cloth hoodie/shirt_tie/suit/cardigan/tshirt, cloth_col, accent, blush, seed)` → `draw(L, face, arms, phase, look, glint, desk_y)` 返回身体 / 手两层精灵（手画在桌子之后）；表情 `normal blink closed tired surprised smile soft sad focus o`，手臂 `rest type chin mouse up wave down hold`；`sheet()` 出设定图；预设 `WANG`（王工：乱发、方框眼镜带反光、胡茬、黑眼圈、灰卫衣）。
- **characters.claude** `crt_off(cv, E, k)` 屏幕收缩成线再成点；`shots.claude_parts` 支持状态键 `led / crt / spark_k`。
- **sets.office** `background(wang_live=True)` 把王工工位留给活体角色；`WANG_HEAD / WANG_DESK_Y / LAPTOP_XY`、`draw_wang_desk(mid, parts, laptop_on, t, steam)`（椅→人→CRT→相框→桌→泡面+热气→手→笔记本→名牌）。
- **sets.props** `laptop_back()`（银色背面 + 珊瑚色火花贴纸 + 屏光外溢）、`steam(t, h, seed)`。
- **ui** `w95_checkbox`、`w95_progress(marquee=t)`、`tooltip`、`toast`（右下角通知）、`STATUS + status_badge`（在线 / 休假中 状态点，可翻转）、`name_card`（人物登场名牌）、`chapter_banner`（幕标题条）。`rubber_stamp` 中文可读性：角度 ≤5°、不加粗、`wear≤0.04`，`zh10 scale=3` 最清楚。
- **audio.cues** `chapter_chime digit_ticks error_buzz deny checkbox heartbeat progress_ticks progress_done toast highlighter status_flip auto_reply crt_off switch_click`。
- 经验：多镜头场景里，前一幕留下的大道具（如金色「周末」砖）在别的角色特写里会抢画面——在该镜头的 `mid()` 里按镜头隐藏（`desk_blocks=False`），只在双人全景里保留连续性。


### v0.4 新增（第三幕《人类的周末》沉淀）
- **sets.street** `Street`：外景街道基类（天空 / 远景楼 / 人行道 / 路灯 / 树，树叶按风摇曳）；咖啡馆橱窗（窗内坐着的人、A 字立牌粉笔画杯子）。
- **sets.town** `Town(Street)`：小镇全景（公园长椅、咖啡馆外摆、婚礼拱门 + 画架像素爱心、窗帘可拉开的住宅窗），`clusters()` 生成灌木 / 花丛。
- **sets.maps** `ParkMap`（俯视公园地图：网格扫描 / BFS 波纹 / 路线绘制用）、`CityAerial`（城市航拍底图）、`claude_mini(direction, phase, glow)`（地图里的迷你 Claude，**地图镜头里放大 2 倍使用**）。
- **characters.person** 修长比例路人：`Look` + `draw(L, pose='stand'|'walk'|'sit', phase, arms, face, prop, tilt, glint, flip)`，`background()` 把路人压灰退后，`sheet()` 出设定图；预设造型含跑步帽、长卫衣、西装伴郎、新郎、新娘等。
- **characters.walker v2** 外景 Claude 走路（`Walker`，腿 / 摆臂 / 手持道具）、`dog_sprite`；旧版保留 `walker_v1.py`。
- **characters.claude** 新姿势 `lie`（躺草地）+ `pillow`（抱枕头），供「数羊」用。
- **particles** `Motes2D`（外景光尘）、`FallingLeaves`（落叶）。
- **ui** `quest_bar`（主线任务条：进行中 / 失败 / 完成）、`achievement`（成就弹窗 + 奖杯，有副标题时高 40）、`hud_banner`（spinner + 进度条，可切完成状态）、`trophy`。
- **audio.cues** `birds wind morning_bed fanfare fail_wah big_ding crowd_gasp claps swish step`。
- 第三幕自带（在 `templates/act3/scene.py`，可直接搬）：`People` 人物精灵缓存、`warm_grade` 暖色递进、`DreamBubble`（云朵梦境气泡 + 羊跳栅栏 + 计数暴涨变羊流 + 气泡爆掉）、`sheep_counter`、`TownShot / PathShot / AerialShot / FreezeShot`（定格：缓存一帧 → 渐降饱和 + 慢推 2.5%）。
- 政策变更：**不再使用章节条**（`chapter_banner` 保留但不用）；第一、二幕最终拼接前需去掉章节条重渲。

### v0.4.1 新增（第三幕 v2 反馈沉淀）
- **anim** `boxes_lint(boxes, min_hold=1.0, per_char=0.10)`：对白框每句「完整显示时长」检查，`boxes_prep` 默认自动调用，不够会在 stderr 打 `[boxes_lint] line held Xs < Ys`；`read_time(text)` 给气泡算阅读时间（0.9 s + 0.12 s/字）。
- **ui** `quest_list`（主线任务条下展开的支线清单：▸ 进行中 / □ 待做 / ✗ 失败 / ✓ 完成）、`zzz`（入睡 z Z Z）、`dust_puff`（落地 / 跳下的小尘团）、`auto_bubble`（暗色「自动回复：Claude 休假中」小气泡）、`ThoughtBubble`（云朵思考气泡，内部画面可动：回忆 / 梦 / 计划）。`quest_bar(kind='支线任务', kind_en='SIDE QUEST')` 当支线条用。
- **characters.claude** `face='map'`：屏幕脸变成发光的三折地图 + 红图钉（「规划模式」）。
- **edit** `screen_zoom(base, inset, rect, k)`：让下一个镜头从角色的脸屏 / 手机 / 显示器里放大铺满全屏（k 0→1），或收回去（k 1→0）；边框发光 + 扫描线在铺满前淡出。
- 第三幕 v2 自带（`templates/act3/scene.py`）：`mem_painter`（暖色回忆画面：夕阳、矮墙、两个穿校服的小孩背影、书包、搭肩动作，半分辨率绘制 ×2 更「像素」）、`AerialShot.frame_after`（定格后的过渡：气泡逐个消失、手机光熄灭、鸟群飞过、颜色恢复）、`TownShot.face_rect`（脸屏在输出画面里的矩形，给 screen_zoom 用）。

### v0.5 新增（油画转场小样沉淀，第四幕备用）
- **sets.river** `River(dusk=0..1)`：480×270 逆光河边夕阳（渐变天 + 云带 + 下沉太阳、远岸树线 + 铁桥 + 小镇灯窗、水面倒影 + 波纹 + 太阳光柱、近岸草坡、空水桶 / 钓具箱、前景芦苇摆动 `front_index(t)`）；`glitter(t)` 水面闪光（bg_patches）、`ripple_rings(...)` 像素涟漪；常量 `HORIZON / SEAT_Y / RIVER_STATE`。两套 `River(0)` / `River(1)` 按 dusk 混合即可做「太阳下沉、天变紫」。
- **characters.backs** `claude_back(sun_side, glow)`（背影坐姿：头壳 + 背板通风口 + 珊瑚耳盖 + Logo 天线，烘焙边缘光）、`person_back(Look, hat='straw'|'cap'|None, seat='stool')`（老人背影 + 草帽 + 折叠凳，`.hand` 给鱼竿锚点）。
- **painterly**（像素 → 油画）：`Painter(ref, focus, length_map, width_map)` 笔触油画——几何（3 层锥形扁笔触，沿结构方向，天空 / 水面偏水平）、厚涂高度图、鬃毛纹理**只生成一次**，`paint(src, t)` 每帧只重采颜色（≈0.3 s/帧，不闪不爬）；`soften`（化开的中间态）、`paint_grade`（印象派暖调）、`ripple_mask`（涟漪前沿逐块抖动溶解）、`ring_glow`（前沿亮环）、`zoom_view / zoom_matrix`（定点推镜）。
- **ui** `toggle(cv, cx, y, on_k, label='消息提醒')`：铃铛 + 开关小面板（关时铃铛加红斜线）。
- **audio** `synth.pluck`（Karplus-Strong 尼龙弦吉他）、`synth.water_plop`；`cues.river_bed`（水拍岸 + 空气 + 两只蟋蟀）、`cues.plop`、`cues.shimmer`（涟漪光扩散）。
- 小样工程：`templates/paint_test/`（timeline / scene / audio，11 s）。

### v0.5.1 新增（油画小样 v2：栈桥海报构图 + 定格）
- **sets.river_pier** `RiverPier(dusk)`：海报构图——透视木栈桥伸进夕阳河面（木板 / 缝 / 钉 / 系船柱 + 绳圈）、分层云（受光底边）、远山 + 杨树 + 右侧小镇尖塔（灯窗随 dusk 点亮）、镜像天空水面 + 光柱、远处小船、睡莲、两侧摆动芦苇；道具灯笼 / 桶 / 钓具箱 / 保温杯；`glitter(t)`、`birds(t)` + `draw_birds`、`ripple_rings`；常量 `CLAUDE_SEAT / OLD_SEAT / BOBBER / LANTERN / PIER_END / RP_STATE`；`pier_mask`、`detail_mask`（小道具 / 小镇 / 芦苇，给油画细笔层用）。
- **characters.backs** `old_fisher_back(sun_side, rod_side)`：精致版钓鱼老人背影（草帽编织纹 + 毛边 + 帽带、灰发、逆光红耳朵、橄榄针织开衫 + 肘部补丁、帆布折叠凳，`.hand` 握竿点）。
- **painterly** `Painter(..., jitter_map, break_map, layers)`：按区域控制笔触颜色抖动（天空低抖动 = 不再像椭圆色块拼贴）和断笔阈值（天空 0.045，笔触不跨色带）；可加第 4 层 r=2.3 细笔。
- 油画分层做法（见 `templates/paint_v2/scene.py`）：背景 Painter + 「清晰层」Painter（人物 + `detail_mask`，小笔触 50% 混入轻柔化源图）；鱼竿 / 鱼线在油画上用抗锯齿细笔 `rod_paint` 重画（1 px 像素线会被抹掉）。
- 工程：`templates/paint_v2/`（timeline / scene / audio，16 s，含 4.6 s 无 UI 定格）。

### v0.6 新增（第四幕《河边》沉淀）
- **characters.claude**：脸 `'load0'..'load7'`（8 点加载圈，按相位轮转）、`'calm'`（安静闭眼「— —」）；手臂 `'ear'`（左手抬到耳盖上）；`draw(..., legs=False)`（近景只画上半身）。
- **characters.backs** `claude_back_walk(phase, sit=0..1, sun_side, glow)`：背影走路 4 帧 + 坐下过渡（56×67，锚点脚底 (28,65)，sit=1 后换 `claude_back()`）；内部头部抽成 `_claude_back_head()`。
- **characters.person**：`Look(hat='straw', straw_col, band_col, wrinkles)` + `draw_straw_hat()`；胡子改成有质感的短胡 + 小胡子；预设 `CAST['old_fisher']`（灰发灰胡、橄榄开衫、草帽、皱纹）。
- **ui**：`name_tab(cv, x, y, name, icon='spark'|'fish')` 名牌、`old_portrait()`（夕阳底老人头像）、`claude_box(..., name, who='claude'|'old')`（多角色对白框，老人说话头像嘴型开合；`narration` 透传 line 的 `who`）；`optimizer_card(t, rows_k, rate_k, crack)`（深色「效率」HUD：声呐 / 鱼群柱 / 风向 / 水温 / 成功率 +83%，可开裂）；`shatter(cv, rgba, x, y, age, floor_y)` 卡片碎成方块下落入水、`shatter_hits()` → 落水时刻表（给音效）。
- **outdoor**：`OutdoorScene.render(..., bg_fx=fn)`（背景打光后、人物合成前处理背景）；`dof(img, sigma, bokeh_k, thr)` 近景景深（高光变圆形光斑）。
- **paint_v2 复用接口**：`PaintV2(toggle_ui=False, t_click=..., fade_out=False)`（关掉自带面板，开关动作放到别的镜头）；`paint_v2/audio.build(ui=False, finalize=False)` 返回未母带的混音，可拼进更长的幕。
- 工程：`templates/act4/`（74 s：背影走路入画 + 双人背影中景 + 正反打近景 + 插入 + 加载圈 / 拨开关 + 油画段拼接 + 手部特写）。写法要点：用 `importlib` 以别名加载另一个工程的 `timeline / scene / audio`（避免 `timeline` 模块重名）；近景 `bake_rim()` 烘焙逆光边缘光 + `dof()`；音频小节网格对齐被拼接段的第 0 小节。

### v0.7 新增（第四幕 v2「表演层 + 像素画质」沉淀）
- **新模块 `perform.py`（表演层）**，全部是 t 的纯函数：`on_twos(t)`（角色动作一拍二 = 15 张/秒，水和光仍 30 帧）；`spring_follow / lag`（任意轨迹的阻尼弹簧跟随 → 天线、帽檐、鱼竿尖的滞后）；`wobble / wobbles`（事件触发的阻尼摆动）；`PoseTrack`（具名姿势 + 缓动混合，返回 `(a, b, k)` 直接传给 `claude.draw(arms=...)` / `person.draw(arms=...)`，`'back'` 带轻微过冲）；`anticipate(u)`（先反向再出发）；`breath_px`（1px 呼吸，呼气停留）；`blink_face`（半闭 → 闭 → 半闭）；`glance`（眼睛快速跳视 + 小过冲，停留时不漂）；`shear_rotate / rotsprite`（像素旋转：三次整数剪切，不糊不掉像素，≤10° 用它）；`squash_about`（绕坐点/脚底挤压拉伸）；`shake_rows / shift_rows / lean_rows / merge`。
- **characters.claude**：手臂改成数据 `arm_spec()`（可插值，`blend_spec`），新姿势 `'clasp'`（双手交握，礼貌等待）、`'knees'`（坐着手放腿上，phase 敲手指）、`'point'`；新眼睛 `'blink1' 'sparkle' 'star' 'squint' 'droop' 'wide2'`，脸屏 `'dots1' / 'dots'`（两个加载点亮了又灭）、`'ellipsis'`（…）；`draw(tilt=度, head_dy, head_dx, ant=(dx,dy), leg_kick)`：歪头（头单独一层绕脖子剪切旋转）、头相对身体位移、天线弹簧弯曲、坐姿脚掌踢起。旧参数输出逐像素不变（`/data/work/perf/diff_claude.py` 回归）。
- **characters.person**：`draw(turn=0..1.6, head_flip=, arms=(a, b, k), arm_ang={side: (上臂°, 前臂°)})`；`head_dir(v)` 屏幕方向转头（−1 左 3/4 → 0 正脸 → 1 右 3/4 → 1.6 右侧脸）。**头与身体夹角不超过约 90°**（身体朝左时头最多转到正脸；要看另一边就转身体），否则像猫头鹰扭头，很诡异（第四幕 v2 样片 v1 的教训）。
- **outdoor.pixel_soft(img, cell, sigma)**：像素保留式背景虚化（替代照片式 `dof`）：`cell = round(4 × 镜头倍率)` 的屏幕网格平均 → 网格上高斯 → 方块光斑 → 最近邻放大。
- **particles.PixelSwarm**：蚊群 / 萤火虫，单个原生像素 + 自发光（`kind='midge'|'firefly'`）；放在较暗的背景前才看得见。
- **sets.river_pier.bucket_side()**：侧面镀锌水桶（卷边、水面反光、两道压筋、凹痕、提手；放置时加 1px 接触阴影）。
- **perform.py 追加**：`bounce_light(a, col, k, rows)`（地面 / 水面反光把角色下半身染一点环境色：白天暖、黄昏紫）；`flicker(t, seed, base, amp)`（灯笼 / 火光的不规则闪烁，纯 t 函数）；`turn_track(t, keys, snap)`（人物转头轨迹：关键朝向之间自动插 0 / 0.6 中间张，不会一帧跳过去）；`contact_shadow(a, col, alpha, spread)` → `(patch, dx, dy)`（坐 / 站在木板上的 1px 接触阴影）。
- **characters.claude**：3×5 像素数字字体 `DIG35` + `face_text()`；脸屏 `face='txt:40×52/=2080'`（`/` 换行；`glow < 0.6` 时字变暗）。
- **ui.hud_notify(cv, x, y, title, body, k, alpha)**：HUD 时钟下方弹出的消息小条（「工作群 · 3 条新消息」）。
- **characters.person.head_dir** 规则写进 docstring：**头与身体朝向差 ≤ 2 个单位（1 单位≈45°）**；身体朝水（+1）时头最多转到 −1（看身边的人）；不要 3/4 身体 + 反向侧脸。
- **audio.cues 追加小表演音**：`creak`（木板 / 折凳嘎吱）、`chuckle`（憋笑的鼻音「哼哼」）、`sigh`（机器人散热口叹气）、`boing`（天线弹簧）、`reel`（渔轮棘轮）。
- **render.patch / `--patch`**：成片里只有几帧有问题时，只重渲这些帧并拼回去（解码原片 → 替换 → 重新编码 crf 15 → 混音），几分钟代替整幕重渲：`python3 -m pixelkit.render SCENE:make --dur D --patch old.mp4 --frames-list 688:702,2983:2997 --audio a.wav --out new.mp4 --workers 2`。
- **vqa（成片抽查）**：`python3 -m pixelkit.vqa out.mp4 --cuts 6.6,19.7,…`：找单帧闪（A-B-A）、非切点的大跳变，以及「切点前 1 帧就变了」（东西提前冒出来）。
- **anim.boxes_cut_lint(boxes, cuts)**：对白框的展开（`t_open − 0.16 … t_open`）/ 收起动画跨过切点时报警（框会在上一个镜头最后一帧冒出来）。规则：`t_open ≥ 切点 + 0.16`。
- 工程：`templates/act4/` 更新为 v2（117.9 s，23 个镜头：背影走路 + 消息提醒 + 请坐 + 侧面双人 + 水桶 POV 扫描 + 卡片碎裂震屏 + 憋笑反应镜头 + 正反打 + 脸屏算式 + 加载圈 / 拨开关 + 油画段 + 黄昏收竿 / 递鱼漂 / 挪近 + 逆光举鱼漂结尾）。表演样片 `act4/sample_perf.py`。渲染内存：每个 worker ≈1.4 GB，4 GB 机器用 `--workers 2`（3 个会被 OOM 反复杀掉，进度卡住）。

### v0.13 新增（《熬夜副本》：320 大像素舞台 + 游戏化叙事 UI）
- **pixstage.py**：`Stage(320,180)` 大像素舞台（掩码绘制、`band` 硬边光池、`cone` 光柱、`render(cam, L, grade, air=, desat=, tint=)`）；v0.13b：`Stage.part(mask, ramp, bevel, light)` 体积着色、`dither(mask, col, k)`、`grad(...)`。`GRADE_NIGHT / GRADE_WARM`、`pixelate()`。
- **gameui.py**（480×270 UI）：字幕 `subtitle / sub_chunks`、`revive_hud`、`year_tag`、`pixel_word / pixel_word_zh / big_zh / big_text`、`cause_panel`、`quest_panel(head_col, body_col)`、`game_button`、`ecg_strip`、`sanity_bar`、`char_card`、`choice_panel`、`danmaku`、`signal_lost`；v0.13b：`player_hud`（头像 + Lv + 精力分段条 + 心率 + 迷你心电图，`dead` / `hit`）、`task_tracker`（任务 + 倒计时 + 失败章）、`result_panel`（结算卡：kv / count 计数滚动 / battery 电量对比，逐行揭示）、`battery_icon`、`onomatopoeia`（「啪！」拟声大字）。
- **sets**：`bedroom_night.BedroomNight`（深夜卧室 v2，`GRADE_BED`）、`phone_feed.PhoneFeed`（刷短视频手机 POV：8 段像素短视频 `draw_clip`、拇指上滑带惯性、状态栏时间 / 充电电量、`screen_color` 给环境光）、`bedroom320`、`hub_doors`（五扇年代门）、`cave320`、`lab1953`、`brain_tower`、`home1964`、`symbols`（太阳 / 齿轮钟 / 温度计 / 粉笔钟 / 巨石 / VS）、`night_inserts`、`paintset`。
- **characters**：`ghost`（小魂：睡帽 + 金色加载环，11 表情 7 手势）、`face_cu`（熬夜脸大特写，连续参数 + 眼睛里的屏幕倒影）、`cat`（橘猫 curl / up / puff）、`cast_sleep`（克莱特曼、阿瑟林斯基、加德纳、科诺普卡……）。
- **plates.py**（v0.13c）：外部生成的背景板（GPT / 手绘）→ 真 320×180 像素舞台：面积缩小 + 反锐化 + k-means 限色（默认 40 色）+ Bayer 有序抖动 + 孤立像素清理；自动自发光掩码 E（灯 / 窗 / 屏幕走 bloom）、`lamps` 发光块列表、`flicker()` 灯光呼吸。`Plate(path).frame()` 返回 Stage，照常叠角色 / 光 / UI；结果缓存 `.plate_*.npz`。
- **acting.py**（v0.13d 动作库）：`Act(face, arms, float_amp).beat(t, 'take'|'startle'|'freeze'|'nod'|'sigh'|'cheer'|'whistle'|'tumble'|'shiver'|'peek'|'angry'|'dizzy'|'point'|'nodyes'|'shake'|'ask', dur, **kw).hold(t0, t1, face=...)`；`act.at(t)` → dx / dy / squash / rot / face / arms / look / fx；`draw_fx(cv, fx, ux, uy, t)` 在 UI 层画 汗滴 / !! / ? / ♪ / 星星 / 💢 / zZ；`ghost_sprite(p, t)` 直接出小魂（含挤压 + 旋转）。每个 beat 自带 预备 → 动作 → 过冲 → 回稳，待机自动漂浮 + 眨眼。
- **characters.worker**：圆滚滚的小工（脑细胞 pink / 清洁队 blue / 细胞 mint / lilac），安全帽 + 头灯，`prop='cart'|'mop'|'card'|'lever'|'towel'`、`walk=True` 走路循环、`hat=None` + `badge='P'` 变蛋白小人、`hand=(x, y)` 牵手、`squash` 缩小分解。
- **characters.fly**：果蝇（normal / sleep 戴睡帽 / hyper / sleepy / dizzy）。**characters.cat**：橘猫。**characters.face_cu**：熬夜脸大特写。
- **core.missing_glyphs(text, font)**：像素字体缺字检查（≈、👍 等会变方块；zh10 没有「犸」）。上线前对所有屏幕字符串跑一遍。
- **v0.13e 融入 + HUD v2**：`Stage.actor(rgba, x, y, E, foot)` 画角色并登记 actor 掩码 + 接触阴影；`Plate.light(fr, key=(x, y))` 让角色吃场景本地光（背景模糊色 → 亮度 + 色调）并在朝主光一侧加 1px 轮廓光（`common.put_human` 已默认走这条路）。`characters.lump`：贴合任意床透视的「被子鼓包 + 头发 + 睡帽」，睡着的人不再贴正脸。`gameui.loc_tag`（年份块 + 地点，4 s 后收成年份）、`revive_pips`（每关一扇小门 + 大号百分比）、`question_card`（本关问题 → 本关答案，基于 ui.quest_bar）、`stat_meter`（侧边滑入的指标条）、`item_card`（羊皮纸道具卡，价签翻面）。中文最小 zh10，正文 zh12。转场：`edit.screen_zoom` 推进屏幕 / `Edit.add(..., 'whip', d, dir=)` 甩镜。
- **v0.13h**（《熬夜副本》全片拼接沉淀）：`levelkit.py`（一关的通用骨架：`hud2` / `revive_curve` / `Anchor` 03:56 存档点卧室——支持 `dawn` 天亮 + 时钟走动 + `dive` 附身俯冲 / `keyed` 关键帧镜头 / `put_human` / `nightcap` / `ghost_dive` / `put_ghost`）、`fx.py`（`melt` 房间融化、`eyelids` 沉重眼皮、`silhouette` 逆光剪影）、`gameui.item_row`（一排道具卡依次弹出，价签统一翻成同一种货币）。每关固定 4 拍：问题卡 → 实验 → 答案卡 → 回存档点。
- **v0.13g**：`sets.debt_props`（7 段数码管 `sevenseg`、欠条怪 `bill_monster`、反应盒、记录纸 `printout`、欠条罐、闹钟、咖啡杯堆）、`sets.clock_factory`（`per_machine` 会停机的周期基因生产线 + `loop_badge` 四步循环环）、`sets.cells.cells_stage`（会随心跳鼓动、可被打乱节拍的细胞片）、`gameui.boss_bar`（头像 + 分段血条 + 白色伤害残影）、`gameui.TopSlot`（顶部中间排队自检）、`qa.flicker_check`（`python3 -m pixelkit.qa flicker out.mp4`）。人物手改成圆形小手，站姿手垂在身侧。
- **ui._a** 夹紧 alpha（修复 `back_out` 过冲导致的 uint8 溢出崩溃）。
- 工程：`templates/aoye/`（《熬夜副本》开场 v2 + 第 1–3 关：timeline / scene / audio 三件套，`voice/tts.py` 逐句 Fish 配音）。

### v0.12 新增（过场 + 全片拼接）
- **assemble.py**：用 EDL 把成片拼成全片。`Clip(path, t_in, t_out, pre, tail, gain_db)` 逐帧精确裁切（跳过某幕自带的淡入 / 在淡出前切走）；`pre` = 声音提前进（预叠到上一段），`tail` = 切走后尾音继续响到下一段；`Black(dur, sound=fn, lead)` = 黑场 + 可选音效（`fn(bus)`，bus 从黑场前 `lead` 秒开始）。声音全部放到一条浮点时间线上，整片**只用一个增益**到 −16.5 LUFS（各幕相对响度不变，不再压缩），真峰值超限才软削波；画面每段单独编码到 `<out>.parts/`（x264 slow / crf 16 / animation）再无损 concat + 混音（AAC 256k，+faststart）；一个 11 路输入的大滤镜图在 4 GB 机器上会被 OOM 杀掉。`--reuse` 复用已编码的段（只改了声音时很快）。7 分钟全片 ≈30 分钟。返回 `(label, start, end)` 列表 → `vqa --cuts`。`python3 film.py --audio-only` 只出混音，先查接缝音量。
- 工程：`templates/full/film.py`（本片 EDL：一→二 0.6 s 黑场 + 两声滴答按第二幕的 1 s 网格提前进；二→三 / 三→四 插入过场；四→五无缝；五→彩蛋 1 s 黑场）。
- 工程：`templates/bridge23/`（3.0 s：黑场里 HUD 00:03 → 08:00 缓入缓出翻滚，`tick_times()` 每分钟一声、限 22 声/秒，落定金闪 + tock + 第一声鸟叫）；`templates/bridge34/`（7.0 s：用 importlib 别名加载上一幕的 timeline / scene 复用街景；只有主角真速走、路人快进；光从午后插值到金色、影子拉长；时钟 14:00 → 17:40 一直带到下一幕；右侧低太阳眩光；水声预叠 0.5 s）。
- **vqa 改成逐帧流式读取**（整部 7 分钟片子一次读进内存会 OOM）。整片跑 vqa 时，各幕内部的切点不在 `--cuts` 里，会报很多 JUMP，只看接缝附近（±1 s）的标记即可。
- `templates/act5/scene.py`：开场 `DuskEcho` 去掉淡入、从第四幕切点 116.3 s 接着推（无缝）。

### v0.11.1 新增（彩蛋 v2：相框 → 河边不再硬切，「走进照片」）
- **anim.push_zoom(t, t0, t1, z0, z1, v0)**：加速推进、在 t1 **零速落定**的推镜（log-zoom 三次 Hermite；`v0` = 进入时的 log-zoom 速度，接上之前的慢推不顿）。
- **anim.screen_follow(z, z0, z1, a, b)**：推/拉镜时中心按屏幕空间跟随（不甩）。
- **sets.inserts.PhotoFrameInsert.fill_cam()** → `(zoom, cx, cy)`：照片高度正好铺满 16:9 画面 = `film_print` / `film_grade` 的中心 1.5 裁切，所以推到这里后 `Edit.add(..., 'dissolve', d)` 进同机位 `film_grade(k=1)` 的照片世界能逐像素对齐（配方见 STYLE_GUIDE 6n）。
- 工程：`templates/egg/` 更新为 v2（29.4 s）：INS 末段推满照片 → 0.7 s 溶解进照片世界（小孩 + 年轻父亲，水开始动）→ 1.1 s 照片里匹配溶解（小孩 → 王工、年轻父亲 → 老人）+ 胶片褪色 → 拉远；`River.frame(age=0..1)`；`audio.py` 办公室声随画面溶解淡出、水声同步升起、「30 年」shimmer。

### v0.11 新增（彩蛋《王工的请假条》）
- **scene.World.render**：`st['bg_soft']=dict(cell, sigma, bokeh_k, dim, desat)` → 背景用 `outdoor.pixel_soft` 做保留像素的虚化（cell 默认 = round(cam.s)，即一个世界像素），近景专用。
- **characters.human**：`draw_arms(right=True)` 可跳过右臂；`reach_arm(L, tx, ty, k, desk_y, pad)` 右手从放松姿势伸向 (tx, ty)；`draw(..., reach=(tx, ty, k))` 返回 `.reach` 精灵；`sets.office.draw_wang_desk` 发现 `wang.reach` 时把手画在相框前（Z 378.8）。
- **characters.backs**：`wang_back(turn=)` 王工背影（坐姿剪影、乱发 `_messy_hair`、卫衣、牛仔裤坐在木板上、接触阴影、去孤立像素）、`kid_back()` 小时候的王工、`old_fisher_back(young=True)` 30 年前的父亲（蓝毛衣黑发）、`old_fisher_back(turn=±1)` 老人转头（头平移 2 px、帽子 1 px、那侧耳朵收起、露脸颊 + 鼻尖）。
- **sets.inserts**：`film_print(rgb, w, h, date)` 老照片（白边、偏色、日期戳 3×5 数字）、`PhotoFrameInsert(style=2)` 桌上相框特写（像素光斑背景、键盘一角、玻璃上王工头肩倒影 + 眼镜反光，`warmth` 让照片变暖并溢到木框 / 桌面、倒影随之淡去）、`film_grade(img, k, date, frame)` 整帧胶片质感（照片活过来的转场）。
- **sets.river_pier**：`RiverPier(sway_amp=)` 芦苇摆幅；`flock(t, t0, p0, vel, n)` + `draw_birds` 大鸟（9 px 翼展、3 帧）；`sparkles(t)` + `draw_sparkles()` 太阳光柱里的四角星芒；`sun_motes(t, n, box)` 夕阳光尘；`DuskDrift(sc, dusk_max).apply(k)` 太阳逐像素下沉 + 天色向 SKY1 变紫（预建 1 px 一档的天空，逐帧插值换进 OutdoorScene）。
- **ui**：`claude_box(who='wang' | 'wang_dusk')` 王工头像（夜办公室 / 夕阳背景、灰色 WANG 名牌）。
- **anim**：`type_times(..., beats={字序: 秒})` 台词中间的表演停顿（「已提交。|看鱼漂|周末快乐。」），对白框和 `voice_line(times=)` 共用。
- ⚠️ `vec.py` / `cushot.py` / `characters/closeup.py` / `sets/cu_props.py`：原生大尺寸近景的试验，画风与全片不一致，**本片不用**（见 STYLE_GUIDE 6m）。
- 工程：`templates/egg/`（28.4 s：WIDE → C_CU → W_CU → C_MED → 相框 INS → 硬切河边 RIVER（v0.11.1 起改为推满照片 + 溶解，见上）；`audio.py` 夜间办公室 → 好的 + 金币 → 状态翻转 + 八音盒 → 水声预叠 0.9 s → 第四幕吉他 Dmaj9 / D 收尾）。

### v0.10 新增（第五幕 v3：问题放进故事、暖色剧场片尾）
- **credits.Theatre(Stage)**：暖色小剧场（替代纯黑舞台）：红丝绒后幕（抖动褶皱，字幕区自动更暗更素）、扇形帷幔 + 金穗、两侧束起的侧幕 + 金绑带流苏、透视木地板 + 金边台口、一排台前灯（`lamps` 每 30 px）。`base(t, spot_k, dust_k, house_k, foot_k, lamp_ks)`（`lamp_ks` = 每盏灯亮度，可从中间往外逐个亮）、`foot_emis(foot_k)`（灯泡自发光 → bloom）。
- **Theatre.audience(t, people, light, seat_y=252, pitch=46, sc=1.9)** → 浮点 RGBA 前景：前排观众背影剪影（座椅靠背在人前面，只露头肩）+ 舞台方向的 1px 暖色轮廓光。`people=[dict(kind='hat'|'messy'|'card', x, dx, dy, clap, clap_dx, clap_dy, card='鱼')]`：草帽老人（宽帽檐亮边 + 帽带 + 草编亮点）、乱发戴眼镜的人（一团头发 + 不规则卷曲发绺 + 耳上眼镜腿反光）、预留座位卡。dx/dy 只动头（点头笑、打瞌睡）；clap = 拍手相位（双手在头侧，别举过头顶——背影看像兔耳朵）。
- **Stage.compose(..., fg=, emis0=)**：`fg` 前景层（观众）盖在角色上，并挡住背后的辉光；`emis0` 额外自发光（台前灯）。
- **sets.dressing**：`desk_calendar()`（29×29 台历：月份头、周一起排、今天蓝框、荧光笔标记、下周六红圈里一条小鱼；3×5 数字字体）、`bobber_stand()`（11×4 小木底座，鱼漂立在上面）。
- **characters.claude 'stretch' 修复**：伸懒腰手臂缩短（上举到头顶两侧而不是伸出画面；第三幕也用这个动作，需重渲）。
- **ui.chat_bubble**：气泡宽度同时考虑名字宽度（「……好。」这种短回复不再把名字裁掉）。
- **audio.music.weekend_bright(bus, g, bar0, nbars, layers, chords=CH_BB, mel, mel_bar0, mel_bus, mutes, t_max)**：Theme B 的「白天版」：F–G–Am–G（C 大调）≈97 bpm，弹跳贝斯、尤克里里（`uke_strum`，下拨 + 反拍上拨）、2/4 拍手、16 分沙锤、1/3 拍轻底鼓、八音盒 + 芯片方波旋律（`MEL_B` / 应答句 `MEL_B2`）；`mutes=[(t0,t1)]` 留白；`ring_chord(bus, t, CH_BB_END)` 收尾延音和弦（Cadd9）。
- **audio.cues**：`handclap(bus, t, gain, pan, seed, tone)`（三层微颤 + 掌心低频，tone 大 = 手小音亮）、`clap_along(bus, t0, t1, period, ...)`（一个人鼓掌，带人味的时间 / 力度抖动）、`shaker(bus, t, ...)`。
- 工程：`templates/act5/` 更新为 v3（70.4 s）：删黑屏问句和片名卡（问题的答案放进故事：周报发出 → 小李回「……好。」「这周末去。」→ Claude ^ ^ → 旁白「我以前没有周末。」/「现在，我知道它长什么样了。」→ 看台历上画圈的周六）；片尾换暖色剧场 + 前排三个座位（老人、留给「鱼」的空座、王工）陪 Claude 笑 / 鼓掌 / 一起打瞌睡；片尾音乐 = 周末主题白天版，职位每拍一个落在拍点上。

### v0.9 新增（第五幕片尾 v2「Claude 制作」）
- **新模块 `credits.py`（片尾舞台 + 平滑字幕）**：
  - `Stage(cx, floor_y, rx, ry)`：480×270 黑盒舞台，一盏像素追光（Bayer 抖动光锥 + 地面光池 + 光里的灰尘）。`base(t, spot_k)` → 底图；`contact_shadow(img, x, w, k)`；`compose(base, sprites=[(rgba, E, x, y[, alpha])], ui_rgba, spot_k, glow, shake)` → 1080p：精灵按离追光的距离打光（暗处 0.30），E 通道自发光 + bloom，UI 层不受光。
  - 平滑字（输出分辨率，不是像素字）：`line(img, text, font, px, x, y, align, col, alpha, gold, glow, tracking, shine)`，字体 `serif`（思源宋体）/ `serifb` / `it`（Georgia 斜体，只有拉丁字）/ `itb` / `sans` / `sansl`；`gold=True` 金色渐变、`shine` 0..1 一道斜向扫光。`pop(t, t0, t1)` → (alpha, dy) 升入 / 飘走；`credit_row(img, t, t0, role, name, y, t1, ...)`：「角色 · · · 名字」以中缝对齐，名字金色斜体带扫光。
  - 像素道具：`clapper(open_k)` 场记板、`pencil()`、`beret()` 贝雷帽、`note(col)` 音符、`headset_spr()`（飞走的耳机）、`mini_card(text)`（「鱼获：0」小标签）；特效：`steam_puffs`（脑袋冒烟）、`combo(cv, x, y, n, age, alpha)`（游戏式 COMBO ×N）、`twinkles(cv, x, y, t, t0)`（四角星小闪）、`stats_card(t, rows, rows_k, big, big_label, big_k, crack)`（「本片数据」卡，可裂开后交给 `ui.shatter`）。
- **characters.claude**：表情 `peek`（左闭右睁，偷看）/ `wink`；手臂 `hips`（叉腰，得意）/ `bow`（鞠躬，双手在前）。
- **render：在途帧上限**（`_bounded`，最多 `workers×4` 帧排队）。以前 `pool.imap` 一次提交全部帧，帧比 x264 编码还快时（片尾舞台）成品帧堆在主进程里被 OOM 杀掉（日志只剩 BrokenPipe + ffmpeg `Invalid buffer size`）。
- 工程：`templates/act5/` 更新为 v2（72.1 s）：片尾 = `credits_tl.py`（时间 + `cred_state(t)` 表演）+ `credits_scene.py`（`Credits(bobber).frame(t)`），`scene.py` 只做接入。

### v0.8.1 新增（第一幕夜景「一滴眼泪」+ 第二幕回炉）
- **shots.OfficeShot 升级到 v0.8 标准**：`_setup(..., dressing=True, desk_props=True)`（同一间有生活感的办公室 + 桌上笔筒 / 便签）；`perf_state(t)` 自动套表演层（一拍二、眨眼前后半闭、1px 呼吸、天线弹簧、歪头）。timeline 可选钩子：`NO_TWOS=[(a,b)]`、`KICKS=[(t0, amp)]`、`tilt_target(t)->deg`、`head_sink(t)->px`；`self.perform=False` 关掉。
- **characters.human：`draw(..., head_dy=0, tilt=0.0)`**：人物也能呼吸 / 歪头（头单独一层绕脖子转）。
- **ui 新图标**：`_icon` 加 `form`（表单）、`seal`（红印章 / 审批）、`power`（电源 / 下线）、`hourglass`（等待）。
- **幕开场转场套路**（第二幕）：从黑场淡入到上一幕最后一个镜头的同构图 → HUD 滑入（`hud_time(x, flash=)`）→ 时钟翻一分钟（tock）→ 镜头推到本幕构图 → 角色一个小决定（天线 kick）→ 窗口从显示器里弹出（`w95_open_fx`）。**不再用章节条。**

- **characters.claude：`draw(..., tear=k, tear_side=1)`**（`draw_tear`）：脸屏上一滴冷青色发光小眼泪（与暖色眼睛对比）。k 0..1：0–0.3 在眼睛外侧眼角涌出（1px → 2×2）→ 0.3–0.75 2×3 水滴带重力下滑、留 1px 暗痕 → 0.75–1 落到屏幕底边摊平成一道细线后熄灭。`side=-1` 换左眼。`shots.ClaudeShot` 会读状态里的 `s['tear']`。
- 用法守则：**只一滴、等台词说完再掉、配 `sad` 眼**；不哭出声、不加音效（克制比大哭更戳人，也给第五幕留余地）。第一幕夜景：`T_TEAR0, T_TEAR1 = 39.0, 41.0`（「我没有周末。」38.9 s 打完 → 掉泪 → 随淡出消失）。

### v0.8 新增（第五幕《周一》沉淀 + 第一幕按新标准回炉）
- **早晨光**：`light.TOD['morning']`（低角度暖阳 + 偏蓝环境光，光柱 2.3）、`post.GRADES['morning_hd2d']`、`props.SKIES['morning']` + `city_view` 早晨分支（浅色楼、少灯窗、白云）、`Office.WINDOW_SKY['morning']`。
- **办公室「有人住过」的布景**：新模块 `sets/dressing.py`：`paper_ball / trash_bin / file_box / floor_cable / coat_stand / floor_plant / wall_shelf（书 / 罐子 / 常春藤 / 小机器人 / 相框 / 地球仪）/ cork_board（河边拍立得）/ whiteboard / framed_art / pen_cup / sticky_pad / snack / pigeon(frame 0..2)`、`floor_rug`（透视正确的基里姆地毯）、`dress_office()`。用法：`Office.background(dressing=True | dict(...))`；`Office.draw_desk(skip={'mug','paper',...}, extra=[(rgba, x, y, dz, E)], content=rgba)`。**同一间办公室在所有幕里都开 `dressing=True`**（第一幕已回灌）。
- **particles.SteamWisps**：输出分辨率的加色热气（杯子）。
- **characters.claude**：手臂 `'reach'`（右手伸到精灵右缘扶东西）。
- **ui：Win95 应用窗口一套**（第五幕周报 + 第一幕词典 / 日历都用它）：
  - `w95_doc(cv, x, y, w, h, title, blocks, t, status, status_col, send, word_count, status_r)`：文字处理器（菜单栏、工具栏图标 + 字体框 + 默认「发送」按钮 idle/hover/pressed/sent、标尺、灰桌面上带阴影的纸页、滚动条、分段状态栏）。blocks：`h1 / meta / li(num) / p / sep / gap`，选项 `n`（可见字数）、`gen`（流式：新字淡入 + 橙色块光标）、`caret`、`sel=(a,b)`（藏青选区白字）、`tail_icon`、`col`、`lh`。返回 `{'send': 按钮中心, 'caret': ...}`（光标滑过去点它）。
  - 外框零件：`soft_shadow`（多层柔和投影，替代硬阴影）、`w95_menubar(cv, cx, cy, cw, items, hot)`、`w95_statusbar(cv, cx, y, cw, segs, t)`（`segs=[dict(text, w, col, busy, right)]`，busy = 跳动省略点）、`default_button(cv, x, y, w, h, label, state, icon)`、`tool_button`、`spinner_dots`、`_icon(kind)`：`new open save B I U align list send book cal search star speaker`、`DOC` 配色。
- **删字的新写法**：选区从右往左扫过去（`sel`）→ 整段消失 + 一声退格，比一个个退格更像「犹豫后删掉」。
- 工程：`templates/act5/`（42 s：第四幕黄昏回声溶解 → 早晨微距拉远（鱼漂太阳点与第四幕结尾同一屏幕位置）→ 在线 / 伸懒腰 / 09:00 叮 / 手指扶稳鱼漂 → 「好的！」→ 周报窗口流式生成 + P.S. 犹豫删改 → 旁白 → 黑场问句 → 片名 → 片尾）。`audio.py`：第一幕 Theme A 放慢到 100 bpm 只留贝斯 + 琶音当「工作模式」，Claude 停住时音乐断掉只剩钟；P.S.2 用河边 D 调 pad + 八音盒；旁白段 Theme B；黑场全静；片尾复用第四幕吉他和弦。
- 第一幕 v4：词典 / 日历换成新窗口零件（词条列表、拼音 + 词性标签、收藏星、状态栏「休息日 0 天 · 下一个假期：未安排」）；办公室布景；表演层回灌 `perf_state()`（一拍二（快进段除外）、1px 呼吸、眨眼前后半闭、每次跳起天线弹簧、「?」时歪头），**时间线一个都没改**。

## 注意

- 工程放 `D:\像素风2d知识\作品\<期>\`，临时输出放 `_work/`（旧沙盒时代是 `/data`）。
- `frame(t)` 内不要缓存「上一帧」；随机数一律用固定种子 + 时间推导。
- UI 一律画在 480×270 的 UI 画布上（整倍放大），不要在 1080p 上直接画字。

## pixelkit.flat：平面像素合成器（v0.15，002 起用）

第一人称的手、道具特写、小票和价签这类「UI 就是画面里的东西」的片子用它。和 pixstage 的区别：没有法线和点光，
只有 GPT 背景板 + 像素精灵 + 像素字一层层叠在同一个 320×180 网格上。

| 函数 | 用途 |
|---|---|
| `plate(path, w, h, crop=)` | GPT 背景板 → 真像素图（结果缓存在原图旁的 `_px/`）。要横移就出宽一点（384×216），要更近就 `crop` |
| `load / blit / scaled / rot / tinted / outline / silhouette` | 精灵。`scaled(sx<0)` 翻面，`blit(clip=)` 做出纸口、遮罩 |
| `text / text_w / text_sprite / rich` | 像素字（`zh12 / zh10 / zh8`），可放大整数倍、描边 |
| `cam(fr, z, cx, cy, dx, dy)` | 世界画布 → 1080p，最近邻；画布可以比 320 宽 |
| `Finish.apply(img, frame, bloom, glow=)` | 辉光（只给传进来的发光画布和很亮的地方）、暗角、颗粒 |
| `shake / drift / keys 以外的缓动` | 震屏、手持感、各种缓动 |

例子：`作品/002_审美力/s1_open/scene.py`（16 个镜头）和 `ep2.py`（字幕、价签、小票、盖章）。
