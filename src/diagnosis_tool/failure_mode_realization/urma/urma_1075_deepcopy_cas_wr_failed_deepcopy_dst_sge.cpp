#include "urma_1075_deepcopy_cas_wr_failed_deepcopy_dst_sge.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1075DeepcopyCasWrFailedDeepcopyDstSge> g_urma("urma_1075");

bool Urma1075DeepcopyCasWrFailedDeepcopyDstSge::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to deepcopy dst sge"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1075DeepcopyCasWrFailedDeepcopyDstSge::GetName() const
{
    return "deepcopy_cas_wr Failed to deepcopy dst sge";
}

std::string Urma1075DeepcopyCasWrFailedDeepcopyDstSge::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `deepcopy_sge(new_wr_cas->dst, old_wr_cas->dst)`";
}

RootCause Urma1075DeepcopyCasWrFailedDeepcopyDstSge::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1075DeepcopyCasWrFailedDeepcopyDstSge::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1075DeepcopyCasWrFailedDeepcopyDstSge::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to deepcopy dst sge";
}

std::string Urma1075DeepcopyCasWrFailedDeepcopyDstSge::GetId() const
{
    return "urma_1075";
}
} // namespace diag
