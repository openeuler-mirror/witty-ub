#include "urma_0177_bondp_modify_jfs_modify_pjfs_fail_index_ret.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0177BondpModifyJfsModifyPjfsFailIndexRet> g_urma("urma_0177");

bool Urma0177BondpModifyJfsModifyPjfsFailIndexRet::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"modify pjfs fail, index:%, ret:%"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0177BondpModifyJfsModifyPjfsFailIndexRet::GetName() const
{
    return "bondp_modify_jfs modify pjfs fail, index:%, ret:%";
}

std::string Urma0177BondpModifyJfsModifyPjfsFailIndexRet::GetRootCauseDesc() const
{
    return "源码在该错误分支记录 URMA_LOG_ERR，通常表示当前函数检测到参数、状态、资源或下游返回值异常；该路径返回 "
           "final_ret";
}

RootCause Urma0177BondpModifyJfsModifyPjfsFailIndexRet::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0177BondpModifyJfsModifyPjfsFailIndexRet::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0177BondpModifyJfsModifyPjfsFailIndexRet::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：modify pjfs fail, index:%, ret:%";
}

std::string Urma0177BondpModifyJfsModifyPjfsFailIndexRet::GetId() const
{
    return "urma_0177";
}
} // namespace diag
