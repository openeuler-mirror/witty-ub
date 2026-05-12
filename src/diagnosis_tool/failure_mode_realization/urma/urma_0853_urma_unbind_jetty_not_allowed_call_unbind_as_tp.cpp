#include "urma_0853_urma_unbind_jetty_not_allowed_call_unbind_as_tp.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0853UrmaUnbindJettyNotAllowedCallUnbindAsTp> g_urma("urma_0853");

bool Urma0853UrmaUnbindJettyNotAllowedCallUnbindAsTp::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Not allowed to call unbind as the tp mode of jetty :% is:%."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0853UrmaUnbindJettyNotAllowedCallUnbindAsTp::GetName() const
{
    return "urma_unbind_jetty Not allowed to call unbind as the tp";
}

std::string Urma0853UrmaUnbindJettyNotAllowedCallUnbindAsTp::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "URMA_ENOPERM";
}

RootCause Urma0853UrmaUnbindJettyNotAllowedCallUnbindAsTp::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0853UrmaUnbindJettyNotAllowedCallUnbindAsTp::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0853UrmaUnbindJettyNotAllowedCallUnbindAsTp::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Not allowed to call unbind as the tp mode of jetty :% is:%.";
}

std::string Urma0853UrmaUnbindJettyNotAllowedCallUnbindAsTp::GetId() const
{
    return "urma_0853";
}
} // namespace diag
