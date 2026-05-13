#include "urma_1082_deepcopy_faa_wr_failed_deepcopy_src_sge.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1082DeepcopyFaaWrFailedDeepcopySrcSge> g_urma("urma_1082");

bool Urma1082DeepcopyFaaWrFailedDeepcopySrcSge::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to deepcopy src sge"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1082DeepcopyFaaWrFailedDeepcopySrcSge::GetName() const
{
    return "deepcopy_faa_wr Failed to deepcopy src sge";
}

std::string Urma1082DeepcopyFaaWrFailedDeepcopySrcSge::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `deepcopy_sge(new_wr_faa->src, old_wr_faa->src)`；该路径返回 0";
}

RootCause Urma1082DeepcopyFaaWrFailedDeepcopySrcSge::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1082DeepcopyFaaWrFailedDeepcopySrcSge::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1082DeepcopyFaaWrFailedDeepcopySrcSge::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to deepcopy src sge";
}

std::string Urma1082DeepcopyFaaWrFailedDeepcopySrcSge::GetId() const
{
    return "urma_1082";
}
} // namespace diag
