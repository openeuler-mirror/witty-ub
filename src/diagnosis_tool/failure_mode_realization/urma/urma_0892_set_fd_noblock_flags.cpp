#include "urma_0892_set_fd_noblock_flags.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0892SetFdNoblockFlags> g_urma("urma_0892");

bool Urma0892SetFdNoblockFlags::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"flags: %"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0892SetFdNoblockFlags::GetName() const
{
    return "set_fd_noblock flags: %";
}

std::string Urma0892SetFdNoblockFlags::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `flags == -1`；该路径返回 -1";
}

RootCause Urma0892SetFdNoblockFlags::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0892SetFdNoblockFlags::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0892SetFdNoblockFlags::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：flags: %";
}

std::string Urma0892SetFdNoblockFlags::GetId() const
{
    return "urma_0892";
}
} // namespace diag
