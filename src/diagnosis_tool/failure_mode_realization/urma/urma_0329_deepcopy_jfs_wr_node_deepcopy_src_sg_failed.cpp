#include "urma_0329_deepcopy_jfs_wr_node_deepcopy_src_sg_failed.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0329DeepcopyJfsWrNodeDeepcopySrcSgFailed> g_urma("urma_0329");

bool Urma0329DeepcopyJfsWrNodeDeepcopySrcSgFailed::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Deepcopy src sg failed"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0329DeepcopyJfsWrNodeDeepcopySrcSgFailed::GetName() const
{
    return "deepcopy_jfs_wr_node Deepcopy src sg failed";
}

std::string Urma0329DeepcopyJfsWrNodeDeepcopySrcSgFailed::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `deepcopy_sg(&new_wr->rw.src, &wr->rw.src, add_hdr)`";
}

RootCause Urma0329DeepcopyJfsWrNodeDeepcopySrcSgFailed::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0329DeepcopyJfsWrNodeDeepcopySrcSgFailed::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0329DeepcopyJfsWrNodeDeepcopySrcSgFailed::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Deepcopy src sg failed";
}

std::string Urma0329DeepcopyJfsWrNodeDeepcopySrcSgFailed::GetId() const
{
    return "urma_0329";
}
} // namespace diag
