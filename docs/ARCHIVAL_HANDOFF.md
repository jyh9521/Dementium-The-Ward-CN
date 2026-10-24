# 项目归档交接（2026-10-24）

## 冻结内容

- 最终源码包含第十五章“初次相遇”、白底绿字“出口”、“有胆你就来！”与汽水机“汽水／泡泡”四处修正，详情见 RELEASE_FOUR_FIXES.md。
- 安装器版本保持 v1.0，SHA256 `5bd98a3d21403bada448ef154fcda22914f12b98cb9294b802d8d4aa5c505939`，78,497,853 字节。
- 已查询 GitHub v1.0 Release：公开安装器的 digest、大小与本地最终文件一致；不重复上传、不移动既有标签。
- 归档前重新运行 `python -B -X utf8 build/release-four-fixes/run_tests.py`：271 tests，OK，退出0。此入口只在内存中将5处测试原件路径指向SHA锁定副本，不改Steam安装、不启动游戏。

## GitHub 与 NAS 的分工

GitHub保存工具、译文、美术差分、测试和技术文档。完整原版输入、完整资源、生成构建、研究中间件及本地规范不提交GitHub。

本地NAS交接目录位于仓库同级：`../Dementium-The-Ward-CN-archive-20261024/`。

- `Dementium-The-Ward-CN-local-only-20261024.zip`：打包时全部Git未跟踪文件，保留仓库相对路径；包含后来提交的少量新源码，属于冗余保底。
- `MANIFEST.json` / ZIP内 `ARCHIVE-MANIFEST.json`：逐文件大小与SHA256。
- 同名 `.zip.sha256`：整个ZIP的SHA256。
- `repository.bundle`：全部本地Git引用，供离线恢复源码历史。
- `MODIFIED_FILE.json` / `DIFF_FILE.json` / `VERIFICATION.txt`：清理结果、删除清单、实际执行证据。
- `restore_archive.py` / `ROLLBACK.sh`：在全新目标目录恢复清单中的已清理文件，拒绝覆盖已有目标。

## 本地保留与清理

打包后逐成员解压读取并核对SHA256/CRC，独立副本恢复测试通过后，才清理已归档的历史build子目录和Python字节码。最新修改产物保持不动。

保留：`build/four-fixes-release`（最新样本与证据）、`build/release-four-fixes`（SHA锁定原版输入及上一安装器）、`build/installer`（安装器载荷/恢复证据）、`dist`（最终安装器）。另保留测试直接引用的少量旧版EXE、字库与电影层差分fixture，避免清理导致原生回归被静默跳过。历史文档中其他build路径须先从ZIP还原，不再假定仍在工作目录。

恢复完整工程：从GitHub克隆或由bundle克隆源码，将ZIP解压到工程根目录（不要把ZIP内清单当作源码）。仅恢复清理文件可运行交接目录的恢复脚本，先恢复到独立目录再按需拷回。

归档不代表新的游戏内验收；此次未启动游戏，也未更改Steam文件。NAS复制由用户完成，复制后请再核对ZIP SHA256。

