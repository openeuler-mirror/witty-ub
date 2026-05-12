#include "urma_0638_urma_bind_jetty_async_not_allowed_bind_local_jetty_w.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0638UrmaBindJettyAsyncNotAllowedBindLocalJettyW> g_urma("urma_0638");

bool Urma0638UrmaBindJettyAsyncNotAllowedBindLocalJettyW::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Not allowed to bind local jetty:%, with remote jetty:%."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0638UrmaBindJettyAsyncNotAllowedBindLocalJettyW::GetName() const
{
    return "urma_bind_jetty_async Not allowed to bind local jetty:%, w";
}

std::string Urma0638UrmaBindJettyAsyncNotAllowedBindLocalJettyW::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "URMA_ENOPERM";
}

RootCause Urma0638UrmaBindJettyAsyncNotAllowedBindLocalJettyW::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0638UrmaBindJettyAsyncNotAllowedBindLocalJettyW::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0638UrmaBindJettyAsyncNotAllowedBindLocalJettyW::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Not allowed to bind local jetty:%, with remote jetty:%.";
}

std::string Urma0638UrmaBindJettyAsyncNotAllowedBindLocalJettyW::GetId() const
{
    return "urma_0638";
}
} // namespace diag
