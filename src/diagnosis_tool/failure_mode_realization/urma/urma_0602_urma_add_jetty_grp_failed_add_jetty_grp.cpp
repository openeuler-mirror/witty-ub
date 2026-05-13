#include "urma_0602_urma_add_jetty_grp_failed_add_jetty_grp.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0602UrmaAddJettyGrpFailedAddJettyGrp> g_urma("urma_0602");

bool Urma0602UrmaAddJettyGrpFailedAddJettyGrp::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"failed to add jetty to jetty_grp."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0602UrmaAddJettyGrpFailedAddJettyGrp::GetName() const
{
    return "urma_add_jetty_to_jetty_grp failed to add jetty to jetty_grp.";
}

std::string Urma0602UrmaAddJettyGrpFailedAddJettyGrp::GetRootCauseDesc() const
{
    return "源码在该错误分支记录 URMA_LOG_ERR，通常表示当前函数检测到参数、状态、资源或下游返回值异常；该路径返回 -1";
}

RootCause Urma0602UrmaAddJettyGrpFailedAddJettyGrp::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0602UrmaAddJettyGrpFailedAddJettyGrp::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0602UrmaAddJettyGrpFailedAddJettyGrp::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：failed to add jetty to jetty_grp.";
}

std::string Urma0602UrmaAddJettyGrpFailedAddJettyGrp::GetId() const
{
    return "urma_0602";
}
} // namespace diag
