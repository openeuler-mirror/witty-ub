#include "urma_0430_urma_cmd_delete_jfc_batch_invalid_param_dev_fd_0.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0430UrmaCmdDeleteJfcBatchInvalidParamDevFd0> g_urma("urma_0430");

bool Urma0430UrmaCmdDeleteJfcBatchInvalidParamDevFd0::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0430UrmaCmdDeleteJfcBatchInvalidParamDevFd0::GetName() const
{
    return "urma_cmd_delete_jfc_batch 参数非法（dev_fd < 0）";
}

std::string Urma0430UrmaCmdDeleteJfcBatchInvalidParamDevFd0::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `dev_fd < 0`；该路径返回 URMA_EINVAL";
}

RootCause Urma0430UrmaCmdDeleteJfcBatchInvalidParamDevFd0::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0430UrmaCmdDeleteJfcBatchInvalidParamDevFd0::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0430UrmaCmdDeleteJfcBatchInvalidParamDevFd0::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter";
}

std::string Urma0430UrmaCmdDeleteJfcBatchInvalidParamDevFd0::GetId() const
{
    return "urma_0430";
}
} // namespace diag
