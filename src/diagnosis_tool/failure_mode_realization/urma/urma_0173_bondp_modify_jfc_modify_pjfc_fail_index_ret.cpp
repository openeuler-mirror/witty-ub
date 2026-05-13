#include "urma_0173_bondp_modify_jfc_modify_pjfc_fail_index_ret.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0173BondpModifyJfcModifyPjfcFailIndexRet> g_urma("urma_0173");

bool Urma0173BondpModifyJfcModifyPjfcFailIndexRet::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"modify pjfc fail, index:%, ret:%"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0173BondpModifyJfcModifyPjfcFailIndexRet::GetName() const
{
    return "bondp_modify_jfc modify pjfc fail, index:%, ret:%";
}

std::string Urma0173BondpModifyJfcModifyPjfcFailIndexRet::GetRootCauseDesc() const
{
    return "源码在该错误分支记录 URMA_LOG_ERR，通常表示当前函数检测到参数、状态、资源或下游返回值异常；该路径返回 "
           "final_ret";
}

RootCause Urma0173BondpModifyJfcModifyPjfcFailIndexRet::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0173BondpModifyJfcModifyPjfcFailIndexRet::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0173BondpModifyJfcModifyPjfcFailIndexRet::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：modify pjfc fail, index:%, ret:%";
}

std::string Urma0173BondpModifyJfcModifyPjfcFailIndexRet::GetId() const
{
    return "urma_0173";
}
} // namespace diag
