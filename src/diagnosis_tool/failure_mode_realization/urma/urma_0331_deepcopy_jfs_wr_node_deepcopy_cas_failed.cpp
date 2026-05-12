#include "urma_0331_deepcopy_jfs_wr_node_deepcopy_cas_failed.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0331DeepcopyJfsWrNodeDeepcopyCasFailed> g_urma("urma_0331");

bool Urma0331DeepcopyJfsWrNodeDeepcopyCasFailed::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Deepcopy cas failed"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0331DeepcopyJfsWrNodeDeepcopyCasFailed::GetName() const
{
    return "deepcopy_jfs_wr_node Deepcopy cas failed";
}

std::string Urma0331DeepcopyJfsWrNodeDeepcopyCasFailed::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `deepcopy_cas_wr(&new_wr->cas, &wr->cas)`";
}

RootCause Urma0331DeepcopyJfsWrNodeDeepcopyCasFailed::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0331DeepcopyJfsWrNodeDeepcopyCasFailed::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0331DeepcopyJfsWrNodeDeepcopyCasFailed::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Deepcopy cas failed";
}

std::string Urma0331DeepcopyJfsWrNodeDeepcopyCasFailed::GetId() const
{
    return "urma_0331";
}
} // namespace diag
