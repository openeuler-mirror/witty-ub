#include "urma_0021_bondp_init_failed_create_global_context.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0021BondpInitFailedCreateGlobalContext> g_urma("urma_0021");

bool Urma0021BondpInitFailedCreateGlobalContext::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to create global context."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0021BondpInitFailedCreateGlobalContext::GetName() const
{
    return "bondp_init Failed to create global context.";
}

std::string Urma0021BondpInitFailedCreateGlobalContext::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "URMA_FAIL";
}

RootCause Urma0021BondpInitFailedCreateGlobalContext::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0021BondpInitFailedCreateGlobalContext::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0021BondpInitFailedCreateGlobalContext::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to create global context.";
}

std::string Urma0021BondpInitFailedCreateGlobalContext::GetId() const
{
    return "urma_0021";
}
} // namespace diag
