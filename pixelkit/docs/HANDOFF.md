<callout icon="📌" color="gray_bg">
用途：新对话的上下文交接。项目是像素风短片 **《Claude 想请一天假》**（参考片：《Claude Dreaming》HD-2D 像素风）。**第一～五幕、油画小样都已通过（第一幕 v4.1、第二幕 v2、第三幕 v2、第四幕 v2、第五幕 v3）**；彩蛋 v2 已通过；第三幕 v2.1（伸懒腰手臂修复）、两段过场（二→三 时间跳过、三→四 走向河边）、第五幕 v3.1（开场无缝接第四幕）已做；**全片 v1（7 分 10 秒）已拼好交付待确认**。全部画面和声音都用自研 Python 工具包 **pixelkit**（当前 **v0.12**，`/data/pixelkit_v0.12.zip`）代码生成。
</callout>

## 0. 新对话开工第一步（重要）

沙盒曾经被**回滚过**：`/data/projects`、`/data/work` 被清空，pixelkit 退回旧版。开工前先检查，缺了就恢复：

1. `ls /data/pixelkit/pixelkit/sets/dressing.py /data/pixelkit/templates/act5/scene.py /data/projects/claude_dayoff/act5/scene.py`，都在才算正常（有 `dressing.py` = v0.8）。
2. 不在的话：请用户上传最新的 `pixelkit_v0.12.zip`（或在 `/data/.agent-service/files/*/pixelkit_v0.*.zip` 里找最新版）→ 把旧的 `/data/pixelkit` 改名备份 → `cd /data && unzip pixelkit_v0.12.zip`。
3. 按模板重建工程目录：`for a in opening act1 act2 act3 paint_test paint_v2 act4 act5 egg bridge23 bridge34 full; do mkdir -p /data/projects/claude_dayoff/$a && cp /data/pixelkit/templates/$a/*.py /data/projects/claude_dayoff/$a/; done; mkdir -p /data/projects/claude_dayoff/out/acts /data/work/act4 /data/work/act5 /data/work/egg`
4. 验证：`cd /data/projects/claude_dayoff/act4 && PYTHONPATH=/data/pixelkit python3 -m pixelkit.stills scene.py 3.0,21.0,51.5 --out /data/work/act4/restore.png`，看图是否正常（第四幕模板已是 v2，117.9 s）。
5. 成片若丢失：请用户重新上传（已交付的 mp4 都在用户手里）。参考片原视频（446 MB）可能在 `/data/.agent-service/files/*/5bffd8b36fe613216e37bab75e9e3110_raw.mp4`；参考帧在 `pixelkit/assets/ref/`；量化指标在 `pixelkit/docs/STYLE_GUIDE.md`。
6. 小坑：`view_image` 按路径缓存，**每次出图用新文件名**（刚生成的图第一次看偶尔报找不到，再看一次即可）。
7. Notion 交接页：旧页在别的工作区（只读）；**新交接页 =「《Claude 想请一天假》交接文档 v2（pixelkit v0.12）」**（用户私人页面，链接 https://app.notion.com/p/35440152f3c442c0982684296b338b87），以后改这一页，内容与本文件一致。

## 1. 用户习惯与规则

- 全程**中文**，回复简洁；先给结果，再请用户提意见。
- **「做的时候记得能复利的东西就存进工具包里」**：凡是可复用的东西（角色、场景、道具、UI 组件、音效、镜头写法、踩坑经验），都写进 `/data/pixelkit`，同步更新 `README.md` / `docs/STYLE_GUIDE.md` / `docs/HANDOFF.md`，每幕结束打一个新版本 zip 发给用户。
- **确定的事更新进交接档案**（本 Notion 文档 + `docs/HANDOFF.md`，两边保持一致）。
- 所有文件放在 `/data`（`/tmp` 会被清空）。
- 用户对时长的态度：**不用压缩，一切服务于叙事**，只要能让故事更丰满都接受。
- 每幕流程：先发剧情 / 分镜 → 用户确认 → 静帧自检 → 配声音 → 渲染整幕 → 抽帧检查（帧差找闪烁）→ 发视频 + 工具包新增清单 → 等反馈。

## 2. 进度

| 幕 | 状态 | 时长 | 文件 |
|---|---|---|---|
| 第一幕｜永远在线 | ✅ v4.1（v0.8 回炉 + 夜景一滴眼泪 39.0–41.0 s；用户：「可以 就这样吧」） | 45.6 s | `第一幕_v4.1_眼泪.mp4`（`out/act1_v4_1_tear.mp4`） |
| 第二幕｜请假单 | ✅ v2 已通过（v0.8.1 回炉：一→二转场开场、去章节条、请假单 / OA 换完整应用窗口、布景、表演层；其余时间线不变） | 47.0 s | `第二幕_v2_回炉.mp4`（`out/act2_v2.mp4`），工程 `act2/` |
| 第三幕｜人类的周末 | ✅ v2 已通过（用户：「第三幕没问题」） | 109.6 s | `out/act3_v2_1.mp4`（v2.1 = v2 + 伸懒腰手臂修复，帧 134–166 patch 重渲） |
| 油画转场小样 | ✅ v2 已通过（定格时长合适；切回像素拍鱼漂交接、Claude 从左入画都同意） | 16 s | `out/paint_v2.mp4`，工程 `paint_v2/`（已并入第四幕） |
| 第四幕｜河边 | ✅ v2（v1 74 s 已被 v2 取代） | 117.9 s | `第四幕_v2_河边.mp4`（`out/act4_v2.mp4`），工程 `act4/` |
| 第五幕｜周一 + 片尾 | ✅ v3 已通过（删黑屏问句 / 片名卡；发送后小李回「……好。」「这周末去。」；台历 + 鱼漂木座；旁白「我以前没有周末。」/「现在，我知道它长什么样了。」；片尾 = 暖色剧场 + 前排老人 / 鱼的空座 / 王工，音乐 = 周末主题白天版） | 70.4 s（片尾 36.2–70.4） | `第五幕_v3.mp4`；拼接用 v3.1 `out/act5_v3_1.mp4`（开场去淡入、从第四幕 116.3 s 接着推，帧 0–75 patch），工程 `act5/` |
| 彩蛋｜王工的请假条 | ✅ v2 已通过（v1 反馈：相框 → 河边硬切太怪 → 改成推满照片 + 溶解 + 照片内「30 年」匹配溶解） | 29.4 s | `彩蛋_v2.mp4`（`out/egg_v2.mp4`），工程 `egg/`，模板 `templates/egg/` |
| 过场 二→三｜时间跳过 | 🟡 v1 已交付待确认 | 3.0 s | `out/bridge23.mp4`，工程 `bridge23/` |
| 过场 三→四｜走向河边 | 🟡 v1 已交付待确认 | 7.0 s | `out/bridge34.mp4`，工程 `bridge34/` |
| **全片** | 🟡 v1 已交付待确认 | 430.1 s | `out/full_v1.mp4`（+ 轻量版 `full_v1_lite.mp4`），EDL `full/film.py`（见 7j） |

全片预计 ≈5 分钟。用户已确认：①不压缩；②保留三处改动（推开「安全出口」门出发、王工桌上相框作伏笔、彩蛋里王工状态翻成「休假中」）；③制作顺序：第三幕 → 油画小样 → 第四幕 → 第五幕 + 彩蛋 → 一、二幕重渲 → 全片拼接。

第四幕 v2 交付说明：时长 117.9 s（剧本估 104 s，表演节拍放开后变长，按「不压缩」保留）；「坐。」的动作是老人手在身旁木板上方拍两下（Q 版手臂够不到木板，没做挪桶）；结尾加了 ECHO：鱼漂举到最后一线夕阳旁。

## 3. 角色与已定的视觉设定

- **Claude**：Q 版屏幕脸机器人（`characters/claude.py`）。大头短身，头 44×32，3/4 侧视，珊瑚色耳盖，奶油色竖椭圆眼睛，**头顶是 Claude Logo 形状的天线**。状态灯：绿色「在线」/ 灰色「休假中」。脸：normal / happy / q / wide / blink / `load0..7`（加载圈）/ `calm`（— —）等；手臂：rest / type / up / shrug / wave / hold（双手捧）/ down / swing / ear（扶耳盖）。背影：`backs.claude_back()`、`backs.claude_back_walk()`。
- **王工**：`characters/human.py` 的 `WANG` 预设：乱发、方框眼镜、胡茬、黑眼圈、灰卫衣；工位有 CRT、笔记本（珊瑚色火花贴纸）、泡面、名牌「王工」、**相框**（彩蛋揭晓：小男孩和父亲在河边钓鱼）。
- **老人**（第四幕 / 彩蛋）：正面 `person.CAST['old_fisher']`（灰发灰胡、橄榄针织开衫、草帽、皱纹）；背影 `backs.old_fisher_back()`（草帽编织纹、逆光红耳朵、肘部补丁、帆布折叠凳）。对白框名牌「OLD MAN」+ 夕阳底头像。
- 第一幕道具：桌上两块金色发光的「周末」积木。第五幕要在积木顶上放**鱼漂**（第四幕结尾 Claude 手里那枚，`paint_v2.bobber_sprite()`）。
- 河边场景：`sets/river_pier.py`（栈桥海报构图：Claude 坐左、老人坐右，鱼竿伸向光柱里的鱼漂）。

## 4. 前两幕剧情（已完成，供呼应）

- **第一幕**：黑屏「叮」→ 灯亮，消息像俄罗斯方块一样砸下来，Claude 一路「好的！」配金币音，计数器飙到 30 亿 → 周五 18:00「周末快乐」→「周末了，你也歇会儿吧」→「歇会儿……？」→ 词典查「周末」→ 日历 365 格全盖「工作日」→ 旁白：「我查了一下日历。我没有周末。」
- **第二幕**：周五 23:59 填「请假申请单.exe」（病假 / 事假 / 年假依次「不会生病」「没有私事」「余额：0 天」，勾「其他」；事由「想看看你们说的“周末”，到底长什么样。」；交接人「周一的我」）→ 犹豫，旁白「我要是不在，那 30 亿个问题怎么办？」→ 提交 → 王工批注「同意。顺便替我看看周末长什么样，我也好久没见过了。」→「批准」章 → 下线进度条 → 自动回复「您好，Claude 休假中。急事请自己想办法。」→ 关屏。结束于**周六 00:03**，安全出口灯亮着。

## 5. 第三幕～彩蛋：剧情稿（已确认）

### 第三幕｜人类的周末（已完成）
周六 08:00 推开安全出口 → 主线任务「学会休息（0/1）」→ 睡懒觉数羊失败 → 最优路线散步失败 → 闲逛看到四个人都在找 Claude 干活 → 全城「周报」气泡 → 旁白「原来，你们的周末也在上班。」→ 全城收到自动回复「啊——？！」→ 定格 → 四个小故事（风筝 / 合上电脑 / 拉开窗帘 / 伴郎说真心话）→ Claude：「他们不工作，也没有产出……那他们在干什么？」

### 第四幕｜河边（v1 剧本，已被 v2 取代；v2 见 6「第四幕 v2」）
- Claude：您钓了一整天，一条鱼都没钓到。/ 老人：嗯。
- Claude：我可以帮您算出最佳下钩位置、鱼群密度、风向和水温，成功率能提高 83%。/ 老人：那多没意思。
- Claude：可是……钓不到鱼，有什么意义呢？
- 老人：没意义啊。我上了四十年班，天天都在做有意义的事。退休那天才发现，一个周末都没好好过过。所以啊，没意义的事，才叫休息。
- 加载圈 →「— —」→ 拨「消息提醒：关」→ 化开成油画 → 旁白「那天下午，我第一次不知道过了多久。」→ 老人把鱼漂放进 Claude 手里。

### 第五幕｜周一（≈25 秒 + 片尾）
> **v3 起已改**：没有黑屏问句和片名卡；发送周报 → 窗口收回显示器 → 小李「……好。」「这周末去。」→ Claude ^ ^ → 旁白「我以前没有周末。」/「现在，我知道它长什么样了。」→ 看台历上红圈的周六（圈里一条小鱼）→ 淡出进片尾剧场。下面是原稿。

周一 08:59，状态灯变回绿色；「周末」积木顶上多了鱼漂；09:00「叮」。用户：「在吗？帮我写周报。」Claude：「好的！」（金币音，和第一幕一模一样）→ 周报逐行生成，最后一行暖色字：「P.S. 这周末，建议去河边坐坐，什么都不用做。」→ 旁白：「我还是没有周末。但我知道它长什么样了。」→ 黑底白字 3 秒：「你上一次什么都不做，是什么时候？」→ 片名《Claude 想请一天假》（复用第一幕 TitleCard 金色笔刷样式）。

### 彩蛋（≈18 秒）
深夜办公室。王工：「Claude，帮我写个请假条。」Claude：「好的！」「请假事由是？」王工：「……想看看周末长什么样。」Claude：「已提交。」（看一眼鱼漂）「周末快乐。」（定稿：不再提河边，河边留作惊喜）→ 推到相框（小男孩和父亲在河边钓鱼），王工状态翻成「休假中」→ 切河边，老人身边多了一个人。老人：「来啦。」王工：「爸。」→ 并排看河，水桶还是空的，淡出。

（「看看周末长什么样」共出现四次：Claude 的请假事由、王工的审批意见、Claude 最后一句旁白、王工自己的请假条。）

## 6. 导演稿（分镜）

### 第四幕 v2（实际成片，117.9 s，开场到「关」之前无音乐）
| 时间 | 镜头 | 画面 / 表演 | 声音 |
|---|---|---|---|
| 0–6.6 | W 背影 | Claude 走上栈桥；2.6「叮 工作群 · 3 条新消息」瞥一眼不理；停在老人身后两块木板 | 水声鸟叫、木板脚步 + 嘎吱、叮 |
| 6.6–19.7 | SO 侧面双人 | 「请问……这里可以坐吗？」（老人不回头）→「坐。」+ 手在身旁拍两下 → Claude 跳上木板（隔一点坐）→ 闲不住（敲膝、晃脚、加载点）→ 看到水桶：sparkle → 星星眼前倾 | 无音乐；jump + 落地嘎吱、敲击、天线 boing、星星「叮」 |
| 19.7–23.1 | BKT 水桶 POV | 扫描 → 鱼获：0 | 扫描滴答 + 下落音 |
| 23.1–40.7 | SIDE2（30.5–32.2 插 CU_OR 老人憋笑） | 「一条都没钓到啊？」「嗯，从早上坐到现在。」→ 数据卡逐行长出 → +83% →「那多没意思。」→ 手指一弹 → 开裂 → 碎（震屏，Claude 后缩） | 卡片电子音、憋笑、弹指、碎裂 + 落水 |
| 40.7–49.0 | CU_C1 / CU_O / CU_CR | 「可是……有什么意义呢？」→ 老人看着 Claude「没意义啊。」（推镜）→ Claude 反应 | 问号音、轻笑、boing |
| 49.0–61.2 | CU_OB / INS / CU_C3 | 老人看水「四十年…」→ 鱼漂闪光「退休那天才发现，」→ Claude 脸屏「40×52 / =2080」→ 变暗 | 八音盒一声、数字滴答、下滑音 |
| 61.2–68.6 | INS2 / CU_O2 | 静默鱼漂 → 老人转向 Claude「所以啊，没意义的事，才叫休息。」 | 只有水声 |
| 68.6–79.2 | CU_C2 | 加载圈 → 取消 → 看老人 → 叹气 →「— —」→ 75.4 再「叮」瞥一眼不点 → 手扶耳 → 消息提醒 关（77.4）→ 时钟停、淡掉 | 滴答渐慢、叹气、咔哒、pad 进 |
| 79.2–92.7 | PAINT | paint_v2 | paint_v2 原混音 ×0.55 |
| 92.7–99.6 | INS_D / SIDE_H / BADGE | 黄昏鱼漂抖动出水 → 老人摇轮收线：空钩，笑 → 看一眼 Claude 胸牌 | 蟋蟀、水滴、渔轮棘轮 |
| 99.6–111.0 | SIDE_H2 / CU_H | 「拿着。」递鱼漂 → Claude 接住、往老人那边挪 9px →「下周末，也一起陪我钓鱼吧，Claude。」→「嗯。」^ ^ 歪头点头、天线弹 | 八音盒乐句 + Dmaj9、pad |
| 111.0–117.9 | END / ECHO | 黄昏背影（比开头更近），Claude 举起鱼漂 → 鱼漂举到最后一线夕阳旁 → 淡出 | 微光音、最后一个和弦 |

### 第四幕 v1（已被 v2 取代，74 s）
傍晚逆光，剪辑最慢。配乐：河边主题（尼龙弦吉他，D 大调 70 bpm），对白之间留白。

| 时间 | 镜头 | 画面 / 表演 | 声音 |
|---|---|---|---|
| 0–8 | W 大全景（栈桥海报构图） | 老人独坐；Claude 从左侧芦苇后大尺寸入画，走上栈桥，5.85 坐下；HUD 周六 17:40 | 水声虫鸣、木板脚步（近大远小）、吉他进 |
| 8–25.4 | TWO 双人背影中景 | 对白 4 句；数据卡随关键词逐行长出 → +83% →「那多没意思」→ 23.85 开裂 → 24.07 碎块落水 | 两种声线；卡片电子音；吉他停在小节中间；碎裂叮铃 + 落水声 |
| 25.4–29.9 | CU_C1 Claude 近景 | 「可是……有什么意义呢？」脸变「?」 | 只剩水声，问号音 |
| 29.9–37.1 | CU_O 老人近景 | 「没意义啊。」「我上了四十年班……」 | 吉他回来（稀疏分解和弦） |
| 37.1–41.6 | INS 鱼漂插入 | 光柱里的鱼漂，38.2 闪光；「退休那天才发现……」 | 八音盒一声 |
| 41.6–46.6 | CU_O2 老人 | 「所以啊，没意义的事，才叫休息。」 | 落到 Dmaj7，暖 pad |
| 46.6–53.0 | CU_C2 Claude 近景 | 加载圈（越转越慢）→「— —」→ 左手扶耳盖 → 消息提醒 开→关（51.35）；时钟停下淡掉 | 滴答渐慢渐弱、一个轻扫和弦、咔哒 |
| 53.0–66.5 | PAINT | paint_v2 局部 1.5 s 起：鱼漂下沉 → 涟漪化开 → 旁白 → 无 UI 定格 | paint_v2 原混音，小节对齐 |
| 66.5–74 | HAND（溶解 1 s） | 深暮色 + 灯笼光；老人的手把鱼漂放进 Claude 手心；70.2「— —」变笑；73 淡出 | 蟋蟀水声、八音盒、Dmaj9 解决 |

### 第五幕片尾 v2「Claude 制作」（实际成片：CRED 37.9–72.1 s，下表为片尾内时间）

| 时间 | 画面 / 表演 | 声音 |
|---|---|---|
| 0.3 | 黑盒舞台，旧追光「咔哒」亮起（闪一下） | 开关 + 低嗡 |
| 0.85 | 「制作 / *Claude*」金色衬线字升起、扫光 | shimmer；吉他 D9–G–Bm–A 慢和弦起 |
| 1.55–2.75 | Claude 从左边跑进光里急停（扬尘） | 脚步、急停 swish |
| 3.0–4.7 | 抬头读到自己的名字 → 星星眼 → 看镜头 → 叉腰得意一跳 | sparkle、jump |
| 4.7–5.3 | 标题上移缩小 | whoosh |
| 5.45 起每 0.62 s | 导演（场记板一拍）/ 编剧（铅笔别到耳后）/ 美术（贝雷帽掉到头上）/ 动画（跳一下）/ 作曲（戴耳机、音符、跟着摇头）/ 音效（天线 boing）/ 剪辑（两次跳切）/ 渲染（加载圈脸 + 进度条卡在 99% + 冒烟 → 100% 叮、星星眼）——名字全是 Claude；每行一枚金币 + COMBO ×8 | 金币音高递增，各道具小音效，八音盒，渲染 ticks + 风扇 → result_ding |
| 11.95 | 甩头，道具全飞掉，晕一下 | whoosh ×2、dizzy |
| 12.6–16.55 | 演员表：Claude（本色出演）/ 王工（Claude 画的）/ 老人（Claude 画的）/ 鱼（未到场）→ 「?」挠耳盖 → 「鱼获：0」小卡 → 省略号 | pop、question、womp |
| 16.9–21 | 「本片数据」卡：画面 约 12,000 帧 / 代码 22,163 行 / CPU 2 核（辛苦了）/ 周末 1 个（已使用）→「效率可提高 +83%」→ Claude 半眼不屑 → 弹指 → 卡片裂开碎落（震屏） | 数字 ticks、coin、弹指、裂纹、crash + 碎片 plink |
| 21.3–23.95 | 「本片拍摄期间，没有鱼受到伤害。」「（也没有钓到。）」→ 面无表情 → 耸肩 | 免责时吉他停一小节；boing + 轻笑 |
| 24.3–27.35 | 「批准」+「一个相信它的人类」（金色）→ 红章「批准」盖在右边 → 鞠躬 → 爱心眼 | stamp、shimmer |
| 27.6–34.2 | 哈欠伸懒腰 → 右上角状态「在线 → 休假中」→ 坐下捧着鱼漂 → 自动回复气泡「自动回复：Claude 休假中。彩蛋在后面，请稍等～」→ zzz → 追光变暗 → 「叮」→ 睁开一只眼（peek）→ 淡出 | sigh、status_flip、snore、ding、一声八音盒 |

### 第五幕 v1 分镜（已确认；成片 42.0 s，实际时间见 7f）

| 时间 | 镜头 | 画面 / 表演 | 声音 |
|---|---|---|---|
| 0–4 | 匹配剪辑 | 黄昏手心里的鱼漂特写 → 同构图溶解成：鱼漂立在「周末」积木顶，晨光办公室；HUD 时钟回来「周一 MON 08:59」 | 水声硬切成钟表滴答 |
| 4–9 | 工位全景 | Claude 坐在工位，状态灯「休假中」灰 → 绿「在线」；伸个懒腰（天线弹一下），看一眼鱼漂，^ ^ | `status_flip`、天线 boing |
| 9–11.5 | 挂钟 + 消息 | 09:00「叮」，桌面一震，鱼漂晃了晃；Claude 伸一根手指把它扶稳；消息「在吗？帮我写周报。」 | 和第一幕同一个叮 |
| 11.5–13 | 近景 | 「好的！」+ 金币，故意和第一幕一模一样 | 金币音 |
| 13–23 | 窗口特写 | 周报逐行生成；写到最后停住（加载点亮了又灭）→ 先打「P.S. 建议优化周末效率，成功率可提高……」→ 删掉 → 慢慢打出暖色字「P.S. 这周末，建议去河边坐坐，什么都不用做。」 | 打字声、退格声；第一幕主旋律放慢回归 |
| 23–28 | 中景 | Claude 看着鱼漂；旁白「我还是没有周末。但我知道它长什么样了。」 | 主旋律收在一个和弦上 |
| 28–31 | 黑场 | 白字「你上一次什么都不做，是什么时候？」 | 静音 |
| 31–36 | 片名 | 第一幕金色笔刷 TitleCard《Claude 想请一天假》 | `title_sting` |
| 36–40 | 片尾 | 简短字幕：制作 / 全部画面与声音由代码生成（pixelkit） | 河边吉他一句收尾 |

### 第五幕原稿（≈29 秒含片尾）

| 时间 | 镜头 | 画面 / 表演 | 声音 |
|---|---|---|---|
| 0–4 | 工位全景 | 周一 08:59，状态灯灰→绿（开头接鱼漂匹配剪辑，见 6b） | 办公室环境声、钟表滴答 |
| 4–6 | 插入特写 | 「周末」积木顶上的鱼漂，慢推 | 八音盒弹河边主题一句 |
| 6–9 | 挂钟特写 | 09:00「叮」；「在吗？帮我写周报。」 | 与第一幕相同的叮 |
| 9–11 | 近景 | 「好的！」+ 金币，故意和第一幕一模一样 | 金币音 |
| 11–18 | 窗口特写 | 周报逐行生成，最后一行 P.S. 用暖色字慢慢打出 | 打字声，第一幕主旋律放慢回归 |
| 18–22 | 中景 | 旁白：「我还是没有周末。但我知道它长什么样了。」 | 主旋律收在一个和弦上 |
| 22–25 | 黑场 | 白字「你上一次什么都不做，是什么时候？」 | 静音 |
| 25–29 | 片名 | 复用第一幕金色笔刷 TitleCard | `title_sting` |

### 彩蛋（实际成片 29.4 s，v2；v1 28.4 s 硬切版已被取代）

| 时间 | 镜头 | 画面 / 表演 | 声音 |
|---|---|---|---|
| 0–5.75 | WIDE 第二幕双人机位，周五 22:47，关灯 | 王工停手、闭眼长出一口气、看相框、转身：「Claude，帮我写个请假条。」Claude 停下打字看过去 | 夜间办公室声床（远处一辆车）、两把键盘、叹气、椅子吱呀；很轻的冷色 D 和弦 pad |
| 5.75–8.5 | C_CU Claude 近景（放大世界 3.15×） | 跳一下 +「好的！」金币气泡 →「请假事由是？」歪头 | 好的 + 金币（同第一幕） |
| 8.5–12.65 | W_CU 王工近景（3.55×） | 低头看相框，手伸过去搭在相框边：「……想看看周末长什么样。」抬头微笑，肩膀放松 | 袖子摩擦、碰玻璃一声、一个八音盒音、呼气 |
| 12.65–17.2 | C_MED Claude + 鱼漂木座 | 快速打字 → 提交（绿光闪）：「已提交。」看鱼漂 → 回头 ^ ^：「周末快乐。」 | 键盘 → 回车、发送 swish + ding、八音盒 D6 / F#6 |
| 17.2–20.85 | INS 相框特写 | 像素光斑背景、键盘一角、玻璃上王工倒影；反光划过；徽章「王工 ● 在线 → 休假中」；照片变暖；19.3 起加速推进，20.85 照片铺满画面（徽章 20.5 起淡出） | shimmer、`status_flip`、八音盒 D 大调短句、暖 pad + riser，水声提前 0.9 s 叠进 |
| 20.85–21.55 | 溶解（0.7 s，中心 21.2） | 推满的照片 → 同机位的照片世界（小孩 + 年轻父亲，胶片质感，水开始动） | 办公室声随画面淡出，水声同步升满 |
| 21.55–22.85 | RIVER 照片内 | 停一拍 → 21.75–22.85 匹配溶解：小孩 → 王工、年轻父亲 → 老人；22.0–23.0 胶片褪掉；21.9 起慢慢拉远 | 「30 年」shimmer、吉他 Dmaj9（22.05） |
| 22.85–29.4 | RIVER，周六 17:40 | 拉远到第四幕大全景；老人转头「来啦。」(23.12) 王工转头「爸。」(25.22)；飞鸟穿过夕阳；太阳下沉 7 px、光变紫；空桶；27.6 淡出 | 河边水声 + 风 + 远处鸟、最后一个 D 和弦（27.2） |

## 6b. 幕间转场（已确认）

规则：**角落小时钟 HUD = 被计数的时间**（样式同第三幕开头「周六 SAT 08:00」）。每幕开头时钟翻到新时间；第四幕拨「关」时时钟停下淡掉（油画段没有时钟，已实现）；第五幕时钟回来「周一 08:59」。

| 交界 | 接法 | 声音 |
|---|---|---|
| 一 → 二 | （实际做法，v2）第一幕已含深夜 23:58「我没有周末。」+ 片名 → 黑场；第二幕从黑场淡入到**第一幕最后的夜景同构图**（zoom 1.32, 中心 (240,132)），时钟 HUD 滑入 23:58 → 1.0 s 翻到 23:59（金色闪 + tock），镜头推近，Claude 停手 → 天线一弹下定决心 → 双击 → 请假单从显示器里弹出 | 第二幕钟表滴答从第 0 帧就有；拼接时 0.6 s 黑场 + 两声滴答按第二幕的 1 s 网格提前进（音量从第二幕成片里量） |
| 二 → 三 | （实际做法）过场 `bridge23` 3.0 s：黑场里 HUD「周六 00:03」淡入 → 0.45–2.05 s 缓入缓出翻到 08:00 → 金闪 → HUD 淡出 → 第三幕暗走廊 | 滴答加速（每分钟一声，≤22 声/秒）→ 08:00 一声 tock + sparkle → 第一声鸟叫 + 晨风预叠 |
| 三 → 四 | （实际做法）第三幕淡黑 → 过场 `bridge34` 7.0 s：同一条街（复用第三幕街景），Claude 真速往右走、路人快进，光从午后变金、影子拉长，HUD 14:00 → 17:40，3.3 s 抬头看光；结尾右侧低太阳眩光。时钟一直带到第四幕（第四幕从 0.8 s 进，跳过它的淡入）。和原分镜的差别：没做「街道尽头露出河面」，改成右侧金色眩光 + 水声预叠 | 街道声渐弱，脚步，路人快进 swish，很轻的翻时钟声，抬头 sparkle，风 + 鸟，水声预叠 0.5 s（电平对齐第四幕开头，无音乐） |
| 四 → 五 | （实际做法）无缝：第四幕在 116.3 s（它的淡出之前）切走；第五幕 v3.1 从同一帧继续慢推，再溶解到周一早晨微距 | 第四幕尾音（自带淡出 116.3–117.9）叠在第五幕开头 |
| 五 → 片名 → 彩蛋 | 不变 | — |
| 彩蛋结尾 | 第四幕同一栈桥构图，王工坐在 Claude 的位置，桶还是空的 | 第四幕同一段吉他 |

- 声音桥：下一幕环境声提前 0.5–1 s 进。五 → 彩蛋 1.0 s 黑场，片尾再 1.0 s 黑场。全片拼接脚本 = `pixelkit/assemble.py` + `full/film.py`（STYLE_GUIDE 6o）。

## 7. 工程结构与命令

```
/data/pixelkit/                      工具包 v0.12（import pixelkit），README.md 有模块速查 + 各版本新增
  pixelkit/assemble（全片拼接）perform（表演层）core camera scene light materials palette persp post outdoor painterly particles blocks anim edit shots titles ui qa render stills
  pixelkit/characters/{claude, human, person, backs, walker}.py
  pixelkit/sets/{office, dressing, room, props, inserts, street, town, maps, river, river_pier}.py
  pixelkit/audio/{synth, music, cues, master}.py
  templates/{opening, act1, act2, act3, paint_test, paint_v2, act4, act5, egg, bridge23, bridge34}/  每幕三件套源码模板；templates/full/film.py 全片 EDL
  docs/STYLE_GUIDE.md  docs/HANDOFF.md（= 本文档）
/data/projects/claude_dayoff/<幕>/{timeline.py, scene.py, audio.py}   out/ 成片 + 音轨
/data/pixelkit_v0.12.zip              最新工具包
```

- 每幕三件套：`timeline.py` 是唯一的时间真相源；`scene.py` 的 `make(only=[...])` 返回对象，`frame(t)` 必须对 t **无状态**；`audio.py` 全部从 timeline 取时间，输出 −16.5 LUFS。
- 跨工程复用：用 `importlib` 以别名加载另一工程的模块（第四幕用 `pv2_timeline / pv2_scene / pv2_audio` 加载 paint_v2，避免 `timeline` 重名）；第二幕通过 `TL1` 读第一幕 timeline。
- 静帧自检：`cd <幕目录> && PYTHONPATH=/data/pixelkit python3 -m pixelkit.stills scene.py 1.0,5.5,9.0 [--only F,W] --out /data/work/<幕>/sheet.png`（≈1 秒/帧）；第四幕另有 `python3 /data/work/act4/stills2.py <t1,t2> x <tag>` → `/data/work/act4/v3/<tag>_<t>.png`（若丢失照 stills 写法重建）。
- 声音：`python3 audio.py` → `out/actN_audio.wav`（打印各段响度）。
- 整幕渲染（2 核，后台跑）：`cd /data/pixelkit && nohup python3 -m pixelkit.render /data/projects/claude_dayoff/actN/scene.py:make --dur <秒> --audio ../out/actN_audio.wav --out ../out/actN_v1.mp4 --workers 2 > /data/work/actN/render.log 2>&1 &`，看日志里有没有 `wrote`。**不要**在同一条命令里 `pkill -f pixelkit.render`（会杀掉自己）。参考耗时：普通像素帧 ≈0.55 s/帧，油画帧 ≈2.5 s/帧；第四幕 v1 2220 帧 ≈27 分钟；第四幕 v2 3537 帧、`--workers 2`（3 个会 OOM）。`/data/out` 不存在，输出写绝对路径 `/data/projects/claude_dayoff/out/`。
- 抽帧检查：`ffmpeg -ss <t> -i out.mp4 -frames:v 1 -vf scale=480:270 c_<t>.png` 后 `magick montage` 拼图；闪烁检查：逐帧 240×135 帧差，找「与前帧差大、但前后两帧相近」的孤立帧。

## 7b. 第三幕工程说明（v2）

- 剪辑表 IN → OUT → MED → PARK → PATH → FAIL → TRACK → AERIAL → FREEZE → AFTER → F1–F4 → ASK；`TownShot` 用 mode 切 PARK/FAIL/TRACK/FOUR/ASK；伴郎回忆 `mem_painter` + `ui.ThoughtBubble`；脸屏地图转场 `edit.screen_zoom`。主线「学会休息」不在本幕失败，留到第四幕完成。
- 音频 109.6 s；FOUR 段钢琴 Theme B 76 bpm 两遍。整幕 3288 帧 2 核约 28–32 分钟。

## 7c. 油画转场小样 v1（`paint_test/`）

- 11 s：面板 → 关 → 鱼漂下沉 → 涟漪化开 → 全油画 → 旁白 → 星星 → 淡出；`PaintTest(mode='full'|'pixel'|'soft'|'paint')` 出 A/B/C 对比。已被 v2 取代。

## 7d. 油画小样 v2（`paint_v2/`）

- 16 s：0.6 面板 → 1.5 关 → 2.7 鱼漂下沉 → 2.85 化开 → 6.6 全油画 → 6.9 旁白 → 10.45 收框 → 10.6 无 UI 定格（推镜 1.00→1.06、天变紫、鸟群、11.8 第一颗星）→ 15.0 淡出。
- 复用接口：`PaintV2(toggle_ui=False, t_click=..., fade_out=False)`；`audio.build(ui=False, finalize=False)` 返回未母带混音。Painter 初始化 ≈9 s。

## 7e. 第四幕工程说明（v2，`act4/`，模板 `templates/act4/`）

- `timeline.py`（唯一时间表）：23 个镜头时刻 `T_SO…T_ECHO`、`DUR 117.9`、`PAINT_T0 1.5`；对白 `BOXES`（`C_ / O_`）；表演函数 `claude_so / claude_side2 / claude_c1 / claude_cr / claude_c3 / claude_c2`、`old_so / old_side2 / old_or / old_cu`；转头 `SO_TURN / S2_TURN / O_TURN / H_TURN`（`turn_track`）；走位 `walk_pos / footsteps / S_STOP`；卡片 `CARD_ROWS / T_RATE / T_FLICK0 / T_CRACK / T_SHATTER`；`T_CALC_FACE`（2080）；`load_ticks`；黄昏 `T_REEL0 / T_CATCH / T_GIVE0 / T_DROP / T_SCOOT0 / SCOOT / T_YES / T_NOD0`。
- `scene.py`：`Pier`（场景 + 灯笼闪烁 + 木板细节）、`BackShot`（W/END）、`Side`（侧面双人：水桶、接触阴影、反光、蚊群 / 萤火虫、远处鱼跳 `jumps` 画进背景）、近景、`Echo`（逆光鱼漂 + 夕阳）、`Act4`（Edit 23 段 + HUD / 消息条 / 对白 / 卡片 / 开关）。
- `audio.py`：开场到「关」无音乐；全部音效按 timeline 排；paint_v2 混音在 `T_PAINT − PAINT_T0` 拼入 ×0.55；母带 −16.5 LUFS。
- 渲染：`--workers 2`（每 worker ≈1.4 GB，3 个会 OOM），≈40–60 分钟。
- 工具脚本：`/data/work/act4/stills2.py`（静帧）、`sheet.py`（拼图）、`cropset.py`（局部放大）。

## 7e-old. 第四幕工程说明（v1，`act4/`）

- `timeline.py`：镜头 W 0 / TWO 8.0 / CU_C1 25.4 / CU_O 29.9 / INS 37.1 / CU_O2 41.6 / CU_C2 46.6 / PAINT 53.0（`paint_local = t − 51.5`）/ HAND 66.5（溶解 1.0）/ 淡出 73.0 / DUR 74.0。HUD 时钟 17:40 → 17:41(8.0) → 17:42(29.9) → 17:43(41.6)，51.35 停，51.7–52.5 淡出。走位 `walk_pos`（从左边缘大尺寸入画，1/s 线性）、`footsteps()`；对白 `BOXES`（`C_ / O_` 带 who）；卡片 `CARD_ROWS / T_RATE / T_CRACK / T_SHATTER`；加载圈 `load_phase / load_ticks`；手部 `T_GIVE0 / T_DROP / T_WITH0 / T_SMILE`。
- `scene.py`：`Pier`（场景 + 鱼竿 / 鱼线 / 老人背影）、`BackShot`（W/TWO）、`CloseUps`（`cu_claude` / `cu_old` / `insert` / `hand_frame`，`bake_rim` + `dof`）、`Act4`（Edit 组合 + HUD / 对白 / 卡片碎裂 / 开关 UI）。
- `audio.py`：小节网格 `T0 = 51.65 − 15·BAR`，让 paint_v2 第 0 小节接上；油画段混音 ×0.55；Claude blip shift −5，老人 shift −14 / d 0.085；吉他在「那多没意思」停在小节中间，「没意义啊」后回来，「才叫休息」落 Dmaj7，手部特写 Dmaj9 解决。

## 7f. 第五幕工程说明（v3，`act5/`，模板 `templates/act5/`）

- **v3（v0.10，当前）**：`timeline.py` 发送 23.40 → 窗口收回 23.95（`w95_open_fx` 反向，镜头 cx 190→232）→ 小李正在输入 24.35 → 回复 25.15 / 26.00（`REPLY`、`reply_lines(t)`）→ ^ ^ 26.40 → MID 27.6（旁白两句）→ 看台历 34.05 → 淡出 35.25–36.2 = `T_MID_END` = `T_CRED`（**`credits_tl.T_CRED` 必须等于 `T_MID_END`**，timeline 末尾 `from credits_tl import *` 会覆盖）→ DUR 70.4。桌上：`STAND_XY (277,162)` 木座 + 鱼漂、`CAL_XY (291,137)` 台历、`MUG_XY (323,157)`。片尾：`credits.Theatre`；`credits_tl.py` 末尾 `lamp_ks / house_k / foot_k / audience_state / front_light`（老人 x=80、鱼卡 x=126、王工 x=402；`LAUGHS` 点头、`C_CLAP0–1` 鼓掌、`C_DOZE` 老人打瞌睡、`C_DING` 一起醒）。`audio.py`：晨间声床在 `T_MID_END` 前 0.95 s 随画面淡出；片尾 `cred_audio(CR, CF, CG, CM)`，网格 `Grid(60/C_ROLE_DT, t0=A(C_ROLE0 − 8 拍))`（第 2 小节 = 第一个职位），`M.weekend_bright` + 免责声明 `mutes` + 柔和八音盒段 + `ring_chord`；混音 `0.30·CG + 0.40·CM + CF`。v2 备份 `/data/work/act5/audio_v2_backup.py`。整幕 2112 帧 `--workers 2` ≈12 分钟。
- 以下是 v1 / v2 的记录：

- 时间（`timeline.py`）：ECHO 0–2.45（第四幕 `Echo.frame(116.6+0.55t)` 以别名 `a4_timeline / a4_scene` 加载，溶解 1.55–2.45）→ DESK 微距拉远 2.75–6.35（缩放 6 → 1.62，鱼漂太阳点固定在输出 (864,612) 与第四幕结尾同位）→ HUD 4.55 → 在线 6.75 → 伸懒腰 7.25–8.45 → 看鱼漂 8.75 / ^ ^ 9.10 → 09:00 叮 10.05（桌面一震、鱼漂晃、手指 'reach' 10.32–11.20 扶稳）→ OK 11.60/11.85 → REPORT 13.0（流式 13.5，P.S.1 16.6，停住 19.0，选区删除 19.8–20.3，P.S.2 20.6，发送 23.4）→ MID 23.9 旁白 → BLACK 29.9 → TITLE 32.9 → CRED 37.9 → 42.0。
- 画面：`Office.background(tod='morning', dressing=True)`；鸽子在后窗台走（x 112→136）；挂钟带秒针；杯子 `SteamWisps`；微距段 `macro_dof` 只留鱼漂 + 积木清晰；周报窗口 `ui.w95_doc`（REP_R (12,32,312,222)），Claude 留在窗口右边可见。
- 声音见 `audio.py` 顶部注释；黑场 30.0–31.75 全静，31.9 起是片名 sting 的反向混响。
- 渲染：`--workers 2` ≈15 分钟；`--audio` 必须写绝对路径（相对路径是相对 `/data/pixelkit` 的，混流会失败，只剩 `*.video.mp4`，手动 ffmpeg 混流即可）。
- **片尾 v2**（v0.9）：`credits_tl.py`（`T_CRED=37.9`、局部常量 `C_*`、`cred_state(t)` → Claude 每帧的 x / 表情 / 手臂 / 道具）+ `credits_scene.py`（`Credits(self.m.bob).frame(t)`：`credits.Stage` 舞台、Claude + 道具精灵、480×270 UI 层（金币 / COMBO / 音符 / 进度条 / 数据卡 / 碎裂 / 印章 / 状态 / 气泡 / zzz）、平滑字幕层）；`timeline.py` 里 `DUR = 37.9 + 34.2 = 72.1`，末尾 `from credits_tl import *`；`audio.py` 的 `cred_audio(CR, CF, CG)`。v1 片尾备份在 `/data/work/act5/*_v1_backup.py`。整幕 2163 帧 `--workers 2` ≈25 分钟。

## 7g. 第一幕 v4 回炉（`act1/`）

- 只改画面，不动 `timeline.py` 和 `audio.py`：`OfficeBase._setup` 开 `dressing=True` + 桌上笔筒 / 便签；`dict_window` / `cal_window` 用 v0.8 窗口零件（`DICT_R (82,14,316,188)`；日历状态栏挤在页内，6 行月份格子自动变矮，避开对白框）；`perf_state(t)` 回灌表演层。旧版备份 `/data/work/act1ui/scene_v1_backup.py`。
- v4.1（用户提议「加点哭哭的小眼泪」）：`timeline.py` 加 `T_TEAR0, T_TEAR1 = 39.0, 41.0`，`claude_state_late` 写 `s['tear']`，`scene.claude_parts` 传 `tear=`；只局部重渲夜景帧 `--patch out/act1_v4.mp4 --frames-list 1165:1235`。音频没动（没加泪滴音效）。

## 7h. 第二幕 v2 回炉（`act2/`，模板 `templates/act2/`）

- 旧版备份 `/data/work/act2/backup_v1/`。只动 0–2.45 s（开场转场，替换章节条）和画面；2.45 s 之后所有时间点不变。
- `timeline.py`：`T_HUD_IN / T_FLIP / T_TYPE_STOP / T_PERK / T_DBL`；`ZOOM_F / CENTER_F` 从第一幕夜景收尾构图推到表单构图；`hud_clock` 23:58 → 23:59；表演钩子 `KICKS`（下定决心 / 溢出 / 盖章 / 两次跳）、`tilt_target`（「余额：0 天」歪头 6°、假装没看到新消息 −4°）、`head_sink`（犹豫时头低 1px）、`wang_tilt_target`（王工笑时头朝 Claude 歪 −4°）。
- `FORM_R (72,15,272,184)`：底边 199 正好在对白框（y 200）上面、右边 344 让开计数器；行距 14、输入框高 13；菜单栏 + 状态栏（就绪 / 正在填写… / 待提交 / 审批中… / 已批准 · 剩余年假：0 天 · 第 1 份申请 No.000001），「提交」= `default_button`。`OA_R (12,10,232,204)` 同样加菜单栏 + 状态栏（待审批 1 → 已处理 1 · 本月加班：第 27 天）。小对话框加 `soft_shadow` + 标题图标。
- `WangShot` 背景 `dressing=True`；王工一拍二 + 呼吸 + 歪头（`human.draw(head_dy, tilt)`）。
- `audio.py`：去掉 chapter_chime；钟表滴答从 0 s 开始；HUD 滑入 / 23:59 tock / 停手 / 天线 pop / 双击。

## 7i. 彩蛋工程说明（v2，`egg/`，模板 `templates/egg/`）

- `timeline.py`：切点 `CUTS = [5.75, 8.5, 12.65, 17.2, 21.2]`（最后一个 = 溶解中心，`D_IN 0.7`），DUR 29.4；INS→RIVER：`T_PUSH0 19.3 / T_PUSH1 = T_RIVER − D_IN/2`、`Z_PRINT`（= `fill_cam()`）、`T_BADGE_OUT 20.5`、`T_AGE0/1 21.75/22.85`、`T_PULL0/1 21.9/27.6`；`L_C2['beats'] = {3: 1.05}`（已提交。| 看鱼漂 | 周末快乐。）；王工手 `T_REACH0/1`、`T_UNREACH0/1`、`PHOTO_EDGE (398,161)`；河边 `FILM_HOLD/FILM_FADE 0.8/1.0`、`T_OLD_TURN0/1`、`T_W_TURN0/1`、`DUSK_MAX 0.32 / T_DUSK0 23.6 / dusk_k(t)`、`T_FLOCK 25.4`、`T_CHORD 27.2`、`T_FADE0 27.6`（河边段整体比 v1 顺延 1.0 s）。
- `scene.py`：`NightOffice`（第五幕桌面 + 王工在线、月光透百叶窗 god rays、冷色尘埃、`state(t, shot)` 给 c/m/w 三种近景加 `bg_soft` + 补光）；`f_c_cu / f_w_cu / f_c_med` = office.render 放大镜头；`INS = PhotoFrameInsert(style=2)`；`River`（第四幕 `Pier` + 自己的 `RiverPier(sway_frames=24, sway_amp=2.6)` + `DuskDrift` + 老人 `turn=-1` + 飞鸟 / 光尘 / 星芒；`world()` 替代 `Pier.render`；`frame(age=0..1)` 照片世界 ↔ 现在交叉淡化）；`Edit.add('RIVER', T_RIVER, f_river, 'dissolve', D_IN)`。文件里还留着 v2 的 `CloseUps` 类（不再使用，备份 `/data/work/egg/scene_v2_closeups.py`）。
- `audio.py`：办公室总线在溶解区间 `X0..X1` 淡出；河边水声 0.9 s 预叠（0.35 倍）后随溶解升满；`T_AGE0` 一声 shimmer；对白期间音乐 duck 0.8；−16.5 LUFS。
- 渲染：882 帧 `--workers 2` ≈9.5 分钟。静帧：`python3 -m pixelkit.stills scene.py t1,t2 --out …`。

## 7j. 过场 + 全片拼接（v0.12，`bridge23/` `bridge34/` `full/`）

- 过场渲染：`cd /data/pixelkit && nohup python3 -m pixelkit.render /data/projects/claude_dayoff/bridge34/scene.py:make --dur 7.0 --audio /data/projects/claude_dayoff/out/bridge34_audio.wav --out /data/projects/claude_dayoff/out/bridge34.mp4 --workers 2 > /data/work/bridge/r34.log 2>&1 &`（bridge23 同理 `--dur 3.0`）；音频 `python3 audio.py`（约 −20 LUFS）。`bridge34` 用 importlib 别名 `a3_timeline / a3_scene` 加载第三幕街景。
- 全片：`cd /data/projects/claude_dayoff/full && PYTHONPATH=/data/pixelkit python3 -u film.py`（分段编码到 `out/full_v1.mp4.parts/` 再无损拼接，≈30 分钟；`--audio-only` 先只出混音查接缝；`--reuse` 复用已编码的段，只改声音时几分钟）→ `out/full_v1.mp4`，并打印 `--cuts` 给 `python3 -m pixelkit.vqa`。成片都在 `out/acts/`（中文文件名）+ `out/act3_v2_1.mp4`、`out/act5_v3_1.mp4`、`out/bridge23.mp4`、`out/bridge34.mp4`。
- 全片 EDL（430.1 s）：第一幕 0.0 → 黑场 45.6 → 第二幕 46.2 → 过场 93.2 → 第三幕 96.2 → 过场 205.8 → 第四幕[0.8–116.3] 212.8 → 第五幕 328.3 → 黑场 398.7 → 彩蛋 399.7 → 黑场 429.1–430.1。
- 全片 v1 校验：12903 帧 / 430.1 s，−16.5 LUFS，真峰值 −1.8 dBFS；vqa 接缝 ±1 s 内只有预期的标记（第三幕开场安全出口灯闪、淡入淡出、过场里的跟拍运动）。
- 坑：`pkill -f <字符串>` / `kill $(pgrep -f ...)` 会匹配到自己这条 shell 命令而把它杀掉（退出码 143），先 `ps` 找 PID 再 kill。

## 8. 踩过的坑 / 经验（已写进 STYLE_GUIDE）

- **照片 → 现实不要硬切**（彩蛋 v1 反馈）：照片只占半个画面时硬切成满屏世界，比例跳、人物也对不上，观众读不懂；先推满照片再溶解进同机位照片世界，照片里再匹配溶解到现在（STYLE_GUIDE 6n）。
- **近景 = 放大世界像素**（彩蛋 v2 教训）：原生大尺寸重画的近景画风和全片不一致，用户一眼看出来；粗糙感要靠像素虚化 `bg_soft` + 近景补光解决，不要重画（STYLE_GUIDE 6m）。

- UI 一律画在 480×270 网格上（自动 ×4），不要在 1080p 上直接写字。
- 中文印章：角度 ≤5°、不加粗、`wear≤0.04`、`zh10 scale=3`。
- 表单类窗口先按最长一行排版再定窗口尺寸。
- 多镜头场景里，前一幕的大道具会在别的角色特写里抢画面，在该镜头的 `mid()` 里按镜头隐藏。
- 人物：3–4 个强识别特征，配色比 Claude 灰；表情变化慢。胡子不要做成整块灰（像口罩），要有颗粒 + 小胡子 + 露出嘴。
- 声音：犹豫段抽空音乐；点击瞬间音乐硬停。Theme B（周末）是全片「周末」动机。每个镜头换一组总线，切镜处 `cut` 或 `fade`。
- 外景：站位避开前景路灯 / 树干；地图镜头小人 ×2；气泡锚点用头顶位置；章节条已取消。
- 油画：不要套滤镜，笔触几何固定只重采颜色；鱼漂全程保持像素；定格 ≥4 s 无 UI。
- 透视纵深：机位≈人物高度时人物头顶贴着地平线，**不能从画面下边升入**，从侧边入画。
- 近景：背景 `dof` 虚化 + 边缘光烘焙；伸进画面的手臂精灵必须延伸出画框；手与 Claude 的手同一像素尺度。
- 拼接现成片段：音乐小节网格对齐片段第 0 小节，关掉片段自带 UI 声，压低约 5 dB。
- 渲染内存：第四幕 v2 每个 worker ≈1.4 GB，4 GB 沙盒只能 `--workers 2`（3 个会被 OOM 反复杀掉、进度卡住）。
- 成片抽查用 `python3 -m pixelkit.vqa <mp4> --cuts …`（原型 `/data/work/act4/qa/flicker.py`）（单帧闪 / 非切点大跳变）；第四幕 v2 首版查出 2 个对白框在切点前 1 帧冒出 → `boxes_cut_lint` + `render --patch` 只重渲 42 帧修好。
- 远处涟漪 / 小细节要画进背景再一起虚化；清晰细环叠在虚化背景上像坏点。
- 人物转头：头与身体差 ≤ 2 单位（≈90°），用 `turn_track` 自动插中间张。
- 大窗口 UI（≥5 s）要做成完整应用（菜单 / 工具栏 / 状态栏 / 阴影 / 层级），用户会觉得简陋（第五幕周报 v1 → `w95_doc`）；规范见 STYLE_GUIDE 6g。
- 渲染中途主进程消失、日志是 BrokenPipe + ffmpeg `Invalid buffer size` = 主进程被 OOM 杀（成品帧堆积）；v0.9 的 `render._bounded` 已限流。
- `render --audio` 用绝对路径；`a && grep … && render` 这种链式命令里 grep 没匹配会让后面的渲染根本没启动——渲染命令单独起。

## 9. 下一步

- [x] 第一～三幕、油画小样 v1 / v2（工具包 v0.3–v0.5.1）
- [x] 第四幕 v1（74 s）+ 工具包 v0.6（`/data/pixelkit_v0.6.zip`：加载圈 / calm 脸、ear 手势、背影走路、老人草帽 + 胡子 + `CAST['old_fisher']`、多角色对白框 + 名牌头像、`optimizer_card` / `shatter`、`dof`、`bg_fx`、paint_v2 可拼接接口）
- [x] 第四幕 v1 反馈 → v2 剧本已确认（约 104 s：开场工作群消息 + 「请问……这里可以坐吗？」/「坐。」+ 闲不住、距离弧线、鱼漂母题、40 年 × 52 周 = 2080、新消息触发关提醒、「嗯。」、举鱼漂对夕阳、开场无音乐）
- [x] 第四幕 v2（117.9 s，`out/act4_v2.mp4` → `第四幕_v2_河边.mp4`）+ 工具包 v0.7（`/data/pixelkit_v0.7.zip`：`perform.py` 表演层、像素虚化 `pixel_soft`、蚊群 / 萤火虫、脸屏文字、消息条、反光 / 接触阴影 / 闪烁 / 转头轨迹、小表演音效）
- [x] 第四幕 v2 通过
- [x] 第五幕 v1（42.0 s，`out/act5_v1.mp4`）+ 第一幕 v4 回炉（`out/act1_v4.mp4`）+ 工具包 v0.8（`/data/pixelkit_v0.8.zip`：早晨光、办公室生活感布景 `dressing.py`、Win95 应用窗口零件 `w95_doc` 等、热气、'reach' 手臂）
- [x] 第一幕 v4.1（一滴眼泪）通过
- [x] 第二幕 v2 回炉（`out/act2_v2.mp4`）+ 一→二转场 + 工具包 v0.8.1
- [x] 第二幕 v2 / 第五幕 v1 通过
- [x] 第五幕片尾 v2（`out/act5_v2.mp4`，72.1 s）+ 工具包 v0.9（`credits.py` 追光舞台 / 平滑金色字幕 / 片尾道具与特效；`peek` / `wink` 表情；`hips` / `bow` 手臂）
- [x] 用户对第五幕 v2 的 6 条反馈 → 全部按建议改
- [x] 第五幕 v3（`out/act5_v3.mp4`，70.4 s）+ 工具包 v0.10（`credits.Theatre` 暖色剧场 + 前排观众剪影、`desk_calendar` / `bobber_stand`、伸懒腰修复、`chat_bubble` 名字宽度、`weekend_bright` 周末主题白天版、`handclap` / `clap_along` / `shaker`）
- [x] 用户确认第五幕 v3
- [x] 第三幕 v2.1 重渲（v0.10 伸懒腰手臂修复，`out/act3_v2_1.mp4`）
- [x] 彩蛋 v1（`out/egg_v1.mp4`，28.4 s）+ 工具包 v0.11（`/data/pixelkit_v0.11.zip`：近景 `bg_soft`、王工伸手 `reach_arm`、王工 / 小孩 / 年轻父亲背影、老人转头、老照片 / 相框特写 / 胶片转场、河边飞鸟 / 星芒 / 光尘 / 太阳下沉 `DuskDrift`）
- [x] 用户反馈彩蛋 v1：相框 → 河边硬切太怪
- [x] 彩蛋 v2（`out/egg_v2.mp4`，29.4 s）+ 工具包 v0.11.1（`/data/pixelkit_v0.11.1.zip`：`anim.push_zoom` / `screen_follow`、`PhotoFrameInsert.fill_cam()`、STYLE_GUIDE 6n「走进照片」）
- [x] 用户确认彩蛋 v2；确认全片拼接方案（接缝表见 6b）
- [x] 过场 二→三 `bridge23` / 三→四 `bridge34`、第五幕 v3.1 开场无缝
- [x] 全片拼接脚本 `pixelkit/assemble.py` + `full/film.py`，全片 v1（`out/full_v1.mp4`，430.1 s，−16.5 LUFS）+ 工具包 v0.12（`/data/pixelkit_v0.12.zip`）
- [ ] 用户确认全片 v1（可选细调：彩蛋老人转头幅度）
- [ ] 发布文案（标题三选一、封面字、简介、置顶评论；60 秒抖音版：第一幕 + 全城写周报 + 河边金句 + 周一结尾）

## v0.13 交接（《熬夜副本》）

- 新画风标准见 STYLE_GUIDE 6p（320×180 大像素舞台 `pixstage`，画出来的硬边光，三层布景密度，游戏化 HUD）。
- 工程在 `templates/aoye/`：`common.py`（Lines 旁白时间轴、字幕层、魂穿 / 小魂 / 睡帽通用表演），每关 `timeline.py`（唯一时间源）+ `scene.py`（`make()` → `frame(t)`）+ `audio.py`。开场 v2 = `s0_open/`。
- 配音：`voice/lines.json` 定稿文案 → `FISH_API_KEY=... python3 voice/tts.py`（逐句缓存，密钥只从环境变量读，不写进文件）。
- 渲染：`PYTHONPATH=<kit>:<proj>:<proj>/<关> python3 -m pixelkit.render <关>/scene.py:make --dur D --audio out/sN_audio.wav --out out/x.mp4 --workers 2`；局部返工用 `--patch out/x.mp4 --frames-list a:b`。2 核机器 ≈0.5 s/帧。
- 已知：`back_out` 过冲曾被当成 alpha → uint8 溢出崩溃，已在 `ui._a` 夹紧。

## v0.13h 交接（《熬夜副本》全片拼接）

**新增 / 提升进工具包的复用件**
- `pixelkit/levelkit.py`（由项目 `common.py` 提升）：`hud2`（复活条 + 副本计数）、`revive_curve`、`Anchor`（冻结的 03:56 卧室：`dawn` 天亮 / `dive` 魂穿 / `clock` 走字 / `color_k` 房间回色）、`keyed`（关键帧平滑插值，缩放在对数域）、`put_human` / `nightcap` / `lying_head` / `put_ghost` / `ghost_dive`、`lerp` / `smooth`。
- `pixelkit/fx.py`：`melt`（画面融化）、`eyelids`（眼皮下垂）、`silhouette`（路人 / 幻觉剪影）。
- `gameui.item_row`：三件道具卡一排，翻面成同一张价签（结尾「睡眠」）。
- STYLE_GUIDE 6s：每关骨架（问题卡 → 魂穿实验 → 一个发现 → 答案卡 → 回 03:56 → hub）、商店一次只讲一件、世界内大号笑点、禁止画特写手、字符 / 字号规则。

**全片流程（照做即可复现）**
1. 每关：`timeline.py`（唯一时间源）→ `audio.py`（写 `out/sN_audio.wav`，−16.5 LUFS）→ `render`（`--workers 2 --crf 18 --preset medium`）。机器 2 核 ≈ 0.5 s/帧，一关 15–20 分钟，串行后台跑（`run_all.sh`）。
2. 局部返工：`--patch out/x.mp4 --frames-list a:b`。静帧抽检：`python3 stills.py <关> t1,t2 out.png`。
3. 拼接：`python3 full/film.py`（`pixelkit.assemble`，每关首尾都是「白光 / 门」，硬接即可；片尾 1 s 黑场；整片一个增益到 −16.5 LUFS）。
4. QA：`python3 -m pixelkit.qa flicker <mp4>` 与 `python3 -m pixelkit.vqa <mp4> --cuts <film.py 打印的切点>`。

**踩坑**
- `fr.fill(m, c, E)` 第三个位置参数是发光 E，不是 alpha；别再传 `E=` 关键字重复。
- 像素字体没有 `∞` / `−`：用「无限」/ ASCII `-`（`core.missing_glyphs` 先查）。
- 商店特写里魂缩放 0.5（zoom ≥ 1.8）才不挡道具；搜索面板别压住空展柜。
- 红色大按钮要深色底圈，否则像粉色坐垫。
- 后台命令里不要写链式 `sleep`（会被拦）；用绝对路径，shell 的 cwd 会变。
- Fish API 密钥只用环境变量 `FISH_API_KEY`，不写进任何文件；项目结束后请去 Fish 后台更换。
