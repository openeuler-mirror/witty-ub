#include "urma_0054_urma_init_repeated_init.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0054UrmaInitRepeatedInit> g_urma("urma_0054");

bool Urma0054UrmaInitRepeatedInit::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"urma_init has been called before."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0054UrmaInitRepeatedInit::GetName() const
{
    return "urma_init 重复初始化";
}

std::string Urma0054UrmaInitRepeatedInit::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `atomic_load(&g_init_flag) > 0`；该路径返回 URMA_EEXIST";
}

RootCause Urma0054UrmaInitRepeatedInit::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0054UrmaInitRepeatedInit::GetFixSuggDesc() const
{
    return "查看/usr/lib64/urma目录下，是否存在liburma_udma.so等驱动文件，或查看文件是否具备x权限，完成正确部署后重试";
}

std::string Urma0054UrmaInitRepeatedInit::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：urma_init has been called before.";
}

std::string Urma0054UrmaInitRepeatedInit::GetId() const
{
    return "urma_0054";
}
} // namespace diag
