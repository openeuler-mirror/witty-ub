#include "urma_1084_deepcopy_sg_invalid_num_sge.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1084DeepcopySgInvalidNumSge> g_urma("urma_1084");

bool Urma1084DeepcopySgInvalidNumSge::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid num_sge: %"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1084DeepcopySgInvalidNumSge::GetName() const
{
    return "deepcopy_sg Invalid num_sge: %";
}

std::string Urma1084DeepcopySgInvalidNumSge::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `num_sge < 0`；该路径返回 -1";
}

RootCause Urma1084DeepcopySgInvalidNumSge::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1084DeepcopySgInvalidNumSge::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1084DeepcopySgInvalidNumSge::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid num_sge: %";
}

std::string Urma1084DeepcopySgInvalidNumSge::GetId() const
{
    return "urma_1084";
}
} // namespace diag
