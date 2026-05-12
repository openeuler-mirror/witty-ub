#include "urma_0665_urma_create_jetty_grp_create_jetty_grp_failed.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0665UrmaCreateJettyGrpCreateJettyGrpFailed> g_urma("urma_0665");

bool Urma0665UrmaCreateJettyGrpCreateJettyGrpFailed::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"create_jetty_grp failed."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0665UrmaCreateJettyGrpCreateJettyGrpFailed::GetName() const
{
    return "urma_create_jetty_grp create_jetty_grp failed.";
}

std::string Urma0665UrmaCreateJettyGrpCreateJettyGrpFailed::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "NULL";
}

RootCause Urma0665UrmaCreateJettyGrpCreateJettyGrpFailed::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0665UrmaCreateJettyGrpCreateJettyGrpFailed::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0665UrmaCreateJettyGrpCreateJettyGrpFailed::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：create_jetty_grp failed.";
}

std::string Urma0665UrmaCreateJettyGrpCreateJettyGrpFailed::GetId() const
{
    return "urma_0665";
}
} // namespace diag
