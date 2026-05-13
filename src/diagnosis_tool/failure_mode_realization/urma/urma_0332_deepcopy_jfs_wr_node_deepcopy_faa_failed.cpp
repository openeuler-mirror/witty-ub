#include "urma_0332_deepcopy_jfs_wr_node_deepcopy_faa_failed.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0332DeepcopyJfsWrNodeDeepcopyFaaFailed> g_urma("urma_0332");

bool Urma0332DeepcopyJfsWrNodeDeepcopyFaaFailed::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Deepcopy faa failed"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0332DeepcopyJfsWrNodeDeepcopyFaaFailed::GetName() const
{
    return "deepcopy_jfs_wr_node Deepcopy faa failed";
}

std::string Urma0332DeepcopyJfsWrNodeDeepcopyFaaFailed::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `deepcopy_faa_wr(&new_wr->faa, &wr->faa)`";
}

RootCause Urma0332DeepcopyJfsWrNodeDeepcopyFaaFailed::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0332DeepcopyJfsWrNodeDeepcopyFaaFailed::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0332DeepcopyJfsWrNodeDeepcopyFaaFailed::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Deepcopy faa failed";
}

std::string Urma0332DeepcopyJfsWrNodeDeepcopyFaaFailed::GetId() const
{
    return "urma_0332";
}
} // namespace diag
