#include "urma_0893_set_fd_noblock_ret.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0893SetFdNoblockRet> g_urma("urma_0893");

bool Urma0893SetFdNoblockRet::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"ret: %"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0893SetFdNoblockRet::GetName() const
{
    return "set_fd_noblock ret: %";
}

std::string Urma0893SetFdNoblockRet::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `ret != 0`；该路径返回 ret";
}

RootCause Urma0893SetFdNoblockRet::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0893SetFdNoblockRet::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0893SetFdNoblockRet::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：ret: %";
}

std::string Urma0893SetFdNoblockRet::GetId() const
{
    return "urma_0893";
}
} // namespace diag
