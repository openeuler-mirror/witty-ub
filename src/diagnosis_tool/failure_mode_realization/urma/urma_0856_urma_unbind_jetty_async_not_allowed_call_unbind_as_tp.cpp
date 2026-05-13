#include "urma_0856_urma_unbind_jetty_async_not_allowed_call_unbind_as_tp.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0856UrmaUnbindJettyAsyncNotAllowedCallUnbindAsTp> g_urma("urma_0856");

bool Urma0856UrmaUnbindJettyAsyncNotAllowedCallUnbindAsTp::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Not allowed to call unbind as the tp mode of jetty :% is:%."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0856UrmaUnbindJettyAsyncNotAllowedCallUnbindAsTp::GetName() const
{
    return "urma_unbind_jetty_async Not allowed to call unbind as the tp";
}

std::string Urma0856UrmaUnbindJettyAsyncNotAllowedCallUnbindAsTp::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "URMA_ENOPERM";
}

RootCause Urma0856UrmaUnbindJettyAsyncNotAllowedCallUnbindAsTp::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0856UrmaUnbindJettyAsyncNotAllowedCallUnbindAsTp::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0856UrmaUnbindJettyAsyncNotAllowedCallUnbindAsTp::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Not allowed to call unbind as the tp mode of jetty :% is:%.";
}

std::string Urma0856UrmaUnbindJettyAsyncNotAllowedCallUnbindAsTp::GetId() const
{
    return "urma_0856";
}
} // namespace diag
