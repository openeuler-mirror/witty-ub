#include "urma_0823_urma_set_jetty_opt_resource_delete_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0823UrmaSetJettyOptResourceDeleteFailure> g_urma("urma_0823");

bool Urma0823UrmaSetJettyOptResourceDeleteFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to exec urma_delete_jetty_to_jetty_grp."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0823UrmaSetJettyOptResourceDeleteFailure::GetName() const
{
    return "urma_set_jetty_opt 删除资源失败";
}

std::string Urma0823UrmaSetJettyOptResourceDeleteFailure::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "URMA_FAIL";
}

RootCause Urma0823UrmaSetJettyOptResourceDeleteFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0823UrmaSetJettyOptResourceDeleteFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0823UrmaSetJettyOptResourceDeleteFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to exec urma_delete_jetty_to_jetty_grp.";
}

std::string Urma0823UrmaSetJettyOptResourceDeleteFailure::GetId() const
{
    return "urma_0823";
}
} // namespace diag
