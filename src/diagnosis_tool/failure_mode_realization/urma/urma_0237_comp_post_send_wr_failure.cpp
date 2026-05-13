#include "urma_0237_comp_post_send_wr_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0237CompPostSendWrFailure> g_urma("urma_0237");

bool Urma0237CompPostSendWrFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid post jfs wr type: %"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0237CompPostSendWrFailure::GetName() const
{
    return "comp_post_send 提交WR失败";
}

std::string Urma0237CompPostSendWrFailure::GetRootCauseDesc() const
{
    return "源码在该错误分支记录 URMA_LOG_ERR，通常表示当前函数检测到参数、状态、资源或下游返回值异常；该路径返回 ret";
}

RootCause Urma0237CompPostSendWrFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0237CompPostSendWrFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0237CompPostSendWrFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid post jfs wr type: %";
}

std::string Urma0237CompPostSendWrFailure::GetId() const
{
    return "urma_0237";
}
} // namespace diag
