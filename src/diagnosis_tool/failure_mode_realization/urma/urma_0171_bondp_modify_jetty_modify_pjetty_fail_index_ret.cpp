#include "urma_0171_bondp_modify_jetty_modify_pjetty_fail_index_ret.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0171BondpModifyJettyModifyPjettyFailIndexRet> g_urma("urma_0171");

bool Urma0171BondpModifyJettyModifyPjettyFailIndexRet::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"modify pjetty fail, index:%, ret:%"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0171BondpModifyJettyModifyPjettyFailIndexRet::GetName() const
{
    return "bondp_modify_jetty modify pjetty fail, index:%, ret:%";
}

std::string Urma0171BondpModifyJettyModifyPjettyFailIndexRet::GetRootCauseDesc() const
{
    return "源码在该错误分支记录 URMA_LOG_ERR，通常表示当前函数检测到参数、状态、资源或下游返回值异常；该路径返回 "
           "final_ret";
}

RootCause Urma0171BondpModifyJettyModifyPjettyFailIndexRet::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0171BondpModifyJettyModifyPjettyFailIndexRet::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0171BondpModifyJettyModifyPjettyFailIndexRet::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：modify pjetty fail, index:%, ret:%";
}

std::string Urma0171BondpModifyJettyModifyPjettyFailIndexRet::GetId() const
{
    return "urma_0171";
}
} // namespace diag
