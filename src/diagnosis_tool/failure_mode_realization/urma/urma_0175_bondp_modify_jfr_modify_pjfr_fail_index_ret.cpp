#include "urma_0175_bondp_modify_jfr_modify_pjfr_fail_index_ret.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0175BondpModifyJfrModifyPjfrFailIndexRet> g_urma("urma_0175");

bool Urma0175BondpModifyJfrModifyPjfrFailIndexRet::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"modify pjfr fail, index:%, ret:%"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0175BondpModifyJfrModifyPjfrFailIndexRet::GetName() const
{
    return "bondp_modify_jfr modify pjfr fail, index:%, ret:%";
}

std::string Urma0175BondpModifyJfrModifyPjfrFailIndexRet::GetRootCauseDesc() const
{
    return "源码在该错误分支记录 URMA_LOG_ERR，通常表示当前函数检测到参数、状态、资源或下游返回值异常；该路径返回 "
           "final_ret";
}

RootCause Urma0175BondpModifyJfrModifyPjfrFailIndexRet::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0175BondpModifyJfrModifyPjfrFailIndexRet::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0175BondpModifyJfrModifyPjfrFailIndexRet::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：modify pjfr fail, index:%, ret:%";
}

std::string Urma0175BondpModifyJfrModifyPjfrFailIndexRet::GetId() const
{
    return "urma_0175";
}
} // namespace diag
