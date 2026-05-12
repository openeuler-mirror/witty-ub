#include "urma_0285_set_jfr_wr_ptjetty_ptseg_without_hdr_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0285SetJfrWrPtjettyPtsegWithoutHdrFailure> g_urma("urma_0285");

bool Urma0285SetJfrWrPtjettyPtsegWithoutHdrFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Recv sge[%] has NULL tseg"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0285SetJfrWrPtjettyPtsegWithoutHdrFailure::GetName() const
{
    return "set_jfr_wr_ptjetty_ptseg_without_hdr 接收失败";
}

std::string Urma0285SetJfrWrPtjettyPtsegWithoutHdrFailure::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `recv_wr->src.sge[i].tseg == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0285SetJfrWrPtjettyPtsegWithoutHdrFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0285SetJfrWrPtjettyPtsegWithoutHdrFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0285SetJfrWrPtjettyPtsegWithoutHdrFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Recv sge[%] has NULL tseg";
}

std::string Urma0285SetJfrWrPtjettyPtsegWithoutHdrFailure::GetId() const
{
    return "urma_0285";
}
} // namespace diag
