#include "urma_1080_deepcopy_faa_wr_failed_deepcopy_dst_sge.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1080DeepcopyFaaWrFailedDeepcopyDstSge> g_urma("urma_1080");

bool Urma1080DeepcopyFaaWrFailedDeepcopyDstSge::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to deepcopy dst sge"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1080DeepcopyFaaWrFailedDeepcopyDstSge::GetName() const
{
    return "deepcopy_faa_wr Failed to deepcopy dst sge";
}

std::string Urma1080DeepcopyFaaWrFailedDeepcopyDstSge::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `deepcopy_sge(new_wr_faa->dst, old_wr_faa->dst)`";
}

RootCause Urma1080DeepcopyFaaWrFailedDeepcopyDstSge::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1080DeepcopyFaaWrFailedDeepcopyDstSge::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1080DeepcopyFaaWrFailedDeepcopyDstSge::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to deepcopy dst sge";
}

std::string Urma1080DeepcopyFaaWrFailedDeepcopyDstSge::GetId() const
{
    return "urma_1080";
}
} // namespace diag
