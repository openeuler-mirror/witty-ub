#include "urma_0265_restore_cr_local_id_query_attr_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0265RestoreCrLocalIdQueryAttrFailure> g_urma("urma_0265");

bool Urma0265RestoreCrLocalIdQueryAttrFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to get vjetty.id of local_id: %, ret: %"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0265RestoreCrLocalIdQueryAttrFailure::GetName() const
{
    return "restore_cr_local_id 查询属性失败";
}

std::string Urma0265RestoreCrLocalIdQueryAttrFailure::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `ret != 0`；该路径返回 -1";
}

RootCause Urma0265RestoreCrLocalIdQueryAttrFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0265RestoreCrLocalIdQueryAttrFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0265RestoreCrLocalIdQueryAttrFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to get vjetty.id of local_id: %, ret: %";
}

std::string Urma0265RestoreCrLocalIdQueryAttrFailure::GetId() const
{
    return "urma_0265";
}
} // namespace diag
