#include "urma_0201_import_pjetty_primary_eid_primary_dev_has_null_rjetty_eid.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0201ImportPjettyPrimaryEidPrimaryDevHasNullRjettyEid> g_urma("urma_0201");

bool Urma0201ImportPjettyPrimaryEidPrimaryDevHasNullRjettyEid::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Primary dev has NULL rjetty eid"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0201ImportPjettyPrimaryEidPrimaryDevHasNullRjettyEid::GetName() const
{
    return "import_pjetty_for_primary_eid Primary dev has NULL rjetty eid";
}

std::string Urma0201ImportPjettyPrimaryEidPrimaryDevHasNullRjettyEid::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `is_empty_eid(&rvjetty_info->slave_id[i].eid)`；该路径返回 -1";
}

RootCause Urma0201ImportPjettyPrimaryEidPrimaryDevHasNullRjettyEid::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0201ImportPjettyPrimaryEidPrimaryDevHasNullRjettyEid::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0201ImportPjettyPrimaryEidPrimaryDevHasNullRjettyEid::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Primary dev has NULL rjetty eid";
}

std::string Urma0201ImportPjettyPrimaryEidPrimaryDevHasNullRjettyEid::GetId() const
{
    return "urma_0201";
}
} // namespace diag
