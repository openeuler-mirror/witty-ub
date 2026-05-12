#include "urma_0703_urma_delete_jetty_resource_delete_failure_jetty_urma_jetty_opt.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0703UrmaDeleteJettyResourceDeleteFailureJettyUrmaJettyOpt> g_urma("urma_0703");

bool Urma0703UrmaDeleteJettyResourceDeleteFailureJettyUrmaJettyOpt::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"jetty still deactived, can not delete."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0703UrmaDeleteJettyResourceDeleteFailureJettyUrmaJettyOpt::GetName() const
{
    return "urma_delete_jetty 删除资源失败（jetty->urma_jetty_opt.is_actived == false）";
}

std::string Urma0703UrmaDeleteJettyResourceDeleteFailureJettyUrmaJettyOpt::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "URMA_EINVAL";
}

RootCause Urma0703UrmaDeleteJettyResourceDeleteFailureJettyUrmaJettyOpt::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0703UrmaDeleteJettyResourceDeleteFailureJettyUrmaJettyOpt::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0703UrmaDeleteJettyResourceDeleteFailureJettyUrmaJettyOpt::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：jetty still deactived, can not delete.";
}

std::string Urma0703UrmaDeleteJettyResourceDeleteFailureJettyUrmaJettyOpt::GetId() const
{
    return "urma_0703";
}
} // namespace diag
