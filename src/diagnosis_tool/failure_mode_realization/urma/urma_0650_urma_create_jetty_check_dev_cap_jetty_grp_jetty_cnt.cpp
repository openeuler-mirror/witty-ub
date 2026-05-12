#include "urma_0650_urma_create_jetty_check_dev_cap_jetty_grp_jetty_cnt.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0650UrmaCreateJettyCheckDevCapJettyGrpJettyCnt> g_urma("urma_0650");

bool Urma0650UrmaCreateJettyCheckDevCapJettyGrpJettyCnt::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"jetty_grp jetty cnt:%, max_jetty in grp:%"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0650UrmaCreateJettyCheckDevCapJettyGrpJettyCnt::GetName() const
{
    return "urma_create_jetty_check_dev_cap jetty_grp jetty cnt:%, max_jetty in";
}

std::string Urma0650UrmaCreateJettyCheckDevCapJettyGrpJettyCnt::GetRootCauseDesc() const
{
    return "源码在该错误分支记录 URMA_LOG_ERR，通常表示当前函数检测到参数、状态、资源或下游返回值异常；该路径返回 -1";
}

RootCause Urma0650UrmaCreateJettyCheckDevCapJettyGrpJettyCnt::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0650UrmaCreateJettyCheckDevCapJettyGrpJettyCnt::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0650UrmaCreateJettyCheckDevCapJettyGrpJettyCnt::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：jetty_grp jetty cnt:%, max_jetty in grp:%";
}

std::string Urma0650UrmaCreateJettyCheckDevCapJettyGrpJettyCnt::GetId() const
{
    return "urma_0650";
}
} // namespace diag
