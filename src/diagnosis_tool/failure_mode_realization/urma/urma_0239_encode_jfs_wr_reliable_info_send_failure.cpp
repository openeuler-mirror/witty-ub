#include "urma_0239_encode_jfs_wr_reliable_info_send_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0239EncodeJfsWrReliableInfoSendFailure> g_urma("urma_0239");

bool Urma0239EncodeJfsWrReliableInfoSendFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Unsupported send opcode"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0239EncodeJfsWrReliableInfoSendFailure::GetName() const
{
    return "encode_jfs_wr_reliable_info 发送失败";
}

std::string Urma0239EncodeJfsWrReliableInfoSendFailure::GetRootCauseDesc() const
{
    return "源码在该错误分支记录 URMA_LOG_ERR，通常表示当前函数检测到参数、状态、资源或下游返回值异常；该路径返回 "
           "URMA_EINVAL";
}

RootCause Urma0239EncodeJfsWrReliableInfoSendFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0239EncodeJfsWrReliableInfoSendFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0239EncodeJfsWrReliableInfoSendFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Unsupported send opcode";
}

std::string Urma0239EncodeJfsWrReliableInfoSendFailure::GetId() const
{
    return "urma_0239";
}
} // namespace diag
