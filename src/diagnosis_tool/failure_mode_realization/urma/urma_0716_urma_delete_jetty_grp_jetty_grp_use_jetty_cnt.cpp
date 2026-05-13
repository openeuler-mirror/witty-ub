#include "urma_0716_urma_delete_jetty_grp_jetty_grp_use_jetty_cnt.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0716UrmaDeleteJettyGrpJettyGrpUseJettyCnt> g_urma("urma_0716");

bool Urma0716UrmaDeleteJettyGrpJettyGrpUseJettyCnt::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"jetty grp in use, jetty_cnt:%."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0716UrmaDeleteJettyGrpJettyGrpUseJettyCnt::GetName() const
{
    return "urma_delete_jetty_grp jetty grp in use, jetty_cnt:%.";
}

std::string Urma0716UrmaDeleteJettyGrpJettyGrpUseJettyCnt::GetRootCauseDesc() const
{
    return "源码在该错误分支记录 URMA_LOG_ERR，通常表示当前函数检测到参数、状态、资源或下游返回值异常；该路径返回 "
           "URMA_ENOPERM";
}

RootCause Urma0716UrmaDeleteJettyGrpJettyGrpUseJettyCnt::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0716UrmaDeleteJettyGrpJettyGrpUseJettyCnt::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0716UrmaDeleteJettyGrpJettyGrpUseJettyCnt::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：jetty grp in use, jetty_cnt:%.";
}

std::string Urma0716UrmaDeleteJettyGrpJettyGrpUseJettyCnt::GetId() const
{
    return "urma_0716";
}
} // namespace diag
