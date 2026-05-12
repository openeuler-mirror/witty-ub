#include "urma_0637_urma_bind_jetty_async_not_allowed_bind_local_jetty.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0637UrmaBindJettyAsyncNotAllowedBindLocalJetty> g_urma("urma_0637");

bool Urma0637UrmaBindJettyAsyncNotAllowedBindLocalJetty::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {
        "Not allowed to bind local jetty:% of mode:% with remote jetty:% of mode:%."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0637UrmaBindJettyAsyncNotAllowedBindLocalJetty::GetName() const
{
    return "urma_bind_jetty_async Not allowed to bind local jetty:% of";
}

std::string Urma0637UrmaBindJettyAsyncNotAllowedBindLocalJetty::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "URMA_ENOPERM";
}

RootCause Urma0637UrmaBindJettyAsyncNotAllowedBindLocalJetty::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0637UrmaBindJettyAsyncNotAllowedBindLocalJetty::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0637UrmaBindJettyAsyncNotAllowedBindLocalJetty::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Not allowed to bind local jetty:% of mode:% with remote jetty:% "
           "of mode:%.";
}

std::string Urma0637UrmaBindJettyAsyncNotAllowedBindLocalJetty::GetId() const
{
    return "urma_0637";
}
} // namespace diag
