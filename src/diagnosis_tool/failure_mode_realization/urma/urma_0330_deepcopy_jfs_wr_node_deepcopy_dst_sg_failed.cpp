#include "urma_0330_deepcopy_jfs_wr_node_deepcopy_dst_sg_failed.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0330DeepcopyJfsWrNodeDeepcopyDstSgFailed> g_urma("urma_0330");

bool Urma0330DeepcopyJfsWrNodeDeepcopyDstSgFailed::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Deepcopy dst sg failed"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0330DeepcopyJfsWrNodeDeepcopyDstSgFailed::GetName() const
{
    return "deepcopy_jfs_wr_node Deepcopy dst sg failed";
}

std::string Urma0330DeepcopyJfsWrNodeDeepcopyDstSgFailed::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `deepcopy_sg(&new_wr->rw.dst, &wr->rw.dst, add_hdr)`";
}

RootCause Urma0330DeepcopyJfsWrNodeDeepcopyDstSgFailed::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0330DeepcopyJfsWrNodeDeepcopyDstSgFailed::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0330DeepcopyJfsWrNodeDeepcopyDstSgFailed::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Deepcopy dst sg failed";
}

std::string Urma0330DeepcopyJfsWrNodeDeepcopyDstSgFailed::GetId() const
{
    return "urma_0330";
}
} // namespace diag
