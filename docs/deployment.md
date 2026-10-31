# BioLens 云端部署与使用

## 用户使用

运行项目根目录的 `启动BioLens.cmd`，或目录分发包中的 `release/0.3.0/win-unpacked/BioLens.exe`。整个目录必须保留。注册用户名（3–32 位字母、数字或下划线）和密码（至少 10 字符），之后创建项目、选择本机目录并聊天。模型由云端提供，不需要个人 API Key。用户名不区分大小写。

服务地址：https://biolens.worldlinesite.com 。浏览器可直接注册登录，上传项目资料并在云端生成报告。桌面版继续使用同一账号。

云端保存账号、项目名称和聊天记录；本地保存目录绑定、执行记录、分析数据与报告。另一台电脑登录后可同步聊天，但必须重新绑定那台电脑上的目录；旧报告不会自动下载。开启本地读取后，实际读取的资料片段、分析摘要会经云端进入模型上下文。文件不整批上传，但在聊天中主动输入的敏感内容仍会随聊天保存。

项目启动器数据目录为 `.local/app-data`；直接运行 EXE 使用 `%APPDATA%/biolens`。账号数据库位于数据目录的 `accounts/<账号ID>/biolens.sqlite3`，生成成果位于 `artifacts`。通过客户端“保存”可导出到指定位置。旧版数据保留，未自动迁移到账号。关闭客户端会中断本地任务；桌面版重启需要重新登录，网页版通过安全 Cookie 保持最多七天会话；尚无密码自助找回。

## 服务组件

- Ubuntu 上 Docker 容器 `biolens-cloud`，镜像 `biolens-cloud:0.2.0`。
- 对外 HTTPS 经 Nginx；后端仅绑定 `127.0.0.1:8937`。
- 容器最多 768 MB 内存、1.5 CPU、128 进程，非 root、只读根文件系统。
- `/opt/biolens/build` 为云端构建源码；`/opt/biolens/secrets.env` 为权限 600 的模型凭据配置，不在镜像/客户端里。
- `/var/lib/biolens/cloud.sqlite3` 为账号数据，WAL 模式。单进程服务、五个推理并发槽；同一账号同时一个推理请求。
- Nginx 配置 `/etc/nginx/sites-available/biolens`；TLS 使用 Let's Encrypt，certbot 自动续期。
- 数据库备份 `/var/lib/biolens/backups`，每日服务器时间 04:15 在线快照，保留最近 7 份。备份与服务同机，尚无异地灾备。

## 运维

在项目目录运行 `node scripts/python.mjs deploy/deploy.py` 重新部署（短暂停止本服务，不改其他站点）。部署工具读取父目录服务器凭据文件和本地 settings；不要分发这些文件或 `.local`。`deploy/install_backup.py` 安装备份服务。

服务器检查命令：

```sh
sudo docker ps --filter name=biolens-cloud
sudo docker logs --tail 80 biolens-cloud
curl -fsS https://biolens.worldlinesite.com/health
sudo nginx -t
sudo systemctl status biolens-backup.timer certbot.timer
sudo systemctl start biolens-backup.service
```

恢复前停止容器，并备份当前数据库及其 WAL/SHM 文件到一个新的人工备份目录。将选定快照复制为 `/var/lib/biolens/cloud.sqlite3`，移走旧数据库对应 WAL/SHM（不可与恢复快照混用），设置 owner 为 `10001:10001`，再启动容器并检查 health、登录与项目。恢复是数据回退操作，应先确定快照时间和影响范围。

公网只开放常规 HTTPS/API。客户端注册有频率限制，登录有限速；会话有效期七天，客户端仅在内存保存令牌。当前适合少量用户试用，未实现邮箱验证、管理员面板和自动更新。

## 验证

`npm test` 包含账号隔离、跨设备聊天同步、本地路径不上传、五槽推理并发及备用文献源测试。`scripts/cloud_e2e.py` 用临时账号测试真实模型、外部文献、本地分析及报告；测试账号需通过 `deploy/cleanup_test_users.py` 清理。自动测试不会修改旧用户聊天。

课程 Notebook 是此前的课程实验材料，尚未重新生成以涵盖云端部署。


## 网页版（0.3）

直接访问 https://biolens.worldlinesite.com 。创建项目后点击顶部“项目文件”，上传 CSV/TSV/PDF/MD/TXT，随后开启“项目资料”权限。聊天、外部检索和 HTML/PDF 报告模式与桌面版一致。同名文件不覆盖，需要先删除再上传。单文件最多 100 MB，每项目 100 个文件，每账号上传总量 500 MB。

网页与桌面共用账号、项目名称、聊天。桌面目录不会自动上传；网页资料保存在服务器，桌面版仍需自行绑定本机目录。成果暂不跨执行端同步：网页报告从网页下载，桌面报告从桌面保存。

云端执行器 `biolens-web` 与账号服务 `biolens-cloud` 分开部署，通过私有 Docker 网络 `biolens-net` 通信。前端静态文件位于 `/var/www/biolens`，浏览器 API 为 `/web-api/`，后端只绑定 `127.0.0.1:8938`。原账号接口保留以兼容桌面客户端。

云端数据位于 `/var/lib/biolens-web`：`accounts/<ID>` 是执行记录数据库，`uploads/<ID>/<项目ID>` 是上传资料，`artifacts/<任务ID>` 是成果。模型密钥只在账号服务容器，网页和执行器不持有该密钥。

网页任务每账号最多一个、全局串行排队。关闭或刷新页面不取消任务，重新打开对应聊天即可看到执行记录。停止运行任务会等待当前步骤安全收尾；服务器重启会将未完成任务标记为 interrupted，需要用户重新发起。当前队列是单进程内存队列，不提供服务重启后的断点恢复。

执行器限制 1800 MB 内存、1.5 CPU，使用只读容器根目录和非 root 用户。首次部署需要下载 Linux 分析依赖和 Chromium。中文 PDF 使用 Noto CJK 字体。大数据可能触及内存上限，当前定位为小规模数据探索。

发布：先 `npm run build`，再 `node scripts/python.mjs deploy/deploy_web.py`。重发云端账号服务使用原 `deploy.py`，脚本会保留网页 Nginx 配置和容器网络。无须为前端维护两份页面代码。

既有每日备份服务同时备份网页账号数据库快照、上传资料与成果，目录 `/var/lib/biolens-web/backups`，保留 7 份，同机保存。运行中的报告文件备份可能不完整，恢复后应重新执行未完成任务。恢复时停止网页容器，将选定归档恢复到独立目录检查后再替换，勿将数据库快照与旧 WAL 文件混用。

网页端到端测试：`node scripts/python.mjs scripts/web_e2e.py`；首次创建临时测试账号，后续复用 `.local/web-test-credentials.json`，避免反复注册触发限流。`scripts/web_verify_outputs.py` 可复核上一次测试的报告与跨端聊天，`scripts/web_preview_check.py` 验证内嵌预览。完成后执行 `deploy/cleanup_test_users.py`，只删除记录的测试账号及对应网页工作区，并移除临时登录文件。测试结果见 `artifacts/web-e2e.json`。
