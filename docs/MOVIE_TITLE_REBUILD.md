# 章节影片原生标题重建

## 已验证

- 16个`MOVIES/CHAPTERnn.AVI.REFORMATTED.AVI.IVF`均为400×240、VP90、30/1帧率、90帧。不是428×240外层PNG。
- 每章全部90帧均离线解码并逐帧hash绑定；16×90=1440帧均通过标题处理，首尾RGB全黑。
- 半秒加密审计发现AMANDA01/INTRO开头嵌入章名：配置现涵盖18部电影、总2192帧。AMANDA01共339帧，0..88为章3，89..338共250帧剧情原样透传；INTRO共413帧，0..89为章1，90..412共323帧透传。573剧情帧全部RGB字节相等且返回空allowed rectangles。
- AMANDA01开头90帧中88帧与独立章3原RGB完全相同，88/89处过渡不相同；单独复开88仍为极暗章名，89已为暗场景起始，故89不作文字擦除。INTRO前90帧与独立章1原RGB完全相同。没有依据文件名盲假定相等。
- 中文章号/副标题逐字复用`image-text.json`对应章节，使用同身份Fusion12px字体；不复用PNG坐标。
- 头行原英文字区横坐标按native帧45的高亮红字独立确定，纵区103..116；副标题原英文字区按实际白字确定，纵区120..135。确切矩形保存在每章recipe。
- 删除区域采用逐行掩码，红装饰像素独立逐行保护；全部改动均限制在allowed_regions。中文副标题宽度与装饰分离，原红装饰不会因较长英文副标题矩形被整块涂黑。
- 每帧分别测量原章号与副标题English笔画的平均红通道亮度，除以原帧45参考亮度，控制中文颜色；不凭帧号构造固定淡入淡出曲线。
- 独立章名首尾黑场不增添字样。嵌入章名的后段剧情mode=unchanged在核验源RGB身份后返回副本与空区域，不运行文字擦除。每帧原始RGB SHA不匹配、未知mode、字库身份不符、缺字、溢出、区域越界和装饰变化均报错。

## API与复现

`tools/build_movie_titles.py`提供`rewrite_titles(original_RGB, recipe, fontpath, frame_index) -> (edited_RGB, allowed_rectangles)`。源IVF由上层电影构建器验证完整SHA并解码，函数再次验证每帧SHA。`verify_movies`可全量离线验证。编码后IVF/DAT同步由独立电影构建器完成，此模块不调整时间轴。

```powershell
python -m unittest discover -s tests -p test_build_movie_titles.py -q
python -X utf8 tools/build_movie_titles.py --archive 'C:\Program Files (x86)\Steam\steamapps\common\Dementium - The Ward\rom.zar'
```

字面输出：`Ran 14 tests`/`OK`；`MOVIE TITLES PASS movies=18 standalone-chapters=16 frames=2192 source=unchanged ornaments=unchanged outside-regions=unchanged`。均退出0。

原生预览和逐帧验证报告位于忽略目录`build/full-research/movie-titles-verified/`；原始及生成整帧不提交。提交内容为翻译recipe、坐标/像素散列、保护掩码及代码。

## 验证边界

以上是源帧及离线生成帧验证，不是启动游戏后的播放验收。影片重新编码与DAT同步须在上层构建流程另行验证；播放器实际显示/转场仍须用户手工检查。新闻画面词属于另一个画面词译注方案，不在本章名替换模块内。
