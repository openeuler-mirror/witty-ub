#include "urma_1077_deepcopy_cas_wr_failed_copy_src_sge.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1077DeepcopyCasWrFailedCopySrcSge> g_urma("urma_1077");

bool Urma1077DeepcopyCasWrFailedCopySrcSge::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to copy src sge"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1077DeepcopyCasWrFailedCopySrcSge::GetName() const
{
    return "deepcopy_cas_wr Failed to copy src sge";
}

std::string Urma1077DeepcopyCasWrFailedCopySrcSge::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `deepcopy_sge(new_wr_cas->src, old_wr_cas->src)`；该路径返回 0";
}

RootCause Urma1077DeepcopyCasWrFailedCopySrcSge::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1077DeepcopyCasWrFailedCopySrcSge::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1077DeepcopyCasWrFailedCopySrcSge::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to copy src sge";
}

std::string Urma1077DeepcopyCasWrFailedCopySrcSge::GetId() const
{
    return "urma_1077";
}
} // namespace diag
