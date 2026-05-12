#include "urma_0057_urma_open_drivers_get_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0057UrmaOpenDriversGetFailure> g_urma("urma_0057");

bool Urma0057UrmaOpenDriversGetFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to get dl addr: %"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0057UrmaOpenDriversGetFailure::GetName() const
{
    return "urma_open_drivers 获取动态库地址失败";
}

std::string Urma0057UrmaOpenDriversGetFailure::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `ret == 0`；该路径返回 -1";
}

RootCause Urma0057UrmaOpenDriversGetFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0057UrmaOpenDriversGetFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0057UrmaOpenDriversGetFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to get dl addr: %";
}

std::string Urma0057UrmaOpenDriversGetFailure::GetId() const
{
    return "urma_0057";
}
} // namespace diag
