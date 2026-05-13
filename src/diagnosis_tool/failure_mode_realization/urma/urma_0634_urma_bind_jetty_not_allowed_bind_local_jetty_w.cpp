#include "urma_0634_urma_bind_jetty_not_allowed_bind_local_jetty_w.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0634UrmaBindJettyNotAllowedBindLocalJettyW> g_urma("urma_0634");

bool Urma0634UrmaBindJettyNotAllowedBindLocalJettyW::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Not allowed to bind local jetty:%, with remote jetty:%."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0634UrmaBindJettyNotAllowedBindLocalJettyW::GetName() const
{
    return "urma_bind_jetty Not allowed to bind local jetty:%, w";
}

std::string Urma0634UrmaBindJettyNotAllowedBindLocalJettyW::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "URMA_ENOPERM";
}

RootCause Urma0634UrmaBindJettyNotAllowedBindLocalJettyW::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0634UrmaBindJettyNotAllowedBindLocalJettyW::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0634UrmaBindJettyNotAllowedBindLocalJettyW::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Not allowed to bind local jetty:%, with remote jetty:%.";
}

std::string Urma0634UrmaBindJettyNotAllowedBindLocalJettyW::GetId() const
{
    return "urma_0634";
}
} // namespace diag
