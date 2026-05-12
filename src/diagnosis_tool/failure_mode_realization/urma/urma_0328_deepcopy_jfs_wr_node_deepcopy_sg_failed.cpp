#include "urma_0328_deepcopy_jfs_wr_node_deepcopy_sg_failed.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0328DeepcopyJfsWrNodeDeepcopySgFailed> g_urma("urma_0328");

bool Urma0328DeepcopyJfsWrNodeDeepcopySgFailed::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Deepcopy sg failed"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0328DeepcopyJfsWrNodeDeepcopySgFailed::GetName() const
{
    return "deepcopy_jfs_wr_node Deepcopy sg failed";
}

std::string Urma0328DeepcopyJfsWrNodeDeepcopySgFailed::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `deepcopy_sg(&new_wr->send.src, &wr->send.src, add_hdr)`";
}

RootCause Urma0328DeepcopyJfsWrNodeDeepcopySgFailed::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0328DeepcopyJfsWrNodeDeepcopySgFailed::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0328DeepcopyJfsWrNodeDeepcopySgFailed::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Deepcopy sg failed";
}

std::string Urma0328DeepcopyJfsWrNodeDeepcopySgFailed::GetId() const
{
    return "urma_0328";
}
} // namespace diag
