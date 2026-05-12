#include "urma_0760_urma_free_jetty_resource_delete_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0760UrmaFreeJettyResourceDeleteFailure> g_urma("urma_0760");

bool Urma0760UrmaFreeJettyResourceDeleteFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to delete jetty because it has remote jetty, try unbind first"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0760UrmaFreeJettyResourceDeleteFailure::GetName() const
{
    return "urma_free_jetty 删除资源失败";
}

std::string Urma0760UrmaFreeJettyResourceDeleteFailure::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "URMA_ENOPERM";
}

RootCause Urma0760UrmaFreeJettyResourceDeleteFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0760UrmaFreeJettyResourceDeleteFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0760UrmaFreeJettyResourceDeleteFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to delete jetty because it has remote jetty, try unbind "
           "first";
}

std::string Urma0760UrmaFreeJettyResourceDeleteFailure::GetId() const
{
    return "urma_0760";
}
} // namespace diag
