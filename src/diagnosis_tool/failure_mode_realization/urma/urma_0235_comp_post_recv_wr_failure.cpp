#include "urma_0235_comp_post_recv_wr_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0235CompPostRecvWrFailure> g_urma("urma_0235");

bool Urma0235CompPostRecvWrFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid post jfr wr type: %"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0235CompPostRecvWrFailure::GetName() const
{
    return "comp_post_recv 提交WR失败";
}

std::string Urma0235CompPostRecvWrFailure::GetRootCauseDesc() const
{
    return "源码在该错误分支记录 URMA_LOG_ERR，通常表示当前函数检测到参数、状态、资源或下游返回值异常；该路径返回 ret";
}

RootCause Urma0235CompPostRecvWrFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0235CompPostRecvWrFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0235CompPostRecvWrFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid post jfr wr type: %";
}

std::string Urma0235CompPostRecvWrFailure::GetId() const
{
    return "urma_0235";
}
} // namespace diag
