#include "urma_1070_resend_wr_from_node_send_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1070ResendWrFromNodeSendFailure> g_urma("urma_1070");

bool Urma1070ResendWrFromNodeSendFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Unsupported send opcode"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1070ResendWrFromNodeSendFailure::GetName() const
{
    return "resend_wr_from_node 发送失败";
}

std::string Urma1070ResendWrFromNodeSendFailure::GetRootCauseDesc() const
{
    return "源码在该错误分支记录 URMA_LOG_ERR，通常表示当前函数检测到参数、状态、资源或下游返回值异常；该路径返回 "
           "URMA_FAIL";
}

RootCause Urma1070ResendWrFromNodeSendFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1070ResendWrFromNodeSendFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1070ResendWrFromNodeSendFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Unsupported send opcode";
}

std::string Urma1070ResendWrFromNodeSendFailure::GetId() const
{
    return "urma_1070";
}
} // namespace diag
