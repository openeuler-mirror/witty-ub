#include "urma_0322_deepcopy_jfr_wr_node_deepcopy_sg_failed.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0322DeepcopyJfrWrNodeDeepcopySgFailed> g_urma("urma_0322");

bool Urma0322DeepcopyJfrWrNodeDeepcopySgFailed::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Deepcopy sg failed"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0322DeepcopyJfrWrNodeDeepcopySgFailed::GetName() const
{
    return "deepcopy_jfr_wr_node Deepcopy sg failed";
}

std::string Urma0322DeepcopyJfrWrNodeDeepcopySgFailed::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `deepcopy_sg(&new_wr->src, &wr->src, add_hdr)`；该路径返回 NULL";
}

RootCause Urma0322DeepcopyJfrWrNodeDeepcopySgFailed::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0322DeepcopyJfrWrNodeDeepcopySgFailed::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0322DeepcopyJfrWrNodeDeepcopySgFailed::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Deepcopy sg failed";
}

std::string Urma0322DeepcopyJfrWrNodeDeepcopySgFailed::GetId() const
{
    return "urma_0322";
}
} // namespace diag
