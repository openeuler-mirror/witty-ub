/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
 * witty-ub is licensed under the Mulan PSL v2.
 * You can use this software according to the terms and conditions of the Mulan PSL v2.
 * You may obtain a copy of Mulan PSL v2 at:
 *     http://license.coscl.org.cn/MulanPSL2/
 * THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY OR FIT FOR A PARTICULAR
 * PURPOSE.
 * See the Mulan PSL v2 for more details.
 */

// B3 B 级：view_visualizer 库——资源文件三级候选路径读取、HTML 模板占位符替换。
// 输入/输出硬编码 /var/witty-ub（测试环境不存在且不可写）：
// LoadView/WriteHtml/Start 只能覆盖失败分支；成功路径经 BuildHtml/ReadResourceFile
// 使用工作目录相对资源（data/view-vis）与仓库源码目录回退资源覆盖。

#include <gtest/gtest.h>

#include <unistd.h>

#include <filesystem>
#include <fstream>
#include <string>

#include <json/json.h>

#include "logger.h"
#include "temp_dir.h"

// 访问 ViewVisualizer 私有方法（本仓库既有测试模式）
#define private public
#include "view_visualizer.h"
#undef private

namespace {
// 打日志的库必须先初始化 log4cplus，否则 SEGFAULT
struct LoggerInit {
    LoggerInit() noexcept { rack::logger::init(nullptr); }
};
static LoggerInit g_loggerInit;

// RAII 临时目录（公共实现见 temp_dir.h）

// 完整模板：包含全部三个占位符
constexpr const char *FULL_PLACEHOLDER_TEMPLATE =
    "<head>__LOG_VIEW_CSS__</head><body>__LOG_VIEW_DATA__<b>__LOG_VIEW_JS__</b></body>";

// script 场景模板：数据占位符位于 script 标签内（验证 "</" 转义）
constexpr const char *SCRIPT_PLACEHOLDER_TEMPLATE =
    "<style>__LOG_VIEW_CSS__</style><script>__LOG_VIEW_DATA__</script><b>__LOG_VIEW_JS__</b>";

// RAII：用例内切换 cwd（ReadResourceFile 的第一候选为相对工作目录路径），析构还原
class ScopedChdir {
public:
    explicit ScopedChdir(const std::filesystem::path &target)
    {
        char buf[4096] = {0};
        if (getcwd(buf, sizeof(buf)) != nullptr) {
            origin_ = buf;
        }
        (void)chdir(target.c_str());
    }
    ~ScopedChdir()
    {
        if (!origin_.empty()) {
            (void)chdir(origin_.c_str());
        }
    }

private:
    std::string origin_;
};

// 在 cwd 的 data/view-vis/ 下写一个资源文件
void WriteCwdResource(const std::string &name, const std::string &content)
{
    std::filesystem::create_directories("data/view-vis");
    std::ofstream out("data/view-vis/" + name, std::ios::trunc);
    out << content;
}

// 构造合法的视图 JSON（callstack_views 为数组）
Json::Value MakeViewJson(const std::string &nodeName = "node-a")
{
    Json::Value root;
    Json::Value view;
    view["name"] = nodeName;
    root["callstack_views"].append(view);
    return root;
}
} // namespace

// fixture：临时目录作为工作目录（cwd 相对资源可控），独立 visualizer 实例
class ViewVisualizerTest : public ::testing::Test {
protected:
    void SetUp() override
    {
        chdir_.emplace(dir.Path());
    }
    void TearDown() override { chdir_.reset(); }

    TempDir dir;
    std::optional<ScopedChdir> chdir_;
    view_visualizer::ViewVisualizer vis;
};

// 生命周期：Initialize 恒成功；Stop/UnInitialize 空实现可安全调用
TEST(ViewVisualizerLifecycle, InitializeAndShutdownAreSafe)
{
    view_visualizer::ViewVisualizer vis;
    EXPECT_EQ(vis.Initialize(), RACK_OK);
    vis.Stop();
    vis.UnInitialize();
    SUCCEED();
}

// Start：输入 /var/witty-ub/log-view.json 不存在（测试环境无该目录）→ RACK_FAIL
TEST(ViewVisualizerLifecycle, StartFailsWhenInputMissing)
{
    view_visualizer::ViewVisualizer vis;
    ASSERT_EQ(vis.Initialize(), RACK_OK);
    // 资源齐全与否不影响：LoadView 先失败
    EXPECT_EQ(vis.Start(), RACK_FAIL);
}

// ---------------------------------------------------------------------------
// ReadResourceFile：三级候选路径
// ---------------------------------------------------------------------------
// 不存在的资源名：三个候选全部 miss → RACK_FAIL
TEST_F(ViewVisualizerTest, ReadResourceMissingFileFails)
{
    std::string content;
    EXPECT_EQ(vis.ReadResourceFile("no_such_resource.bin", content), RACK_FAIL);
}

// cwd 相对路径 data/view-vis 优先于源码目录回退资源
TEST_F(ViewVisualizerTest, ReadResourcePrefersCwdRelativePath)
{
    // 不创建 cwd 资源也能读到仓库内置模板（回退路径生效）
    std::string fromSource;
    ASSERT_EQ(vis.ReadResourceFile("log_view.html", fromSource), RACK_OK);
    EXPECT_NE(fromSource.find("__LOG_VIEW_DATA__"), std::string::npos);

    // 再放置 cwd 版本：内容优先于仓库版本
    WriteCwdResource("log_view.html", "CWD_TEMPLATE_MARK");
    std::string content;
    EXPECT_EQ(vis.ReadResourceFile("log_view.html", content), RACK_OK);
    EXPECT_EQ(content, "CWD_TEMPLATE_MARK");
}

// ---------------------------------------------------------------------------
// BuildHtml：模板占位符替换与转义
// ---------------------------------------------------------------------------
// 完整模板：数据/CSS/JS 三占位符全部替换，JSON 以两空格缩进嵌入
TEST_F(ViewVisualizerTest, BuildHtmlReplacesAllPlaceholders)
{
    WriteCwdResource("log_view.html", FULL_PLACEHOLDER_TEMPLATE);
    WriteCwdResource("log_view.css", "CSS_MARKER_123{}");
    WriteCwdResource("log_view.js", "JS_MARKER_456();");

    const std::string html = vis.BuildHtml(MakeViewJson("fn-x"));
    EXPECT_NE(html, "");
    EXPECT_EQ(html.find("__LOG_VIEW"), std::string::npos); // 占位符全部被替换
    EXPECT_NE(html.find("CSS_MARKER_123{}"), std::string::npos);
    EXPECT_NE(html.find("JS_MARKER_456();"), std::string::npos);
    // JSON 数据：两空格缩进 + 键值内容（jsoncpp 冒号两侧带空格）
    EXPECT_NE(html.find("\"name\" : \"fn-x\""), std::string::npos);
    EXPECT_NE(html.find("\"callstack_views\""), std::string::npos);
}

// JSON 中的 "</" 被转义为 "<\"，防止提前闭合 script 标签
TEST_F(ViewVisualizerTest, BuildHtmlEscapesClosingScriptTag)
{
    // 模板须含全部三个占位符（缺任何一个都会在对应检查处返回空串）
    WriteCwdResource("log_view.html", SCRIPT_PLACEHOLDER_TEMPLATE);
    WriteCwdResource("log_view.css", "c");
    WriteCwdResource("log_view.js", "j");

    Json::Value root = MakeViewJson();
    root["callstack_views"][0]["payload"] = "</script><b>evil";

    const std::string html = vis.BuildHtml(root);
    EXPECT_NE(html, "");
    // "</script>" -> "<\/script>"（仅 "</" 处插入反斜杠）
    EXPECT_NE(html.find("<\\/script><b>evil"), std::string::npos);
    // 原始未转义序列不应出现在数据中（模板自身的 </script> 标签保留）
    EXPECT_EQ(html.find("\"></script><b>evil"), std::string::npos);
}

// 模板缺少数据占位符 → 空串
TEST_F(ViewVisualizerTest, BuildHtmlMissingDataPlaceholderReturnsEmpty)
{
    WriteCwdResource("log_view.html", "<head>__LOG_VIEW_CSS__</head><body><b>__LOG_VIEW_JS__</b></body>");
    WriteCwdResource("log_view.css", "c");
    WriteCwdResource("log_view.js", "j");
    EXPECT_EQ(vis.BuildHtml(MakeViewJson()), "");
}

// 模板缺少 CSS 占位符 → 空串
TEST_F(ViewVisualizerTest, BuildHtmlMissingCssPlaceholderReturnsEmpty)
{
    WriteCwdResource("log_view.html", "<body>__LOG_VIEW_DATA__<b>__LOG_VIEW_JS__</b></body>");
    WriteCwdResource("log_view.css", "c");
    WriteCwdResource("log_view.js", "j");
    EXPECT_EQ(vis.BuildHtml(MakeViewJson()), "");
}

// 模板缺少 JS 占位符 → 空串
TEST_F(ViewVisualizerTest, BuildHtmlMissingJsPlaceholderReturnsEmpty)
{
    WriteCwdResource("log_view.html", "<head>__LOG_VIEW_CSS__</head>__LOG_VIEW_DATA__");
    WriteCwdResource("log_view.css", "c");
    WriteCwdResource("log_view.js", "j");
    EXPECT_EQ(vis.BuildHtml(MakeViewJson()), "");
}

// 仓库内置真实模板可完整构建（回退路径 + 真实占位符布局）
TEST_F(ViewVisualizerTest, BuildHtmlWithSourceTemplateSucceeds)
{
    // 不写 cwd 资源：三级回退读取仓库 data/view-vis 下的真实模板与资源
    const std::string html = vis.BuildHtml(MakeViewJson("fn-repo"));
    EXPECT_NE(html, "");
    EXPECT_EQ(html.find("__LOG_VIEW_"), std::string::npos);
    EXPECT_NE(html.find("fn-repo"), std::string::npos);
}

// cwd 有模板但故意写一个坏模板（无任何占位符）+ 缺 css：
// 回退源码目录 css/js 存在，但坏模板缺占位符 → 空串（资源回退与占位符检查叠加路径）
TEST_F(ViewVisualizerTest, BuildHtmlBadTemplateWithPartialCwdResources)
{
    WriteCwdResource("log_view.html", "<html>no placeholder here</html>");
    // css/js 走回退路径（仓库内置）
    EXPECT_EQ(vis.BuildHtml(MakeViewJson()), "");
}

// ---------------------------------------------------------------------------
// LoadView / WriteHtml：/var/witty-ub 不可写环境下的失败分支
// ---------------------------------------------------------------------------
// LoadView：/var/witty-ub/log-view.json 打不开 → RACK_FAIL
TEST_F(ViewVisualizerTest, LoadViewFailsWithoutInputFile)
{
    Json::Value root;
    EXPECT_EQ(vis.LoadView(root), RACK_FAIL);
}

// WriteHtml：/var/witty-ub 目录不存在且无权创建 → RACK_FAIL
TEST_F(ViewVisualizerTest, WriteHtmlFailsWithoutWritableVarDir)
{
    EXPECT_EQ(vis.WriteHtml("<html></html>"), RACK_FAIL);
}

// ---------------------------------------------------------------------------
// B5 追加：LoadView / WriteHtml / Start 成功路径（经 .rodata 等长补丁把
// "/var/witty-ub"（13 字符）重定向到 /tmp/witty-b5，上方既有失败分支用例
// 先于补丁执行不受影响）+ ViewVisualizerModule 生命周期（引用类拉入模块 .o）。
// ---------------------------------------------------------------------------
#include <sys/mman.h>

#include <charconv>
#include <cstdint>
#include <cstring>
#include <sstream>
#include <vector>

#include "view_visualizer_module.h"

namespace {
struct PatchRegion {
    uintptr_t start;
    uintptr_t end;
    int prot;
};

// /proc/self/maps 权限段中 r/w/x 字符的位置。
constexpr std::size_t PERM_READ_INDEX = 0;
constexpr std::size_t PERM_WRITE_INDEX = 1;
constexpr std::size_t PERM_EXEC_INDEX = 2;
// 单个映射区大小上限（64MB），超出则跳过，避免误扫巨型映射。
constexpr std::size_t MAX_REGION_BYTES = 64u << 20;
// /proc/self/exe 路径缓冲长度。
constexpr std::size_t PATH_BUFFER_SIZE = 4096;

int ParsePerm(const char *perms)
{
    int prot = 0;
    if (perms[PERM_READ_INDEX] == 'r') {
        prot |= PROT_READ;
    }
    if (perms[PERM_WRITE_INDEX] == 'w') {
        prot |= PROT_WRITE;
    }
    if (perms[PERM_EXEC_INDEX] == 'x') {
        prot |= PROT_EXEC;
    }
    return prot;
}

// 收集自身可执行映像的只读映射区。
std::vector<PatchRegion> CollectSelfExeRegions(const std::string &exe)
{
    std::vector<PatchRegion> regions;
    std::ifstream maps("/proc/self/maps");
    std::string line;
    while (std::getline(maps, line)) {
        std::istringstream row(line);
        std::string range, perms, offset, dev, inode, mapPath;
        row >> range >> perms >> offset >> dev >> inode;
        if (!(row >> mapPath)) {
            continue; // 匿名映射无路径
        }
        const auto dash = range.find('-');
        uintptr_t start = 0;
        uintptr_t end = 0;
        const bool rangeOk = dash != std::string::npos &&
                             std::from_chars(range.data(), range.data() + dash, start, 16).ec == std::errc{} &&
                             std::from_chars(range.data() + dash + 1, range.data() + range.size(), end, 16).ec ==
                                 std::errc{};
        if (!rangeOk || mapPath != exe || perms[PERM_READ_INDEX] != 'r' || end <= start ||
            end - start > MAX_REGION_BYTES) {
            continue;
        }
        regions.push_back({start, end, ParsePerm(perms.c_str())});
    }
    return regions;
}

// 把 pos 起长度 len 的区间所在页改为可写（跨页时两页都改）；返回首页是否改写成功。
bool MakePagesWritable(uintptr_t pos, std::size_t len, std::size_t pageSize)
{
    const uintptr_t firstPage = pos & ~(pageSize - 1);
    const uintptr_t lastPage = (pos + len - 1) & ~(pageSize - 1);
    if (mprotect(reinterpret_cast<void *>(firstPage), pageSize, PROT_READ | PROT_WRITE) != 0) {
        return false;
    }
    if (lastPage != firstPage) {
        mprotect(reinterpret_cast<void *>(lastPage), pageSize, PROT_READ | PROT_WRITE);
    }
    return true;
}

// 恢复覆盖 [pos, pos+len) 的所有映射区原始权限。
void RestorePageProtection(uintptr_t pos, std::size_t len, std::size_t pageSize,
                           const std::vector<PatchRegion> &regions)
{
    const uintptr_t firstPage = pos & ~(pageSize - 1);
    const uintptr_t lastPage = (pos + len - 1) & ~(pageSize - 1);
    for (const auto &r : regions) {
        if (firstPage >= r.start && firstPage < r.end) {
            mprotect(reinterpret_cast<void *>(firstPage), pageSize, r.prot);
        }
        if (lastPage != firstPage && lastPage >= r.start && lastPage < r.end) {
            mprotect(reinterpret_cast<void *>(lastPage), pageSize, r.prot);
        }
    }
}

// 在自身可执行映像的只读映射中把 from 原地替换为 to（等长），返回替换次数。
// 逐页按原始权限恢复，避免波及相邻 rw-p（.data）映射。
int PatchHardcodedString(const std::string &from, const std::string &to)
{
    if (from.size() != to.size() || from.empty()) {
        return 0;
    }
    const std::size_t pageSize = static_cast<std::size_t>(sysconf(_SC_PAGESIZE));
    char exe[PATH_BUFFER_SIZE] = {0};
    if (readlink("/proc/self/exe", exe, sizeof(exe) - 1) <= 0) {
        return 0;
    }
    const std::vector<PatchRegion> regions = CollectSelfExeRegions(exe);
    int patched = 0;
    for (const auto &region : regions) {
        for (uintptr_t pos = region.start; pos + from.size() <= region.end; ++pos) {
            if (memcmp(reinterpret_cast<void *>(pos), from.data(), from.size()) != 0) {
                continue;
            }
            if (!MakePagesWritable(pos, from.size(), pageSize)) {
                break;
            }
            std::copy(to.begin(), to.end(), reinterpret_cast<char *>(pos));
            RestorePageProtection(pos, from.size(), pageSize, regions);
            ++patched;
            pos += from.size() - 1;
        }
    }
    return patched;
}

// 与 /var/witty-ub 等长（13 字符）
constexpr const char *K_PATCHED_ROOT = "/tmp/witty-b5";

void EnsureVarPathPatched()
{
    static bool patched = [] {
        std::filesystem::create_directories(K_PATCHED_ROOT);
        PatchHardcodedString("/var/witty-ub", K_PATCHED_ROOT);
        return true;
    }();
    (void)patched;
}

std::string PatchedInputPath() { return std::string(K_PATCHED_ROOT) + "/log-view.json"; }
std::string PatchedOutputPath() { return std::string(K_PATCHED_ROOT) + "/log-view-vis.html"; }

void WriteInputJson(const std::string &content)
{
    std::ofstream out(PatchedInputPath(), std::ios::trunc);
    out << content;
}
} // namespace

// LoadView：补丁后输入可读，解析成功且结构校验通过
TEST_F(ViewVisualizerTest, LoadViewSucceedsWithRedirectedPath)
{
    EnsureVarPathPatched();
    WriteInputJson(R"({"callstack_views":[{"name":"patched-node"}]})");

    Json::Value root;
    EXPECT_EQ(vis.LoadView(root), RACK_OK);
    ASSERT_TRUE(root["callstack_views"].isArray());
    EXPECT_EQ(root["callstack_views"][0]["name"].asString(), "patched-node");
}

// LoadView：输入存在但 JSON 格式非法 → RACK_FAIL（解析失败分支）
TEST_F(ViewVisualizerTest, LoadViewFailsOnMalformedJson)
{
    EnsureVarPathPatched();
    WriteInputJson(R"({"callstack_views": [)"); // 截断的非法 JSON

    Json::Value root;
    EXPECT_EQ(vis.LoadView(root), RACK_FAIL);
}

// LoadView：JSON 合法但缺 callstack_views 数组 → RACK_FAIL（结构校验分支）
TEST_F(ViewVisualizerTest, LoadViewFailsOnInvalidStructure)
{
    EnsureVarPathPatched();
    WriteInputJson(R"({"something_else": 42})");

    Json::Value root;
    EXPECT_EQ(vis.LoadView(root), RACK_FAIL);
}

// WriteHtml：补丁后输出目录可写，内容完整落盘
TEST_F(ViewVisualizerTest, WriteHtmlSucceedsAfterPathRedirect)
{
    EnsureVarPathPatched();
    ASSERT_EQ(vis.WriteHtml("<html>MARK_BODY</html>"), RACK_OK);
    std::ifstream in(PatchedOutputPath());
    ASSERT_TRUE(in.is_open());
    std::string content((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());
    EXPECT_EQ(content, "<html>MARK_BODY</html>");
}

// WriteHtml：输出路径被同名目录阻挡 → ofstream 打不开 → RACK_FAIL
TEST_F(ViewVisualizerTest, WriteHtmlFailsWhenOutputBlockedByDirectory)
{
    EnsureVarPathPatched();
    std::filesystem::remove_all(PatchedOutputPath()); // 先清掉此前用例落盘的同名文件
    std::filesystem::create_directories(PatchedOutputPath());
    EXPECT_EQ(vis.WriteHtml("<html></html>"), RACK_FAIL);
    std::filesystem::remove_all(PatchedOutputPath()); // 还原，避免影响后续用例
}

// Start 全链路：合法输入 + 仓库回退资源 → 成功生成可视化 HTML
TEST_F(ViewVisualizerTest, StartSucceedsEndToEnd)
{
    EnsureVarPathPatched();
    WriteInputJson(R"({"callstack_views":[{"name":"start-node"}]})");
    std::filesystem::remove_all(PatchedOutputPath());

    ASSERT_EQ(vis.Initialize(), RACK_OK);
    EXPECT_EQ(vis.Start(), RACK_OK);

    std::ifstream in(PatchedOutputPath());
    ASSERT_TRUE(in.is_open());
    std::string content((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());
    EXPECT_NE(content.find("start-node"), std::string::npos);
    EXPECT_EQ(content.find("__LOG_VIEW_"), std::string::npos); // 三个占位符全部替换
}

// Start：LoadView 成功但输出被阻挡 → RACK_FAIL（WriteHtml 失败上抛分支）
TEST_F(ViewVisualizerTest, StartFailsWhenOutputBlocked)
{
    EnsureVarPathPatched();
    WriteInputJson(R"({"callstack_views":[{"name":"blocked-node"}]})");
    std::filesystem::remove_all(PatchedOutputPath()); // 先清掉此前用例落盘的同名文件
    std::filesystem::create_directories(PatchedOutputPath());

    EXPECT_EQ(vis.Start(), RACK_FAIL);
    std::filesystem::remove_all(PatchedOutputPath());
}

// ViewVisualizerModule：Initialize/Start 成功、GetViewVisualizer 非空、Stop/UnInitialize 安全
TEST_F(ViewVisualizerTest, ModuleLifecycleSucceeds)
{
    EnsureVarPathPatched();
    WriteInputJson(R"({"callstack_views":[{"name":"module-node"}]})");
    std::filesystem::remove_all(PatchedOutputPath());

    view_visualizer::ViewVisualizerModule module;
    ASSERT_EQ(module.Initialize(), RACK_OK);
    EXPECT_NE(module.GetViewVisualizer(), nullptr);
    EXPECT_EQ(module.Start(), RACK_OK);

    module.Stop();
    module.UnInitialize();
    EXPECT_TRUE(std::filesystem::exists(PatchedOutputPath()));
}

// ViewVisualizerModule：输入缺失时 Start 失败（模块失败分支）
TEST_F(ViewVisualizerTest, ModuleStartFailsWhenInputMissing)
{
    EnsureVarPathPatched();
    std::filesystem::remove(PatchedInputPath());

    view_visualizer::ViewVisualizerModule module;
    ASSERT_EQ(module.Initialize(), RACK_OK);
    EXPECT_NE(module.Start(), RACK_OK);
    module.Stop();
    module.UnInitialize();
}
